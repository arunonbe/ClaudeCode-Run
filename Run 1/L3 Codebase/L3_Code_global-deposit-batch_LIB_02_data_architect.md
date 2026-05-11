# Data Architect Report — global-deposit-batch_LIB

## 1. Module Structure

The library consists of six Maven modules:

| Module | Artifact | Purpose |
|---|---|---|
| `global-deposits-batch` | `global-deposits-batch` | Core batch job implementations |
| `global-deposits-batch-cbts-client` | `global-deposits-batch-cbts-client` | Direct CBTS HTTP client |
| `global-deposits-batch-config` | `global-deposits-batch-config` | Spring Boot application config and context wiring |
| `global-deposits-batch-data` | `global-deposits-batch-data` | Data model / prototype classes |
| `global-deposits-batch-qa` | `global-deposits-batch-qa` | Integration test suite |
| `global-deposits-batch-xplatform-client` | `global-deposits-batch-xplatform-client` | xPlatform iEFT client |

---

## 2. Database Schema

### 2.1 Core iEFT Transaction Journal

The primary database entities are in the `ecountcore` database (inferred from the H2 JDBC URL `jdbc:h2:mem:ecountcore` in `application.yml` line 9 and the SQL queries in `RecurringGlobalDepositServiceProcessor.java`):

**Table: `core_ieft_transaction_journal`**

| Column | Data Type | Description |
|---|---|---|
| `id` | (Long, PK) | Transaction record ID (`record.getRowId()`) |
| `tx_status` | Integer | Processing status (0=pending, 1=extracted/success, 5=failed, 6=error) |
| `extracted_date` | DateTime | Date/time of successful processing |

SQL operations on this table (from `RecurringGlobalDepositServiceProcessor.java` lines 19–24):
- `UPDATE core_ieft_transaction_journal SET tx_status=1, extracted_date=getdate() WHERE id=?` — success
- `UPDATE core_ieft_transaction_journal SET tx_status=5 WHERE id=?` — invalid data failure
- `UPDATE core_ieft_transaction_journal SET tx_status=6 WHERE id=?` — unexpected error

**Table: `core_ieft_transaction_journal_addenda`**

| Column | Description |
|---|---|
| `id` | Links to `core_ieft_transaction_journal.id` |
| `field_type` | NACHA addenda field type (185 = cross-border) |
| `value` | Addenda value (3 = processed) |

SQL operations (lines 20–23):
- SELECT to check for existing addenda 185 records
- INSERT addenda record if none exists
- UPDATE addenda value to 3 if exists

### 2.2 H2 In-Memory Database (Test/Config Module)

The `global-deposits-batch-config` module's `application.yml` configures an H2 in-memory database:
```yaml
datasource:
  url: jdbc:h2:mem:ecountcore;Mode=MSSQLServer
```

The `Mode=MSSQLServer` flag configures H2 to emulate SQL Server syntax, confirming the production database is Microsoft SQL Server.

Schema and seed data are managed via:
- `schema.sql` — DDL for test schema
- `data.sql` — DML seed data for testing

---

## 3. File-Based Data (Reject CSV Files)

### 3.1 Cambridge Rejection CSV Format

Files are read from an input directory matching `*.csv` pattern (`GlobalDepositRejectsItemReader.java` line 66).

**CSV Schema** (from `fileReader()` bean, lines 46–49):
```
transferId, returnedUsd, amount, fee, returnReason, fxRate
```

Test data files in `global-deposits-batch-qa/src/test/resources/test-data/batch/internal/globaldepositrejectprocess/` reveal real-world test scenarios:
- `cambridge-rejected-transactions-one-record.csv`
- `cambridge-rejected-transactions-two-records.csv`
- `cambridge-rejected-transactions-duplicate-records.csv`
- `cambridge-rejected-transactions-long-transfer-id.csv`
- `cambridge-rejected-transactions-malformed.csv`
- `cambridge-rejected-transactions-invalid-format.txt`

The `GlobalDepositRejectRecord` Lombok data class maps these fields:
```java
private String transferId;
private BigDecimal returnedUsd;
private BigDecimal amount;
private BigDecimal fee;
private String returnReason;
private BigDecimal fxRate;
private Timestamp created;
```

### 3.2 File Lifecycle

Files move through three states:
1. **Input** (`batch-jobs.global-deposit-reject-process.input`): Incoming CSV files from Cambridge
2. **Processed** (`batch-jobs.global-deposit-reject-process.processed`): Successfully processed files
3. **Failed** (`batch-jobs.global-deposit-reject-process.failed`): Files that caused processing errors

This is managed by `GlobalDepositRejectsMoveFileStepListener` which runs `@BeforeStep` and `@AfterStep`.

---

## 4. CBTS API Data Models

### 4.1 Rate Object

```java
// Rate.java (global-deposits-batch-data)
// Fields include rate ID, exchange rate, currency pair, expiry
```

### 4.2 Transfer Object

```java
// Transfer.java (global-deposits-batch-data)
// Fields include transfer ID, status, amount, currency
```

### 4.3 Configuration Objects (xPlatform Client)

From `global-deposits-batch-xplatform-client`:

| Class | Purpose |
|---|---|
| `CbtsHttpProperties` | HTTP timeout/credential properties |
| `CbtsUrlProperties` | CBTS API URL configuration |
| `XplatformClientProperties` | xPlatform agent and header configuration |

---

## 5. Credential and Sensitive Data Assessment

### 5.1 Hardcoded Credentials in application.yml (CRITICAL)

`global-deposits-batch-config/src/main/resources/application.yml` lines 28–29:

```yaml
cbts:
  http-client:
    username: "[REDACTED — rotate immediately]"
    password: "[REDACTED — rotate immediately]"
```

**This is a critical security finding**: Actual CBTS API credentials are committed to source control in `application.yml`. These appear to be development/QA credentials (the base URL is `cbts-dev.amer1.wirecard.com`) but they are nonetheless real credentials in a code repository.

This violates:
- PCI DSS Requirement 6.3.3 (no hardcoded credentials in code)
- NIST CSF 2.0 PR.AA-01 (identity management)
- GitLab/GitHub secret scanning policies

**These credentials must be rotated immediately and moved to a secrets management system (Azure Key Vault or equivalent).**

### 5.2 Transaction Data Sensitivity

The `core_ieft_transaction_journal` table processes international electronic funds transfers. Depending on the columns not exposed in the SQL queries (but present in the full table schema), this table may contain:
- Account numbers (DDA/routing numbers for ACH)
- Transfer amounts
- Beneficiary identifiers

Transfer amounts and IDs are in the reject CSV files, which are received from Cambridge and processed on the file system. These files should be secured with restricted filesystem ACLs.

### 5.3 CBTS Development URL in Code

The base URL `https://cbts-dev.amer1.wirecard.com/cross-border-transfer-service` in `application.yml` line 32 points to a Wirecard-branded development environment. Post-acquisition, it is unclear if this URL is still active or has been redirected. If the URL points to an unmanaged external system, there is a risk that CBTS API calls may fail silently or reach an unexpected endpoint.

---

## 6. Data Flow

```
[External Cambridge FX (CBTS)]
    |
    | CSV reject files (sftp/file share)
    v
[global-deposit-reject-process batch]
    |
    | Read CSV → GlobalDepositRejectRecord
    v
[JDBC: core_ieft_transaction_journal UPDATE]
    |
    | Move processed files
    v
[Filesystem: processed/ or failed/]

[DB: core_ieft_transaction_journal (pending records)]
    |
    | Spring Batch JdbcPagingItemReader
    v
[recurring-global-deposit-service batch]
    |
    | RecurringGlobalDepositServiceProcessor
    |
    |--→ [RateService.transfer(record)] → [CBTS API]
    |
    | JDBC: UPDATE tx_status
    v
[DB: core_ieft_transaction_journal (status updated)]
    |
    | JDBC: INSERT/UPDATE core_ieft_transaction_journal_addenda
    v
[DB: core_ieft_transaction_journal_addenda]
```
