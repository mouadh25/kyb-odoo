# Changelog — KYB Odoo Connector

All notable changes to the **KYB Odoo Connector** (`kyb_odoo`) are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) alongside Odoo's native versioning matrix.

---

## Odoo Version Matrix & Release Mapping

The KYB connector maintains a unified, backwards-compatible codebase supporting Algerian corporate ERP deployments across supported Long-Term Support (LTS) foundations and modern release generations.

When deployed into an Odoo instance, the universal semantic version (`1.4.2`) maps to the corresponding major version:

| Odoo Target Version | Module Version Code | Market Tier | Compatibility Status |
| :--- | :--- | :--- | :---: |
| **Odoo 20.0** (Community & Enterprise) | `20.0.1.4.4` | Current Released Generation | **🟢 Locked & Certified** |
| **Odoo 19.0** (Community & Enterprise) | `19.0.1.4.4` | Primary Enterprise Adoption (Algeria) | **🟢 Locked & Certified** |
| **Odoo 18.0** (Community & Enterprise) | `18.0.1.4.4` | Active Production Standard | **🟢 Locked & Certified** |
| **Odoo 17.0** (Community & Enterprise) | `17.0.1.4.4` | Primary Enterprise Adoption (Algeria) | **🟢 Locked & Certified** |
| **Odoo 16.0** (Community & Enterprise) | `16.0.1.4.4` | Legacy LTS / SME Installed Base | **🟢 Locked & Certified** |

---

## [1.4.4] - October 2026

### Added: Date de Création & National Registry Wilaya 99 Support
* **Date de Création / Immatriculation (`kyb_date_creation`):** Added official creation date field on `res.partner` and partner views, automatically synchronized from CNRC immatriculation date, displayed in the verification card, and tracked in Odoo chatter logs.
* **National Registry (Wilaya 99 - Grandes Entreprises):** Expanded Décret 05-468 regex engines to support CNRC National Registries (e.g. NAFTAL, Sonatrach with prefix `99B` and `99/00-XXXXXXXB`), preventing rejection of national corporate identifiers.
* **Décret 05-468 Hardening & Accurate Year Suffix:** Hardened `format_official_rc` to dynamically extract the registration year from `kyb_date_creation`, eliminating legacy wilaya duplication and ensuring strict compliance with Algerian official invoicing standards.
* **Multilingual Localization:** Complete translations for creation date added to French (`Date de Création`), English (`Date of Creation`), and Arabic (`تاريخ التأسيس / القيد بالسجل التجاري`).

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
