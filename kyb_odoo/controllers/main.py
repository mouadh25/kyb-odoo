# -*- coding: utf-8 -*-
import hashlib
import hmac
import json
import logging
from odoo import http
from odoo.http import request

try:
    from odoo.tools import html_escape
except ImportError:
    import html
    html_escape = html.escape
try:
    from markupsafe import Markup
except ImportError:
    Markup = lambda s: s

try:
    from ..models.res_partner import _get_kyb_client, _get_config_param
except (ImportError, ValueError):
    from models.res_partner import _get_kyb_client, _get_config_param

_logger = logging.getLogger(__name__)


import odoo

_ROUTE_TYPE = "jsonrpc" if getattr(odoo.release, "version_info", (0,))[0] >= 19 else "json"


class KybAutocompleteController(http.Controller):

    @http.route(["/kyb/autocomplete", "/conforme/autocomplete"], type=_ROUTE_TYPE, auth="user")
    def autocomplete(self, q, **kwargs):
        """
        AJAX call wrapper to query the KYB Gateway for fuzzy autocomplete.
        """
        if not q or len(q) < 3:
            return []

        try:
            client = _get_kyb_client(request.env)
            matches = client.search.autocomplete(q, poll=False)
            client.close()
            return matches or []
        except Exception as exc:
            _logger.warning("KYB AJAX autocomplete controller failed: %s", exc)
            return {"error": str(exc)}


class KybWebhookController(http.Controller):

    @http.route("/kyb/webhook", type=_ROUTE_TYPE, auth="public", methods=["POST"], csrf=False)
    def receive_webhook(self, **kwargs):
        """
        Inbound Webhook Receiver for KYB Proactive Alerts (Loi 25-11):
        Accepts push notifications from KYB background workers.
        Updates partner status and re-audits open vendor bills.
        """
        configured_key = _get_config_param(request.env, "kyb.api_key", default="")
        if not configured_key:
            return {"status": "error", "message": "KYB API key not configured"}

        # Constant-time authentication verification (Bearer Token or HMAC-SHA256 signature)
        data = request.jsonrequest if hasattr(request, "jsonrequest") else kwargs
        auth_header = request.httprequest.headers.get("Authorization", "")
        sig_header = request.httprequest.headers.get("X-KYB-Signature", "")
        token_val = kwargs.get("token") or (data.get("token") if isinstance(data, dict) else None)

        is_authenticated = False
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
            if hmac.compare_digest(token, configured_key):
                is_authenticated = True
        elif token_val and hmac.compare_digest(str(token_val), configured_key):
            is_authenticated = True
        elif sig_header:
            try:
                raw_body = request.httprequest.get_data()
                expected_sig = hmac.new(configured_key.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
                if hmac.compare_digest(sig_header, expected_sig):
                    is_authenticated = True
            except Exception:
                is_authenticated = False

        if not is_authenticated:
            _logger.warning("KYB Webhook unauthorized access attempt rejected from %s", getattr(request.httprequest, "remote_addr", "unknown"))
            return {"status": "error", "message": "Unauthorized: invalid signature or bearer token"}

        if not data:
            return {"status": "error", "message": "Empty payload"}

        event_type = data.get("event") or data.get("event_type")
        payload = data.get("payload") or data

        _logger.info("KYB Webhook received: event=%s", event_type)

        if event_type in ("entity.status_changed", "entity.strike_off", "compliance.completed"):
            nif = payload.get("nif")
            rc = payload.get("rc_number") or payload.get("rc")
            new_status = payload.get("statut_cnrc") or payload.get("status")
            date_rad = payload.get("date_radiation") or payload.get("dateRadiation")

            domain = []
            if nif:
                domain.append(("kyb_nif", "=", nif))
            elif rc:
                domain.append(("kyb_rc", "=", rc))

            if domain:
                partner = request.env["res.partner"].sudo().search(domain, limit=1)
                if partner:
                    vals = {}
                    if new_status:
                        mapped = "RADIE" if "RAD" in str(new_status).upper() else ("ACTIF" if "ACT" in str(new_status).upper() else partner.kyb_statut_cnrc)
                        vals["kyb_statut_cnrc"] = mapped
                    if date_rad:
                        vals["kyb_date_radiation"] = str(date_rad)[:10]

                    if vals:
                        partner.write(vals)
                        safe_stat = html_escape(str(vals.get("kyb_statut_cnrc", "")))
                        partner.message_post(
                            body=Markup(
                                f"<div class='alert alert-warning'>"
                                f"<strong>Alerte Webhook KYB :</strong> Statut légal mis à jour via notification proactive (Statut: {safe_stat})."
                                f"</div>"
                            ),
                            subtype_xmlid="mail.mt_note",
                        )

                    # Re-audit any open draft vendor bills for this partner
                    open_bills = request.env["account.move"].sudo().search([
                        ("partner_id", "=", partner.id),
                        ("move_type", "in", ("in_invoice", "in_refund")),
                        ("state", "=", "draft"),
                    ])
                    for bill in open_bills:
                        bill._audit_temporal_compliance()

                    return {
                        "status": "success",
                        "partner_id": partner.id,
                        "partner_name": partner.name,
                        "updated_status": partner.kyb_statut_cnrc,
                        "audited_bills": len(open_bills),
                    }

        return {"status": "ignored", "event": event_type}
