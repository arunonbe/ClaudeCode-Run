# DS_DB_GP_emxn — Solution Architect Report

## 1. Technical Debt Inventory

| Debt Item | Location | Severity | Remediation |
|-----------|----------|----------|-------------|
| SQL 2008 compatibility level (compat 100) | `emxn.sqlproj` line 63 | CRITICAL | Upgrade to SQL 2019+ compat 150 |
| TDE not enabled | `emxn.sqlproj` line 51 (`IsEncryptionOn=False`) | HIGH | Enable TDE; migrate to Always Encrypted for SSN columns |
| Named individual SQL logins (~200) | `Security/` folder | HIGH | Convert to AD group-based access; remove individual logins |
| No change tracking / CDC | `emxn.sqlproj` line 47 | HIGH | Enable CDC on PII tables for audit trail |
| ANSI_NULLS disabled | `emxn.sqlproj` lines 65–66 | MEDIUM | Enable ANSI_NULLS; required for filtered indexes and future compat |
| QUOTED_IDENTIFIER disabled | `emxn.sqlproj` line 71 | MEDIUM | Enable; required for XML, JSON, and modern T-SQL features |
| ReadCommittedSnapshot disabled | `emxn.sqlproj` line 59 | MEDIUM | Enable RCSI to eliminate reader-writer blocking |
| VardecimalStorageFormatOn enabled | `emxn.sqlproj` line 61 | LOW | Disable; replace with row compression |
| No DeltaSql migration scripts | Repo root | MEDIUM | Implement migration script folder alongside DACPAC |
| No README/documentation | `README.md` (1 line) | MEDIUM | Create comprehensive README with entity purpose, owner, deployment guide |
| 16,594 stored procedures in source control | `dbo/Stored Procedures/` | LOW | Acceptable for GP; but DACPAC diff times are very long — consider GP upgrade path |

## 2. Security Vulnerability Assessment

### 2.1 HIGH PRIORITY — Data at Rest Encryption
**Finding**: `IsEncryptionOn=False` in `emxn.sqlproj` (line 51). Transparent Data Encryption (TDE) is not enabled.  
**Impact**: Employee SSNs (`UPR00100.SOCSCNUM`), spouse SSNs (`UPR00100.SPOUSESSN`), and dates of birth are stored unencrypted on disk. A physical media breach or backup file exfiltration would expose sensitive PII.  
**Remediation**: Enable TDE at the SQL Server instance level. For the most sensitive columns (`SOCSCNUM`, `SPOUSESSN`), consider SQL Server Always Encrypted to prevent even DBA-level access to plaintext values.

### 2.2 HIGH PRIORITY — Individual Named SQL Logins
**Finding**: Security folder contains ~200 individual-named login scripts (e.g., `Amber.Lukacko.sql`, `Patricia.Pace.sql`, `mstaudenmayer.sql`).  
**Impact**: When employees depart, their SQL logins persist until manually revoked. PCI DSS Requirement 8.2 requires unique user IDs and Requirement 8.8 requires that access for former personnel is immediately revoked.  
**Remediation**: Migrate to Windows Integrated Authentication via Active Directory groups. Remove all individual SQL logins. Implement quarterly access review (PCI DSS Req 7.2.1).

### 2.3 HIGH PRIORITY — No Audit Trail
**Finding**: `IsChangeTrackingOn=False`, no CDC, no DDL triggers committed.  
**Impact**: No record of who read or modified employee PII or financial data. This conflicts with SOC 1/2 control objectives and LFPDPPP audit requirements.  
**Remediation**: Enable SQL Server Audit (server audit + database audit specification) targeting `UPR00100`, `PM00200`, `RM00101`, and GL posting tables. FortiDB (evidenced by `FortiDBRptRole` in Security folder) may already provide external DAM coverage — confirm scope.

### 2.4 MEDIUM PRIORITY — ANSI Settings Disabled
**Finding**: `AnsiNulls=False`, `AnsiPadding=False`, `AnsiWarnings=False`, `QuotedIdentifier=False` (all in `emxn.sqlproj` lines 65–72).  
**Impact**: Non-standard SQL behaviour; potential for silent data truncation (`AnsiWarnings=False`), inconsistent NULL comparisons, and incompatibility with modern SQL Server features including XML, JSON, and columnstore indexes.  
**Remediation**: Enable all ANSI settings. This requires regression testing of all 16,594 stored procedures — a significant effort, best paired with a GP upgrade project.

## 3. All Database Objects with Purpose

### Tables (1,078 total — key objects)

| Table | Purpose | PII/Sensitive Flag |
|-------|---------|-------------------|
| `UPR00100` | Employee master — SSN, DOB, demographics | **CRITICAL PII** |
| `UPR00102` | Employee address | **HIGH PII** |
| `UPR00111` | Employee deductions | Payroll financial |
| `UPR00300` | Employee pay codes | Payroll |
| `UPR10100` | Payroll transaction work | Payroll financial |
| `UPR10200` | Payroll distribution | GL mapping |
| `PM00200` | Vendor master — Tax ID, phone, address | **HIGH PII / Tax ID** |
| `PM10000` | Open payable transactions | Financial |
| `PM20000` | Historical payable transactions | Financial |
| `RM00101` | Customer master — phone, address | **MEDIUM PII** |
| `RM10101` | Open receivable transactions | Financial |
| `RM20101` | Historical receivable transactions | Financial |
| `GL00100` | Chart of accounts | Business confidential |
| `GL10000` | Unposted journal entry header | Financial |
| `GL20000` | Posted GL transactions | Financial |
| `SY01200` | Internet/email addresses for all master records | **HIGH PII (email)** |
| `SOP10100` | Sales order header | Financial |
| `POP10100` | Purchase order header | Financial |
| `IV00101` | Inventory item master | Inventory |
| `IV10000` | Inventory transaction work | Inventory |
| `AF00100` | Fixed asset subsystem | Asset register |

### Views (143 total — key objects)

| View | Purpose | PII Exposure |
|------|---------|-------------|
| `Employees.sql` | Denormalised employee data | **HIGH — includes HR fields** |
| `EmployeeSummary.sql` | Employee summary report view | **HIGH** |
| `PayrollTransactions.sql` | Payroll transaction view | **HIGH — payroll amounts** |
| `PayrollCheckAndDistributionHistory.sql` | Historical payroll cheques | **HIGH** |
| `Customers.sql` | Denormalised customer view | **MEDIUM — phone, address** |
| `Vendors.sql` | Denormalised vendor view | **MEDIUM — Tax ID, phone** |
| `AccountTransactions.sql` | GL transaction view | Business confidential |
| `SalesTransactions.sql` | Sales ledger view | Business confidential |
| `ReceivablesTransactions.sql` | AR transactions view | Business confidential |
| `PayablesTransactions.sql` | AP transactions view | Business confidential |

### Stored Procedures (16,594 — by category)

| Category | Count (approx) | Purpose |
|----------|---------------|---------|
| `zDP_*` | ~12,000 | GP auto-generated CRUD data providers |
| `taCreate*` / `eConnect` | ~500 | eConnect API transaction procedures |
| `aag*` | ~200 | Analytical Accounting sub-ledger |
| `cm*` | ~150 | Cash Management |
| `cnp*` | ~100 | Collections Management |
| `ASI*` | ~100 | Service module procedures |
| Custom/Onbe | ~50 | Non-GP custom procedures |
| SVC/FieldService | ~100 | Field service management |
| Other GP built-in | ~3,394 | Various GP module procedures |

### Functions (193 total)

All follow `DYN_FUNC_*` naming convention — GP decode functions mapping numeric codes to descriptions. No PII data access.

## 4. Remediation Priority Matrix

| Priority | Item | Owner | Effort |
|----------|------|-------|--------|
| P1 (Now) | Enable TDE | DBA/Security | 1 day + testing |
| P1 (Now) | Audit individual SQL logins; remove leavers | DBA/IT Security | 1 week |
| P1 (Now) | Enable SQL Server Audit on PII tables | DBA | 2 days |
| P2 (Q3) | SQL Server compatibility level upgrade (2008 → 2019) | DBA + App team | 4–6 weeks |
| P2 (Q3) | Implement FortiDB DAM coverage (if not already active) | Security team | 2 weeks |
| P2 (Q3) | Enable RCSI (ReadCommittedSnapshot) | DBA | 1 day (requires exclusive access) |
| P3 (Next cycle) | Convert individual logins to AD groups | IT/DBA | 4 weeks |
| P3 (Next cycle) | Assess GP upgrade path (Dynamics 365 BC) | Architecture | 3 months planning |
| P4 (Roadmap) | Enable ANSI settings, fix truncation risks | Dev + DBA | 6+ months |
| P4 (Roadmap) | Implement Always Encrypted for SSN columns | Security + DBA | 6+ months |

## 5. Summary Risk Score

| Category | Score (1–5) |
|----------|------------|
| Data sensitivity | 5 — SSN, DOB, employee PII, tax IDs |
| Security posture | 2 — TDE off, named logins, no audit |
| Operational maturity | 2 — No CI/CD, no migration scripts |
| Compliance readiness | 2 — LFPDPPP gaps, PCI connected-system risk |
| Architectural currency | 1 — SQL 2008 compat, GP legacy stack |

**Overall Risk: HIGH** — Immediate remediation of TDE and login governance is required before the next compliance review cycle.
