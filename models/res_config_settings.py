# -*- coding: utf-8 -*-
"""
KYB Configuration Settings — Enterprise settings panel for sovereign API credentials.
Allows configuring API keys and Gateway URLs without requiring Developer Mode.
"""

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    kyb_api_key = fields.Char(
        string="KYB Secret API Key",
        config_parameter="kyb.api_key",
        help="Clé d'API secrète KYB (e.g. sk_live_... pour la production ou sk_test_conforme_sandbox_key_001 pour le bac à sable gratuit).",
    )
    kyb_base_url = fields.Char(
        string="KYB Gateway Base URL",
        config_parameter="kyb.base_url",
        default="https://kyb.digidevagency.dz",
        help="URL du gateway souverain KYB (par défaut: https://kyb.digidevagency.dz).",
    )
