# DS_DP_db02 — Business Analyst Report

## Repository Overview

**Repo name:** DS_DP_db02  
**Server instance (inferred):** P-DB02 / C-DB02 — `p-db02-ha.nam.wirecard.sys\db02` (production HA), `d-na-db02.nam.wirecard.sys\db02,2232` (dev)  
**Evidence:** DB07 SSIS config `20210611-SQ-3087-configure ivr card activation dtsx.sql`, line 1; DB07 Finance project `20200212_NAMDATASVC-1883_DB07 Configure for Finance SSIS project.sql`, line 2  
**Active date range of change scripts:** October 2019 – February 2023  
**Script count:** ~65 SQL scripts (highest volume of the 6 repos)  
**Branching model:** Single `master` branch

---

## Business Purpose

DB02 is the **core card transaction processing and account management node** in the Onbe prepaid card platform. It hosts the primary `EcountCore` and `EcountCore_Process` databases, which contain card account records, ACH/DDA payment status, transaction source/facility definitions, and IVR card activation data. It is the **highest-complexity and most business-critical** of the six analyzed nodes.

### Primary Business Processes

1. **Card Account Lifecycle Management** — DB02 hosts `fdr_card_account`, `fdr_card_account_detail`, and `fdr_card_account_registration` tables that store card identity, expiration, block codes, and cardholder registration data. Multiple scripts insert card account records and associated journal entries for card program restorations and corrections (`20200311_NATS-6935_insert_card_account_and_journal.sql`).

2. **ACH/DDA Payment Processing** — The `core_profile_dda_payment_nacha_status` and `ach_transfer_detail` tables track NACHA ACH payment entries. Scripts correct failed entries, delete invalid NACHA status records (`20191018_NATS-5468`), and manage DDA exclusion lists. DB02 is directly in scope for **NACHA Operating Rules compliance** and **Reg E** (consumer protections on electronic fund transfers).

3. **Transaction Source/Facility Code Management** — DB02 manages the authoritative `fdr_profile_transaction_source` and `fdr_profile_transaction_facility` tables in `EcountCore` — the transaction type dimension tables that classify every financial event in the platform. This includes ATM withdrawals, Cambridge Global Deposit withdrawals, Same Day ACH, and online portal transactions. These tables feed reporting on DB06 and the data warehouse.

4. **KYC (Know Your Customer) Tracking** — In March 2022 (SQ-5175), a new KYC tracking subsystem was added to EcountCore on DB02. The `kyc_tracker` and `kyc_tracker_status` tables store KYC portal interaction records keyed by `program_id`, `dda_number`, and `card_last_four_number`. The stored procedure `kyc_status_insert_update` orchestrates the KYC workflow. This is directly relevant to **GLBA**, **CCPA**, and **AML/KYC regulatory obligations**.

5. **Dormancy and Escheatment Processing** — DB02 manages dormancy rules (`app_profile_escheatment_rules`) at the state level for prepaid card dormancy periods (e.g., updating Kentucky's dormancy period to 3 years, NATS-5448). Multiple escheatment queue management scripts appear throughout the history. This relates to **state-level unclaimed property laws** and affects Onbe's finance reconciliation.

6. **IVR Card Activation Backfill** — In June 2021 (SQ-3087), a significant data backfill was performed on `EcountCore_Process` to populate `ivr_card_activation_stage` from the Vendor database's IVR call logs (21.5 million activation records spanning 2018–2021). This indicates DB02 is the authoritative source for card activation status data.

7. **Cambridge Global Deposit (GD) Withdraw Processing** — Transaction codes for Cambridge-rail cross-border deposits were added (NAMDATASVC-1468, NAMDATASVC-2299) connecting to `worldlink` and `maritime` facilities. This relates to **global payout rails** and international money movement regulatory compliance.

---

## Key Programs and Clients

Evidence of specific program IDs in scripts:
- Program `04011*` series — referenced in multiple card account inserts
- Program `04014*` series — referenced in `app_profile_dda_exclusions` inserts
- `04014563` — Charter program for External Escheatment Report (DB06 reference)
- Cambridge project programs — added as sources/facilities (NAMDATASVC-1468)
- TXU energy client — ACH controls update (SQ-2206)
- Same Day ACH expansion programs — (SQ-1676, SQ-1260, SQ-3539)
- `ms11` ruleset — escheatment rules update (NATS-11086)

---

## Regulatory Relevance

| Regulation | Relevance | Evidence |
|---|---|---|
| PCI DSS v4.0.1 Req 3 | Cardholder data storage | `fdr_card_account` (card_id, dda_number), `fdr_card_account_detail` (exp_date), `fdr_card_account_registration` (cardholder PII) |
| NACHA Operating Rules | ACH file processing | `core_profile_dda_payment_nacha_status`, NACHA status delete/update scripts |
| Reg E (12 CFR 1005) | Electronic fund transfer consumer protections | DDA payment status corrections, pending restorals |
| GLBA | Non-public financial information | KYC tracker, cardholder registration data |
| CCPA / State Privacy Laws | PII handling | `fdr_card_account_registration` (name, email, address, phone) |
| State Unclaimed Property Laws | Escheatment | `app_profile_escheatment_rules` by state/rule_set_id |
| AML / BSA | KYC compliance | `kyc_tracker`, `kyc_tracker_status`, `kyc_status_insert_update` SP |
| Reg E — Same Day ACH | Same-day credit/debit rules | Same Day ACH transaction codes added in multiple scripts |

---

## Key Business Events (Chronological)

| Date | Ticket | Business event |
|---|---|---|
| 2019-10-09 | NATS-5257 | Expiration date update on core tables |
| 2019-10-17 | NAMDATASVC-102 | Switch table row compression enabled (EcountCore_Process) |
| 2019-10-18 | NATS-5468 | Invalid NACHA status record deleted |
| 2019-10-23 | NAMDATASVC-1468 | Cambridge project sources/facilities added |
| 2019-12-30 | NATS-6279 | Void check resets |
| 2020-02-03 | NAMDATASVC-1804 | New transaction codes added |
| 2020-03-11 | NATS-6935 | Card account and journal records inserted (program restoration) |
| 2020-07-21 | NAMDATASVC-2299 | DDA exclusions added for same-day ACH |
| 2020-08-13 | NAMDATASVC-2399 | BakerTilly audit access granted |
| 2021-03-09 | (manual) | STAR transaction corrections for DDA accounts |
| 2021-06-11 | SQ-3087 | IVR activation backfill (21.5M records) |
| 2022-03-14 | SQ-5175 | KYC tracker subsystem deployed |
| 2023-02-15 | (manual) | Core profile subfee insert |

---

## Summary Assessment

DB02 is the **highest-criticality database node** in the DS_DP set. It is the central card account processing engine, the NACHA/ACH gateway, and the KYC compliance hub for the Onbe prepaid platform. The breadth of its schema (EcountCore, EcountCore_Process, with multiple transaction dimensions) and the volume of change history (65+ scripts over 3+ years) confirm it as the primary CDE database in this node cluster. Any migration, upgrade, or architectural change must treat DB02 as the anchor node.
