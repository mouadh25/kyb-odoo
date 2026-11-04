# -*- coding: utf-8 -*-
import logging
from odoo import release
from odoo.modules import module as odoo_module

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Ensure ir_module_module.latest_version reflects the newly hot-reloaded manifest version."""
    try:
        for attr_name in dir(odoo_module):
            attr_obj = getattr(odoo_module, attr_name, None)
            if hasattr(attr_obj, "cache_clear"):
                try:
                    attr_obj.cache_clear()
                except Exception:
                    pass
        manifest = odoo_module.load_information_from_description_file("kyb_odoo")
        raw_ver = manifest.get("version") or "2.0.8"
        series = getattr(release, "serie", None) or getattr(release, "major_version", "20.0")
        full_ver = raw_ver if str(raw_ver).startswith(f"{series}.") else f"{series}.{raw_ver}"
        cr.execute(
            "UPDATE ir_module_module SET latest_version = %s WHERE name = 'kyb_odoo'",
            (full_ver,),
        )
        _logger.info("KYB post-migrate: confirmed latest_version = %s", full_ver)
    except Exception as exc:
        _logger.warning("KYB post-migrate version sync warning: %s", exc)
