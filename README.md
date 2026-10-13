# KYB Odoo Connector â€” Algerian Corporate Identity & Temporal Tax Compliance

[![Odoo Version](https://img.shields.io/badge/Odoo-16.0%20|%2017.0%20|%2018.0%20|%2019.0%20|%2020.0-533afd.svg)](https://apps.odoo.com)
[![License: LGPL-3](https://img.shields.io/badge/License-LGPL--3-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0)
[![Sovereign Cloud](https://img.shields.io/badge/Residency-AlgÃ©rie%20TÃ©lÃ©com%20Datacenter-10b981.svg)](https://kyb.digidevagency.dz)
[![Law Compliance](https://img.shields.io/badge/Compliance-Loi%2018--07%20/%2025--11-06b6d4.svg)](https://kyb.digidevagency.dz)

**Turnkey Odoo connector extending `res.partner` with instant NIF/RC auto-completion (<10ms), real-time CNRC status verification, and temporal invoice deductibility audits under Algerian Fiscal Law (CIDTA Art. 176 & CTCA Art. 30).**

Developed and maintained by **Mouadh Benhassine** ([@mouadh25](https://github.com/mouadh25)) for **Digidev Agency** ([digidevagency.dz](https://digidevagency.dz)).

---

## 1. Key Capabilities

* **Instant NIF & RC Auto-Completion (<10ms):** When creating or editing any vendor or customer in `res.partner`, typing their 15-digit NIF or Trade Registry (RC) number automatically resolves and populates:
  * Company Legal Name (*Raison Sociale*)
  * Registered Physical Address (*Adresse SiÃ¨ge Social*)
  * Share Capital (*Capital Social*)
  * Statistical Identification Number (*NIS*)
  * Tax Role Number (*Article d'Imposition*)
  * Primary Business Activity Code (*ActivitÃ© Principale*)
  * Comprehensive Registry Activities (*Toutes les ActivitÃ©s RC*)
  * Legal Representative (*GÃ©rant / ReprÃ©sentant LÃ©gal*)
* **DÃ©cret 05-468 RC Formatting & Validation Engine:** Fully implements the Algerian statutory trade registry standard (`WW/00-XXXXXXX[A|B|C|D]YY`). Validates all 69 Wilayas (Loi 26-06), auto-pads 7-digit registry numbers, parses compressed/spaced/Arabic variants, and establishes bidirectional synchronization with Odoo's native `company_registry` field.
* **Objective Temporal Status Audit (CIDTA Art. 176 & CTCA Art. 30):** Protects corporate accounting teams against tax audit reassessments (*rejets fiscaux sur Ã‰tat 104*). A vendor strike-off (*Radiation*) only disallows transactions issued *after* the effective date. The connector audits status objectively against the exact invoice date with sanitized, neutral institutional notices (zero legal liability assertions).
* **Fuzzy Name Autocomplete in Partner Dropdowns:** Overrides `res.partner._name_search` and intercepts `partner_autocomplete` to query KYB's pre-indexed database, providing instant suggestions when typing company names in invoice, sales, and purchase forms.
* **Visual CNRC Status Badges:** Color-coded status badges on partner views:
  * <span style="color:#10b981">**ACTIF**</span> â€” Active and legally registered company.
  * <span style="color:#ef4444">**RADIÃ‰**</span> â€” Deregistered vendor (non-deductible expense warning).
  * <span style="color:#f59e0b">**SUSPENDU**</span> â€” Temporarily suspended registration.
* **Configurable HTTP Timeout & Built-in Observability:** Configurable `kyb.timeout` (default 35.0s) supporting deep live scrapes, paired with real-time roundtrip timing logs (`_logger.info`) for end-to-end telemetry.
* **100% Data Residency in Algeria (Law 18-07 / Law 25-11):** Direct connection to KYB API (by Digidev) hosted at the AlgÃ©rie TÃ©lÃ©com Cloud Datacenter in Algiers. Zero data egress to offshore cloud providers.

---

## 2. Architecture & Data Flow

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”                     â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚     Odoo ERP Instance     â”‚                     â”‚    KYB API (by Digidev)   â”‚
â”‚   (Community / Enterprise)â”‚                     â”‚  (AlgÃ©rie TÃ©lÃ©com Cloud)  â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜                     â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
              â”‚                                                 â”‚
              â”‚  1. Preemptive Socket Warmup (warmup())         â”‚
              â”‚     [Reuses Keep-Alive pool with 120s timeout]  â”‚
              â”‚â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€>â”‚
              â”‚                                                 â”‚
              â”‚  2. User enters NIF/RC in res.partner           â”‚
              â”‚     [Sub-100ms over warm TLS socket]            â”‚
              â”‚â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€>â”‚
              â”‚                                                 â”‚
              â”‚  3. Sub-80ms resolution in KYB Database         â”‚
              â”‚     (or real-time CNRC extraction & cache sync) â”‚
              â”‚<â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”‚
              â”‚     Returns: Raison Sociale, RC, NIS,           â”‚
              â”‚     Article d'Imposition, Status, Radiation Dateâ”‚
              â”‚                                                 â”‚
              â”‚  4. Auto-populates fields & renders badge       â”‚
              â–¼                                                 â–¼
```

### 2.1 High-Performance Connection Pooling & Keep-Alive
The connector features a built-in process-level client cache (`_CLIENT_CACHE`) that pools HTTP connections using persistent `requests.Session()` sockets:
* **HTTP Keep-Alive Reuse:** TCP and TLS connections are kept open and reused across multiple `onchange` and `_name_search` events, aligned with the gateway's 120-second idle connection timeout.
* **Preemptive Warmup (`warmup()`):** Eliminates cold connection latency by pre-establishing TLS handshakes on module load or worker spawn, cutting lookup times from ~240ms down to **~76ms**.
* **Query Guards & Pagination:** Partner autocomplete automatically adheres to the sovereign gateway's 3-character minimum guard (`QUERY_TOO_SHORT`) and supports configurable candidate limits (`limit=1..50`).

---

## 3. Installation

### Option A: 1-Click via Official Odoo Apps Store (Recommended)
1. Visit the [Official Odoo Apps Store](https://apps.odoo.com) and search for **`kyb_odoo`** or **`KYB`**.
2. Click **Install**. Odoo will automatically place the module into your addons directory.

### Option B: Git Clone (Auditable & Custom Deployments)
Clone this repository directly into your custom addons directory:

```bash
cd /opt/odoo/custom-addons
git clone https://github.com/mouadh25/kyb-odoo.git kyb_odoo
chown -R odoo:odoo kyb_odoo
```

Restart your Odoo service:
```bash
sudo systemctl restart odoo
```

In Odoo:
1. Enable **Developer Mode** (**Settings â†’ Activate Developer Mode**).
2. Go to **Apps â†’ Update Apps List**.
3. Search for **"KYB"** and click **Install**.

---

## 4. Configuration

You can configure your credentials in one of two ways:

### Option A: Standard Settings UI (No Developer Mode Required)
Navigate to **Settings â†’ General Settings â†’ KYB Sovereign Verification** and enter your API Key and Gateway URL.

### Option B: System Parameters
Navigate to **Settings â†’ Technical â†’ Parameters â†’ System Parameters** and configure:

| Parameter Key | Default / Recommended Value | Description |
| :--- | :--- | :--- |
| `kyb.api_key` | `sk_live_...` (or test key `sk_test_kyb_sandbox_key_001`) | Your KYB API Bearer token. |
| `kyb.base_url` | `https://kyb.digidevagency.dz` | Official sovereign gateway endpoint. |
| `kyb.timeout` | `35.0` | HTTP request timeout in seconds (handles deep live scrapes). |
| `kyb.sovereign_autocomplete` | `True` | Intercept native autocomplete to enforce sovereign data residency (Loi 25-11). |

> **Tip:** You can test immediately using the public sandbox key `sk_test_kyb_sandbox_key_001` with zero billing charges.

---

## 5. Free Sandbox Verification & Synthetic Test Fixtures

Test your integration safely without burning production credits using our deterministic synthetic test fixtures (compliant with Law 18-07):

| Test NIF | Expected Entity Name | Status | Verified Scenario |
| :--- | :--- | :---: | :--- |
| `000000000000001` | **SARL ATLAS DEMO** | `ACTIF` | Active company with complete NIF, RC, NIS, and Tax Role. |
| `000000000000002` | **EURL MEDITERRANEE DEMO** | `RADIÃ‰` | Deregistered vendor (Radiation Date: `2024-03-12`). |
| `000016001234567` | **SARL DEMO RESELLER** | `ACTIF` | Reseller demonstration entity for sales demos. |

---

## 6. Security, Privacy & Law 18-07 / 25-11 Compliance

* **No Secret Storage:** This connector does not store or leak your private API keys in client-side code; all API communication is executed securely server-side via Python.
* **Law 18-07 Article 44 Strict Compliance:** Cross-border personal data transfers are strictly prohibited under Algerian law. All lookups resolve through our sovereign Algerian IP infrastructure at AlgÃ©rie TÃ©lÃ©com.
* **Auditable Codebase:** Pure Python implementation (~150 lines in `models/res_partner.py`) allowing security teams and DSI auditors to perform exhaustive code reviews in under 5 minutes.

---

## 7. Versioning & Release Changelog

The connector follows [Semantic Versioning](https://semver.org) and adheres to Odoo's native version mapping (`<odoo_major>.<module_version>`).

For detailed release history, new features, bug fixes, and upgrade notes across versions, consult the official [CHANGELOG.md](CHANGELOG.md).

| Odoo Version | Module Version Code | Market Adoption & Tier | Multi-Language (i18n) | Status |
| :--- | :--- | :--- | :---: | :---: |
| **Odoo 20.0** | `20.0.1.4.2` | Current Released Generation | FR / AR / EN | **ðŸŸ¢ Locked & Certified** |
| **Odoo 19.0** | `19.0.1.4.2` | Primary Enterprise Adoption (Algeria) | FR / AR / EN | **ðŸŸ¢ Locked & Certified** |
| **Odoo 18.0** | `18.0.1.4.2` | Active Production Standard | FR / AR / EN | **Supported** |
| **Odoo 17.0** | `17.0.1.4.2` | Primary Enterprise Adoption (Algeria) | FR / AR / EN | **Supported** |
| **Odoo 16.0** | `16.0.1.4.2` | Legacy LTS / SME Installed Base | FR / AR / EN | **Supported** |

---

## 8. Documentation & Technical Resources

Authoritative documentation and integration guides for the KYB ecosystem:
* **Customer Admin Portal:** [kyb.digidevagency.dz](https://kyb.digidevagency.dz)
* **Authoritative API Documentation:** [kyb.digidevagency.dz/docs](https://kyb.digidevagency.dz/docs)
* **Interactive Scalar Reference:** [kyb.digidevagency.dz/docs/scalar](https://kyb.digidevagency.dz/docs/scalar)
* **ERP Integrator & Administrator Manual:** [doc/INTEGRATOR_MANUAL.md](doc/INTEGRATOR_MANUAL.md)
* **Institutional User Manual (PDF):** [doc/USER_MANUAL.pdf](doc/USER_MANUAL.pdf)
* **Release Changelog:** [CHANGELOG.md](CHANGELOG.md)

---

## 9. License & Credits

* **License:** GNU Lesser General Public License v3.0 ([LGPL-3.0](LICENSE)).
* **Author:** **Mouadh Benhassine** ([@mouadh25](https://github.com/mouadh25))
* **Parent Enterprise:** **Digidev Agency** ([digidevagency.dz](https://digidevagency.dz))
* **Platform Ingress:** [kyb.digidevagency.dz](https://kyb.digidevagency.dz)
* **Technical Documentation:** [kyb.digidevagency.dz/docs](https://kyb.digidevagency.dz/docs) Â· [Scalar OpenAPI 3.1](https://kyb.digidevagency.dz/docs/scalar)

