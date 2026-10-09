# KYB Odoo Connector — Algerian Corporate Identity & Temporal Tax Compliance

[![Odoo Version](https://img.shields.io/badge/Odoo-16.0%20|%2017.0%20|%2018.0%20|%2019.0%20|%2020.0-533afd.svg)](https://apps.odoo.com)
[![License: LGPL-3](https://img.shields.io/badge/License-LGPL--3-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0)
[![Sovereign Cloud](https://img.shields.io/badge/Residency-Algérie%20Télécom%20Datacenter-10b981.svg)](https://kyb.digidevagency.dz)
[![Law Compliance](https://img.shields.io/badge/Compliance-Loi%2018--07%20/%2025--11-06b6d4.svg)](https://kyb.digidevagency.dz)

**Turnkey Odoo connector extending `res.partner` with instant NIF/RC auto-completion (<10ms), real-time CNRC status verification, and temporal invoice deductibility audits under Algerian Fiscal Law (CIDTA Art. 176 & CTCA Art. 30).**

Developed and maintained by **Mouadh Benhassine** ([@mouadh25](https://github.com/mouadh25)) for **Digidev Agency** ([digidevagency.dz](https://digidevagency.dz)).

---

## 1. Key Capabilities

* **Instant NIF & RC Auto-Completion (<10ms):** When creating or editing any vendor or customer in `res.partner`, typing their 15-digit NIF or Trade Registry (RC) number automatically resolves and populates:
  * Company Legal Name (*Raison Sociale*)
  * Registered Physical Address (*Adresse Siège Social*)
  * Share Capital (*Capital Social*)
  * Statistical Identification Number (*NIS*)
  * Tax Role Number (*Article d'Imposition*)
  * Primary Business Activity Code (*Activité Principale*)
* **Temporal Status Audit (CIDTA Art. 176 & CTCA Art. 30):** Protects corporate accounting teams against tax audit reassessments (*rejets fiscaux sur État 104*). A vendor strike-off (*Radiation*) only disallows transactions issued *after* the effective date. The connector audits status against the exact invoice date.
* **Fuzzy Name Autocomplete in Partner Dropdowns:** Overrides `res.partner._name_search` to query KYB's sovereign pre-indexed database, providing instant suggestions when typing company names in invoice, sales, and purchase forms.
* **Visual CNRC Status Badges:** Color-coded status badges on partner views:
  * <span style="color:#10b981">**ACTIF**</span> — Active and legally registered company.
  * <span style="color:#ef4444">**RADIÉ**</span> — Deregistered vendor (non-deductible expense warning).
  * <span style="color:#f59e0b">**SUSPENDU**</span> — Temporarily suspended registration.
* **100% Sovereign Data Residency (Law 18-07 / Law 25-11):** Direct connection to KYB's sovereign cluster hosted at the Algérie Télécom Cloud Datacenter in Algiers. Zero data egress to offshore cloud providers.

---

## 2. Architecture & Data Flow

```
┌───────────────────────────┐                     ┌───────────────────────────┐
│     Odoo ERP Instance     │                     │     KYB Sovereign API     │
│   (Community / Enterprise)│                     │  (Algérie Télécom Cloud)  │
└─────────────┬─────────────┘                     └─────────────┬─────────────┘
              │                                                 │
              │  1. User enters NIF in res.partner              │
              │────────────────────────────────────────────────>│
              │                                                 │
              │  2. Sub-10ms lookup in PostgreSQL Sovereign DB │
              │     (or real-time CNRC extraction & cache sync) │
              │<────────────────────────────────────────────────│
              │     Returns: Raison Sociale, RC, NIS,           │
              │     Article d'Imposition, Status, Radiation Date│
              │                                                 │
              │  3. Auto-populates fields & renders badge       │
              ▼                                                 ▼
```

---

## 3. Installation

### Option A: 1-Click via Official Odoo Apps Store (Recommended)
1. Visit the [Official Odoo Apps Store](https://apps.odoo.com) and search for **`kyb_odoo`** or **`conforme`**.
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
1. Enable **Developer Mode** (**Settings → Activate Developer Mode**).
2. Go to **Apps → Update Apps List**.
3. Search for **"KYB"** and click **Install**.

---

## 4. Configuration

Navigate to **Settings → Technical → Parameters → System Parameters** and configure the two required keys:

| Parameter Key | Default / Recommended Value | Description |
| :--- | :--- | :--- |
| `kyb.api_key` | `sk_live_...` (or test key `sk_test_kyb_sandbox_key_001`) | Your KYB API Bearer token. |
| `kyb.base_url` | `https://kyb.digidevagency.dz` | Official sovereign gateway endpoint. |

> **Tip:** You can test immediately using the public sandbox key `sk_test_kyb_sandbox_key_001` with zero billing charges.

---

## 5. Free Sandbox Verification & Synthetic Test Fixtures

Test your integration safely without burning production credits using our deterministic synthetic test fixtures (compliant with Law 18-07):

| Test NIF | Expected Entity Name | Status | Verified Scenario |
| :--- | :--- | :---: | :--- |
| `000000000000001` | **SARL ATLAS DEMO** | `ACTIF` | Active company with complete NIF, RC, NIS, and Tax Role. |
| `000000000000002` | **EURL MEDITERRANEE DEMO** | `RADIÉ` | Deregistered vendor (Radiation Date: `2024-03-12`). |
| `000016001234567` | **SARL DEMO RESELLER** | `ACTIF` | Reseller demonstration entity for sales demos. |

---

## 6. Security, Privacy & Law 18-07 / 25-11 Compliance

* **No Secret Storage:** This connector does not store or leak your private API keys in client-side code; all API communication is executed securely server-side via Python.
* **Law 18-07 Article 44 Strict Compliance:** Cross-border personal data transfers are strictly prohibited under Algerian law. All lookups resolve through our sovereign Algerian IP infrastructure at Algérie Télécom.
* **Auditable Codebase:** Pure Python implementation (~150 lines in `models/res_partner.py`) allowing security teams and DSI auditors to perform exhaustive code reviews in under 5 minutes.

---

## 7. License & Credits

* **License:** GNU Lesser General Public License v3.0 ([LGPL-3.0](LICENSE)).
* **Author:** **Mouadh Benhassine** ([@mouadh25](https://github.com/mouadh25))
* **Parent Enterprise:** **Digidev Agency** ([digidevagency.dz](https://digidevagency.dz))
* **Platform Ingress:** [kyb.digidevagency.dz](https://kyb.digidevagency.dz)
* **Technical Documentation:** [kyb.digidevagency.dz/docs](https://kyb.digidevagency.dz/docs) · [Scalar OpenAPI 3.1](https://kyb.digidevagency.dz/docs/scalar)
