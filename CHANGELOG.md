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
| **Odoo 20.0** (Community & Enterprise) | `20.0.1.4.2` | Current Released Generation | **🟢 Locked & Certified** |
| **Odoo 19.0** (Community & Enterprise) | `19.0.1.4.2` | Primary Enterprise Adoption (Algeria) | **🟢 Locked & Certified** |
| **Odoo 18.0** (Community & Enterprise) | `18.0.1.4.2` | Active Production Standard | **🟢 Locked & Certified** |
| **Odoo 17.0** (Community & Enterprise) | `17.0.1.4.2` | Primary Enterprise Adoption (Algeria) | **🟢 Locked & Certified** |
| **Odoo 16.0** (Community & Enterprise) | `16.0.1.4.2` | Legacy LTS / SME Installed Base | **🟢 Locked & Certified** |

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
