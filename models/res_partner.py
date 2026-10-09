# -*- coding: utf-8 -*-
"""
KYB integration for res.partner — Real-time NIF auto-lookup, temporal audit, and contact autocomplete.

This module extends ``res.partner`` with:
    1. Custom fields for Algerian corporate identity (NIF, RC, NIS, Article d'Imposition, CNRC status).
    2. An ``onchange`` handler that auto-populates partner data from the KYB sovereign API
       when a NIF or RC is entered.
    3. A ``_name_search`` override that queries the KYB fuzzy search endpoint
       for real-time autocomplete in many2one partner selector fields.
    4. Resilient multi-runtime support: seamlessly uses the official ``conforme`` SDK if installed,
       or falls back to native Python ``requests`` with zero external package requirements.
"""

import logging
from typing import Optional

import requests
from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class _NativeSearchNamespace:
    """Namespace mirroring the official SDK search capabilities."""

    def __init__(self, client: "_NativeKybClient"):
        self._client = client

    def autocomplete(self, query: str, poll: bool = False) -> list:
        res = self._client.candidates(query)
        if isinstance(res, dict):
            return res.get("candidates") or res.get("results") or res.get("data") or []
        if isinstance(res, list):
            return res
        return []


class _NativeKybClient:
    """
    Zero-dependency Native KYB HTTP Client for Odoo.
    Uses standard Python 'requests' library bundled with all Odoo environments.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://kyb.digidevagency.dz",
        timeout: float = 15.0,
        lang: str = "fr",
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.lang = lang
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "Accept-Language": lang,
            "User-Agent": "Odoo-KYB-Connector/17.0 (Sovereign)",
        })
        self.search = _NativeSearchNamespace(self)

    def resolve(self, query: str) -> dict:
        url = f"{self.base_url}/api/v1/entity/resolve"
        resp = self._session.get(url, params={"q": query}, timeout=self.timeout)
        return self._handle_response(resp)

    def candidates(self, query: str, limit: int = 20) -> dict:
        url = f"{self.base_url}/api/v1/entity/candidates"
        resp = self._session.get(
            url, params={"q": query, "limit": limit}, timeout=self.timeout
        )
        return self._handle_response(resp)

    def _handle_response(self, resp: requests.Response) -> dict:
        try:
            data = resp.json()
        except Exception:
            data = {}

        if not resp.ok:
            # Extract localized error from universal trilingual error envelope
            msg = (
                data.get("message")
                or data.get(f"message_{self.lang}")
                or data.get("error")
                or f"HTTP {resp.status_code} Error"
            )
            code = data.get("code", "API_ERROR")
            raise UserError(f"[{code}] {msg}")
        return data

    def close(self):
        self._session.close()


def _get_kyb_client(env):
    """
    Lazily initialise and return a synchronous KYB client.

    Reads credentials from Odoo system parameters:
        - ``kyb.api_key`` (or legacy ``conforme.api_key``) — Bearer token for authentication.
        - ``kyb.base_url`` (or legacy ``conforme.base_url``) — API gateway URL (default: https://kyb.digidevagency.dz).

    Supports both the official ``conforme`` PyPI package and native ``requests``.
    """
    ICP = env["ir.config_parameter"].sudo()
    api_key = (
        ICP.get_param("kyb.api_key", default="")
        or ICP.get_param("conforme.api_key", default="")
    )
    base_url = (
        ICP.get_param("kyb.base_url", default="")
        or ICP.get_param("conforme.base_url", default="")
        or "https://kyb.digidevagency.dz"
    )

    if not api_key:
        raise UserError(
            "La clé API KYB n'est pas configurée.\n\n"
            "Veuillez vous rendre dans Paramètres → Configuration Générale → KYB Sovereign Verification "
            "pour définir votre clé d'API (ou utiliser la clé sandbox 'sk_test_conforme_sandbox_key_001')."
        )

    user_lang = env.user.lang or "fr"
    lang_code = "ar" if "ar" in user_lang else ("en" if "en" in user_lang else "fr")

    try:
        from conforme import Conforme
        return Conforme(api_key=api_key, base_url=base_url, timeout=15.0)
    except ImportError:
        return _NativeKybClient(
            api_key=api_key, base_url=base_url, timeout=15.0, lang=lang_code
        )


class ResPartner(models.Model):
    _inherit = "res.partner"

    # ──────────────── Custom Algerian Fiscal Fields ────────────────

    kyb_nif = fields.Char(
        string="NIF (Numéro d'Identification Fiscale)",
        size=20,
        index=True,
        tracking=True,
        help="15 or 20-digit Algerian National Tax Identification Number.",
    )
    kyb_rc = fields.Char(
        string="Numéro RC",
        size=30,
        tracking=True,
        help="Numéro du Registre de Commerce (CNRC).",
    )
    kyb_article_imposition = fields.Char(
        string="Article d'Imposition (Numéro de Rôle)",
        size=30,
        tracking=True,
        help="Numéro d'Article d'Imposition (Art 114 CPF), crowd-cached via KYB.",
    )
    kyb_nis = fields.Char(
        string="NIS (Numéro d'Identification Statistique)",
        size=30,
        tracking=True,
        help="Numéro d'Identification Statistique délivré par l'ONS.",
    )
    kyb_statut_cnrc = fields.Selection(
        selection=[
            ("ACTIF", "Actif"),
            ("RADIE", "Radié"),
            ("SUSPENDU", "Suspendu"),
            ("INCONNU", "Inconnu"),
        ],
        string="Statut CNRC",
        default="INCONNU",
        tracking=True,
        help="Current CNRC registration standing from the KYB sovereign registry.",
    )
    kyb_activite = fields.Char(
        string="Activité Principale",
        help="Primary business activity as registered with CNRC.",
    )
    kyb_last_verified = fields.Datetime(
        string="Dernière vérification KYB",
        readonly=True,
        help="Timestamp of the last successful KYB API verification.",
    )

    # ── Legacy Backward Compatibility Aliases ──
    conforme_nif = fields.Char(related="kyb_nif", readonly=False, string="NIF (Alias)")
    conforme_rc = fields.Char(related="kyb_rc", readonly=False, string="Numéro RC (Alias)")
    conforme_article_imposition = fields.Char(related="kyb_article_imposition", readonly=False, string="Article d'Imposition (Alias)")
    conforme_nis = fields.Char(related="kyb_nis", readonly=False, string="NIS (Alias)")
    conforme_statut_cnrc = fields.Selection(related="kyb_statut_cnrc", readonly=False, string="Statut CNRC (Alias)")
    conforme_activite = fields.Char(related="kyb_activite", readonly=False, string="Activité (Alias)")
    conforme_last_verified = fields.Datetime(related="kyb_last_verified", readonly=True, string="Dernière vérification (Alias)")

    # ──────────────── Action Buttons & Onchange Handlers ───────────

    def action_verify_kyb(self):
        """Action button to trigger manual verification from partner form."""
        self.ensure_one()
        query = (self.kyb_nif or self.conforme_nif or self.vat or self.kyb_rc or self.name or "").strip()
        if not query:
            raise UserError("Veuillez renseigner un NIF, un RC ou une Raison Sociale pour lancer la vérification.")
        return self._do_kyb_resolve(query)

    def action_verify_conforme(self):
        """Backward compatible action method alias."""
        return self.action_verify_kyb()

    @api.onchange("vat")
    def _onchange_vat(self):
        """Auto-populate when the standard Odoo VAT field is entered."""
        if self.vat and not self.kyb_nif:
            self.kyb_nif = self.vat.strip()
            return self._onchange_kyb_nif()

    @api.onchange("kyb_nif", "conforme_nif")
    def _onchange_kyb_nif(self):
        """
        When the user enters or modifies the NIF field, query the KYB API
        and auto-populate the partner form with the resolved entity data.
        """
        nif = (self.kyb_nif or self.conforme_nif or "").strip()
        if not nif or len(nif) not in (15, 20):
            return
        return self._do_kyb_resolve(nif)

    def _do_kyb_resolve(self, query: str):
        try:
            client = _get_kyb_client(self.env)
            profile = client.resolve(query)
            client.close()
        except UserError:
            raise
        except Exception as exc:
            _logger.warning("KYB resolve failed for %s: %s", query, exc)
            return {
                "warning": {
                    "title": "Vérification KYB",
                    "message": f"Impossible de certifier l'entité '{query}' : {exc}",
                }
            }

        # Map API response fields to Odoo partner fields (supports envelope unwrapping)
        if isinstance(profile, dict):
            data = profile.get("entity") or profile.get("data") or profile
            if not isinstance(data, dict):
                data = profile

            nif = data.get("nif")
            if nif:
                self.kyb_nif = nif
                if not self.vat:
                    self.vat = nif

            raison = data.get("raison_sociale") or data.get("raisonSociale") or data.get("name", "")
            if raison and not self.name:
                self.name = raison

            rc = data.get("rc_number") or data.get("rcNumber") or data.get("rc") or data.get("numero_rc", "")
            if rc:
                self.kyb_rc = rc

            statut = (data.get("statut_cnrc") or data.get("statutCnrc") or data.get("statut") or "INCONNU").upper()
            if "RAD" in statut or "مشطب" in statut:
                mapped_statut = "RADIE"
            elif "ACT" in statut or "نشط" in statut:
                mapped_statut = "ACTIF"
            elif "SUSP" in statut:
                mapped_statut = "SUSPENDU"
            else:
                mapped_statut = "INCONNU"

            if mapped_statut in dict(self._fields["kyb_statut_cnrc"].selection):
                self.kyb_statut_cnrc = mapped_statut

            activite = data.get("activite") or data.get("activitePrincipale", "")
            if activite:
                self.kyb_activite = activite

            adresse = data.get("adresse") or data.get("adresseSiegeSocial", "")
            wilaya = data.get("wilaya", "")
            if adresse and not self.street:
                self.street = adresse
            elif wilaya and not self.street:
                self.street = f"Siège Social, {wilaya}"

            if wilaya and not self.city:
                self.city = wilaya

            article = data.get("article_imposition") or data.get("articleImposition") or data.get("article_imp", "")
            if article:
                self.kyb_article_imposition = article

            nis = data.get("nis") or data.get("numero_nis", "")
            if nis:
                self.kyb_nis = nis

            self.kyb_last_verified = fields.Datetime.now()

    # ──────────────── _name_search Override ────────────────────────

    @api.model
    def _name_search(
        self,
        name: str = "",
        domain: Optional[list] = None,
        operator: str = "ilike",
        limit: int = 100,
        order: Optional[str] = None,
    ):
        """
        Override ``_name_search`` to enrich autocomplete results with KYB
        fuzzy search when standard Odoo search yields fewer than ``limit`` results.
        """
        res = super()._name_search(
            name=name, domain=domain, operator=operator, limit=limit, order=order
        )

        if not name or len(name) < 3 or len(res) >= limit:
            return res

        try:
            client = _get_kyb_client(self.env)
            matches = client.search.autocomplete(name, poll=False)
            client.close()
        except Exception as exc:
            _logger.debug("KYB autocomplete skipped: %s", exc)
            return res

        if isinstance(matches, dict):
            matches = (
                matches.get("candidates")
                or matches.get("results")
                or matches.get("data")
                or []
            )

        if not isinstance(matches, list):
            return res

        res_list = list(res) if isinstance(res, (list, tuple)) else []
        existing_ids = set()
        for r in res_list:
            if isinstance(r, tuple):
                existing_ids.add(r[0])
            else:
                existing_ids.add(r)

        for match in matches:
            nif = match.get("nif") or match.get("NIF", "")
            raison = match.get("raison_sociale") or match.get("raisonSociale", "")
            if not nif or not raison:
                continue

            partner = self.search([("kyb_nif", "=", nif)], limit=1)
            if not partner:
                statut = (match.get("statut_cnrc") or match.get("statutCnrc") or "INCONNU").upper()
                mapped_statut = "INCONNU"
                if statut in dict(self._fields["kyb_statut_cnrc"].selection):
                    mapped_statut = statut

                partner = self.create({
                    "name": raison,
                    "kyb_nif": nif,
                    "kyb_rc": match.get("rcNumber") or match.get("rc") or match.get("numero_rc") or match.get("rc_number", ""),
                    "kyb_statut_cnrc": mapped_statut,
                    "kyb_activite": match.get("activite") or match.get("activitePrincipale", ""),
                    "street": match.get("adresse") or match.get("adresseSiegeSocial", "") or match.get("wilaya", ""),
                    "city": match.get("wilaya", ""),
                    "kyb_last_verified": fields.Datetime.now(),
                })

            if partner.id not in existing_ids:
                if res_list and isinstance(res_list[0], tuple):
                    res_list.append((partner.id, partner.display_name or partner.name))
                else:
                    res_list.append(partner.id)
                existing_ids.add(partner.id)

        return res_list
