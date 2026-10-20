# -*- coding: utf-8 -*-
{
    "name": "KYB — Algerian Corporate Identity & Temporal Fiscal Compliance",
    "version": "19.0.1.4.4",
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

Required Apps (Client-Facing Naming)
-------------------------------------
* **Invoicing** (French: *Facturation* — technical module: ``account``):
  Free Community application. Does **NOT** require the paid Enterprise "Accounting" (*Comptabilité* / ``account_accountant``) module. Provides vendor bills, customer invoices, and fiscal settings.
* **Contacts** (French: *Contacts* — technical module: ``contacts``):
  Free Community directory application. Provides counterparty records, address management, and legal fiscal badges.
* **Partner Autocomplete** (technical module: ``partner_autocomplete``):
  Standard Odoo framework engine providing interactive typing suggestions on partner names and automatic company enrichment.

Version-Specific Details
------------------------
* **Odoo 16.0, 17.0, 18.0, 19.0**:
  - Requires the standard free **Invoicing** (*Facturation*), **Contacts**, and **Partner Autocomplete** apps.
  - Activating KYB automatically installs both apps if they are not already installed.
* **Odoo 20.0**:
  - The **Invoicing** (*Facturation*) engine is pre-bundled in the foundational commercial installation with **Contacts** active by default.

Configuration
-------------
1. Navigate to **Invoicing (or General Settings) → Configuration → Settings → KYB Sovereign Verification**:
   * **API Key**: Enter your provisioned KYB API key (e.g., ``sk_live_...`` or public sandbox key ``sk_test_kyb_sandbox_key_001``).
   * **Base URL**: The sovereign Algerian API endpoint (default: ``https://kyb.digidevagency.dz``).
2. Zero external dependencies required: the connector operates via native HTTP requests.

Compatibility
-------------
* Odoo 16.0, 17.0, 18.0, 19.0, 20.0 (Community & Enterprise)
* Python ≥ 3.10
* Multi-company support enabled
    """,
    "author": "Mouadh Benhassine (Digidev Agency)",
    "website": "https://kyb.digidevagency.dz",
    "license": "LGPL-3",
    "images": [
        "static/description/banner.png",
        "static/description/screenshot_pm_corporate.png",
        "static/description/screenshot_temporal_audit.png",
        "static/description/screenshot_autocomplete.png",
    ],
    "depends": [
        "base",                  # Odoo Core Engine
        "contacts",              # Client-Facing App: "Contacts" (res.partner)
        "account",               # Client-Facing App: "Invoicing" / Facturation (Free Community module, NOT paid Accounting)
        "partner_autocomplete",  # Native Odoo Partner Autocomplete Engine
    ],
    "data": [
        "security/kyb_security.xml",
        "data/kyb_cron.xml",
        "views/res_config_settings_views.xml",
        "views/kyb_menus.xml",
        "views/res_partner_views.xml",
        "views/account_move_views.xml",
    ],
    "external_dependencies": {
        "python": ["requests"],
    },
    "installable": True,
    "application": True,
    "sequence": 10,
    "auto_install": False,
}
