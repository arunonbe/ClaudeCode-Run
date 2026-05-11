# DS_DB_vendor — Enterprise Architect Assessment

## 1. Platform Generation and Role

The Vendor database is a **mid-generation, multi-purpose FDR processor integration database** targeting SQL Server 2016. The design spans multiple eras: the `GBBase`/`GBLoads`/`GBMap` schema structure and the `CustomerMaster` table (created August 2011, per `uspUpdateCustomerMaster` header) represent a 2011-era ETL pipeline design. The `dbo` schema FDR import tables with embedded dates (`fdr_process_dcaf_chd_data_20061223`) suggest even earlier legacy tables from 2006 that were never consolidated or replaced.

The database sits at the **data ingestion boundary** of the Onbe platform — it is the first internal repository for cardholder data received from the FDR processing network. This gives it a dual role: a landing zone for raw processor data and a stable operational reference for active cardholder accounts.

---

## 2. Architectural Role

```
FDR Card Processing Network
           |
           | (daily file feeds: CD-012, CD-014, CD-051, CD-063, etc.)
           v
    DS_DB_vendor
    ┌─────────────────────────────────────────────────────────┐
    │  GBLoads (ETL control)                                  │
    │    └── Files, FileSteps, Log, tmpNESSTable              │
    │  dbo (staging / operational)                            │
    │    ├── fdr_import_* (raw FDR record staging)            │
    │    ├── fdr_cardholder_master (full PAN — CRITICAL)      │
    │    ├── ness_hits (OFAC screening results)               │
    │    ├── IVR_CallLog (IVR interaction logs)               │
    │    └── chargeback_process_queue (Reg E chargebacks)     │
    │  GBBase (core cardholder repository)                    │
    │    ├── CustomerMaster (SSN + PAN — CRITICAL)            │
    │    ├── AuthorizedTransactions (PAN + transaction data)  │
    │    └── PostedTransactions (PAN + settlement data)       │
    │  GBMap (reporting views)                                │
    │    └── DDA_Card_Account_Detail (exposes SSN + PAN)      │
    └─────────────────────────────────────────────────────────┘
           |                        |
           v                        v
    NESS OFAC engine         All platform service accounts
    (daily extract)          (via Vendor_Select role)
```

---

## 3. Critical Dependency Analysis

### 3.1 Upstream Dependency: FDR
The entire `GBBase` cardholder repository is populated from FDR file feeds. FDR is an external dependency — any FDR outage, file format change, or FDR contract change directly affects the currency and completeness of the Vendor database.

### 3.2 Downstream Dependency: NESS
The `uspNESSDailyExtract` procedure feeds the external NESS OFAC screening engine. As documented in DevOps (section 3.3), the WHERE clause bug (`PICreated > @startdate AND PICreated > @enddate`) means the extract currently produces an empty result set. If this bug is present in production, NESS receives no data, and OFAC screening is silently failing for the entire FDR-sourced cardholder population.

### 3.3 Downstream Dependency: Platform Services
`Vendor_Select` members include all 12+ production service accounts. These services depend on the Vendor database for:
- Cardholder lookup (via `GBMap.DDA_Card_Account_Detail`)
- Transaction history (via `GBMap.Authorized_Transaction_Detail`, `GBMap.Posted_Transaction_Detail`)
- Chargeback status (via `dbo.chargeback_process_queue`)
- IVR call history (via `dbo.IVR_CallLog`)

---

## 4. Multi-Purpose Schema Design — Architectural Concern

The four-schema design (dbo/GBBase/GBLoads/GBMap) conflates several distinct architectural concerns into one database:

| Schema | Architectural Role | Industry Pattern |
|---|---|---|
| GBBase | Operational cardholder data store | Should be a separate operational database |
| GBLoads | ETL pipeline control | Should be a dedicated ETL/SSIS catalog database |
| dbo | FDR file staging + IVR logging + chargebacks + NESS hits | Should be separated by domain |
| GBMap | Reporting views | Should be a separate reporting layer |

The consolidation into a single database creates:
1. **Shared blast radius:** a corrupted `GBLoads` file load can lock tables in `GBBase`, blocking all platform services that depend on `Vendor_Select` access to `GBMap` views.
2. **Inconsistent access control:** `db_datareader` members get read access to all four schemas — ETL control tables and OFAC hit records are equally accessible.
3. **Backup complexity:** the database contains both short-lived staging data (dbo FDR imports) and long-retention BSA records (ness_hits) — backup and retention policies must span multiple regulatory requirements.

---

## 5. PCI DSS CDE Scoping

The Vendor database is definitively within PCI DSS CDE scope because `dbo.fdr_cardholder_master.card_number CHAR(16)` and `GBBase.CustomerMaster.CardNumber VARCHAR(100)` store full PANs. All PCI DSS controls applicable to CDE systems apply:

| PCI DSS Req | Control | Current State |
|---|---|---|
| Req 3.4 | PAN rendered unreadable in storage | FAILED — full PAN in VARCHAR |
| Req 7.2 | Least-privilege access | PARTIAL — db_owner granted broadly |
| Req 8.6 | Named individual accounts managed | GAP — nam\jd62380 in db_owner |
| Req 10.2 | Audit logs for data access | PARTIAL — FortiDB deployed but db_owner can disable |
| Req 6.3.3 | Security patches applied | PASSING — SQL Server 2016 in extended support |

---

## 6. Modern Architecture Equivalent

In a modern cloud-native architecture, the Vendor database's concerns would be separated:

```
FDR Integration Service (microservice)
├── Stateless file processor — no persistent PAN storage
├── Tokenises PAN on ingest using Azure Key Vault (never stores raw PAN)
└── Publishes events to event bus

Cardholder Data Service
├── Tokenised cardholder master (no SSN in plaintext — use StrongBox/AKV)
├── Transaction history (tokenised card references)
└── CDC via Azure Event Hubs

OFAC Screening Service
├── Real-time screening via NESS or Azure Cognitive Services fuzzy match
├── Batch nightly verification
└── Hit records in dedicated compliance-grade data store with 5-year retention

IVR Call Log Service
├── Session log with masked card (last 4 only) and no DOB storage
├── 90-day retention policy enforced at service layer
└── Access restricted to IVR service account only
```

The fundamental difference is that a modern architecture would never allow a plain VARCHAR `SSN` column in an FDR-sourced customer master table.

---

## 7. Technical Debt Summary

| Item | Severity | Notes |
|---|---|---|
| `fdr_cardholder_master.card_number CHAR(16)` — full PAN plaintext | Critical | PCI DSS Req 3.4 violation |
| `CustomerMaster.SSN VARCHAR(50)` — plaintext SSN | Critical | GLBA/CCPA/GDPR violation |
| `uspNESSDailyExtract` WHERE clause bug — empty result set | Critical | OFAC screening silently failing |
| `db_owner` for service accounts and named individual | Critical | PCI DSS Req 7.2 |
| `NAM\UAT` in production `db_datareader` | Critical | PCI DSS Req 6 env segregation |
| GoogleBinKey uses DES algorithm (broken crypto) | High | PCI DSS Req 3.6.1 |
| GoogleBinCert expired October 2012 | High | Dead / broken crypto object |
| CDC on CustomerMaster expands SSN/PAN surface area | High | CDC change tables inherit sensitivity |
| No CI/CD pipeline | High | PCI DSS Req 6 |
| Dated ad-hoc tables (september.sql, sep_quality.sql) | Medium | Data governance |
| IVR DOB retention — no enforced cleanup schedule | Medium | GDPR Art 5(1)(e) |
| Four-schema single database with mixed retention requirements | Medium | Operational complexity |
