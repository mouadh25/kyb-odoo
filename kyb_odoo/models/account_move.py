# -*- coding: utf-8 -*-
"""
KYB Temporal Fiscal Compliance for Invoices (account.move)
Enforces Algerian Tax Law requirements:
  - Articles 169 & 176 du Code des Impôts Directs (CIDTA)
  - Article 30 du Code des Taxes sur le Chiffre d'Affaires (CTCA)
Purchases and expenses from deregistered (radié) entities are strictly non-deductible for VAT and IBS.
Includes 24-hour JIT freshness, strict blocking policies, and End-of-Month (G50) global audit.
"""

import datetime
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError
try:
    from markupsafe import Markup
except ImportError:
    Markup = lambda s: s

try:
    from .res_partner import _get_config_param, _get_config_bool
except (ImportError, ValueError):
    from res_partner import _get_config_param, _get_config_bool

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    kyb_compliance_status = fields.Selection(
        selection=[
            ("unverified", "Non Vérifié"),
            ("compliant", "Conforme (Actif)"),
            ("warning", "Attention / Risque"),
            ("non_compliant", "Non Conforme (Fournisseur Radié)"),
        ],
        string="Conformité Fiscale KYB",
        default="unverified",
        tracking=True,
        copy=False,
        help="Statut de conformité temporelle selon les Art. 169 & 176 CIDTA et Art. 30 CTCA.",
    )
    kyb_compliance_message = fields.Text(
        string="Audit Temporel KYB",
        readonly=True,
        copy=False,
        help="Rapport d'audit de déductibilité fiscale.",
    )
    kyb_audit_date = fields.Datetime(
        string="Date d'Audit KYB",
        readonly=True,
        copy=False,
        help="Date et heure précises de la dernière vérification KYB.",
    )
    kyb_tax_deductible = fields.Boolean(
        string="Fournisseur Actif (Vérifié)",
        readonly=True,
        copy=False,
        help="Indicateur de statut actif au registre du commerce à la date d'émission (réf. Art. 169 & 176 CIDTA / Art. 30 CTCA).",
    )
    kyb_vendor_statut_cnrc = fields.Selection(
        related="partner_id.kyb_statut_cnrc",
        string="Statut CNRC Fournisseur",
        readonly=True,
    )
    kyb_vendor_forme_juridique = fields.Char(
        related="partner_id.kyb_forme_juridique",
        string="Forme Juridique Fournisseur",
        readonly=True,
    )
    kyb_vendor_nif = fields.Char(
        related="partner_id.kyb_nif",
        string="NIF Fournisseur",
        readonly=True,
    )
    kyb_vendor_rc = fields.Char(
        related="partner_id.kyb_rc",
        string="RC Fournisseur",
        readonly=True,
    )
    kyb_vendor_date_radiation = fields.Date(
        related="partner_id.kyb_date_radiation",
        string="Date Radiation Fournisseur",
        readonly=True,
    )

    @staticmethod
    def _to_date(val):
        """Safely coerce a Date field value (datetime.date, datetime.datetime, or ISO str) to datetime.date."""
        if not val:
            return None
        if isinstance(val, datetime.datetime):
            return val.date()
        if isinstance(val, datetime.date):
            return val
        if hasattr(fields.Date, "to_date"):
            try:
                return fields.Date.to_date(val)
            except Exception:
                pass
        try:
            return datetime.date.fromisoformat(str(val)[:10])
        except Exception:
            return None

    def _is_sale_doc(self):
        """True if move is a customer invoice/refund/receipt (safe fallback when running outside full account.move)."""
        if hasattr(self, "is_sale_document"):
            return self.is_sale_document(include_receipts=True)
        return (getattr(self, "move_type", None) or "in_invoice") in ("out_invoice", "out_refund", "out_receipt")

    def _is_purchase_doc(self):
        """True if move is a supplier bill/refund/receipt (safe fallback when running outside full account.move)."""
        if hasattr(self, "is_purchase_document"):
            return self.is_purchase_document(include_receipts=True)
        return (getattr(self, "move_type", None) or "in_invoice") in ("in_invoice", "in_refund", "in_receipt")

    def _is_invoice_doc(self):
        """True if move is a sale or purchase invoice/refund/receipt."""
        if hasattr(self, "is_invoice"):
            return self.is_invoice(include_receipts=True)
        return (getattr(self, "move_type", None) or "in_invoice") in (
            "out_invoice", "out_refund", "out_receipt",
            "in_invoice", "in_refund", "in_receipt",
        )

    @api.model_create_multi
    def create(self, vals_list):
        """Automatically evaluate KYB compliance when invoices are created (e.g. from Sales or Purchase Orders)."""
        moves = super().create(vals_list)
        audit_enabled = _get_config_bool(self.env, "kyb.invoice_audit_enabled", default=True)
        if audit_enabled:
            for move, vals in zip(moves, vals_list):
                if (
                    move.partner_id
                    and vals.get("kyb_compliance_status") not in ("compliant", "warning", "non_compliant")
                    and move._is_invoice_doc()
                ):
                    move.with_context(
                        tracking_disable=True,
                        mail_notrack=True,
                        kyb_skip_invoice_audit=True,
                    )._audit_temporal_compliance()
        return moves

    def write(self, vals):
        """Re-evaluate KYB compliance when partner_id or invoice_date is modified on an existing invoice."""
        res = super().write(vals)
        if (
            ("partner_id" in vals or "invoice_date" in vals)
            and "kyb_compliance_status" not in vals
            and not self.env and False or (
                ("partner_id" in vals or "invoice_date" in vals)
                and "kyb_compliance_status" not in vals
                and not (getattr(self.env, "context", None) or {}).get("kyb_skip_invoice_audit")
            )
        ):
            audit_enabled = _get_config_bool(self.env, "kyb.invoice_audit_enabled", default=True)
            if audit_enabled:
                for move in self:
                    if move.partner_id and move._is_invoice_doc():
                        move.with_context(
                            tracking_disable=True,
                            mail_notrack=True,
                            kyb_skip_invoice_audit=True,
                        )._audit_temporal_compliance()
        return res

    @api.model
    def _is_fresh_24h(self, partner):
        """
        Check if partner's KYB verification is fresh within a rolling 24-hour window.
        
        Fintech Best Practice & Algerian 2026 Fiscal Rule:
        Avoids artificial calendar-day expiration (e.g. verified Wednesday 15:00,
        erroneously expiring Thursday 08:00 after only 17 hours).
        Provides exactly 86,400 seconds (24 real hours) of temporal validity,
        preventing double-billing of credits across afternoon/morning work sessions.
        
        Legal Alignment (Loi Fiscale 2026):
        - Art. 169 & 176 CIDTA: Prior mandatory authentication of counterparty.
        - Art. 30 CTCA: Deductibility of VAT requires valid active registration at transaction time.
        - Code de Commerce Art. 23/24: Opposabilité des actes et date d'effet CNRC.
        """
        if not partner or not partner.kyb_last_verified:
            return False
        delta = fields.Datetime.now() - partner.kyb_last_verified
        return delta.total_seconds() < 86400  # 24 real hours

    @api.model
    def _is_verified_today(self, partner):
        """Backward compatibility alias pointing to rolling 24h freshness."""
        return self._is_fresh_24h(partner)

    @api.onchange("partner_id", "invoice_date")
    def _onchange_kyb_temporal_compliance(self):
        """Re-evaluate fiscal compliance when partner or invoice date changes."""
        self._audit_temporal_compliance()
        if (
            self.partner_id
            and self._is_sale_doc()
            and self.kyb_compliance_status in ("non_compliant", "warning")
        ):
            return {
                "warning": {
                    "title": _("⚠️ Alerte Risque Commercial (Client Radié)"),
                    "message": self.kyb_compliance_message,
                }
            }

    def action_verify_kyb_compliance(self):
        """Header button action and bulk action to audit temporal fiscal compliance."""
        if not self:
            return

        compliant_count = 0
        non_compliant_count = 0
        warning_count = 0

        for move in self:
            if not move.partner_id:
                continue

            partner = move.partner_id
            has_ident = bool(
                partner.kyb_nif
                or partner.kyb_rc
                or partner.vat
                or (partner.company_registry if "company_registry" in partner._fields else False)
            )
            # 24-Hour Rolling Just-In-Time Freshness Rule:
            # If partner has NIF/RC and has NOT been verified within the last 24h, re-resolve live legal standing.
            # If already verified within 24h, reuse local verified profile (0 credits, <1ms).
            if has_ident and not self._is_fresh_24h(partner):
                try:
                    partner.action_verify_kyb()
                except Exception as e:
                    _logger.warning("Partner JIT verification failed during invoice audit: %s", e)

            move._audit_temporal_compliance()

            if move.kyb_compliance_status == "compliant":
                compliant_count += 1
            elif move.kyb_compliance_status == "non_compliant":
                non_compliant_count += 1
            elif move.kyb_compliance_status == "warning":
                warning_count += 1

        if len(self) == 1:
            if not self.partner_id:
                raise UserError(_("Veuillez sélectionner un partenaire avant de vérifier la conformité fiscale."))
            status_label = dict(self._fields["kyb_compliance_status"].selection).get(
                self.kyb_compliance_status, self.kyb_compliance_status
            )
            if self._is_sale_doc() and self.kyb_compliance_status == "non_compliant":
                status_label = _("Non Conforme (Client Radié — Risque Commercial)")
            msg_type = (
                "danger"
                if self.kyb_compliance_status == "non_compliant"
                else ("warning" if self.kyb_compliance_status == "warning" else "success")
            )
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Audit Temporel KYB"),
                    "message": _("Verdict pour '%(partner)s' : %(status)s") % {
                        "partner": self.partner_id.name,
                        "status": status_label,
                    },
                    "sticky": self.kyb_compliance_status == "non_compliant",
                    "type": msg_type,
                },
            }

        # Bulk notification summary
        msg_type = "danger" if non_compliant_count > 0 else "success"
        summary_msg = (
            _("Audit en masse terminé (%(total)d factures auditées) :\n"
              "• %(compliant)d Conforme(s) (Actifs)\n"
              "• %(non_compliant)d Non Conforme(s) (Tiers Radiés - Risque fiscal/commercial)\n"
              "• %(warning)d Suspect(s) / Avertissement(s)") % {
                "total": len(self),
                "compliant": compliant_count,
                "non_compliant": non_compliant_count,
                "warning": warning_count,
            }
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Audit de Masse KYB Terminé"),
                "message": summary_msg,
                "sticky": non_compliant_count > 0,
                "type": msg_type,
            },
        }

    def _audit_temporal_compliance(self):
        """Core compliance rule evaluator for both Supplier Bills and Customer Invoices."""
        for move in self.with_context(kyb_skip_invoice_audit=True):
            partner = move.partner_id
            if not partner:
                move.kyb_compliance_status = "unverified"
                move.kyb_compliance_message = False
                continue

            statut = (partner.kyb_statut_cnrc or "INCONNU").upper()
            inv_date = move.invoice_date or fields.Date.context_today(move)
            is_sale = move._is_sale_doc()

            if "RAD" in statut or "مشطب" in statut:
                rad_date = partner.kyb_date_radiation
                inv_date_obj = self._to_date(inv_date)
                rad_date_obj = self._to_date(rad_date)
                if rad_date_obj and inv_date_obj and inv_date_obj > rad_date_obj:
                    move.kyb_compliance_status = "non_compliant"
                    move.kyb_tax_deductible = False
                    move.kyb_audit_date = fields.Datetime.now()
                    if is_sale:
                        move.kyb_compliance_message = (
                            f"⚠️ Alerte Risque Commercial (Client Radié) :\n"
                            f"Le client '{partner.name}' est enregistré comme radié au registre officiel depuis le {rad_date}.\n"
                            f"La présente facture de vente est datée du {inv_date} (postérieurement à la date de radiation enregistrée).\n"
                            f"Information : La facturation reste autorisée (TVA collectée exigible), mais il est recommandé d'exiger un règlement au comptant et de vérifier le dossier pour l'État 104 (Art. 183 ter CIDTA)."
                        )
                    else:
                        move.kyb_compliance_message = (
                            f"⚠️ Signalement Registre Officiel (Fournisseur Radié) :\n"
                            f"Le fournisseur '{partner.name}' est enregistré comme radié depuis le {rad_date}.\n"
                            f"La présente facture est datée du {inv_date} (postérieurement à la date de radiation enregistrée).\n"
                            f"Information : Selon les dispositions des Art. 169 & 176 CIDTA et Art. 30 CTCA, une vérification comptable préalable est recommandée."
                        )
                else:
                    move.kyb_compliance_status = "warning"
                    move.kyb_tax_deductible = False
                    move.kyb_audit_date = fields.Datetime.now()
                    if is_sale:
                        move.kyb_compliance_message = (
                            f"⚠️ Client Signalé Radié (Registre Officiel) :\n"
                            f"Le client '{partner.name}' est enregistré comme radié (Date radiation : {rad_date or 'Non renseignée'}).\n"
                            f"Recommandation : Vérifiez la solvabilité du client (paiement au comptant) et la concordance État 104."
                        )
                    else:
                        move.kyb_compliance_message = (
                            f"⚠️ Fournisseur Signalé Radié (Registre Officiel) :\n"
                            f"Le partenaire '{partner.name}' est enregistré comme radié (Date radiation : {rad_date or 'Non renseignée'}).\n"
                            f"Veuillez vérifier la situation auprès de vos services comptables."
                        )
            elif "ACT" in statut or "نشط" in statut:
                move.kyb_compliance_status = "compliant"
                move.kyb_tax_deductible = True
                move.kyb_audit_date = fields.Datetime.now()
                role_label = "Client" if is_sale else "Fournisseur"
                move.kyb_compliance_message = (
                    f"✅ {role_label} Actif au Registre :\n"
                    f"Le partenaire '{partner.name}' est enregistré comme actif au registre du commerce (NIF: {partner.kyb_nif or partner.vat or 'Renseigné'})."
                )
            elif "SUSP" in statut:
                move.kyb_compliance_status = "warning"
                move.kyb_tax_deductible = False
                move.kyb_audit_date = fields.Datetime.now()
                move.kyb_compliance_message = (
                    f"⚠️ Registre Suspendu :\n"
                    f"L'activité du partenaire '{partner.name}' est suspendue auprès du CNRC."
                )
            else:
                move.kyb_compliance_status = "unverified"
                move.kyb_tax_deductible = False
                move.kyb_audit_date = False
                move.kyb_compliance_message = (
                    f"ℹ️ Non Vérifié :\n"
                    f"Le partenaire '{partner.name}' n'a pas encore fait l'objet d'une vérification sur le registre KYB."
                )

    def action_post(self):
        """
        Override action_post to enforce compliance policies:
        - Purchase documents (Vendor Bills): Enforce configurable blocking_policy (strict_block or soft_warn)
          per Articles 169 & 176 CIDTA and Article 30 CTCA.
        - Sale documents (Customer Invoices): Perform JIT verification and post a non-blocking
          Chatter warning note when billing a deregistered (radié) customer (credit risk & État 104 audit trail).
        """
        audit_enabled = _get_config_bool(self.env, "kyb.invoice_audit_enabled", default=True)
        blocking_policy = _get_config_param(self.env, "kyb.invoice_blocking_policy", default="strict_block")
        unverified_policy = _get_config_param(self.env, "kyb.unverified_partner_policy", default="allow_warn")

        if audit_enabled:
            for move in self:
                if not move._is_invoice_doc():
                    continue

                partner = move.partner_id
                has_ident = bool(
                    partner and (
                        partner.kyb_nif
                        or partner.kyb_rc
                        or partner.vat
                        or (partner.company_registry if "company_registry" in partner._fields else False)
                    )
                )
                if has_ident and not self._is_fresh_24h(partner):
                    try:
                        partner.action_verify_kyb()
                    except Exception as e:
                        _logger.warning("Partner JIT refresh failed during post: %s", e)

                move._audit_temporal_compliance()

                # Branch A: Purchase Documents (Vendor Bills / Refunds)
                if move._is_purchase_doc():
                    # Policy 1: Non-Compliant / Radié Supplier
                    if move.kyb_compliance_status == "non_compliant":
                        if blocking_policy == "strict_block":
                            date_str = str(partner.kyb_date_radiation) if partner.kyb_date_radiation else _("Date non précisée")
                            inv_str = str(move.invoice_date or fields.Date.context_today(move))
                            raise UserError(
                                _("⛔ COMPTABILISATION INTERROMPUE (Contrôle Registre KYB)\n\n"
                                  "Réglementation applicable : Articles 169 & 176 du CIDTA et Article 30 du CTCA.\n\n"
                                  "Le fournisseur '%(partner)s' est enregistré comme radié au registre officiel en date du %(rad_date)s.\n"
                                  "La facture %(move_name)s est datée du %(inv_date)s (postérieurement à la date de radiation enregistrée).\n\n"
                                  "Recommandation de contrôle :\n"
                                  "• Selon la réglementation fiscale, les transactions conclues avec un fournisseur radié font l'objet d'un contrôle de déductibilité.\n"
                                  "• Une vérification comptable préalable auprès de votre service financier ou fiscal est recommandée avant validation.\n\n"
                                  "Pour modifier la politique de blocage ou obtenir une dérogation, contactez votre Responsable Conformité.")
                                % {
                                    "partner": partner.name,
                                    "rad_date": date_str,
                                    "move_name": move.name or _("Brouillon"),
                                    "inv_date": inv_str,
                                }
                            )
                        else:
                            msg_html = (move.kyb_compliance_message or "").replace("\n", "<br/>")
                            move.message_post(
                                body=Markup(
                                    f"<div class='alert alert-danger'>"
                                    f"<strong>Signalement Registre Officiel (Fournisseur Radié - Réf. Art. 176 CIDTA) :</strong><br/>"
                                    f"{msg_html}"
                                    f"</div>"
                                ),
                                message_type="notification",
                                subtype_xmlid="mail.mt_note",
                            )

                    # Policy 2: Unverified Partner on Purchase Document
                    elif move.kyb_compliance_status == "unverified" and unverified_policy == "require_verify":
                        raise UserError(
                            _("⛔ VALIDATION BLOQUÉE : Le fournisseur '%(partner)s' n'a pas encore fait l'objet d'une vérification préalable KYB.\n"
                              "Veuillez renseigner son NIF/RC et cliquer sur 'Vérifier Fiche KYB' avant de comptabiliser cette facture.")
                            % {"partner": partner.name}
                        )

                # Branch B: Sale Documents (Customer Invoices / Refunds) — Always Non-Blocking with Chatter Alert
                elif move._is_sale_doc():
                    if move.kyb_compliance_status in ("non_compliant", "warning") and partner and (
                        "RAD" in (partner.kyb_statut_cnrc or "").upper()
                        or "مشطب" in (partner.kyb_statut_cnrc or "")
                        or "SUSP" in (partner.kyb_statut_cnrc or "").upper()
                    ):
                        msg_html = (move.kyb_compliance_message or "").replace("\n", "<br/>")
                        move.message_post(
                            body=Markup(
                                f"<div class='alert alert-warning'>"
                                f"<strong>Signalement Risque Commercial &amp; État 104 (Client Radié — Non-Bloquant) :</strong><br/>"
                                f"{msg_html}"
                                f"</div>"
                            ),
                            message_type="notification",
                            subtype_xmlid="mail.mt_note",
                        )

        return super().action_post() if hasattr(super(), "action_post") else True

    # ──────────────── End-of-Month Global Audit (G50 Safety Net) ──────────────────

    @api.model
    def action_kyb_trigger_eom_audit(self):
        """Action button in Cockpit to trigger End-of-Month Global Fiscal Audit."""
        return self.cron_kyb_end_of_month_audit(manual_trigger=True)

    @api.model
    def cron_kyb_end_of_month_audit(self, manual_trigger=False):
        """
        End-of-Month Global Compliance Pre-Audit (G50 Safety Net):
        Audits all vendor bills for the current accounting period before statutory tax filing.
        Re-verifies all active counterparties against KYB gateway.
        """
        today = fields.Date.context_today(self)
        first_day_of_month = today.replace(day=1)

        domain = [
            ("move_type", "in", ("in_invoice", "in_refund")),
            ("invoice_date", ">=", first_day_of_month),
            ("invoice_date", "<=", today),
            ("state", "!=", "cancel"),
        ]
        moves = self.search(domain)
        _logger.info("KYB EOM Audit starting: %d vendor bills found for period >= %s", len(moves), first_day_of_month)

        distinct_partners = moves.mapped("partner_id")
        reverified_partners = 0
        for partner in distinct_partners:
            if partner.kyb_nif or partner.kyb_rc:
                try:
                    partner.action_verify_kyb()
                    reverified_partners += 1
                except Exception as exc:
                    _logger.warning("EOM Audit partner verify failed for %s: %s", partner.name, exc)

        compliant_count = 0
        non_compliant_moves = self.env["account.move"]
        warning_count = 0

        for move in moves:
            move._audit_temporal_compliance()
            if move.kyb_compliance_status == "compliant":
                compliant_count += 1
            elif move.kyb_compliance_status == "non_compliant":
                non_compliant_moves |= move
            elif move.kyb_compliance_status == "warning":
                warning_count += 1

        non_compliant_count = len(non_compliant_moves)
        tax_exposure_dzd = sum(non_compliant_moves.mapped("amount_total"))

        summary_msg = (
            _("Audit de Clôture Mensuelle G50 Terminé :\n"
              "• Période examinée : Du %(start)s au %(end)s\n"
              "• Total Factures Fournisseurs : %(total)d (dont %(partners)d partenaires vérifiés)\n"
              "• ✅ Conformes : %(compliant)d\n"
              "• 🔴 Non Conformes (Fournisseurs Radiés) : %(non_compliant)d\n"
              "• ⚠️ Montant Exposé (Fournisseurs Radiés) : %(exposure).2f DZD\n"
              "• ℹ️ Avertissements : %(warning)d") % {
                "start": first_day_of_month,
                "end": today,
                "total": len(moves),
                "partners": reverified_partners,
                "compliant": compliant_count,
                "non_compliant": non_compliant_count,
                "exposure": tax_exposure_dzd,
                "warning": warning_count,
            }
        )
        _logger.info("KYB EOM Audit Result:\n%s", summary_msg)

        if manual_trigger:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Audit de Clôture Mensuelle G50"),
                    "message": summary_msg,
                    "sticky": non_compliant_count > 0,
                    "type": "danger" if non_compliant_count > 0 else "success",
                },
            }
        return True
