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
| **Odoo 20.0** (Community & Enterprise) | `20.0.2.0.9` | Current Released Generation | **🟢 Locked & Certified** |
| **Odoo 19.0** (Community & Enterprise) | `19.0.2.0.9` | Primary Enterprise Adoption (Algeria) | **🟢 Locked & Certified** |
| **Odoo 18.0** (Community & Enterprise) | `18.0.2.0.9` | Active Production Standard | **🟢 Locked & Certified** |
| **Odoo 17.0** (Community & Enterprise) | `17.0.2.0.9` | Primary Enterprise Adoption (Algeria) | **🟢 Locked & Certified** |
| **Odoo 16.0** (Community & Enterprise) | `16.0.2.0.9` | Legacy LTS / SME Installed Base | **🟢 Locked & Certified** |
| **Odoo 15.0** (Community & Enterprise) | `15.0.2.0.9` | Extended Legacy Enterprise Support | **🟢 Locked & Certified** |
| **Odoo 14.0** (Community & Enterprise) | `14.0.2.0.9` | Mature LTS Legacy Deployment | **🟢 Locked & Certified** |

---

## [2.0.9] - 2026-11-07 (Hardened 2026-11-09)

### Security & Hardening (Enterprise Audit SEC-1..5)
* **SEC-1 (Stored XSS Neutralization):**
  * Applied `html_escape()` across all dynamic variables interpolated into Chatter cards (`res_partner.py`), vendor bill & customer invoice compliance alerts (`account_move.py`), and webhook alert messages (`main.py`). Malicious payloads (`<script>`, `<img onerror>`, `<b>` tags) are converted into harmless HTML entities before `Markup()` wrapping.
* **SEC-2 (Timing-Safe Inbound Webhook Authentication):**
  * Integrated constant-time `hmac.compare_digest` in `receive_webhook()` controller for both `Authorization: Bearer <token>` and HMAC-SHA256 `X-KYB-Signature` verification, eliminating timing attack vectors.
* **SEC-3 (Access Rights & Privilege Escalation Protection):**
  * Enforced internal user checks (`self.env.user.has_group('base.group_user')`) on `action_verify_kyb` and `enrich_company_message_post`, raising `AccessError` for portal or public users.
* **SEC-4 (SSRF Defense & Protocol Whitelisting):**
  * Validated URL schemes in `_get_kyb_client()`, restricting `kyb.base_url` to `http` and `https` and automatically resetting invalid protocols (`file://`, `gopher://`, `ftp://`) to the sovereign gateway URL.
* **SEC-5 (Graceful Autocomplete Degradation):**
  * Enclosed `autocomplete_by_name()` and `autocomplete_by_vat()` with defensive exception containment returning `[]` upon network interruptions without freezing user input.
* **Algerian Territorial & Fiscal Precision:**
  * Added `ALGERIAN_WILAYAS_ARABIC` dictionary covering 58/69 Wilayas in Arabic script (`قسنطينة`, `الجزائر`, `سطيف`, `وهران`, `البليدة`).
  * Added Pre-2022 single-0 NIF extraction (e.g. NAFTAL `099916000969164` -> Wilaya `16` Alger / Cheraga).
  * Date overwrite protection preventing certified creation/radiation dates from being wiped by partial updates.

### Added
* **Décret Exécutif n° 05-468 (Art. 3) Personne Physique Statutory Identity Engine:**
  * Enforces Algerian commercial law naming for individual merchants (Category A/C & Auto-Entrepreneurs): civil identity (`NOM PRÉNOM`) is legally primary, formatted as `NOM PRÉNOM (NOM COMMERCIAL)` when a distinct commercial sign exists (automatically rejecting BOAL address fragments such as `ESC 02`, `LOT 14`, `BLOC B`, `CITE ...`), else strictly `NOM PRÉNOM`.
  * Standardizes individual merchant governance fields: `kyb_representant_legal = NOM PRÉNOM (Titulaire)`, `kyb_forme_juridique = Personne Physique`, `kyb_capital_social = N/A (Patrimoine Individuel)`, and `is_company = False` (`company_type = person`).
* **Automatic NIF-to-CNRC Category A Enrichment Cascade:**
  * Resolving a natural person by their 15/20-digit NIF (`185250600194154`) when `kyb_rc` is empty automatically triggers a live Category A registry discovery and enriches the official Trade Register (`11/00-0365048A11`) and NAE activity nomenclature.
* **Full Multi-Version Support Across Odoo 14.0 & 15.0 LTS Foundations:**
  * Backported partner autocomplete and fiscal verification engines to legacy Odoo 14.0 (QWeb `<t t-extend="partner_autocomplete.dropdown">`, `kyb_assets.xml`) and Odoo 15.0 (`web.assets_qweb`, `web.assets_backend`).
  * Dedicated qualification testbeds live and certified behind sovereign HTTPS endpoints: `https://odoo14.digidevagency.dz` and `https://odoo15.digidevagency.dz`.

### Fixed
* **Odoo 14 `company_registry` Attribute Defensive Resolution:**
  * Protected `company_registry` access via `getattr(rec, "company_registry", "")` to eliminate `AttributeError` when saving partner records on Odoo 14 installations where `company_registry` is not defined on `res.partner`.
* **Legacy Runtimes Dynamic Versioning & Default Loader (`res_config_settings`):**
  * Implemented defensive `default_get` and `set_values` in `res_config_settings.py` to correctly resolve `kyb_installed_version` via manifest lookup and `odoo.release`, preventing false "update available" notices on legacy Odoo 14/15/16 instances.
* **Non-Fabricated Algerian Immatriculation Year Resolution:**
  * Updated `_deduce_algerian_creation_date` to return a clean 4-digit year string (`YYYY`) derived from NIF/RC instead of fabricating an artificial `YYYY-01-01` date.
* **Single-Card In-Place Update & OWL Chatter Bus Synchronization (Zero Double Cards):**
  * Updated `_post_kyb_audit_log()` to modify `existing_cards[0]` in-place (`existing_cards[0].write(update_vals)`), unlink any extra legacy cards (`existing_cards[1:].unlink()`), and explicitly broadcast the updated `body` to the active user's OWL `Store` over `bus.bus`. Preserves a single `mail.message` ID (`same_card_id_in_place = True`), eliminating double cards in both PostgreSQL and the browser OWL Chatter across all creation, autocomplete, and re-verification workflows.
* **Cross-Version `_message_track` & Deferred Precommit Tracking Suppression (Odoo 16.0 – 20.0):**
  * Overrode `_message_track(self, fields_iter, initial_values)` to pass `fields_iter = ()` into `super()` when `mail_notrack` / `tracking_disable` is active or when the partner has `kyb_nif` / `kyb_rc` (preserving Odoo 16's `({}, {})` tuple and Odoo 17–20's `{}` dict return signatures).
  * Added `self.env.flush_all()` and `self.env.cr.precommit.run()` at the start of `_post_kyb_audit_log()` so deferred Odoo 20 precommit tracking hooks (`Company Name Entity` / `Dénomination de la société`) are flushed and purged before writing the single audit card.
* **Stale Duplicate NIF Warning Cleanup & Address Street Preservation:**
  * Automatically purges stale `Doublon Fiscal` warnings from Chatter when a partner's NIF changes and deduplicates warnings for the same NIF.
  * Preserves street strings (`street`) when `wilaya` is empty unless `_split_algerian_commune_wilaya` resolves a valid 2-digit Wilaya code.

---

## [2.0.8] - 2026-11-06

### Added
* **Configurable Customer Invoice Compliance Governance (`kyb.customer_invoice_policy` — Ventes & État 104):**
  * Added **Action sur Client Radié (Ventes / État 104)** in **Settings → KYB Compliance** with 3 enterprise governance modes:
    * `soft_warn` (**Default — Recommended**): *Avertissement & Traçabilité État 104* — Allows confirming Customer Invoices (`out_invoice` / `out_refund`) while displaying a non-blocking warning notification on selection and logging a deduplicated **`Signalement Risque Commercial & État 104 (Client Radié — Non-Bloquant)`** alert box in the invoice Chatter (`mail.mt_note`).
    * `strict_block`: *Blocage Strict* — Prevents posting Customer Invoices for deregistered customers (`⛔ FACTURATION CLIENT INTERROMPUE` referencing **Art. 183 ter du CIDTA**).
    * `badge_only`: *Badge Uniquement* — Updates `kyb_compliance_status` (`Non Conforme (Tiers Radié)`) and the KYB tab audit report silently without modal dialogs or Chatter notes on sales invoices.
  * Automatically evaluates `kyb_compliance_status` upon `account.move.create()` and `write()` so invoices generated from Sales Orders (`sale.order` -> *Créer une facture*) or Purchase Orders immediately display their compliance status (`compliant`, `warning`, `non_compliant`) in Draft state without requiring manual audit clicks.
  * Preserves strict configurable blocking (`strict_block` / `soft_warn`) on Purchase Bills (`in_invoice` / `in_refund`) under Articles 169 & 176 CIDTA and Article 30 CTCA.
* **5 Statutory Legal Invariants & Address / Governance Normalization:**
  * **Verbatim Décret 05-468 RC Preservation:** Preserves modern electronic national trade register numbers (e.g. `24/00-1052733B24`) verbatim without rewriting prefixes from address Wilayas.
  * **Universal Invoice RC Format Recognition:** Seamlessly resolves official slashed (`24/00-1052733B24`), compact (`24B1052733`), single-digit wilaya (`9B0068239`), prefixed (`RC: ...`), and Arabic-numeral Trade Register strings.
  * **Exact Registration Date Integrity:** Populates `kyb_date_creation` strictly when an authenticated day/month/year is published; keeps the date field `False` when only the registration year is known (preventing arbitrary `01/01/YYYY` assumptions).
  * **Administrative Commune & Wilaya Decoupling:** Separates `city` (Commune) from `state_id` (Wilaya), enforces `street2 = False`, strips trailing locality repetitions from `street`, and maps official 5-digit Algerian postal codes (`zip`).
  * **Sanitized Governance & NAE Nomenclature:** Strips publication action verbs (`Désigner`, `Nommer`) from `kyb_representant_legal` and formats primary economic activities strictly as `[CODE] LIBELLÉ` with secondary NAE codes as clean bullet lists.
* **10-Second Anti-Rebond Credit Protection Guard:**
  * Added a 10-second debounce guard on `action_verify_kyb()` ("Vérifier Fiche KYB") to prevent accidental credit consumption on rapid repeated clicks.
* **In-Memory Python Hot-Reload during 1-Click Upgrades (`migrations/0.0.0/pre-migrate.py` & `post-migrate.py`):**
  * Automatically reloads `odoo.addons.kyb_odoo` modules in-place (`importlib.reload`) and refreshes ORM model hooks during `button_immediate_upgrade()`, ensuring 1-click in-app updates apply Python model changes immediately with zero container restarts.

### Fixed
* **Single-Card In-Place Update & OWL Chatter Bus Synchronization:**
  * Updated `_post_kyb_audit_log()` to modify `existing_cards[0]` in-place (`existing_cards[0].write(update_vals)`), unlink any extra cards (`existing_cards[1:].unlink()`), and explicitly push the updated `body` to the active user's OWL `Store` over `bus.bus` (`Store(card).add(card, ["body"])`). Guarantees strictly **1** `Vérification KYB` card in both PostgreSQL and the browser OWL Chatter across all workflows.
  * Replaced Bootstrap pink/red `<code>` tags with clean zinc monospace (`#18181b`), converted the card header to a 100%-width 2-column table to prevent badge collisions under `html_sanitize`, and attributed statutory audit notes directly to the active authenticated user (`author_id`).
* **Décret Exécutif n° 05-468 Personne Physique Legal Identity Naming & NIF-to-CNRC Category A Cascade:**
  * Enforced statutory naming for individual merchants (Category A/C & Auto-Entrepreneurs): civil identity (`NOM PRÉNOM`) is primary, formatted as `NOM PRÉNOM (NOM COMMERCIAL)` when a distinct commercial sign exists (rejecting BOAL address fragments like `ESC 02`), with `kyb_representant_legal = NOM PRÉNOM (Titulaire)`, `kyb_forme_juridique = Personne Physique`, `kyb_capital_social = N/A (Patrimoine Individuel)`, and `is_company = False` (`company_type = person`).
  * Enabled automatic NIF-to-CNRC Category A RC and NAE activity enrichment when resolving a natural person NIF (`185250600194154` → `11/00-0365048A11`).
* **Suppressed Deferred Precommit ORM Field-Diff Tracking & Stale Duplicate NIF Warnings:**
  * Applied `tracking_disable=True`, `mail_notrack=True`, and `kyb_skip_audit_post=True` across all KYB write paths and overrode `_message_track()` so re-verifying or switching a partner in autocomplete never emits raw field-diff tracking lines (`Company Name Entity` / `Dénomination de la société`).
  * Automatically purges stale `Doublon Fiscal` warnings when a partner's NIF changes and deduplicates warnings for the same NIF.
* **Accurate Invoice Telemetry Counters & Role-Neutral Labels:**
  * Aligned `_gather_instance_telemetry()` with `kyb_compliance_status` on `account.move` and standardized invoice badge labels across all languages to **Tiers Radié** / **Tiers Actif (Vérifié)**.

## [2.0.7] - 2026-10-27

### Fixed
* **Eliminated Card-Inside-a-Card Chatter Nested Styling:**
  Removed the redundant outer box border (`border: 1px solid #e4e4e7`), background (`#fafafa`), and rounded corners (`border-radius: 8px`) from `_post_kyb_audit_log`. The statutory KYB audit log now renders seamlessly inside Odoo's native chatter message container instead of appearing as a nested card inside a card.
* **Chatter Deduplication — Single Sovereign KYB Card Guarantee:**
  `_post_kyb_audit_log` now automatically purges any redundant `Contact créé` notification or ORM field-tracking diffs on the partner, leaving exactly **one** pristine institutional KYB audit card as the sole chatter entry.
* **Suppressed ORM Field-Diff Tracking & Auto Creation Logs:**
  Added `mail_create_nolog=True`, `mail_notrack=True`, and `tracking_disable=True` on both partner creation and update write paths to prevent Odoo from posting raw `None → value` diff messages.
* **Removed Redundant `Statut Registre` Row from Chatter Card:**
  The first table row inside the `_post_kyb_audit_log` HTML card duplicated the status badge already visible in the card header (`Vérification KYB | ACTIF`). Row removed — status badge in the header is the single authoritative status indicator.
* **Removed Duplicate `Verify KYB` Header Button:**
  The form-level `<header>` button (appearing above the sheet) duplicated the button already present inside the dedicated **KYB — Fiscal Verification** tab. Removed the header button; the tab button remains the sole entry point.

## [2.0.6] - 2026-10-26

### Added
* **Chatter Audit Card Publication Visibility (`mail.mt_comment`):**
  Switched audit message subtype from `mail.mt_note` to `mail.mt_comment` (`message_type="comment"`), guaranteeing audit card visibility when filtering chatter by standard discussions or "Messages".
* **Multi-Status Institutional Badges & Explicit Status Row:**
  Extended status badge styling across 4 distinct legal states: `ACTIF` (🟢 #10b981), `RADIÉ` (🔴 #ef4444), `SUSPENDU` (🟠 #f59e0b), and `NON TROUVÉ` (⚪ #71717a). Added a dedicated, prominent `Statut Registre : <STATUS>` key-value row at the top of the tabular card.
* **Auto-Entrepreneur 20-Digit NIF Support (Loi 22-23):**
  Full transparent resolution of auto-entrepreneur 20-digit NIFs with automatic fallback to 15-digit root and zero RC requirement.
* **Pre-2022 Wilaya 00 Corporate NIF Compatibility:**
  Guaranteed live DGI validation for authentic enterprises registered prior to 2022 in Wilaya 00 (e.g. `000016...`).

---

## [2.0.5] - 2026-10-26

### Fixed
* **Odoo 20 Personne Physique Persona State Integrity (`is_company = False`):**
  Resolved an Odoo 20 framework quirk where assigning a value to the standard `vat` field triggered native partner compute/inverse logic that reset `is_company` to `True`. Implemented strict post-write re-assertion ensuring sole proprietorships, individual traders, artisans, and auto-entrepreneurs maintain individual status (`is_company = False` / Particulier) in compliance with Décret 05-468 and Law 18-07.
* **Auto-Entrepreneur & Artisan Direct Resolution Alignment:**
  Seamlessly synchronized with the Thick Core's direct DGI certification fallback for individual taxpayers exempt from commercial registration (Loi 22-23 Art. 4). Fiches are populated with `statut_cnrc: ACTIF`, `forme_juridique: Personne Physique`, `capital_social: N/A (Patrimoine Individuel)`, and `representant_legal: [Nom Prénom] (Titulaire)`.

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
* **Pre-2000 Algerian Trade Register (RC) Recognition (Wilayas 80–99):**
  Extended the Trade Register validator across the thick core and connector to accept historic pre-2000 Algerian business registrations carrying Wilaya codes 80 to 99 (e.g. `98B0102835` / `98/00-0102835B`), enabling instantaneous autocomplete and certification for historic commercial enterprises.
* **Semantic Versioning Telemetry & False Update Suppression:**
  Replaced string inequality comparisons with integer-tuple semantic comparisons (`tuple(installed) >= tuple(latest)`) across the sovereign Gateway and Odoo Settings models, eliminating spurious update prompts when running the current release.
* **Authoritative Chatter Audit Card In-Place Refresh:**
  Replaced suppression guards with in-place message refresh, ensuring that when a counterparty is fully enriched from an initial autocomplete skeleton, the institutional audit card in the chatter is updated immediately with all certified fiscal attributes (NIF, NIS, RC Décret 05-468, Capital Social, Date d'Immatriculation, Legal Representative, NAE Activities).
* **Defensive Relational Type Adaptation:**
  Added defensive unwrapping for relational Many2one dictionaries in `res.partner` ORM hooks (`create` and `write`) to safeguard PostgreSQL foreign keys against nested dictionary adaptations.
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
