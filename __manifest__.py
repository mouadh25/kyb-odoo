# -*- coding: utf-8 -*-
{
    "name": "KYB — Algerian Corporate Identity & Temporal Fiscal Compliance",
    "version": "17.0.1.0.0",
    "category": "Accounting/Localisation",
    "summary": "Instant NIF/RC verification (<10ms), temporal strike-off audit (CIDTA Art. 176), and auto-completion for Algerian counterparties.",
    "description": """
KYB Sovereign Corporate Identity & Fiscal Verification Connector
=================================================================

Integrates the **KYB sovereign corporate identity, registry intelligence, and temporal evidence API**
(hosted at the Algérie Télécom Sovereign Cloud Datacenter, compliant with Law 18-07 / 25-11)
directly into Odoo's partner management and invoicing workflows.

Key Features
------------
* **Instant NIF & RC Auto-Completion (<10ms)**: Typing an Algerian Tax Identification Number (NIF) or Trade Registry (RC) into ``res.partner`` instantly auto-populates Raison Sociale, registered legal address, share capital, NIS, and Article d'Imposition.
* **Temporal Status Audit (CIDTA Art. 176 & CTCA Art. 30)**: Validates supplier registration standing at the exact date of the invoice, preventing VAT deduction disallowance on deregistered (radié) suppliers.
* **Real-time Name Autocomplete**: Overrides ``res.partner._name_search`` to query KYB's pre-indexed fuzzy search engine, providing instant autocomplete in many2one partner dropdowns.
* **Visual CNRC Status Badges**: Displays color-coded legal standing badges (ACTIF / RADIÉ / SUSPENDU) directly on partner views.
* **100% Sovereign & Confidential**: Operates in strict adherence to Algerian Law 18-07 on personal data protection. Zero data leaves Algerian sovereign soil.

Configuration
-------------
1. Install the ``conforme`` Python client (``pip install conforme``).
2. Configure Odoo system parameters in **Settings → Technical → System Parameters**:
   * ``conforme.api_key`` — Your provisioned KYB API key (e.g., ``sk_live_...`` or public test key ``sk_test_kyb_sandbox_key_001``).
   * ``conforme.base_url`` — The sovereign API endpoint (default: ``https://kyb.digidevagency.dz``).

Compatibility
-------------
* Odoo 16.0, 17.0, 18.0, 19.0, 20.0 (Community & Enterprise)
* Python ≥ 3.10
* Multi-company support enabled
    """,
    "author": "Mouadh Benhassine (Digidev Agency)",
    "website": "https://kyb.digidevagency.dz",
    "license": "LGPL-3",
    "depends": ["base", "contacts"],
    "data": [
        "views/res_config_settings_views.xml",
        "views/res_partner_views.xml",
    ],
    "external_dependencies": {
        "python": ["requests"],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
