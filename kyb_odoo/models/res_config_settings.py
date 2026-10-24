# -*- coding: utf-8 -*-
"""
KYB Configuration Settings — Enterprise settings panel for KYB API (by Digidev) credentials.
Allows configuring API keys and Gateway URLs without requiring Developer Mode.
"""

import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


def _get_config_param(env, key, default=""):
    """Universally get string config parameter across Odoo 16, 17, 18, 19, and 20."""
    try:
        icp = env["ir.config_parameter"].sudo()
        if hasattr(icp, "get_str"):
            val = icp.get_str(key, default=None)
            return val if val is not None else default
        if hasattr(icp, "get_param"):
            return icp.get_param(key, default=default)
        rec = icp.search([("key", "=", key)], limit=1)
        return rec.value if rec and rec.value is not None else default
    except Exception:
        return default


def _set_config_param(env, key, value):
    """Universally set string config parameter across Odoo 16, 17, 18, 19, and 20."""
    try:
        icp = env["ir.config_parameter"].sudo()
        str_val = str(value) if value is not None else ""
        if hasattr(icp, "set_str"):
            return icp.set_str(key, str_val)
        if hasattr(icp, "set_param"):
            return icp.set_param(key, str_val)
        rec = icp.search([("key", "=", key)], limit=1)
        if rec:
            rec.write({"value": str_val})
        else:
            icp.create({"key": key, "value": str_val})
    except Exception as exc:
        _logger.warning("Failed to set config param %s: %s", key, exc)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    kyb_api_key = fields.Char(
        string="KYB Secret API Key",
        config_parameter="kyb.api_key",
        help="Clé d'API secrète KYB (e.g. sk_live_... pour la production ou sk_test_kyb_sandbox_key_001 pour le bac à sable gratuit).",
    )
    kyb_base_url = fields.Char(
        string="KYB Gateway Base URL",
        config_parameter="kyb.base_url",
        default="https://kyb.digidevagency.dz",
        help="URL du gateway KYB (par défaut: https://kyb.digidevagency.dz).",
    )
    kyb_sovereign_autocomplete = fields.Boolean(
        string="CNRC Autocomplete",
        config_parameter="kyb.sovereign_autocomplete",
        default=True,
        help="Intercepts company name searches to query the Algerian CNRC registry instead of offshore Odoo IAP / Dun & Bradstreet servers.",
    )
    kyb_allow_worldwide_fallback = fields.Boolean(
        string="Allow Worldwide Fallback",
        config_parameter="kyb.allow_worldwide_fallback",
        default=False,
        help="Allows fallback to international search when specifically clicking 'Search Worldwide'.",
    )
    kyb_autocomplete_filter = fields.Selection(
        selection=[
            ("all", "Toutes les entités (Actif & Radié — Recommandé conformité fiscale)"),
            ("active_only", "Entités Actives uniquement (Exclure les entreprises radiées)"),
        ],
        string="Filtre Autocomplétion Tiers",
        config_parameter="kyb.autocomplete_filter",
        default="all",
        help="Contrôle si l'autocomplétion inclut les entreprises radiées pour l'audit d'anciennes factures ou seulement les entités actives.",
    )
    kyb_autocomplete_limit = fields.Integer(
        string="Nombre Maximum de Résultats",
        config_parameter="kyb.autocomplete_limit",
        default=20,
        help="Nombre de candidats affichés dans le menu déroulant (10 à 30).",
    )
    kyb_duplicate_nif_policy = fields.Selection(
        selection=[
            ("warn", "Avertissement (Notifier la présence d'un contact existant)"),
            ("block", "Blocage Strict (Interdire la duplication du NIF)"),
            ("ignore", "Ignorer (Comportement natif Odoo multi-établissements)"),
        ],
        string="Détection des Doublons Fiscaux (NIF)",
        config_parameter="kyb.duplicate_nif_policy",
        default="warn",
        help="Contrôle le comportement lorsqu'un NIF saisi existe déjà sur une autre fiche partenaire.",
    )
    kyb_invoice_audit_enabled = fields.Boolean(
        string="Audit Temporel des Factures",
        config_parameter="kyb.invoice_audit_enabled",
        default=True,
        help="Contrôle automatiquement la conformité temporelle (Art. 169 & 176 CIDTA / Art. 30 CTCA) sur les factures d'achat.",
    )
    kyb_invoice_blocking_policy = fields.Selection(
        selection=[
            ("strict_block", "Blocage Strict (Interdire la comptabilisation si radié)"),
            ("soft_warn", "Avertissement (Consignation dans le Chatter sans blocage)"),
            ("warning", "Avertissement (Consignation dans le Chatter sans blocage)"),
        ],
        string="Politique de Validation des Factures",
        config_parameter="kyb.invoice_blocking_policy",
        default="strict_block",
        help="Comportement lors de la confirmation d'une facture d'achat pour un fournisseur radié.",
    )
    kyb_unverified_partner_policy = fields.Selection(
        selection=[
            ("allow_warn", "Autoriser avec avertissement 'Non Vérifié'"),
            ("require_verify", "Exiger la vérification KYB préalable"),
        ],
        string="Politique Fournisseurs Non Vérifiés",
        config_parameter="kyb.unverified_partner_policy",
        default="allow_warn",
        help="Comportement lors de la saisie d'un fournisseur n'ayant pas encore été vérifié sur le registre.",
    )
    kyb_eom_auto_audit = fields.Boolean(
        string="Audit Automatique de Clôture Mensuelle G50",
        config_parameter="kyb.eom_auto_audit",
        default=True,
        help="Déclenche une tâche planifiée mensuelle pour auditer l'ensemble des factures du mois avant déclaration G50.",
    )
    kyb_eom_audit_day = fields.Integer(
        string="Jour du mois pour l'audit G50",
        config_parameter="kyb.eom_audit_day",
        default=18,
        help="Jour du mois auquel l'audit automatique est exécuté (par défaut le 18, avant la date limite fiscale du 20).",
    )

    # ──────────────── Version & Auto-Update Engine ────────────────
    kyb_installed_version = fields.Char(
        string="Version Installée",
        compute="_compute_kyb_versions",
        help="Version actuellement active du connecteur KYB dans cette instance Odoo.",
    )
    kyb_latest_version = fields.Char(
        string="Dernière Version Disponible",
        config_parameter="kyb.latest_version",
        default="2.0.0",
    )
    kyb_update_available = fields.Boolean(
        string="Mise à Jour Disponible",
        compute="_compute_kyb_versions",
    )
    kyb_changelog = fields.Char(
        string="Notes de Version",
        config_parameter="kyb.changelog",
    )
    kyb_last_telemetry_sync = fields.Datetime(
        string="Dernière Vérification",
        config_parameter="kyb.last_telemetry_sync",
    )
    kyb_update_policy = fields.Selection(
        selection=[
            ("auto", "Automatique — Correctifs réglementaires et patchs mineurs appliqués sans intervention"),
            ("manual", "Manuel (Conforme ITIL) — Notification en cockpit uniquement. Validation administrateur requise"),
        ],
        string="Politique de Mise à Jour",
        config_parameter="kyb.update_policy",
        default="auto",
        help="En mode Automatique, les correctifs de conformité fiscale (Loi 25-11) sont appliqués de manière autonome. En mode Manuel, aucune modification de code n'est effectuée sans approbation explicite de l'administrateur (conforme aux normes ITIL Change Enablement).",
    )
    kyb_auto_update_patches = fields.Boolean(
        string="Mise à Jour Automatique des Correctifs",
        config_parameter="kyb.auto_update_patches",
        default=True,
        help="Applique automatiquement les correctifs de sécurité et de conformité mineurs lors de la vérification planifiée.",
    )

    @api.onchange("kyb_update_policy")
    def _onchange_kyb_update_policy(self):
        self.kyb_auto_update_patches = bool(self.kyb_update_policy == "auto")

    def _compute_kyb_versions(self):
        import re
        for rec in self:
            mod = self.env["ir.module.module"].sudo().search([("name", "=", "kyb_odoo")], limit=1)
            inst = mod.installed_version if mod and mod.installed_version else "2.0.0"
            rec.kyb_installed_version = inst
            latest = rec.kyb_latest_version or "2.0.0"
            inst_clean = re.sub(r'^\d+\.0\.', '', str(inst)).strip()
            latest_clean = re.sub(r'^\d+\.0\.', '', str(latest)).strip()
            rec.kyb_update_available = bool(latest_clean and inst_clean and inst_clean != latest_clean)

    def _gather_instance_telemetry(self):
        """Gathers aggregate client instance metadata for sovereign fleet observability (Loi 25-11 compliant)."""
        import platform
        try:
            import odoo.release
            odoo_ver = getattr(odoo.release, "version", "unknown")
        except Exception:
            odoo_ver = "unknown"

        db_uuid = _get_config_param(self.env, "database.uuid")
        db_name = self.env.cr.dbname or ""
        web_url = _get_config_param(self.env, "web.base.url")

        mod = self.env["ir.module.module"].sudo().search([("name", "=", "kyb_odoo")], limit=1)
        mod_ver = mod.installed_version if mod and mod.installed_version else "2.0.0"

        # Enterprise edition detection
        is_enterprise = bool(self.env["ir.module.module"].sudo().search_count([("name", "=", "web_enterprise"), ("state", "=", "installed")]))
        if not is_enterprise:
            try:
                import odoo.release
                if hasattr(odoo.release, "version_info"):
                    is_enterprise = "e" in str(odoo.release.version_info).lower()
            except Exception:
                pass

        # Company & user scale
        company_count = self.env["res.company"].sudo().search_count([])
        active_users = self.env["res.users"].sudo().search_count([("active", "=", True), ("share", "=", False)])
        currency = "DZD"
        if hasattr(self.env, "company") and self.env.company and self.env.company.currency_id:
            currency = self.env.company.currency_id.name or "DZD"

        # Installed business modules footprint
        core_apps = ["account", "sale", "purchase", "crm", "stock", "point_of_sale", "project", "mrp", "hr"]
        installed_apps = self.env["ir.module.module"].sudo().search([
            ("name", "in", core_apps),
            ("state", "=", "installed"),
        ]).mapped("name")

        # Partner compliance distribution
        partner_count = self.env["res.partner"].sudo().search_count([])
        verified_count = self.env["res.partner"].sudo().search_count([("kyb_statut_cnrc", "!=", False)])
        active_count = self.env["res.partner"].sudo().search_count([("kyb_statut_cnrc", "=", "ACTIF")])
        radie_count = self.env["res.partner"].sudo().search_count([("kyb_statut_cnrc", "=", "RADIE")])
        suspendu_count = self.env["res.partner"].sudo().search_count([("kyb_statut_cnrc", "=", "SUSPENDU")])
        unverified_candidates = self.env["res.partner"].sudo().search_count([
            ("kyb_statut_cnrc", "=", False),
            "|", ("vat", "!=", False), ("kyb_rc", "!=", False),
        ])

        # Invoice audit metrics
        audited_invoices = 0
        compliant_invoices = 0
        blocked_invoices = 0
        if "kyb_audit_status" in self.env["account.move"]._fields:
            audited_invoices = self.env["account.move"].sudo().search_count([("kyb_audit_status", "!=", False)])
            compliant_invoices = self.env["account.move"].sudo().search_count([("kyb_audit_status", "=", "compliant")])
            blocked_invoices = self.env["account.move"].sudo().search_count([("kyb_audit_status", "in", ["non_compliant", "blocked"])])

        # Configuration security posture
        config_posture = {
            "invoice_blocking_policy": _get_config_param(self.env, "kyb.invoice_blocking_policy", "strict_block"),
            "duplicate_nif_policy": _get_config_param(self.env, "kyb.duplicate_nif_policy", "warn"),
            "sovereign_autocomplete": str(_get_config_param(self.env, "kyb.sovereign_autocomplete", "True")).lower() == "true",
            "auto_update_patches": str(_get_config_param(self.env, "kyb.auto_update_patches", "False")).lower() == "true",
            "eom_auto_audit": str(_get_config_param(self.env, "kyb.eom_auto_audit", "True")).lower() == "true",
        }

        return {
            "client_type": "odoo",
            "connector_version": mod_ver,
            "odoo_version": str(odoo_ver),
            "database_uuid": str(db_uuid),
            "database_name": str(db_name),
            "instance_url": str(web_url),
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "is_enterprise": is_enterprise,
            "company_count": company_count,
            "active_users": active_users,
            "currency": currency,
            "installed_apps": installed_apps,
            "metrics": {
                "total_partners": partner_count,
                "verified_partners": verified_count,
                "active_partners": active_count,
                "radie_partners": radie_count,
                "suspendu_partners": suspendu_count,
                "unverified_candidates": unverified_candidates,
                "audited_invoices": audited_invoices,
                "compliant_invoices": compliant_invoices,
                "blocked_invoices": blocked_invoices,
            },
            "configuration": config_posture,
        }

    def action_check_kyb_update(self):
        """Manually triggers version check and telemetry heartbeat to Conforme Gateway."""
        import requests
        base_url = (self.kyb_base_url or "https://kyb.digidevagency.dz").rstrip("/")
        api_key = self.kyb_api_key or ""
        telemetry_data = self._gather_instance_telemetry()

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": f"Odoo-KYB-Connector/{telemetry_data['connector_version']} (Odoo {telemetry_data['odoo_version']}; Sovereign)",
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        target_url = f"{base_url}/api/v1/client/telemetry" if api_key else f"{base_url}/api/v1/version"
        try:
            if api_key:
                resp = requests.post(target_url, json=telemetry_data, headers=headers, timeout=10)
            else:
                resp = requests.get(
                    f"{base_url}/api/v1/version",
                    params={
                        "client": "odoo",
                        "version": telemetry_data["connector_version"],
                        "odoo_version": telemetry_data["odoo_version"],
                        "db_uuid": telemetry_data["database_uuid"],
                        "db_name": telemetry_data["database_name"],
                    },
                    headers=headers,
                    timeout=10,
                )

            if resp.status_code == 200:
                data = resp.json()
                latest = data.get("latest_version") or "2.0.0"
                changelog = data.get("changelog") or ""
                has_update = data.get("has_update", False)
                force_upgrade = data.get("force_upgrade", False)

                _set_config_param(self.env, "kyb.latest_version", latest)
                _set_config_param(self.env, "kyb.update_available", str(has_update).lower())
                _set_config_param(self.env, "kyb.force_upgrade", str(force_upgrade).lower())
                if changelog:
                    _set_config_param(self.env, "kyb.changelog", changelog)
                _set_config_param(self.env, "kyb.last_telemetry_sync", fields.Datetime.now())

                if has_update:
                    msg = _("Nouvelle version %s disponible ! Cliquez sur 'Mettre à jour maintenant'.") % latest
                    msg_type = "warning"
                else:
                    msg = _("Votre connecteur KYB est parfaitement à jour (v%s).") % telemetry_data["connector_version"]
                    msg_type = "success"

                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": _("Vérification des Mises à Jour KYB"),
                        "message": msg,
                        "type": msg_type,
                        "sticky": False,
                    },
                }
            else:
                raise UserError(_("Erreur du serveur KYB (HTTP %d) lors de la vérification.") % resp.status_code)
        except Exception as exc:
            _logger.warning("KYB update check failed: %s", exc)
            raise UserError(_("Impossible de contacter le serveur KYB: %s") % str(exc))

    def action_upgrade_kyb_module(self):
        """Downloads latest certified release ZIP from Gateway and executes in-place immediate upgrade."""
        import io, os, shutil, zipfile
        import requests

        module_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if not os.access(module_path, os.W_OK):
            raise UserError(
                _("Le répertoire du module (%s) est en lecture seule.\n"
                  "Veuillez mettre à jour le module via Git ou votre gestionnaire de conteneurs.") % module_path
            )

        base_url = (self.kyb_base_url or "https://kyb.digidevagency.dz").rstrip("/")
        download_url = f"{base_url}/api/v1/downloads/kyb_odoo.zip"
        _logger.info("Downloading KYB module update from: %s", download_url)

        try:
            resp = requests.get(download_url, timeout=45)
            if resp.status_code != 200:
                raise UserError(_("Échec du téléchargement de l'archive de mise à jour (HTTP %d).") % resp.status_code)

            zip_buffer = io.BytesIO(resp.content)
            if not zipfile.is_zipfile(zip_buffer):
                raise UserError(_("Le fichier téléchargé n'est pas une archive ZIP valide."))

            with zipfile.ZipFile(zip_buffer) as zf:
                namelist = zf.namelist()
                has_manifest = any(f.endswith("__manifest__.py") for f in namelist)
                if not has_manifest:
                    raise UserError(_("L'archive téléchargée ne contient pas de fichier __manifest__.py valide."))

                temp_extract_dir = os.path.join(os.path.dirname(module_path), "_kyb_odoo_update_tmp")
                if os.path.exists(temp_extract_dir):
                    shutil.rmtree(temp_extract_dir, ignore_errors=True)
                os.makedirs(temp_extract_dir, exist_ok=True)

                zf.extractall(temp_extract_dir)

                source_root = temp_extract_dir
                if os.path.exists(os.path.join(temp_extract_dir, "kyb_odoo", "__manifest__.py")):
                    source_root = os.path.join(temp_extract_dir, "kyb_odoo")

                for item in os.listdir(source_root):
                    src_item = os.path.join(source_root, item)
                    dst_item = os.path.join(module_path, item)
                    if os.path.isdir(src_item):
                        if os.path.exists(dst_item):
                            shutil.rmtree(dst_item, ignore_errors=True)
                        shutil.copytree(src_item, dst_item)
                    else:
                        if os.path.exists(dst_item):
                            try:
                                os.remove(dst_item)
                            except Exception:
                                pass
                        shutil.copy2(src_item, dst_item)

                shutil.rmtree(temp_extract_dir, ignore_errors=True)
                _logger.info("KYB module files updated cleanly in %s", module_path)

        except Exception as exc:
            _logger.error("KYB in-app update extraction failed: %s", exc)
            raise UserError(_("Erreur lors de l'application de la mise à jour: %s") % str(exc))

        mod = self.env["ir.module.module"].sudo().search([("name", "=", "kyb_odoo")], limit=1)
        if mod:
            _logger.info("Triggering button_immediate_upgrade for kyb_odoo...")
            return mod.button_immediate_upgrade()

        return {"type": "ir.actions.client", "tag": "reload"}

    @api.model
    def cron_kyb_sync_telemetry(self):
        """Automated daily cron: sends heartbeat telemetry and checks for updates."""
        try:
            settings = self.env["res.config.settings"].create({})
            settings.action_check_kyb_update()
            update_policy = _get_config_param(self.env, "kyb.update_policy", "auto")
            auto_patches = (update_policy == "auto") and (str(_get_config_param(self.env, "kyb.auto_update_patches", "True")).lower() == "true")
            update_avail = str(_get_config_param(self.env, "kyb.update_available", "false")).lower() == "true"
            force_upgrade = str(_get_config_param(self.env, "kyb.force_upgrade", "false")).lower() == "true"

            if update_avail and (auto_patches or force_upgrade):
                _logger.info("KYB automated in-place upgrade triggered via cron (policy=%s, force_upgrade=%s)", update_policy, force_upgrade)
                settings.action_upgrade_kyb_module()
        except Exception as err:
            _logger.warning("KYB cron telemetry sync failed: %s", err)

