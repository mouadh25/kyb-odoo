# Changelog — KYB Odoo Connector

All notable changes to the **KYB Odoo Connector** (`kyb_odoo`) are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) alongside Odoo's native versioning matrix.

---

## Odoo Version Matrix & Release Mapping

The KYB connector maintains a unified, backwards-compatible codebase supporting Algerian corporate ERP deployments across supported Long-Term Support (LTS) foundations and modern release generations.

When deployed into an Odoo instance, the universal semantic version maps to the corresponding major version:

| Odoo Target Version | Module Version Code | Market Tier | Compatibility Status |
| :--- | :--- | :--- | :---: |
| **Odoo 20.0** (Community & Enterprise) | `20.0.2.0.4` | Current Released Generation | **🟢 Locked & Certified** |
| **Odoo 19.0** (Community & Enterprise) | `19.0.2.0.4` | Primary Enterprise Adoption (Algeria) | **🟢 Locked & Certified** |
| **Odoo 18.0** (Community & Enterprise) | `18.0.2.0.4` | Active Production Standard | **🟢 Locked & Certified** |
| **Odoo 17.0** (Community & Enterprise) | `17.0.2.0.4` | Primary Enterprise Adoption (Algeria) | **🟢 Locked & Certified** |
| **Odoo 16.0** (Community & Enterprise) | `16.0.2.0.4` | Legacy LTS / SME Installed Base | **🟢 Locked & Certified** |

---

## [2.0.4] - 2026-10-24

### Added
* **Predictive Company Autocomplete Dropdown:**
  Interactive counterparty search rendering real-time legal standing badges (`Actif` in green / `Radié` in red) aligned to the far right, official formatted Trade Register (RC), Wilaya, legal structure, and duplicate counterparty warning (`• ⚠️ Existant (#ID)`).
* **Fiscal Standing Prioritization:**
  Dynamic candidate sorting prioritizing active commercial enterprises before deregistered vendors in autocomplete search results.
* **Configurable Autocomplete Filtering:**
  Added customizable settings in Odoo General Settings for result filtering (`all` vs `active_only`) and configurable candidate display limits (10 to 30, default 20).
* **Automated Update Policy Governance:**
  Formalized ITIL-aligned update policies in General Settings (`Manual` vs `Automatic`) with scheduled daily maintenance checks and 1-click in-app upgrades.

### Changed
* **Official Décret 05-468 RC Canonical Normalization:**
  Enforced canonical 16-character Trade Register formatting (`WW/00-XXXXXXX[A|B|C|D]YY`) on field exit with automatic padding and bidirectional registry synchronization.
* **Neutral Chatter Audit Trail & Invoice Compliance Notices:**
  Standardized partner chatter verification cards and vendor bill compliance notices to state `Consultation Registre Officiel` uniformly across all Odoo editions.
* **Chatter Deduplication Governance:**
  Added strict duplicate prevention in `res.partner` chatter to avoid redundant verification cards when re-verifying a counterparty.
* **Web Client Asset Architecture Hardening:**
  Streamlined asset bundle declarations and eliminated redundant template overrides to ensure clean CSS/OWL compilation and seamless cross-version compatibility across Odoo 16.0–20.0.

### Fixed
* **Cross-Version Client Serialization Stabilization:**
  Resolved client-side date serialization constraints during counterparty selection on modern web runtimes (Odoo 20.0). Dates are written securely via server-side ORM methods.
* **Multi-Version Universal Compatibility:**
  Certified 100% operational parity and passing automated test suites across all 5 Odoo generations: Odoo 16.0 LTS, 17.0, 18.0, 19.0, and 20.0.

---

## [1.4.6] - October 2026

### Fixed
* **Date Synchronization & Candidate Switching:** Resolved an issue where rapidly switching counterparty candidates in autocomplete retained stale establishment dates from previously selected candidates, causing inverted date sequences. Both `kyb_date_creation` and `kyb_date_radiation` are now synchronically bound to the newly selected candidate with defensive chronological invariants (`immatriculation <= radiation`).
* **Radiation Date Visibility in Chatter:** Added official `Date de Radiation` display to the institutional chatter audit card for deregistered (radié) counterparties.
* **Algerian Administrative Address Decomposition (Commune vs Wilaya):** Implemented authoritative address decomposition (`_split_algerian_commune_wilaya`) parsing CNRC dual-column formats (`COMMUNE/WILAYA`, e.g. `IBN ZIAD/CONSTANTINE`). Counterparties registered in peripheral CNRC antennae now correctly map to their sovereign Wilaya state (e.g. State 25 - Constantine) without polluting city and address fields.
* **Institutional Monochromatic Card Design:** Aligned chatter audit cards with Law 25-11 institutional White & Zinc typography tokens (eliminating AI blue-purple artifacts and lateral border accents).

---

## [1.4.5] - October 2026

### Improved
* **Official Registry Terminology ("Date d'Immatriculation"):** Standardized the counterparty registration date label to **Date d'Immatriculation** across partner forms and chatter audit trails to align strictly with official CNRC (Centre National du Registre du Commerce) terminology and Algerian commercial standards (Décret 05-468).
* **Multi-Format Date Interpretation:** Enhanced registration date parsing supporting standard Algerian registry formats (ISO, DD/MM/YYYY, and registration year) with seamless localization.

### Added
* **Dual-Field ORM Compatibility Alias:** Added `kyb_date_immatriculation` as an alias alongside `kyb_date_creation`, ensuring zero-migration backward compatibility for custom reporting, third-party addons, and automated workflows.

### Fixed
* **Native Autocomplete Selection Stabilization:** Resolved a client-side interface error occurring during counterparty selection from Odoo's native autocomplete dropdown, ensuring smooth, instantaneous form population across all web client generations.
* **Multi-Version Python Compatibility:** Reinforced syntax and runtime compatibility across Python 3.10, 3.11, and 3.12 environments supporting Odoo 16.0 LTS through Odoo 20.0.

---

## [1.4.4] - October 2026

### Added
* **Creation Date Tracking (`kyb_date_creation`):** Added official establishment and registration date support for Algerian counterparties with multilingual localization (FR, EN, AR).
* **National Registry Support (Wilaya 99):** Extended recognition for national commercial registrations and large enterprises (CNRC Central).

### Improved
* **Official RC Formatting (Décret 05-468):** Enhanced registration formatting with dynamic registration year derivation.

---


## [1.4.3] - October 2026


### Fixed: Native Autocomplete Selection & Counterparty Legal Enrichment
* **Partner Autocomplete Deep Enrichment:** Resolved issue where selecting a suggested counterparty from Odoo's native `partner_autocomplete` dropdown did not populate legal fiscal fields. Both candidate selection and interactive `_onchange_kyb_rc` now reliably populate Raison Sociale, NIF (VAT), Trade Register (RC), Statistical Number (NIS), Share Capital, and Legal Address.
* **Corporate vs Individual Persona Integrity:** Enforced Décret 05-468 categorization: Personnes Morales (Commercial Companies) automatically configure `is_company = True` with standardized `kyb_forme_juridique` (SPA, SARL, EURL, SNC), while Personnes Physiques (sole proprietors, individual traders) preserve `is_company = False` and `company_type = "person"`.
* **Many2one Dictionary Mapping:** Hardened partner creation and writing against varied dictionary shapes returned by Odoo's client-side OWL autocomplete controller.

### Improved: Performance & Network Resilience
* **Keystroke Storm Immunity:** Added 60-second in-memory candidate cache in `_NativeKybClient` (`_candidates_cache`), preventing duplicate network queries during rapid typing in partner search fields.
* **Session & Localization Initialization:** Ensured HTTP `requests.Session()` and request language headers (`self.lang`) are properly initialized across threaded worker processes.
* **Dependency Precision:** Explicitly declared `partner_autocomplete` in `__manifest__.py` dependencies.

---

## [1.4.2] - October 2026

### Improved: Multi-Version Runtime Compatibility Across Odoo 16 to 20
* **Multi-Version Architecture:** Harmonized view structures and dynamic field attributes across all supported Odoo LTS and current release generations (Odoo 16.0 through 20.0).
* **Partner Search & Autocomplete:** Enhanced partner lookup and fuzzy search delegation in relational dropdown fields.
* **Natural Person (PP) Profile Resolution:** Enhanced handling for sole proprietorships and individual merchants in accordance with national commercial standards.
* **Developer Resources:** Added direct references to self-service developer documentation and onboarding endpoints.

### Fixed: View Compilation on Odoo 16 LTS
* Resolved view attribute constraints on form action buttons across older Odoo client runtimes.
* Fixed keyword argument handling in partner lookup delegation methods on Odoo 18.0.

---

## [1.4.1]

### Improved: Duplicate Identification Governance & Validation
* **Fiscal Duplicate Policies:** Introduced configurable settings to warn or restrict duplicate Tax Identification Number (NIF) registrations.
* **Trade Register Standardization (Décret 05-468):** Enhanced automated formatting and validation of official Commercial Registry (RC) numbers across all 69 Wilayas.
* **Contact Deduplication:** Improved integration with native partner merge and contact deduplication workflows.
* **Technical Documentation:** Packaged technical integrator manual detailing system parameters and field mapping specifications.

---

## [1.3.9]

### Improved: Regional Regulatory Coverage & Dynamic Forms
* **Regulatory Updates:** Updated administrative wilaya validation to encompass Wilayas 59 through 69.
* **Dynamic Form Population:** Improved client-side responsiveness during tax identifier entry.
* **Invoicing Compliance:** Reinforced official registry formatting synchronization on printed reports.

---

## [1.1.0]

### Improved: Multi-Language Localization & Activity Classifications
* **Internationalization:** Added full localized catalogs for French, Modern Standard Arabic, and English.
* **Business Activity Mapping:** Improved display of primary and secondary official economic activity classifications.
* **User Interface:** Added standard branding and application icon assets.

---

## [1.0.0]

### Initial Release: Core KYB Verification & Compliance Engine
* **Identifier Resolution:** Real-time auto-completion of Algerian Tax Identification Numbers (NIF) and Trade Registry numbers (RC).
* **Temporal Invoice Compliance:** Automated vendor standing verification relative to transaction dates for tax deductibility protection.
* **Legal Standing Indicators:** Standard status indicators for active, deregistered, and suspended corporate records.
* **Connection Pooling:** Built-in client connection reuse for high-throughput enterprise environments.
