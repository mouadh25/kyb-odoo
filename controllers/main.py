# -*- coding: utf-8 -*-
import logging
from odoo import http
from odoo.http import request
try:
    from ..models.res_partner import _get_kyb_client
except (ImportError, ValueError):
    from models.res_partner import _get_kyb_client

_logger = logging.getLogger(__name__)


class KybAutocompleteController(http.Controller):

    @http.route(["/kyb/autocomplete", "/conforme/autocomplete"], type="json", auth="user")
    def autocomplete(self, q, **kwargs):
        """
        AJAX call wrapper to query the KYB Gateway for fuzzy autocomplete.
        
        Usage in JS:
            ajax.jsonRpc('/kyb/autocomplete', 'call', {'q': 'my company'})
            .then(function (data) { ... });
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
