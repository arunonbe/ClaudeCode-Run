# Data Architect — INIT1400-GPScribe

## Data Entities and Flow

```
[Dev_Swiftgift_CRM]                    [SWIFT DB]                    [DYNAMICS GP]
10.10.150.7                            P-AZ-GPSQL-VM01               P-AZ-GPSQL-VM01
─────────────────────                  ─────────────────────         ─────────────────
CRM_Invoice_Report                     CA_tblStg_ScribeInvoice       SOP10100 (hdr)
  INVOICE_ID                    ──►    INVOICE_ID                ──► SOP10200 (lines)
  DOCUMENT_NUM (SOPNUMBE)              DOCUMENT_NUM                  SOP10202
  DOCUMENT_DATE                        DOCUMENT_DATE                 SOP10106
  CUSTOMER_ID                          CUSTOMER_ID                   SOP10107
  ITEM_NUMBER                          ITEM_NUMBER                   SOP10101
  QUANTITY                             QUANTITY                      SOP10102
  UNIT_PRICE                           UNIT_PRICE
  EXTENDEDPRICE                        EXTENDEDPRICE           ──► CA_tblScribeInvoice_ErrorLog
  CURRENCY_ID                          CURRENCY_ID
  BATCH_ID                             BATCH_ID
  SOURCE                               SOURCE
  TYPE (SOPTYPE 3=Invoice, 4=Returns)  TYPE
  ...10 generic FIELD columns          ...
  Processed (flag)                     Processed ('N'/'Y')
```

## Schema Details

### CA_tblStg_ScribeInvoice (Staging Table, SWIFT DB)

| Column | Type | Notes |
|--------|------|-------|
| INVOICE_ID | — | Source CRM invoice key |
| SOURCE | — | CRM source identifier |
| TYPE | — | SOPTYPE: 3=Invoice, 4=Returns |
| TYPE_ID | — | Document ID (DOCID in GP) |
| DOCUMENT_NUM | CHAR(21) | GP SOP number (SOPNUMBE) |
| DOCUMENT_DATE | DATE | Invoice date |
| DEFAULT_SITE_ID | — | GP site/location |
| BATCH_ID | CHAR(15) | GP batch grouping |
| CUSTOMER_ID | CHAR(15) | GP customer number (CUSTNMBR) |
| ITEM_NUMBER | CHAR(31) | GP item number (ITEMNMBR) |
| UNIT_OF_MEASURE | CHAR(8) | |
| QUANTITY | NUMERIC(19,2) | |
| UNIT_PRICE | NUMERIC(19,2) | |
| EXTENDEDPRICE | NUMERIC(19,2) | Line total |
| CURRENCY_ID | CHAR(15) | |
| CUSTOMER_NAME | — | |
| CUSTOMER_PO | CHAR(20) | |
| ID_COMMENT, TEXT_COMMENT, NOTE | — | |
| FIELD1–FIELD10 | — | 10 generic extension columns |
| Version_InsertDate, Version_EndDate | — | Staging metadata |
| Processed | CHAR(1) | 'N' = unprocessed, 'Y' = imported to GP |
| ProcessLine | CHAR(1) | Line-level processed flag |
| UserId | CHAR(?) | Value: 'eConnect' (set by Step 1) |

### CA_tblScribeInvoice_ErrorLog (Error Log, SWIFT DB)

| Column | Notes |
|--------|-------|
| SOPNUMBE | Failed document number |
| BATCHID | Batch identifier |
| ITEMNMBR | Item that failed |
| RECID | Record ID |
| ErrCode | eConnect error code |
| ErrMsg | Error description (from `DYNAMICS..taErrorCode`) |

Created 2024-11-12 per change log in `DYNO_Scribe_West_InvoiceImport.sql`.

### CRM_Invoice_Report (Source, Dev_Swiftgift_CRM at 10.10.150.7)

| Column | Notes |
|--------|-------|
| DOCUMENT_NUM | Invoice number |
| Processed | NULL = unprocessed, 0 = unprocessed, 1 = processed |
| All staging columns | Mirrored to staging table |

## Data Sensitivity Classification

| Data Element | Classification | Regulatory Relevance |
|--------------|---------------|---------------------|
| CUSTOMER_ID, CUSTOMER_NAME | PII (business entity) | GDPR Art. 4 if EU customers; CCPA if CA customers |
| CUSTOMER_PO | Commercial | Contract data |
| UNIT_PRICE, EXTENDEDPRICE, QUANTITY | Financial | GAAP, SOX (if applicable) |
| CURRENCY_ID, DOCUMENT_DATE | Financial | Revenue recognition |
| ITEM_NUMBER (fee codes) | Business-sensitive | Revenue reporting |

**Note**: This pipeline does **not** appear to process PAN (Primary Account Numbers), CVV, or other cardholder payment credentials. The fee item codes (`ACHFEE`, `PUSHPAYFEE`, etc.) reference fee product line items in the GP item master, not actual payment card data. However, the customer records (`RM00101`) in GP may link back to card program clients, placing this system within the broader Onbe data environment requiring access controls consistent with GLBA and CCPA data handling requirements.

## Linked Server Architecture Risk

The integration relies on a **SQL Server Linked Server** connecting from `P-AZ-GPSQL-VM01` to IP address `10.10.150.7`. This introduces several data architecture concerns:

1. **Hardcoded IP address**: The linked server is defined by IP `10.10.150.7`, not a DNS hostname. Any IP change at the source CRM server breaks the integration silently until the next scheduled run.

2. **Source database named `Dev_Swiftgift_CRM`**: The database name contains `Dev_`, suggesting it may be a development or test database. If this is the actual production CRM database with a `Dev_` prefix (a legacy naming artifact), that represents a naming governance failure. If it is truly a development database, then production invoice data is being sourced from a non-production system, which violates data governance and audit trail integrity.

3. **Cross-server `OPENQUERY`**: `OPENQUERY` executes queries in the security context of the linked server login. The linked server credentials are stored in the SQL Server credential store on `P-AZ-GPSQL-VM01`. These credentials are not visible in the repository, but the existence of a linked server to an IP address implies a service account or SQL login is stored on the GP server with read access to the CRM database and execute access to `INTI1400_UpdateProcessedFlag`.

4. **Write-back to source system**: `DYNO_Scribe_West_DataImport.sql` calls `[10.10.150.7].[Dev_Swiftgift_CRM].[dbo].[INTI1400_UpdateProcessedFlag]` to update the processed flag in the CRM. This means the GP SQL Server has **write access to the CRM source database** via the linked server. This bidirectional access increases the blast radius of any SQL injection or credential compromise on either system.

## Data Retention and Lifecycle

- **Staging table** (`CA_tblStg_ScribeInvoice`): Records are marked `Processed = 'Y'` but not deleted. The staging table acts as a permanent import audit log. There is no evidence of a purge/archive procedure. Over time this table will grow without bound.
- **Error log** (`CA_tblScribeInvoice_ErrorLog`): Inserts only; no purge mechanism. Errors persist indefinitely.
- **GP SOP tables**: Failed import records are deleted (`SOP10100`, `SOP10200`, etc.) within the same transaction. Successfully imported records persist in GP per GP's standard document lifecycle.

## Data Quality Controls

| Control | Implementation |
|---------|---------------|
| Duplicate prevention | `DOCUMENT_NUM NOT IN (SELECT FROM SOP10100 WHERE DOCDATE >= -3 months)` — prevents re-import of documents already in GP |
| Inactive item filter | `ITEM_NUMBER IN (SELECT FROM IV00101 WHERE INACTIVE=0)` — TOP 1000 limit (potential gap if >1000 active items) |
| Inactive customer filter | `CUSTOMER_ID IN (SELECT FROM RM00101 WHERE INACTIVE=0)` — TOP 10000 limit |
| Zero quantity exclusion | `ISNULL(QUANTITY,0) <> 0` |
| OASIS exclusions | LEFT JOIN to `OASIS_Exclusion` table with `IS NULL` filter |
| Atomic cleanup | Failed imports have SOP records deleted from all 7 GP SOP tables |

**Risk**: The `TOP 1000` limit on the active items filter and `TOP 10000` on customers means if either master table has more active records than the limit, some valid invoices will be silently excluded from import with no error raised.

## Data Governance Gaps

1. **Source database naming** (`Dev_Swiftgift_CRM`): Requires clarification — is this the actual production CRM or a test copy? If production, the naming is misleading and a governance failure.
2. **No data lineage documentation**: The repository contains SQL scripts only; no data catalog, no lineage diagram, no data dictionary.
3. **No staging table TTL**: The staging table grows without bound; no archival or purge policy is defined.
4. **Linked server credential management**: The credentials for `10.10.150.7` linked server access are stored in SQL Server's credential store, not in a managed secrets vault (Azure Key Vault). Rotation of these credentials requires direct DBA intervention on the GP server.
