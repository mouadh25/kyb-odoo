# -*- coding: utf-8 -*-
import logging
import sys
from odoo.models import MetaModel

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Hot-reload kyb_odoo Python models during in-place module upgrades
    so 1-click upgrades (action_upgrade_kyb_module / button_immediate_upgrade)
    apply Python code changes immediately in memory without requiring a server restart.
    """
    try:
        MetaModel.module_to_models["kyb_odoo"] = []
        for mod_name in list(sys.modules.keys()):
            if mod_name == "odoo.addons.kyb_odoo" or mod_name.startswith("odoo.addons.kyb_odoo."):
                sys.modules.pop(mod_name, None)
        _logger.info("KYB pre-migrate: purged cached kyb_odoo modules from sys.modules for clean hot-reload (from %s)", version)
    except Exception as exc:
        _logger.warning("KYB pre-migrate hot-reload warning: %s", exc)
