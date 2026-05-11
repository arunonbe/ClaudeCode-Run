# DS_DB_CBTS — Data Architect View

## 1. Schema Overview

The CBTS database uses a flat `dbo` schema with 22 tables. DDL files are UTF-16 LE encoded (BOM present: `FF FE`) — a Windows-default encoding. All tables were scripted against the `[CBTS]` database (`USE [CBTS] GO`). The database uses `ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON` and `OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF` on all indexes — standard SQL Server 2019+ defaults.

---

## 2. Complete Table Inventory

### 2.1 Core Transfer Domain

| Table | Key Columns | Data Classification | Sensitivity |
|---|---|---|---|
| `ADDRESS` | `ID` VARCHAR(36), `VERSION`, `STREET_1`, `STREET_2`, `CITY`, `STATE_PROVINCE`, `POSTAL_CODE`, `COUNTRY` | PII — full address | **HIGH** |
| `REMITTER` | `ID`, `VERSION`, `REMITTER_ID` (unique), `FIRST_NAME`, `LAST_NAME`, `ADDRESS_ID` → ADDRESS, **`ACCOUNT_IDENTIFIER`** VARCHAR(50), `GATEWAY`, `GATEWAY_REMITTER_ID`, `ENABLED`, `BRAND`, `INSERTED_AT/BY`, `UPDATED_AT/BY` | **PII + Account ID** | **HIGH** |
| `BENEFICIARY` | `ID`, `VERSION`, `BENEFICIARY_ID` (unique), `REMITTER_ID`, `FIRST_NAME`, `LAST_NAME`, `BANK_CURRENCY`, `PAYMENT_METHOD`, `ADDRESS_ID` → ADDRESS, `PHONE_NUMBER`, `EMAIL`, **`SWIFT_BIC_CODE`** VARCHAR(12), `BANK_NAME`, `BANK_ADDRESS_ID` → ADDRESS, **`ACCOUNT_NUMBER`** VARCHAR(50), **`ROUTING_CODE`** VARCHAR(50), `REGULATORY` VARCHAR(36), `GATEWAY`, `GATEWAY_BENEFICIARY_ID`, `ENABLED` | **HIGH SENSITIVITY — bank account number, routing code, SWIFT/BIC, phone, email** | **CRITICAL** |
| `RATE` | `ID`, `VERSION`, `RATE_ID` (unique), `AMOUNT`, `PAYERS_CURRENCY`, `BENEFICIARIES_CURRENCY`, `REQUEST_TYPE`, `VALUE`, `STATUS`, `GATEWAY`, `GATEWAY_RATE_ID`, `GATEWAY_BOOKING_ID`, `BRAND`, `REMITTER_ID`, `PAYMENT_AMOUNT` | Financial — FX rate and amounts | **MEDIUM** |
| `RATE_HISTORY` | Same columns as RATE (history audit copy) | Financial audit | **MEDIUM** |
| `TRANSFER` | `ID`, `VERSION`, `TRANSFER_ID` (unique), `RATE_ID`, `BENEFICIARY_ID`, `FEE_AMOUNT`, `STATUS`, `GATEWAY`, `GATEWAY_TRANSFER_ID` VARCHAR(128), `INSERTED_AT/BY`, `UPDATED_AT/BY` | Transaction record | **HIGH** |
| `TRANSFER_HISTORY` | Same columns as TRANSFER (history audit copy) | Audit | **HIGH** |
| `TRANSFER_RETURN` | `ID`, `VERSION`, `TRANSFER_ID`, `GATEWAY_BOOKING_ID`, **`WIRE_NUMBER`** VARCHAR(22), `PAYMENT_REFERENCE`, `PAYEE`, `REASON`, `CURRENCY`, `AMOUNT`, `DATE_OPENED`, `CLOSED`, `RETURNED_USD`, `FX_RATE` | Wire return details | **HIGH** |
| `BENEFICIARY_REGULATORY_RULE` | `ID`, `BENEFICIARY_ID`, regulatory rule fields | Compliance metadata | **MEDIUM** |
| `RECON_FILE` | `ID`, `VERSION`, `RECON_FILE_ID`, `FILE_NAME`, `DATE`, `AMOUNT`, `COUNT`, `CURRENCY`, `STATUS`, `SOURCE`, `INSERTED_AT/BY`, `UPDATED_AT/BY` | Reconciliation | **MEDIUM** |

### 2.2 Spring Batch Infrastructure Tables

| Table | Purpose |
|---|---|
| `BATCH_JOB_INSTANCE` | Unique job definitions (JOB_NAME, JOB_KEY) |
| `BATCH_JOB_EXECUTION` | Per-execution records (start/end time, status, exit_code, exit_message) |
| `BATCH_JOB_EXECUTION_PARAMS` | Per-execution parameter values (type_cd, key_name, string_val, date_val, long_val, double_val) |
| `BATCH_JOB_EXECUTION_CONTEXT` | Serialised execution context (SHORT_CONTEXT VARCHAR(2500), SERIALIZED_CONTEXT NVARCHAR(MAX)) |
| `BATCH_STEP_EXECUTION` | Per-step details (read_count, write_count, filter_count, rollback_count, skip_count, commit_count, start_time, end_time, exit_code) |
| `BATCH_STEP_EXECUTION_CONTEXT` | Serialised step context |
| `BATCH_JOB_EXECUTION_SEQ` | Sequence table (ID BIGINT, UNIQUE_KEY) |
| `BATCH_JOB_SEQ` | Sequence table |
| `BATCH_STEP_EXECUTION_SEQ` | Sequence table |
| `DATABASECHANGELOG` | Liquibase migration log (ID, AUTHOR, FILENAME, DATEEXECUTED, ORDEREXECUTED, MD5SUM, DESCRIPTION, TAG, LIQUIBASE, CONTEXTS, LABELS, DEPLOYMENT_ID) |
| `DATABASECHANGELOGLOCK` | Liquibase migration lock (ID, LOCKED, LOCKGRANTED, LOCKEDBY) |

---

## 3. Sensitive Data Field Inventory

| Table.Column | Data Type | Classification | Regulatory Flag |
|---|---|---|---|
| `BENEFICIARY.ACCOUNT_NUMBER` | VARCHAR(50) | **Bank account number** | **CRITICAL** — foreign bank account; FinCEN Travel Rule (31 CFR §1010.410); GDPR Art. 9 (financial data) |
| `BENEFICIARY.ROUTING_CODE` | VARCHAR(50) | **Bank routing / sort code** | **HIGH** — combined with account number enables wire transfers |
| `BENEFICIARY.SWIFT_BIC_CODE` | VARCHAR(12) | **SWIFT/BIC code** | **HIGH** — identifies beneficiary's financial institution |
| `BENEFICIARY.FIRST_NAME`, `LAST_NAME` | VARCHAR(100) | PII — cardholder/beneficiary name | GDPR/CCPA; FinCEN Travel Rule originator/beneficiary info |
| `BENEFICIARY.EMAIL` | VARCHAR(250) | PII — email | GDPR/CCPA |
| `BENEFICIARY.PHONE_NUMBER` | VARCHAR(100) | PII — phone | GDPR/CCPA |
| `REMITTER.FIRST_NAME`, `LAST_NAME` | VARCHAR(100) | PII — remitter name | GDPR/CCPA; FinCEN Travel Rule |
| `REMITTER.ACCOUNT_IDENTIFIER` | VARCHAR(50) | Account reference | HIGH — links to Onbe prepaid account |
| `ADDRESS.*` (street, city, state, postal, country) | VARCHAR fields | PII — full address | GDPR/CCPA |
| `TRANSFER_RETURN.WIRE_NUMBER` | VARCHAR(22) | Wire reference | MEDIUM — financial reference |
| `TRANSFER_RETURN.PAYEE` | VARCHAR(255) | Payee name | PII |
| `BATCH_JOB_EXECUTION_CONTEXT.SERIALIZED_CONTEXT` | NVARCHAR(MAX) | Serialised Java object | **POTENTIAL** — serialised context may contain PII if job parameters include personal data |

---

## 4. Encryption at Rest Assessment

### Column-Level Encryption
- **None detected**: No `VARBINARY` encrypted columns, no `ENCRYPTBYKEY` patterns, no Always Encrypted column definitions are present in any CBTS DDL.
- `BENEFICIARY.ACCOUNT_NUMBER` (VARCHAR 50) stores a foreign bank account number **in plaintext**.
- `BENEFICIARY.ROUTING_CODE` (VARCHAR 50) stores a routing/sort code **in plaintext**.
- These are highly sensitive financial identifiers that, in a PCI DSS-aware environment, should at minimum be encrypted at the database-column level or stored via a tokenisation vault.

### Transparent Data Encryption (TDE)
- Cannot be confirmed from DDL alone. Must be verified against the production SQL Server instance.
- **Recommendation**: TDE should be active on CBTS given it stores international bank account details.

### Application-Layer Encryption
- The Java application layer may encrypt data before insertion (cannot be confirmed from SQL DDL). If application-layer encryption is used, the ciphertext should not be stored in VARCHAR columns — only in VARBINARY or properly sized VARCHAR with documented encryption scheme.

---

## 5. Data Classification Summary

| Tier | Tables | Notes |
|---|---|---|
| **Tier 1 — Critical (financial/identity)** | `BENEFICIARY`, `REMITTER`, `ADDRESS` | Contains foreign bank account numbers, SWIFT codes, full names and addresses |
| **Tier 2 — High (transactional)** | `TRANSFER`, `TRANSFER_HISTORY`, `TRANSFER_RETURN`, `RECON_FILE` | Transaction records with amounts, wire numbers, FX rates |
| **Tier 3 — Medium (operational)** | `RATE`, `RATE_HISTORY`, `BENEFICIARY_REGULATORY_RULE` | FX rates and regulatory rules |
| **Tier 4 — Low (infrastructure)** | `BATCH_*` tables, `DATABASECHANGELOG*` | Spring Batch metadata; Liquibase migration log |

---

## 6. Index Strategy

| Table | Index | Notes |
|---|---|---|
| `TRANSFER` | `PK_TRANSFER` (clustered on ID), `UDX_TRANSFER_TX_REF_ID` (unique nonclustered on TRANSFER_ID), `IDX_TRANSFER_STATUS` (nonclustered on STATUS) | STATUS index supports job-level polling for pending/in-progress transfers |
| `BENEFICIARY` | `PK_BENEFICIARY`, `UDX_BENEFICIARY_ID`, `IDX_BENE_REMITTER` (on REMITTER_ID) | REMITTER_ID index supports beneficiary lookup by sender |
| `REMITTER` | `PK_REMITTER`, `UDX_REMITTER_ID` | Unique remitter reference |
| `RATE` | `PK_RATE`, `UDX_RATE_TX_REF_ID`, `IDX_RATE_REMITTER`, `IDX_RATE_STATUS` | Status and remitter indexed for quote management |
| `TRANSFER_RETURN` | `PK_TRANSFER_RETURN`, `UDX_TRANSFER_RETURN_ID` (unique on TRANSFER_ID), `IDX_TRANSFER_RETURN_DEAL` (on GATEWAY_BOOKING_ID) | |

---

## 7. PCI DSS / Regulatory Scope

**CBTS is not in PCI DSS CDE scope** for prepaid card data (no PANs stored), but it is in scope for:
- **FinCEN Bank Secrecy Act** (cross-border wire transfer recordkeeping)
- **OFAC** (beneficiary bank account + SWIFT code must be screened)
- **GDPR** (beneficiary is likely an EEA resident for some transfers — full GDPR Art. 4 personal data present)
- **Reg E Remittance Transfer Rule** (CFPB 12 CFR 1005 Subpart B)

The foreign bank account number in `BENEFICIARY.ACCOUNT_NUMBER` is Tier 1 sensitive data under Onbe's data classification and must be protected with equivalent or stronger controls to PAN data.

---

## 8. Data Retention

- `INSERTED_AT`/`UPDATED_AT` columns are present on core tables, providing creation and modification timestamps.
- No `purge_date`, `retention_date`, or archival flag columns exist.
- `TRANSFER_HISTORY` and `RATE_HISTORY` are append-only history tables with no deletion mechanism.
- For FinCEN compliance, records of cross-border transfers must be retained for 5 years (31 CFR §1010.430).
