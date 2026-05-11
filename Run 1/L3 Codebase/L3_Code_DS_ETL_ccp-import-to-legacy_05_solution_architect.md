# DS_ETL_ccp-import-to-legacy — Solution Architect Report

## 1. Technical Architecture

| Attribute | Value |
|-----------|-------|
| Technology | SSIS 2012 (SQL Server Integration Services) — Project Deployment Model |
| Package format | `.dtsx` SSIS XML package (FormatVersion 3 — SSIS 2012 format) |
| Project format | `.dtproj` — SSIS 2012 Project Deployment Model |
| Build output | `.ispac` (Integration Services Project Archive) |
| Package count | 10 |
| Source system | Pipe-delimited flat files from `C:\ETL\In\WDCCP\` |
| Target system | SQL Server `CCP` database on `d-na-db01.nam.wirecard.sys\db01,2232` |
| DB driver | `SQLNCLI11.1` (SQL Server Native Client 11 — EOL) |
| Auth | Windows Integrated Security (SSPI) to target DB |
| Notification | SMTP email via `SMTP Connection Manager.conmgr` |

---

## 2. API Surface

This is a batch ETL pipeline with no HTTP API surface. External interfaces:

1. **File system input**: `C:\ETL\In\WDCCP\` — 10 source file patterns consumed from the file system.
2. **OLE DB output**: `CCP-SQLDB` connection to `CCP` database — 10 staging table destinations.
3. **SMTP output**: Failure notification emails to `namds@wirecard.com`.
4. **SSIS catalog (runtime)**: Packages are executed via SSISDB catalog invocation (SQL Server Agent job or `dtexec.exe` / `isserver.exe`).

---

## 3. Security Posture

### 3.1 Authentication

- **Database connection** (`CCP-SQLDB.conmgr`): Windows Integrated Security (SSPI) — appropriate; no SQL credentials in the connection manager.
- **SMTP connection**: (`SMTP Connection Manager.conmgr`): Not readable (binary `.conmgr`); SMTP credentials/anonymity unknown.
- **No SQL credentials** in the visible project artefacts — connection uses Windows AD which is positive.

### 3.2 Sensitive Data in Transit

- Source flat files (`sunrise_wdccp_*.txt`) are transferred from the CCP export location to `C:\ETL\In\WDCCP\` — no encryption in transit is specified.
- `CardExpirationDate` is included in `Import_bin_cardstatus.dtsx` as part of the file input — SAD data in transit via unencrypted flat file.
- No PGP/SSL file encryption is configured (unlike the Gen-3 `exemplar-cross-border-transfer-service` which uses PGP for file exchange).

### 3.3 Secrets / Credentials

- No hardcoded SQL Server credentials in `CCP-SQLDB.conmgr` — uses Windows auth.
- `Project.params` contains `NoReply@wirecard.com` (mail sender) — not a secret but a Wirecard-era address.
- SMTP connection manager credentials are binary; cannot be assessed from visible artefacts.

### 3.4 Data Exposure Risks

- **Flat files on filesystem**: Source files containing potential card account identifiers and expiration dates are stored as plaintext on the SSIS server file system. No access control beyond OS-level file permissions is defined in this project.
- **No file-level encryption**: Contrast with Gen-3 pattern (PGP-encrypted SFTP in `exemplar-cross-border-transfer-service`).
- **CDE scoping**: Until a QSA formally scopes `AccountIdentifier` and `CardExpirationDate`, the SSIS server processing these files may be in CDE scope.

---

## 4. Technical Debt

| Issue | Severity | Detail |
|-------|---------|--------|
| SSIS 2012 — SQL Server EOL | CRITICAL | SQL Server 2012 reached EOL July 2022; no security patches since then |
| SQLNCLI11.1 EOL driver | HIGH | SQL Server Native Client 11 superseded by Microsoft OLE DB Driver for SQL Server (MSOLEDBSQL); SQLNCLI11 no longer receives updates |
| `nam.wirecard.sys` domain dependency | HIGH | Wirecard AD domain; may be decommissioned post-acquisition |
| `namds@wirecard.com` / `NoReply@wirecard.com` | HIGH | Wirecard email addresses hardcoded in project params; failure notifications may be going to an abandoned inbox |
| No automated tests | HIGH | No data quality assertions, row count validation, or reconciliation tests |
| No CI/CD | HIGH | Manual deployment only |
| No error recovery / restart | MEDIUM | SSIS 2012 packages have no checkpoint/restart mechanism unless explicitly configured |
| Hardcoded file path (`C:\ETL\In\WDCCP\`) | MEDIUM | Not parameterised; breaks on SSIS server change |
| SSIS project created April 2019 | LOW | Over 6 years old; no evidence of update since initial creation |

---

## 5. Gen-3 Migration Assessment

**Migration complexity**: HIGH (if still active); RETIRE (if eCount is decommissioned)

If eCount remains active and this pipeline must be migrated to Gen-3 architecture:

### Replacement architecture
| Current | Gen-3 Equivalent |
|---------|-----------------|
| SSIS flat file reader | Spring Batch `FlatFileItemReader` with `DelimitedLineTokenizer` |
| SSIS OLE DB destination | Spring Data JPA / Spring JDBC `JdbcBatchItemWriter` |
| SSISDB project deployment | Kubernetes CronJob + Spring Boot JAR |
| Windows SSPI auth | Spring Security + Azure AD / service principal |
| Plaintext flat files | PGP-encrypted SFTP (as used in `exemplar-cross-border-transfer-service`) |
| `SQLNCLI11.1` | `mssql-jdbc` (Microsoft JDBC Driver for SQL Server) |
| `namds@wirecard.com` | Onbe-managed email DL via notification service |

### Data migration concerns
1. `CardExpirationDate` — if kept in Gen-3, requires explicit PCI DSS scope classification and QSA sign-off.
2. `AccountIdentifier` — must be formally determined to be either a tokenised reference (safe) or a PAN-adjacent value (requires PCI DSS tokenisation controls).
3. Staging database (`CCP`) — if retained, must be migrated to SQL Server with current driver support and Liquibase-managed schema.

---

## 6. Code-Level Risks

| Risk | Location | Detail |
|------|---------|--------|
| `CardExpirationDate` in file import | `Import_bin_cardstatus.dtsx` | SAD field in plaintext flat file and staging DB — PCI DSS Req 3.3 violation risk |
| `AccountIdentifier` PAN linkage | `Import_bin_account.dtsx`, `Import_bin_cardstatus.dtsx` | 32-char identifier with 4-char `CardNumber` — PAN reconstruction risk if identifier encodes BIN + partial PAN |
| Wirecard email addresses not updated | `Project.params` | `namds@wirecard.com` — failure notifications silently dropped if inbox abandoned |
| Server name hardcoded in connection manager | `CCP-SQLDB.conmgr` | `d-na-db01.nam.wirecard.sys\db01,2232` — will fail if server or domain is renamed/decommissioned |
| No source file integrity check | All packages | No hash or digital signature verification on source files before import — tampered files would be imported silently |
| Decimal precision 19/5 | `Import_bin_transaction.dtsx` | Financial amounts at precision 19 with scale 5; verify this matches target column precision to avoid rounding |
