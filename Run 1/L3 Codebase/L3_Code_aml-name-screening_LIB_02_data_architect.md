# aml-name-screening_LIB — Data Architect View

## Data Stores

| Store | Type | Role |
|-------|------|------|
| Input XLS file | File system, HSSF/BIFF8 `.xls` | Subject names to screen |
| `Ecountcore` database | Microsoft SQL Server (via jTDS JDBC) | Authoritative cardholder registration source |
| Output `amlResultSheet` tab | File system, HSSF/BIFF8 `.xls` (same file as input) | Screening results written back in-place |
| Log files | File system (Log4j `DatedFileAppender`) | Execution trace including SQL and field values |

## Schema & Tables

### Table: `fdr_dda_account_registration` (Ecountcore SQL Server)

Columns read by the screening query (`NameScreeningDAO.java` line 85):

| Column | Java Variable | Notes |
|--------|--------------|-------|
| `first_name` | `first_name` | Subject first name |
| `middle_name` | `middle_name` | Subject middle name |
| `last_name` | `last_name` | Subject last name |
| `dda_number` | `dda_number` | Demand Deposit Account number — financial identifier |
| `card_id` | `card_id` | Prepaid card identifier |
| `created` | `created` | Account creation timestamp |
| `city` | `city` | Cardholder city |
| `state` | `state` | Cardholder state |
| `postal` | `postal` | Postal/ZIP code |
| `country` | `country` | Country |
| `address1` | `address` | Street address |
| `home_email` | `email` | Email address (PII) |
| `home_phone` | `contact` | Phone number (PII) |

The full SQL query issued at runtime (DAO line 85):
```sql
select first_name, middle_name, last_name, dda_number, card_id, created,
       city, state, postal, country, address1, home_email, home_phone
from fdr_dda_account_registration
where (first_name+' '+middle_name+' '+last_name like '%<firstName>%<middleName>%<lastName>%')
```

No additional tables, views, stored procedures, or joins are used. No schema DDL is included in the repository.

### Input XLS Schema (expected, inferred from code)

Sheet 0 (unnamed), row 0 = header. Columns:
- Column 0: First Name
- Column 1: Middle Name
- Column 2: Last Name

Additional columns beyond index 2 are parsed but ignored.

### Output XLS Schema

Sheet name: `amlResultSheet`. Created fresh on `rowcount == 2` (i.e., the first subject row), deleting any prior sheet of that name. Columns:

| Index | Header |
|-------|--------|
| 0 | FIRSTNAME |
| 1 | MIDDLENAME |
| 2 | LASTNAME |
| 3 | DDA |
| 4 | CARDID |
| 5 | CREATED |
| 6 | CITY |
| 7 | STATE |
| 8 | POSTAL |
| 9 | COUNTRY |
| 10 | ADDRESS |
| 11 | EMAIL |
| 12 | CONTACT |

## Sensitive Data Handling

- **PII** — `home_email`, `home_phone`, `address1`, `city`, `state`, `postal`, `country`, `first_name`, `middle_name`, `last_name` are all retrieved and written to the output XLS file with no masking or redaction.
- **Financial identifiers** — `dda_number` (DDA) and `card_id` are written to the output in plain text. DDA numbers may constitute account-level financial data protected under GLBA and PCI DSS.
- **Credentials in source** — `NameScreeningConstants.java` lines 25–26 contain hardcoded plaintext values (`USERNAME = "report"`, `PASSWORD = "[REDACTED — rotate immediately]"`). A commented-out alternate pair (`[REDACTED — rotate immediately]`/`[REDACTED — rotate immediately]`) exists at lines 28–29.
- **Credentials in Maven settings** — `.mvn/wrapper/settings.xml` contains plaintext passwords for Nexus (`dwil15?`), ecount release (`d3v0nly`), and ecount snapshot (`d3v0nly`) server accounts (lines 38–51).
- **Credentials in logs** — `NameScreeningDAO.java` logs the full SQL string at INFO level (line 86), including the name values but not the credentials themselves.
- **DDA/CardID in logs** — Lines 108–110 of NameScreeningDAO.java log `dda_number` and `card_id` at INFO level for every result row, creating an uncontrolled PII/financial data trail.

## Encryption & Protection

- **At rest** — None. Input/output XLS files are unencrypted HSSF binary format. No OS-level encryption is enforced by the application.
- **In transit** — JDBC connection uses jTDS driver to SQL Server on port 2431 (`applicationContext.xml` line 44). No SSL/TLS configuration is specified in the connection URL or driver properties; jTDS defaults to unencrypted transport unless explicitly configured.
- **Credentials** — Stored in plaintext in source code and Maven settings XML. Not externalized to a secrets manager.
- **Output file** — Written to the same path as the input file via `FileOutputStream` with no access control or password protection (`NameScreeningHelper.java` line 210).

## Data Flow

```
[Operator filesystem]
    XLS input file (names)
          |
          | FileInputStream (NameScreeningHelper.loadInputFile)
          v
[JVM in-memory]
    HashMap<Integer, StringBuilder>  (rowIndex -> pipe-delimited name string)
          |
          | JDBC query (NameScreeningDAO.execute)
          v
[SQL Server: Ecountcore]
    fdr_dda_account_registration
          |
          | ResultSet (13 columns)
          v
[JVM in-memory]
    ArrayList<ArrayList<String>>  (result rows)
          |
          | FileOutputStream (NameScreeningHelper.updateWorkbook)
          v
[Operator filesystem]
    Same XLS file, sheet "amlResultSheet"
          |
          | Log4j DatedFileAppender
          v
[Log files on disk]
    SQL text + DDA numbers + card IDs at INFO level
```

## Data Quality & Retention

- **No deduplication** — If the same name appears in multiple input rows, duplicate queries are issued and duplicate result rows are appended to the output sheet.
- **No result pagination** — All matching rows from `fdr_dda_account_registration` are loaded into memory simultaneously. For a common name this could return thousands of rows.
- **No null safety on DB columns** — `rs.getString(...)` calls are made without null checks; a null column value in the DB would produce a null in the `ArrayList`, which is handled only in `updateWorkbook` via the `null != result.get(i).get(j)` check (line 191).
- **Column count assumptions** — The output loop hardcodes `j < 13` (line 178). If the DB query result set ever changes column count, silent data misalignment occurs.
- **No data retention policy** — The output XLS accumulates all results indefinitely. There is no archival, deletion, or rotation mechanism.
- **Log retention** — Log4j `DatedFileAppender` creates dated log files, but no maximum retention period or size limit is configured in the repository.

## Compliance Gaps

| Gap | Regulation | Severity |
|-----|-----------|----------|
| Plaintext credentials in source and settings.xml | PCI DSS Req 8.2, Req 8.3 | Critical |
| No encryption in transit for JDBC to SQL Server | PCI DSS Req 4.2 | High |
| PII written to unencrypted XLS file | GLBA, GDPR Art. 32, CCPA | High |
| PII (DDA, card_id) logged at INFO level | PCI DSS Req 3, GLBA | High |
| No data retention / deletion controls on output | GDPR Art. 5(1)(e), CCPA | Medium |
| No masking of financial identifiers in output | PCI DSS Req 3.3 | Medium |
| DDA number is not a PAN but is sensitive financial data | GLBA, internal data classification | Medium |
