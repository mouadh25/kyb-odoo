# Changelog — KYB Odoo Connector

All notable changes to the **KYB Odoo Connector** (`kyb_odoo`) are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) alongside Odoo's native versioning matrix.

---

## Odoo Version Matrix & Release Mapping

The KYB connector maintains a unified, backwards-compatible codebase engineered to support Algerian corporate ERP deployments across both long-term support (LTS) foundations and modern releases. In the Algerian enterprise and SME market, **Odoo 17** and **Odoo 19** represent the dominant production adoption, while **Odoo 16** is actively maintained across legacy SME installations, **Odoo 18** is deployed in production, and **Odoo 20** is supported as the latest released generation.

When packaged or deployed into an Odoo instance, the universal semantic version (`1.4.2`) is mapped to the corresponding Odoo major version:

| Odoo Target Version | Module Version Code | Market Adoption & Tier | Compatibility Status |
| :--- | :--- | :--- | :---: |
| **Odoo 20.0** (Community & Enterprise) | `20.0.1.4.2` | Current Released Generation | **🟢 Locked & Certified** |
| **Odoo 19.0** (Community & Enterprise) | `19.0.1.4.2` | **Primary Enterprise Adoption (Algeria)** | **🟢 Locked & Certified** |
| **Odoo 18.0** (Community & Enterprise) | `18.0.1.4.2` | Active Production Standard | **🟢 Locked & Certified** |
| **Odoo 17.0** (Community & Enterprise) | `17.0.1.4.2` | **Primary Enterprise Adoption (Algeria)** | **🟢 Locked & Certified** |
| **Odoo 16.0** (Community & Enterprise) | `16.0.1.4.2` | Legacy LTS / SME Installed Base | **🟢 Locked & Certified** |

---

## [1.4.2] - 2026-10-13 (Updated 2026-10-14)

### Odoo 16–20 Production Certification & Store Presentation Overhaul

#### Added
* **Official 7-Day Free Trial (100 Credits) Store Integration**:
  * Prominent hero trial showcase in `static/description/index.html` offering 100 free live CNRC/DGI verification credits and up to 3 sub-keys for test/staging/production instances.
  * Direct onboarding CTA linking to `https://kyb.digidevagency.dz/onboarding` (`target="_blank"`).
  * Direct API documentation reference linking to `https://kyb.digidevagency.dz/docs/scalar`.

#### Changed
* **Institutional Authority Store Presentation (`index.html`)**:
  * Complete purging of legacy indigo accents (`#533afd`) and artificial card border stripes.
  * Unified typography pairing Inter at weight 300 with negative tracking and tabular numerals (`tnum`).
  * Restrained monochromatic zinc palette (`#18181b` primary CTAs, `#ffffff` card surfaces, `#e4e4e7` hairline borders).

### Odoo 16.0 Production Certification & Legacy LTS Audit

#### Added
* **View `invisible` Architecture Universalization**:
  * Universalized XML views across Odoo 16–20 by removing field-level `invisible="..."` on header buttons, content groups, and alert cards.
  * Resolved fatal Odoo 16 server-side view compilation error (`ValueError: NameError: name 'state' is not defined` via `_postprocess_context_dependent`).
  * Converted temporal compliance audit action to a permanent form header button, allowing instant compliance audits on both draft and posted invoices.
* **ORM `_name_search` Signature Harmonization**:
  * Hardened `BaseModel._name_search` polyfill in `models/res_partner.py` to support Odoo 16's native `(name, args, operator, limit)` signature with dynamic `TypeError` handling.
* **Air-Gapped SOP Verification Loop on Clean Database (`odoo16_store_test_db`)**:
  * Clean installation verified (**43.93s** — fastest install time in the entire testing matrix, 0 errors, `state = 'installed'`, version `16.0.1.4.2`).
  * Extremely compact footprint (**37 MB** database footprint, 146.6 MiB container memory).
  * Real-world operational benchmark passed: Autocomplete (34.7ms), Corporate PM resolution (133.0ms), Live CNRC scraping (14.99s), Deep enrichment (93.4ms), Proactive webhook (37.6ms), Temporal invoice blocking (82.8ms).
  * 234-request progressive concurrency burst suite completed with 0 errors (Peak 46.3 RPS, P50 121.7ms).
  * Live Chrome DevTools visual audit on `https://odoo16.digidevagency.dz` passed with zero errors.

### Odoo 17.0 Production Certification & Personne Physique Resolution

#### Added
* **Personne Physique (Commerçants Individuels) Robust Legal Resolution**:
  * Added statutory handling for individual merchants under Algerian Commercial Code and Law 18-07.
  * Corrected `kyb_capital_social` mapping to explicitly indicate `"N/A (Patrimoine Individuel)"` reflecting Algerian statutory undivided patrimony rather than clearing fields.
  * Corrected `kyb_representant_legal` mapping to designate the titular individual owner (`Titulaire`) rather than expecting corporate manager appointments.
  * Bidirectional synchronization hardened between `kyb_nif` and native `vat` across individual and corporate contact profiles.
  * Unified autocomplete candidate mapping for individual sole proprietorships.
* **Air-Gapped SOP Verification Loop on Clean Database (`odoo17_store_test_db`)**:
  * Clean installation verified (47.34s, 0 errors, `state = 'installed'`, version `17.0.1.4.2`).
  * Lightweight footprint (38 MB database footprint, 160.5 MiB container memory).
  * Real-world operational benchmark passed: Autocomplete (42.2ms), Corporate PM resolution (148.5ms), Live CNRC scraping (3.54s), Deep enrichment (34.2ms), Proactive webhook (66.9ms), Temporal invoice blocking (103.4ms).
  * 234-request progressive concurrency burst (1 to 25 workers) with 0 errors and 53.5 RPS peak throughput.
* **Chrome DevTools Live UI Audit (`https://odoo17.digidevagency.dz`)**:
  * Verified 5 authentic views (Partner form, KYB tab, Personne Physique verified profile, Vendor bills tree, and Bill detail audit banner) with 100% responsive consistency under Odoo 17 OWL web client.

### Odoo 18.0 Production Certification & ORM Signature Harmonization

#### Added
* **BaseModel.name_search Keyword Argument Harmonization**:
  * Harmonized keyword argument passing in `res.partner` delegation to `args=domain` across Odoo 17.0–20.0 runtimes.
  * Resolves `TypeError: unexpected keyword argument 'domain'` on Odoo 18.0 ORM signature.
* **Air-Gapped SOP Verification Loop on Clean Database (`odoo18_store_test_db`)**:
  * Clean installation verified (56.41s, 0 errors, `state = 'installed'`, version `18.0.1.4.2`).
  * Zero memory leaks or excessive disk footprint (40 MB database footprint, 76.77 MiB container memory).
  * Real-world operational benchmark passed: Autocomplete (43.3ms), Corporate PM resolution (132.9ms), Live CNRC scraping (13.09s), Deep enrichment (98.1ms), Proactive webhook (68.5ms), Temporal invoice blocking (320.3ms).
  * 234-request progressive concurrency burst (1 to 25 workers) with 0 errors and 53.5 RPS peak throughput.
* **Chrome DevTools Live UI Audit (`https://odoo18.digidevagency.dz`)**:
  * Verified 4 authentic views (Partner form, KYB tab, Vendor bills tree, and Bill detail audit banner) with 100% responsive consistency under Odoo 18 web client.

### Odoo 19.0 Production Certification & Universal ORM Polyfill

#### Added
* **Universal `_name_search` Polyfill across Odoo 16 through 20**:
  * Safe delegation to parent `_name_search` under Odoo 16.0, and graceful fallback to native `name_search` under Odoo 17.0–20.0.
  * Eliminates `AttributeError` on Many2one partner selector dropdowns across modern ORM runtimes.
* **Air-Gapped SOP Verification Loop on Clean Database (`odoo19_store_test_db`)**:
  * Clean installation verified (53.69s, 0 errors, `state = 'installed'`, version `19.0.1.4.2`).
  * Real-world operational benchmark passed: Autocomplete (35.8ms), CEVITAL resolution (149.8ms), Live CNRC scraping (3.49s), Deep enrichment (70.8ms), Proactive webhook (43.1ms), Temporal invoice blocking (414.7ms).
  * 234-request progressive concurrency burst (1 to 25 workers) with 0 errors and 31.6 RPS peak throughput.
* **Chrome DevTools Live UI Audit (`https://odoo19.digidevagency.dz`)**:
  * Verified 4 authentic views (Partner form, KYB tab, Vendor bills tree, and Bill detail audit banner) with 100% responsive consistency under Odoo 19 purple web client.

### Odoo 20.0 Production Lock & Executive Manual Suite (2026-10-12)

#### Added
* **Executive User Manual (11-Page Master PDF)**:
  * Packaged `doc/USER_MANUAL.pdf` with comprehensive workflows, step-by-step illustrations, and authentic full-width runtime screenshots.
  * Dedicated guidance for Monthly Tax Closing (G50 Safety Net), FAQ, and Technical Support procedures.
  * Formulated neutral, factual compliance terminology meeting enterprise audit standards.
* **Fiscal Duplicate Warning & Blocking Policy Controls**:
  * Added `kyb_duplicate_nif_policy` in Settings (`warn`, `block`, `ignore`).
  * Onchange handlers immediately alert users of duplicate NIF entries with direct navigation to existing partner records.
  * Autocomplete displays `• ⚠️ Existant (#ID)` for previously registered counterparties.

---

## [1.4.1] - 2026-10-12

### Fiscal Duplicate Governance, Legal Entity Partitioning & Integrator Suite

#### Added
* **Fiscal Duplicate Identifier (NIF) Protection**:
  * Configurable company-wide policy for duplicate tax identification numbers.
  * Seamless interoperability with native Odoo Contact Deduplication Wizard (`base.partner.merge.automatic.wizard`).
* **Corporate Entity (PM) vs Individual (PP) Privacy Controls**:
  * Distinction between Corporate Entities (`is_company = True`, open fuzzy autocomplete) and Natural Persons (`is_company = False`, deterministic-only resolution).
  * Guarantees compliance with national data privacy standards.
* **Comprehensive Integrator & Administrator Technical Manual**:
  * Packaged `doc/INTEGRATOR_MANUAL.md` detailing system parameters, data dictionaries, duplicate workflows, and troubleshooting.
* **Universal In-Connector Décret 05-468 Formatter & Validator**:
  * Native Python parsing and formatting engine for Algerian Trade Register numbers (`format_official_rc`).
  * Normalizes all partner entries to the official `WW/00-XXXXXXX[A|B|C|D]YY` format across all 69 Wilayas.
* **Bidirectional RC & Company Registry Synchronization**:
  * Automatically synchronizes Odoo's native `company_registry` with official Trade Register formats on invoice reports.

---

## [1.3.9] - 2026-10-11

### Dual Official RC Format (Décret 05-468), 69 Wilayas & Zero-Refresh UI

#### Added
* **Official Commercial Registry Invoicing Format (Décret exécutif n° 05-468)**:
  * Full dual representation: internal index + official invoicing standard.
  * Ensures printed customer and vendor invoices comply with commercial invoicing regulations.
* **National 69 Wilayas Regulatory Update (Loi n° 26-06)**:
  * Full validation for newly established Wilayas 59 through 69.
* **Zero-Refresh Reactive UI on NIF Entry**:
  * Instant form auto-population upon NIF/VAT entry without requiring manual page reload.

---

## [1.1.0] - 2026-10-10

### Dual Activity Streams, Full i18n (FR/AR) & Institutional Visual Design

#### Added
* **Dual-Stream CNRC Business Activity Display**:
  * Dominant primary economic activity with official NAE code.
  * Secondary activities displayed as clean structured reference list.
* **Multi-Language Internationalization (i18n)**:
  * Native catalogs for French (`fr_FR`, `fr`), Modern Standard Arabic (`ar_001`, `ar`), and English (`en_US`).
* **High-Resolution Institutional Insignia**:
  * Official light shield icon (`icon.png`) and verified App Switcher presence.

---

## [1.0.0] - 2026-10-01

### Sovereign Corporate Identity & Temporal Fiscal Verification Engine

#### Added
* **Instant NIF & RC Auto-Completion**:
  * Real-time resolution of Algerian Tax Identification Numbers (NIF) and Commercial Registry numbers (RC).
* **Temporal Status Audit Engine (CIDTA Art. 176 & CTCA Art. 30)**:
  * Automated standing verification against vendor bill dates to protect tax deductibility.
* **Fuzzy Name Autocomplete in Many2one Dropdowns**:
  * Seamless partner suggestions when typing company names.
* **Color-Coded Status Badges**:
  * Visual legal standing badges: `ACTIF` (green), `RADIÉ` (red), `SUSPENDU` (amber).
* **Preemptive Socket Warmup & Connection Pooling**:
  * Sub-80ms lookup latency with persistent HTTP connection reuse.
* **Synthetic Test Fixtures**:
  * Deterministic test NIFs for sandbox integration.
* **100% Sovereign Data Residency**:
  * Server-side Python implementation connecting directly to Algérie Télécom Cloud.
