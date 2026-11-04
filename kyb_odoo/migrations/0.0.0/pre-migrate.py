# -*- coding: utf-8 -*-
import importlib
import logging
import os
import sys
from odoo import models, release
from odoo.modules import module as odoo_module

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Hot-reload kyb_odoo Python models during in-place module upgrades
    so 1-click upgrades (action_upgrade_kyb_module / button_immediate_upgrade)
    apply Python code changes immediately in memory without requiring a server restart.
    """
    try:
        # 1. Ensure shared bind-mount permissions allow all Odoo containers (uid 100 & 101) to read/write
        addon_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        for root, dirs, files in os.walk(addon_dir):
            for d in dirs:
                try:
                    os.chmod(os.path.join(root, d), 0o777)
                except Exception:
                    pass
            for f in files:
                try:
                    os.chmod(os.path.join(root, f), 0o666)
                except Exception:
                    pass

        # 2. Clear cached manifest dictionaries in odoo.modules.module (@lru_cache)
        for attr_name in dir(odoo_module):
            attr_obj = getattr(odoo_module, attr_name, None)
            if hasattr(attr_obj, "cache_clear"):
                try:
                    attr_obj.cache_clear()
                except Exception:
                    pass

        # 3. Purge cached kyb_odoo model classes in MetaModel.module_to_models and sys.modules,
        #    then immediately re-import odoo.addons.kyb_odoo so registry.load(cr, package)
        #    registers the freshly updated classes in memory.
        meta_cls = type(models.Model)
        mod_map = getattr(meta_cls, "module_to_models", None)
        if isinstance(mod_map, dict):
            mod_map["kyb_odoo"] = []

        for mod_name in list(sys.modules.keys()):
            if mod_name == "odoo.addons.kyb_odoo" or mod_name.startswith("odoo.addons.kyb_odoo."):
                sys.modules.pop(mod_name, None)

        importlib.invalidate_caches()
        importlib.import_module("odoo.addons.kyb_odoo")

        # 4. Refresh package version metadata in caller frame and database
        manifest = odoo_module.load_information_from_description_file("kyb_odoo")
        raw_ver = manifest.get("version") or "2.0.8"
        series = getattr(release, "serie", None) or getattr(release, "major_version", "20.0")
        full_ver = raw_ver if str(raw_ver).startswith(f"{series}.") else f"{series}.{raw_ver}"

        for depth in (1, 2, 3):
            try:
                frame = sys._getframe(depth)
                pkg = frame.f_locals.get("pkg") or frame.f_locals.get("package")
                if pkg is not None:
                    if hasattr(pkg, "data") and isinstance(pkg.data, dict):
                        pkg.data["version"] = full_ver
                    if hasattr(pkg, "installed_version"):
                        pkg.installed_version = full_ver
            except Exception:
                pass

        cr.execute(
            "UPDATE ir_module_module SET latest_version = %s WHERE name = 'kyb_odoo'",
            (full_ver,),
        )
        _logger.info(
            "KYB pre-migrate: hot-reloaded kyb_odoo (%s) into module_to_models (%d models)",
            full_ver,
            len(mod_map.get("kyb_odoo", [])) if isinstance(mod_map, dict) else -1,
        )
    except Exception as exc:
        _logger.warning("KYB pre-migrate hot-reload warning: %s", exc)
