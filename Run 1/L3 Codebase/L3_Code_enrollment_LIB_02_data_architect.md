# Data Architect Analysis — enrollment_LIB

## Repository Overview

**Repo:** `enrollment_LIB`
**Key source files:** `src/main/java/com/citi/processes/enrollment/`
**Spring config:** `src/main/resources/spring.xml`
**Build:** Maven, Java 1.6 source level (`pom.xml` lines 118–120)

---

## Data Architecture Overview

This library implements a **batch extract data pipeline** with three layers:

1. **Source:** SQL Server relational database, accessed via Spring JdbcTemplate / `StoredProcedure` (`Extract.java`, `Profile.java`, `Status.java`).
2. **Enrichment:** StrongBox XML-RPC service that decrypts sensitive fields (SSN, DOB, ACH tokens) on demand.
3. **Sink:** Fixed-width flat file written to a filesystem location, then moved to an FTP staging path.

---

## Core Data Model

### `ExtractInfo` (transfer object)
Defined in `src/main/java/com/citi/processes/enrollment/common/ExtractInfo.java`.

| Field | Type | Description | Sensitivity |
|-------|------|-------------|-------------|
| `puid` | String | Primary unique identifier for the cardholder account | Internal key |
| `ssn` | String | Social Security Number — **PII/sensitive** | PII — GLBA, CCPA |
| `dob` | String | Date of birth — **PII** | PII |
| `ecountId` | String | Legacy eCount system identifier | Internal |
| `firstName`, `middleName`, `lastName` | String | Cardholder name | PII |
| `email` | String | Email address | PII |
| `mobilePhone` | String | Mobile phone number | PII |
| `address1–2`, `attention`, `company`, `city`, `state`, `postal`, `country` | String | Full postal address | PII |
| `addressUpdate` | String | Address change indicator | |
| `pud1–5` | String | Programme user-defined fields | Programme-specific |
| `date`, `time` | String | Event timestamp | |
| `eventType` | String | ENROLL / UNENROLL / SYSTEM-ENROLL | |
| `optionType` | String | Enrollment option (e.g., ACH, e-card) | |
| `secutiryToken` | String | Card security token — **note: field name contains a typo** | Sensitive |
| `achSecureToken` | String | ACH secure token — tokenised ACH credential | Sensitive |
| `bankName` | String | Bank name | Financial |
| `routingNumber` | String | ABA routing number | Financial — Reg E |
| `accountNumber` | String | Bank account number | Financial — Reg E |
| `accountType` | String | Checking / savings | Financial |

**Note:** `ExtractInfo` carries full bank account details (`routingNumber`, `accountNumber`) and identity data (`ssn`, `dob`). This is one of the most sensitive data structures in the Onbe platform.

### `StatusInfo` (status tracking)
Defined in `src/main/java/com/citi/processes/enrollment/common/StatusInfo.java`. Tracks the processing status of a programme report for a given date, product, brand, and affiliate combination.

### `ProfileInfo` (programme profile)
Defined in `src/main/java/com/citi/processes/enrollment/common/ProfileInfo.java`. Drives the processing loop — determines which programmes need reports generated.

---

## Database Access Layer

### Stored Procedure: `get_enrollment_extract_by_program_id`
Defined at `Extract.java` line 27. Parameters:
- `@program_id` (VARCHAR)
- `@start_date` (VARCHAR)
- `@end_date` (VARCHAR)

Returns a `ResultSet` mapped by `ExtractInfoRowMapper` (inner class of `Extract.java`, lines 49–188). The mapper reads 23 fields from the result set, including `PUID`, `ECOUNT_ID`, names, address, contact, PUD fields, timestamp, event type, option type, security tokens, and ACH fields.

**Concern:** The stored procedure name, parameters, and column names are all hardcoded. This creates tight coupling between the Java layer and the database stored procedure API.

### `Profile` DAO
Calls a stored procedure to retrieve `ProfileInfo` records for programmes with a given status (`profile.getProfileInfo(1)`, `ProcessMain.java` line 51). These define which programmes and date ranges to process.

### `Status` DAO
Writes `StatusInfo` records to a report status table to track processing outcomes.

---

## StrongBox Integration

`StrongBoxClient.java` implements a **tokenisation service client** — it retrieves the plaintext values of sensitive fields (SSN, DOB, ACH data) that are stored as opaque references in the database. The protocol is XML-RPC over HTTP.

### Data Flow with StrongBox
```
Database result (contains token reference in securityToken / achSecureToken fields)
   |
   v
ProcessStrongBox.processRequest(listExtractInfo)
   |
   v
StrongBoxClient.readData(reference)  -- HTTP POST XML-RPC to StrongBox URI
   |
   v
ExtractInfo.ssn, .dob, .routingNumber, .accountNumber populated with plaintext
   |
   v
FileHandler.generateFile() -- writes to flat file
```

**Risk:** Plaintext SSN, DOB, and ACH account numbers pass through JVM memory in `ExtractInfo` objects. These are not zeroed after use, persisting in memory until GC. This is a standard concern for Gen-1/Gen-2 Java batch processes.

---

## File Format

The flat file is a **fixed-width record format** defined by field sizes configured in `spring.xml` (lines 61–107). Fields include:
- Header record: `recTypeIdentifier`, `runTime`, `fileName`, `programId`, `numberOfRecords`
- Detail records: all cardholder fields
- Trailer record

Field sizes are externalised as properties (`${size.puid}`, etc.), allowing format changes without code changes.

---

## Data Quality Observations

1. **Typo in field name:** `secutiryToken` (misspelling of `securityToken`) appears in `ExtractInfo.java` line 37 and `Extract.java` line 178. This has been carried forward and is now a frozen API contract.
2. **Null handling:** All field mappings in `ExtractInfoRowMapper` check for null and non-empty string before setting values (lines 54–186). This is defensive but produces empty strings in the output for missing data.
3. **Date/time splitting:** Timestamp is split into separate `date` and `time` String fields (lines 159–166) using `Calendar` — a legacy pattern that predates `java.time`.
4. **SSN and DOB not sourced from database:** Based on the mapper, `ssn` and `dob` are NOT mapped from the stored procedure result set — they are presumably populated by the StrongBox retrieval step. This is the correct design for tokenised sensitive data.

---

## Data Lineage Summary

```
Source DB (SQL Server)
  |-- program_profile_table (read: which programmes to process)
  |-- program_report_status_table (read+write: processing status)
  |-- get_enrollment_extract_by_program_id (stored proc: enrollment records)
         |
         v
    ExtractInfo (Java DTO in memory)
         |
         v
    StrongBox (XML-RPC: resolve tokens -> SSN, DOB, ACH fields)
         |
         v
    Fixed-width flat file (output: FileHandler)
         |
         v
    FTP staging location (moved by FileHandler.moveFiles())
```
