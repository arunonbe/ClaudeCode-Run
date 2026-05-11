# Solution Architect — INIT1400-GPScribe

## Technical Debt Register

### Critical Severity

| ID | Location | Issue | Regulatory Impact |
|----|----------|-------|-------------------|
| TD-001 | `DYNO_Scribe_West_DataImport.sql` line 33 | Linked server defined by hardcoded IP `10.10.150.7` — no DNS name; IP change silently breaks integration | Operational continuity |
| TD-002 | `DYNO_Scribe_West_InvoiceImport.sql` decoded | Recovery procedure requires manual modification of production SP code; no parameterized re-run path | SOX-adjacent: manual changes to production code without deploy pipeline |
| TD-003 | `INIT1400-SQLJob.sql` line 26 | Job owner `NAM\David.Laumonier` — named personal AD account; account deactivation stops job silently | Business continuity |

### High Severity

| ID | Location | Issue | Impact |
|----|----------|-------|--------|
| TD-004 | `DYNO_Scribe_West_InvoiceImport.sql` decoded lines 597–603 | DB Mail alert is commented out with `/* Need DBMAIL turned on */`; no alerting on eConnect import failures | Silent revenue recognition failures |
| TD-005 | `DYNO_Scribe_West_InvoiceImport.sql` decoded line 230 | `TOP 1000` limit on active items filter — if GP has >1000 active items, some valid invoices are silently excluded | Data completeness risk |
| TD-006 | `DYNO_Scribe_West_InvoiceImport.sql` decoded line 231 | `TOP 10000` limit on active customers — same truncation risk for large customer bases | Data completeness risk |
| TD-007 | `DYNO_Scribe_West_DataImport.sql` line 137 | Bidirectional linked server write access — GP server can write to CRM source via remote SP call | Increased attack surface; blast radius of SQL injection |
| TD-008 | `DYNO_Scribe_West_InvoiceImport.sql` | File saved in UTF-16 LE (wide-char) encoding — incompatible with standard SQL tools, text search, and diff tools | Maintainability; code review difficulty |

### Medium Severity

| ID | Location | Issue | Impact |
|----|----------|-------|--------|
| TD-009 | `DYNO_Scribe_West_DataImport.sql` line 33 | Source database named `Dev_Swiftgift_CRM` — `Dev_` prefix ambiguous; may be production with a legacy dev name | Data governance; audit trail integrity |
| TD-010 | Both SPs | No environment-specific configuration; IPs and DB names are hardcoded | No dev/QA isolation; testing risks production data |
| TD-011 | `DYNO_Scribe_West_InvoiceImport.sql` | No transaction wrapping around the entire invoice import loop — a mid-run server failure leaves staging marked as processed but GP records absent | Data consistency on crash |
| TD-012 | `DYNO_Scribe_West_InvoiceImport.sql` decoded line 226 | Comment `-- AND x.DOCUMENT_DATE = '6/18/2024' -- Used for Testing Purpose` left in production SP | Indicates testing was done directly in production code |
| TD-013 | Repository | No CI/CD pipeline; no deploy automation; no version control of stored procedure state on server | Drift risk; no audit trail of deployed versions |

## Security Vulnerabilities

### Finding 1 — Hardcoded IP Linked Server with Write Access (TD-001, TD-007)

**Files**: `DYNO_Scribe_West_DataImport.sql` lines 33 and 137

**Description**: The SQL Server Linked Server connecting from `P-AZ-GPSQL-VM01` to `10.10.150.7` enables:
- Reading all unprocessed invoices from `CRM_Invoice_Report` via `OPENQUERY`.
- Executing `INTI1400_UpdateProcessedFlag` to update records in the CRM source database.

This bidirectional capability means the GP server has a persistent, privileged connection to the CRM server. If an attacker gains SQL execution on the GP server (via SQL injection in any SWIFT DB stored procedure, or via a compromised service account), they can potentially:
- Read all CRM invoice data.
- Corrupt the `Processed` flag to cause re-import or to suppress imports.
- Enumerate other databases accessible on `10.10.150.7`.

**Remediation**: Replace the linked server write-back pattern with an event/message pattern: after staging, publish a message to Azure Service Bus with the processed document list; a lightweight API on the CRM side consumes the message and updates its own processed flag. This eliminates the GP server's write access to the CRM database.

### Finding 2 — Silent Failure on eConnect Import Errors (TD-004)

**File**: `DYNO_Scribe_West_InvoiceImport.sql` decoded lines 597–603

**Description**: When eConnect returns a non-zero error code for an invoice, the error is logged to `CA_tblScribeInvoice_ErrorLog` and the procedure continues processing remaining invoices. No exception is raised, no job step fails, and the DB Mail alert (`sp_send_dbmail`) that would notify `david.laumonier@onbe.com` is commented out.

This means that on any given business day, some invoices may silently fail to import to GP. The only way to detect this is to query `CA_tblScribeInvoice_ErrorLog` manually, or to run a reconciliation between the CRM invoice count and the GP SOP invoice count.

From a financial controls perspective, silent import failures create an undetected gap in accounts receivable, potentially misstating revenue for the period. This is relevant under GAAP revenue recognition requirements and potentially under SOX if this business unit is within scope.

**Remediation**: Uncomment and configure `sp_send_dbmail`. Additionally, add a `RAISERROR` after the import loop if `@tblResultErrSum` contains non-zero entries, causing the SQL Agent job step to fail and trigger the job's event log notification.

### Finding 3 — `TOP N` Hard Limits on Master Data Lookups (TD-005, TD-006)

**File**: `DYNO_Scribe_West_InvoiceImport.sql` decoded lines 230–231

**Code patterns**:
- `IN (SELECT TOP 1000 ITEMNMBR FROM SWIFT..IV00101 WHERE INACTIVE = 0)` — active items filter
- `IN (SELECT TOP 10000 CUSTNMBR FROM SWIFT..RM00101 WHERE INACTIVE = 0)` — active customers filter

**Description**: These `TOP N` clauses have no ORDER BY, meaning the 1000/10000 selected rows are non-deterministic (dependent on SQL Server's execution plan). If the GP database has more than 1000 active items or more than 10000 active customers, some valid invoices will be silently excluded from import with no error. There is no alert, no logging, and no indication to the operator that records were dropped.

**Remediation**: Remove the `TOP N` limits and use direct `EXISTS` subqueries or `IN (SELECT ITEMNMBR FROM IV00101 WHERE INACTIVE = 0)` without artificial limits. If performance is a concern, create appropriate indexes on `IV00101(INACTIVE, ITEMNMBR)` and `RM00101(INACTIVE, CUSTNMBR)`.

### Finding 4 — Wide-Character File Encoding (TD-008)

**File**: `DYNO_Scribe_West_InvoiceImport.sql`

**Description**: The file is saved in UTF-16 LE encoding with BOM, causing each ASCII character to appear as a space-separated letter when read by standard tools. This makes:
- Code review in GitHub (web UI) effectively impossible — the diff view shows garbled content.
- Text search tools (grep, CodeQL) may not parse the file correctly, potentially missing security findings.
- Any secret scanning tool that does not decode UTF-16 will fail to detect hardcoded credentials.

**Remediation**: Re-save the file as UTF-8 without BOM. Standard SQL Server Management Studio can re-save in UTF-8. Add a `.editorconfig` rule to enforce UTF-8 encoding for `.sql` files.

## Remediation Priority Matrix

| Priority | Item | Estimated Effort |
|----------|------|-----------------|
| 1 — Immediate | Enable DB Mail and RAISERROR on import failures | 0.5 day |
| 2 — Immediate | Change job owner to a service account | 0.5 day |
| 3 — Sprint 1 | Remove `TOP N` limits on item/customer lookups | 0.5 day |
| 4 — Sprint 1 | Add `@batch_id` parameter for targeted re-run without SP code modification | 1 day |
| 5 — Sprint 1 | Re-save `DYNO_Scribe_West_InvoiceImport.sql` as UTF-8 | 0.5 day |
| 6 — Sprint 2 | Replace linked server IP with DNS hostname and store credentials in Key Vault | 2 days |
| 7 — Sprint 2 | Replace write-back linked SP call with Service Bus message pattern | 3–5 days |
| 8 — Sprint 2 | Implement Azure Monitor alert on INIT1400 job failures | 1 day |
| 9 — Quarter 2 | Implement CI/CD deploy pipeline for SQL scripts (SSDT or Flyway) | 3–5 days |
| 10 — Quarter 2 | Implement environment separation (Dev/QA/Prod config) | 2–3 days |

## Positive Observations

- The error handling pattern — capturing eConnect return codes, logging to `@tblImportResults`, then deleting partial GP records for failed invoices — is a sound compensating transaction pattern. It prevents orphaned partial invoices in GP, which would be worse than a missed import.
- The `OASIS_Exclusion` table pattern is a good extensibility design: new fee types or item exclusions can be added via a data change without modifying stored procedure code.
- The duplicate prevention guard (`DOCUMENT_NUM NOT IN (SELECT FROM SOP10100 WHERE DOCDATE >= -3 months)`) prevents double-posting of invoices that may be re-staged on a manual re-run.
- The Monday lookback logic (`DATEPART(dw, GETDATE()) = 2 THEN DATEADD(DAY, -2, ...)`) correctly handles the weekend gap so that Friday invoices are included in Monday's run.
- The inline change log comment block at the top of `DYNO_Scribe_West_InvoiceImport.sql` (though obscured by encoding) provides a useful development history trail in the absence of a formal change management system.
