# DS_DB_vendor — Data Architect Assessment

## 1. Schema Architecture

The Vendor database uses four explicit schemas: `dbo`, `GBBase`, `GBLoads`, and `GBMap`. This multi-schema design separates operational staging (dbo), core cardholder data (GBBase), ETL control (GBLoads), and reporting views (GBMap). The design indicates a structured data warehouse pipeline pattern where raw file data lands in dbo staging, is promoted to GBBase, and is surfaced for consumption via GBMap views.

---

## 2. Schema: dbo — FDR Staging and Operational Tables

### 2.1 `dbo.fdr_cardholder_master`
File: `dbo/Tables/fdr_cardholder_master.sql`

```sql
CREATE TABLE [dbo].[fdr_cardholder_master] (
    [card_number]     CHAR (16) NULL,  -- FULL 16-DIGIT PAN
    [status_code]     CHAR (1)  NULL,
    [cardholder_name] CHAR (54) NULL,
    [expiration]      DATETIME  NULL   -- card expiration date
);
```

**CRITICAL FINDING:** `card_number CHAR(16)` stores the full 16-digit PAN (Primary Account Number). There is no masking, truncation, tokenisation, or encryption. This table has no primary key and no indexes. Combined with `cardholder_name` and `expiration`, this table contains a complete set of card-present fraud enablement data. PCI DSS Requirement 3.4 mandates that stored PAN be rendered unreadable — this table violates that requirement.

---

### 2.2 `dbo.fdr_import_cd_012` — FDR CD-012 Import (SHA1 Hashing Trigger)
File: `dbo/Tables/fdr_import_cd_012.sql`

This table receives FDR CD-012 card data records with a `card_hash CHAR(20)` field. An `AFTER INSERT` trigger (`fdr_import_cd_012_insert_trigger`, lines 26–37) applies SHA1 hashing to `card_hash` on insert:

```sql
UPDATE fdr_import_cd_012
SET fdr_import_cd_012.card_hash = hashbytes('sha1', rtrim(fdr_import_cd_012.card_hash))
FROM inserted
WHERE fdr_import_cd_012.file_date = inserted.file_date
  AND fdr_import_cd_012.record_number = inserted.record_number
```

**Positive security control:** the SHA1 hashing trigger ensures that the raw card number (if initially populated in `card_hash`) is immediately hashed on insert. The comment at line 31 `-- 2007-03-21 MSA Card number removal` confirms this was added explicitly to prevent card number storage.

**Note on SHA1:** SHA1 is cryptographically weak and unsuitable as a standalone card hash for PCI DSS purposes (PCI DSS recommends keyed HMAC or other salted hash). However, the intent to prevent plaintext PAN storage is the correct approach.

---

### 2.3 `dbo.fdr_process_dcaf_chd_data_20090519` — DCAF Card Holder Data
File: `dbo/Tables/fdr_process_dcaf_chd_data_20090519.sql`

Stores FDR DCAF (Debit Card Account File) cardholder data: `card_hash CHAR(20)`, `dda_number CHAR(16)`, `exp_date CHAR(4)`, balance fields. The table name includes a date (`20090519`) indicating it was created or modified in May 2009 — suggesting this is a point-in-time schema snapshot that was never refactored into a version-neutral name. The disabled indexes (`ALTER INDEX ... DISABLE` at lines 30 and 40) indicate the table may be in a degraded operational state.

---

### 2.4 `dbo.ness_hits` — OFAC Screening Results
File: `dbo/Tables/ness_hits.sql`

Contains the full NESS OFAC screening output for every cardholder match:

| Column | Type | Content |
|---|---|---|
| `last_name` / `first_name` | VARCHAR(1000) | Submitted cardholder name |
| `address` | VARCHAR(2000) | Submitted cardholder address |
| `nationality` | VARCHAR(255) | Nationality field |
| `passport` | VARCHAR(400) | Passport number |
| `birth_date` | VARCHAR(50) | Date of birth |
| `matched_against` | VARCHAR(2100) | SDN list entity matched against |
| `matched_last_name` / `matched_first_name` | VARCHAR(255/511) | Matched SDN entry name |
| `matched_alias_name` | VARCHAR(2500) | Matched alias |
| `matched_address` | VARCHAR(3000) | Matched address on SDN list |
| `matched_birth_date` | VARCHAR(255) | SDN list birth date |
| `disposition_id` | CHAR(5) | Resolution outcome |
| `reviewer_id` | CHAR(3) | Reviewer identifier |
| `final` | CHAR(10) | Final disposition |

This table combines cardholder PII with OFAC SDN match data. It is a BSA/AML compliance record requiring long-term retention and strict access control. The wide VARCHAR columns (`keyword VARCHAR(8000)`, `matched_alias_name VARCHAR(2500)`) hold SDN list matching metadata.

---

### 2.5 `dbo.IVR_CallLog` — IVR Call Records
File: `dbo/Tables/IVR_CallLog.sql`

Key fields of concern:
- `session_id VARCHAR(255)` — session identifier (PK via unique index)
- `ani VARCHAR(255)` — Automatic Number Identification (caller's phone number) — PII
- `dnis VARCHAR(255)` — Dialed Number Identification Service
- `card_number VARCHAR(10)` — partial card number (last 10 or first 10 digits)
- `dob VARCHAR(12)` — date of birth provided by caller — PII
- `zip VARCHAR(10)` — ZIP code provided by caller
- `dda VARCHAR(255)` — DDA account number

The `dob` field on IVR call records is a significant PII storage concern — it captures the DOB cardholder entered for authentication, stored indefinitely unless `usp_IVR_CallLog_Cleanup` is run regularly.

---

### 2.6 `dbo.chargeback_process_queue` — Chargeback Queue
File: `dbo/Tables/chargeback_process_queue.sql`

Stores active chargeback cases: `dda_number CHAR(16)`, `card_id INT`, `ticket_number VARCHAR(15)`, `auth_amnt INT`, `tx_amnt INT`, `cb_amount INT`, `reason_code VARCHAR(4)`, `post_tx_id UNIQUEIDENTIFIER`. The queue has a proper FK to `chargeback_profile_status_code` and an index on `process_id`. This is a well-structured operational table.

---

## 3. Schema: GBBase — Core Cardholder Repository

### 3.1 `GBBase.CustomerMaster` — CRITICAL PII TABLE
File: `GBBase/Tables/CustomerMaster.sql`

The most sensitive table in the Vendor database. Stores the complete cardholder master record as received from FDR:

| Column | Type | PII Risk |
|---|---|---|
| `CardNumber` | VARCHAR(100) | Full PAN — plaintext |
| `ECN` | VARBINARY(256) | Encrypted Card Number |
| `SSN` | VARCHAR(50) | Social Security Number — **PLAINTEXT** |
| `ESN` | VARBINARY(256) | Encrypted SSN |
| `EBD` | VARBINARY(256) | Encrypted Birth Date |
| `msc2DOB` | VARCHAR(50) | Date of Birth — plaintext |
| `PrimaryCardholderFirstName` | VARCHAR(50) | |
| `PrimaryCardholderLastName` | VARCHAR(50) | |
| `AddressLine1/2`, `City`, `State`, `Zip` | VARCHAR | Full address |
| `PrimaryPhoneNumber` | VARCHAR(10) | |
| `SecondaryPhoneNumber` | VARCHAR(10) | |
| `AccountNumber` | VARCHAR(30) | DDA number |

**CRITICAL FINDINGS:**
1. `SSN VARCHAR(50)` — Social Security Number stored in **plaintext**. This is a direct violation of PCI DSS Requirement 3.3 (sensitive authentication data must not be stored) and a fundamental GLBA/CCPA/GDPR privacy failure. SSN is not cardholder data in the PCI sense, but it is among the most sensitive categories of PII under any privacy regulation.
2. `CardNumber VARCHAR(100)` — Full PAN in plaintext alongside the encrypted version `ECN VARBINARY(256)`. Having both plaintext and encrypted versions in the same row is unusual — it suggests the plaintext version may be a legacy field that was supposed to be cleared but was not.
3. `msc2DOB VARCHAR(50)` — Date of birth in plaintext. The column name prefix `msc2` suggests it was added as a "miscellaneous" field, potentially bypassing data governance controls.
4. The simultaneous presence of `SSN` (plaintext) and `ESN` (encrypted) for the same field suggests the plaintext column predates an encryption initiative that was never completed for the SSN field.

**CDC (Change Data Capture) is enabled** on this table — `GBBase.CustomerMaster_CDC_Journal` (`GBBase/Views/CustomerMaster_CDC_Journal.sql`) queries `cdc.fn_cdc_get_all_changes_GBBase_CustomerMaster()`. This means every INSERT and DELETE to `CustomerMaster` (including SSN values) is captured in the CDC change tables, expanding the PII surface area beyond the base table.

The `GBBase.CustomerMaster_Journal` view provides a non-CDC journal. Both views expose all PII columns including SSN and CardNumber.

---

### 3.2 `GBBase.AuthorizedTransactions`
File: `GBBase/Tables/AuthorizedTransactions.sql`

- `CardNumber VARCHAR(30)` — plaintext card number in authorized transaction records
- `ECN VARBINARY(256)` — encrypted card number (parallel to CustomerMaster pattern)
- `AccountNumber VARCHAR(30)` — DDA number
- Transaction amount, merchant data, authorization response

Again, the co-existence of plaintext `CardNumber` and encrypted `ECN` is a data architecture inconsistency suggesting incomplete encryption migration.

---

### 3.3 `GBBase.PostedTransactions`
File: `GBBase/Tables/PostedTransactions.sql`

- `CardNumber VARCHAR(30)` — plaintext card number in posted/settled transactions
- `ECN VARBINARY(256)` — encrypted equivalent
- Full transaction settlement data (amount, merchant, post date, settlement date)

---

## 4. Schema: GBLoads — ETL Control

### 4.1 `GBLoads.Files` and `GBLoads.FileSteps`
Implement a file processing pipeline with status tracking. `Files` records each loaded file with start/end time and record count. `FileSteps` tracks sub-steps within each file load. `GBLoads.Log` is the parent load record.

### 4.2 `GBLoads.tmpNESSTable` — NESS Staging
File: `GBLoads/Tables/tmpNESSTable.sql`

A flat staging table receiving raw NESS response file rows. All columns are `VARCHAR(8000)` — no type enforcement. Fields include `LastName`, `FirstName`, `Address`, `Nationality`, `Passport`, `DateOfBirth` — raw OFAC screening results before parsing into `dbo.ness_hits`. This table retains raw PII until truncated at the start of the next NESS file load.

---

## 5. Schema: GBMap — Reporting Views

### 5.1 `GBMap.DDA_Card_Account_Detail`
File: `GBMap/Views/DDA_Card_Account_Detail.sql`

A critical view that surfaces `SSN`, `CardNumber`, `msc2DOB` (as DOB), full name, address, phone, balance, and card status from `GBBase.CustomerMaster`. This view is used as the source for `uspNESSDailyExtract` and is accessible to all `Vendor_Select` role members — meaning every production service account has read access to full cardholder SSN and PAN data through this view.

---

## 6. Security Objects of Concern

### 6.1 `GoogleBinCert` and `GoogleBinKey`
Files: `Security/GoogleBinCert.sql`, `Security/GoogleBinKey.sql`

```sql
CREATE CERTIFICATE [GoogleBinCert]
    WITH SUBJECT = N'Google Bin', START_DATE = N'2011-10-09', EXPIRY_DATE = N'2012-10-09';

CREATE SYMMETRIC KEY [GoogleBinKey]
    WITH ALGORITHM = DES
    ENCRYPTION BY CERTIFICATE [GoogleBinCert];
```

**Critical findings:**
1. `ALGORITHM = DES` — DES (56-bit) has been cryptographically broken since the late 1990s and is prohibited under PCI DSS. Any data encrypted with DES should be considered unprotected.
2. The certificate expired in **October 2012** — over 12 years ago. A SQL Server certificate past its expiry date cannot be used to open the symmetric key in standard configurations.
3. The purpose (`Google Bin` subject) is unclear — likely related to a Google BIN lookup integration for card brand identification. If any data was encrypted with `GoogleBinKey`, it is now inaccessible (expired cert) or trivially decryptable (broken DES algorithm).

---

## 7. Data Flow Diagram

```
FDR File Feeds (daily)
        |
        v
GBLoads.Files (file registry)
        |
        v
dbo.fdr_import_* (raw staging tables per record type)
GBBase.CustomerMaster (via uspUpdateCustomerMaster)
GBBase.AuthorizedTransactions
GBBase.PostedTransactions
        |
        v
GBMap views (DDA_Card_Account_Detail, etc.)
        |
        ├── uspNESSDailyExtract --> NESS OFAC engine
        │                               |
        │                               v
        │                        dbo.ness_hits (OFAC results)
        |
        └── dbo.IVR_CallLog (IVR system call logs)
        └── dbo.chargeback_process_queue (chargeback pipeline)
```
