# DS_DP_db04 — Business Analyst Report

## Repository Overview

**Repo name:** DS_DP_db04  
**Server instance (inferred):** P-DB04 — `q-db04.nam.wirecard.sys\db04,2232` (QA), production equivalent inferred  
**Active date range:** October 2019 – May 2023 (longest active span in the 6-node set: 3.5+ years)  
**Script count:** ~130 SQL scripts (highest raw count)  
**Branching model:** Single `master` branch  
**Note:** DB04 also serves as the QA proxy for DB02 workloads (per DB07 SSIS configuration)

---

## Business Purpose

DB04 is the **cardholder-facing web portal content and customer service operations database node**. It hosts two primary databases:

1. **`cbaseapp`** — The content base application database. This is the backend datastore for the customer-facing card portal (ClientZone / OnePortal), storing UI configuration, copy tags (localized text content), skin definitions (brand templates), notification service templates, inquiry types, and cardholder security audit data.

2. **`EcountCore`** / **`EcountCore_Process`** — DB04 also shares the core card processing schema with DB02, but the DB04 scripts indicate it serves a **partitioned processing role** with monthly partition management for audit device data.

---

## Primary Business Processes

### 1. Customer Portal Content Management (cbaseapp)
DB04 is the definitive content management system for the Onbe multi-brand card portal. The volume of scripts (100+ from 2021–2023 alone) is dominated by:

- **Skin creation** (`xcontent` versioned skin deployments) — Brand-specific visual themes for client programs. Scripts follow the pattern `xcontent1.0.XX_DB04_cbaseapp_Create_skin.sql`. Over 30 xcontent skin deployments observed between versions 1.0.12 and 1.0.35 (2021–2023). This indicates active white-labeling activity for new client programs.

- **Copy tag management** — Localized UI text strings for cardholder portal pages. Specific copy tags observed include:
  - T-Mobile card program (`04011*` prefix) — signup path text, French language copy, popup messages, T&C updates
  - Zoetis (pharmaceutical company) — shop page navigation, card detail copy
  - Porsche, Bentley, Lamborghini — car brand rebate/incentive programs (disclaimer copy tags)
  - BioLife (plasma donation) — access tab notes
  - IDD Bank — T&C and privacy notice
  - MB Bank (Mercedes-Benz) — T&C
  - People's Bank — template entries

- **Affiliate field configuration** — Field-level settings for affiliate portals (Western Union, KYC required fields, password validation configuration)

- **Notification service templates** — US and Canadian notification templates for OTP, card activation, and balance notifications (`20210929_SQ-4558-4614_DB04_notification_svc_canada.sql`, `_us.sql`)

### 2. Customer Service Operations (CSA)
DB04's `cbaseapp` hosts:
- **Inquiry type categories** — `inquiry_types_category` and `Inquiry_types` tables for customer service agent (CSA) ticket categorization
- **Biocatch fraud scoring audit** — The `biocatch_api_audit` table (2023) stores behavioral biometric fraud scores from BioCatch API calls during cardholder sessions
- **Security audit device data** — `security_audit_device_user_data` and its switch/staging variant, partitioned by month, tracks device browser, OS, model, and geographic location for cardholder login events

### 3. Payment Expiration Date Management
DB04 hosts a `Payment` table (cross-reference to DB02's `fdr_card_account`) with expiration date updates (`20191009_NATS-5257_Payment_table_update_expiration_date.sql`).

### 4. Partition Control for Process Data
DB04 manages `cbaseapp_process_partition_control` — a monthly partition function for the security audit device data tables. This is the DB04-specific partitioning layer (distinct from DB02's process table partitioning).

---

## Client Programs Identified

The copy tag volume reveals specific client programs on DB04:

| Client / Program | Evidence | Program ID pattern |
|---|---|---|
| T-Mobile | Numerous copy tag scripts 2022–2023 | `04011*` |
| Zoetis | Shop page, card detail copy tags | 2023 scripts |
| Porsche | Disclaimer copy tags | `04011221` |
| Bentley | Disclaimer copy tags | Program not specified |
| Lamborghini | Disclaimer copy tags | Program not specified |
| BioLife (plasma donation) | Access tab notes | Program not specified |
| IDD Bank | T&C, privacy notice | Program not specified |
| MB (Mercedes-Benz) Bank | T&C | Program not specified |
| People's Bank | Template entries | `04011*` |
| Wirecard → Onbe copytag | Wirecard logo/verbiage update (SQ-234) | Payday program |

The client mix — automotive brands, pharmaceutical, telecom, banking — confirms DB04 serves the **rebate, incentive, and prepaid card issuance** product lines across multiple consumer verticals.

---

## Regulatory Relevance

| Regulation | Relevance | Evidence |
|---|---|---|
| PCI DSS v4.0.1 Req 3 | Cardholder data in security audit tables | `security_audit_device_user_data` captures device/geo data for cardholder sessions |
| PCI DSS v4.0.1 Req 6 | Secure application development | BioCatch fraud scoring integration audit trail |
| PCI DSS v4.0.1 Req 10 | Audit logging | Device security audit with monthly partitioning |
| CCPA | PII in device/location audit | `device_geography` in `security_audit_device_user_data` |
| GLBA | Cardholder portal content | Terms and conditions, privacy notices stored as copy tags |
| UDAAP | Consumer disclosure accuracy | Copy tags include fee disclosures, T&C — must be accurate |
| PIPEDA / Quebec Law 25 | Canadian cardholder notifications | Canadian notification templates in `cbaseapp` |

---

## Key Business Events (Chronological Highlights)

| Date | Ticket | Business event |
|---|---|---|
| 2019-10-04 | NAMPPDDEV-807 | Permissions for new stored procs |
| 2019-10-09 | NATS-5257 | Payment expiration date update |
| 2019-10-18 | NAMDATASVC-1388 | Monthly partition scheme for security audit device data |
| 2020-02-12 | NAMDATASVC-1879 | Old jobs disabled, new index maintenance jobs deployed |
| 2020-11-04 | SQ-234 | Wirecard → Payday copytag updated (brand transition) |
| 2021-03-16 | SQ-1111 | ROLE_FILE_VIEW security role created in cbaseapp |
| 2021-04-23 | NATS-11158 | PS_TECHAPI user permissions created |
| 2021-09-29 | SQ-4558/4614 | Email Form inquiry type; US+CA notification templates |
| 2021-11-02 | xcontent 1.0.12 | First xcontent skin versioning begins |
| 2022-01-27 | SQ-5183 | KYC required field configuration |
| 2022-04-18 | SQ-5713 | Card ordered date update |
| 2023-02-15 | (new) | BioCatch API audit table + stored procedure |
| 2023-05-06 | (new) | Western Union affiliate field configuration |
| 2023-07-08 | (new) | T-Mobile signup path copy tags |
| 2023-09-03 | (new) | T-Mobile French-language copy tags |

---

## Summary Assessment

DB04 is the **content management and customer service operations** node in the DS_DP cluster. Its business significance is different from DB02 (core card processing) — it does not process financial transactions directly but instead stores the configuration data and UI content that cardholders interact with. The high volume of xcontent skin deployments and copy tag changes indicates an **active client onboarding and content update pipeline** that generates the majority of DB04's operational workload. The addition of BioCatch fraud scoring integration (2023) and KYC field configuration positions DB04 as an emerging fraud prevention data store in addition to its content management role.
