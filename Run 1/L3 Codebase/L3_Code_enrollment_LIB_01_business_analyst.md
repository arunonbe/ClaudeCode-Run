# Business Analyst Analysis — enrollment_LIB

## Repository Overview

**Repo name:** `enrollment_LIB`
**Type:** Batch extract library — cardholder enrollment reporting
**Primary language:** Java (compiled at Java 1.6 source level, `pom.xml` lines 118–120)
**Framework:** Spring 2.0.8 (XML configuration), jTDS JDBC driver
**Artifact:** `com.ecount.processes.enrollment:enrollment:2.0.3-SNAPSHOT` (`pom.xml` line 7)
**Historical owner:** Previously labelled as `com.citi.processes.enrollment` (package names throughout `src/`), indicating legacy Citi Prepaid / eCount lineage now under Onbe/North Lane ownership.

---

## Business Purpose

`enrollment_LIB` implements the **cardholder enrollment extract process** — a scheduled batch job that queries a SQL Server database for enrollment activity within a defined date range and produces fixed-width flat files for downstream processing (e.g., FTP delivery to an issuing bank or partner).

### Business Function

The library supports **three enrollment event types** (defined in `EventType.java`):
- `ENROLL` (0) — a cardholder has newly enrolled.
- `UNENROLL` (1) — a cardholder has withdrawn from a programme.
- `SYSTEMENROLL` (2) — a system-initiated enrollment (e.g., auto-enroll on card activation).

For each programme/brand/affiliate combination that has a pending extract, the process:
1. Queries enrollment records from the database via stored procedure `get_enrollment_extract_by_program_id` (`Extract.java` line 27).
2. Resolves sensitive data (SSN, ACH account details) from a **StrongBox** secure data store via XML-RPC (`StrongBoxClient.java`).
3. Generates a fixed-width flat file with header, detail, and trailer records (`FileHandler` bean in `spring.xml` lines 54–107).
4. Moves the file to an FTP staging location.
5. Updates the report status table to `COMPLETE` or `FAILED`.

### Business Entities Handled

| Entity | Source | Sensitive Data Fields |
|--------|--------|-----------------------|
| Cardholder profile | `dbo` database via stored proc | `puid`, `firstName`, `lastName`, `email`, `mobilePhone` |
| Address | Database | `address1`, `address2`, `city`, `state`, `postal`, `country` |
| ACH banking details | StrongBox secure retrieval | `routingNumber`, `accountNumber`, `bankName` |
| Identity | StrongBox / database | `ssn`, `dob` (present in `ExtractInfo.java` lines 11–12) |
| Enrollment event | Database | `eventType` (ENROLL/UNENROLL/SYSTEM-ENROLL), `optionType`, timestamps |

### Compliance Relevance

This batch process handles **PII and financial account data** including:
- Social Security Numbers (`ssn` field, `ExtractInfo.java` line 11).
- Full bank routing and account numbers (`routingNumber`, `accountNumber`, lines 39–40).
- Date of birth (`dob`, line 12).

This places the library squarely in scope for:
- **GLBA** — financial data of cardholders.
- **CCPA / PIPEDA** — PII of US and Canadian residents.
- **PCI DSS** — potential cardholder data if card numbers are ever included (the `PUID` field may proxy for account numbers).
- **Reg E** — ACH enrollment data is subject to consumer protection rules.

### Report Status Lifecycle

| Status Code | Meaning |
|-------------|---------|
| `0` | `ReportStatus.COMPLETE` — extract generated and file moved |
| `1` | In-flight |
| `2` | `ReportStatus.FAILED_MOVE` — extract generated but file move failed; retry from this step |
| `FAILED` | Terminal failure (`ReportStatus.FAILED.getId()`, `ProcessMain.java` line 107) |

### Programme Processing Loop

`ProcessMain.java` (lines 51–130) iterates over all active programmes (those with `status = 1` from `profile.getProfileInfo(1)`) and for each generates reports for all required date ranges. This is a multi-programme, multi-date-range batch — appropriate for high-volume prepaid card programmes with many brands and affiliates.

---

## Business Risk and Gaps

| Risk | Description |
|------|-------------|
| No de-duplication | The extract query (`get_enrollment_extract_by_program_id`) is not visible in this repo; if the stored procedure returns duplicates, the flat file will contain duplicate cardholder records |
| Batch failure is non-atomic | A failure mid-programme sets `endStatus = 1` and continues to the next programme (line 126); partial output files may be created |
| SSN and DOB in flat file | `ExtractInfo.java` carries `ssn` and `dob` fields; if these are emitted in the flat file, the file must be classified as highly sensitive and encrypted at rest and in transit |
| No reconciliation | There is no record count reconciliation between database query results and file output |
| Status table update | The `status.setReportStatus()` call (line 113) is the only persistent record of processing; if this fails, the programme may be re-processed on next run |

---

## Stakeholders

| Role | Concern |
|------|---------|
| Programme Management | Which programmes and brands are processed |
| Operations | Monitoring batch success/failure; re-running failed programmes |
| Compliance / Privacy | PII handling, data minimisation, GLBA/CCPA compliance |
| Partner Banks / Affiliates | Receiving the extract files via FTP |
| Security | StrongBox credential management, file encryption |
