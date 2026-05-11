# DS_ETL_great-plains-to-oas-coda — Solution Architect View

## Technical Architecture
- **Runtime**: SQL Server 2012 Integration Services (SSIS), package format version 6
- **Solution**: Visual Studio 2010 (.sln format version 11.00), single DTPROJ project
- **SSIS engine version**: 11.0.7001.0 (SQL Server 2012 SP4)
- **Script components**: VB.NET (embedded in DTSX XML), AssemblyVersion 1.0.0.0, Citigroup/2012 copyright
- **Packages**: 2 — `SSIS_CODA_GPFeed.dtsx` (85 KB), `SSIS_RfCks.dtsx` (96 KB)
- **Connection managers**: 4 — ATLYS_RvCR (ADO.NET), GP Server (OLEDB), ODS (OLEDB), Flat File
- **No application framework** beyond the SSIS runtime; no Java, .NET service, or REST layer

## API Surface
None. Inputs are database stored procedure calls and flat file reads. Output is flat file writes to a UNC path.

## Security Posture

### Authentication
- `Integrated Security=True/SSPI` on all DB connections — Windows Kerberos/NTLM; no embedded credentials in .conmgr files.
- Package runs under the Windows identity of the executing agent/service account.
- The connection manager files in the repo reference QA server (`q-db04`) — production connections must be overridden in SSISDB or the package will connect to QA.

### Secrets / Credentials
- No passwords found in any `.conmgr`, `.dtsx`, or `.params` file.
- `pFTPFolder` parameter is empty — if FTP credentials were to be added, this is where they would live; no current risk but no SFTP alternative implemented.

### Crypto / Transport
- SQLNCLI11.1 (OLE DB) and `System.Data.SqlClient` (ADO.NET) — both are legacy SQL Server 2012-era drivers.
  - SQLNCLI11.1 defaults to TLS 1.0 for encryption; **TLS 1.0 is deprecated** under PCI DSS v4.0 (Req 4.2.1).
  - `System.Data.SqlClient` in .NET 4.x also defaults to TLS 1.0 unless OS-level config forces TLS 1.2+.
- Flat file output — no encryption. Files on UNC share in plaintext.
- VB.NET Script Component — compiled inline; no external DLL dependencies visible.

### CVEs / Library Risk
- SSIS 11.0.7001.0 (SQL Server 2012 SP4 CU9) — end-of-life July 2022; any unpatched CVEs from 2022 onward are unaddressed.
- SQLNCLI11.1 — deprecated by Microsoft; recommend migration to MSOLEDBSQL.
- `commons-logging`, Spring, etc. are not applicable here (Java libs are in ecore-batch, not this repo).

## Technical Debt
| Item | Severity | Evidence |
|---|---|---|
| Package format SQL 2012 / SSDT VS2010 | Critical | sln format 11.00, dtsx LastModifiedProductVersion 11.0.7001.0 |
| Hardcoded C:\GIT\rfcks.csv input path | Critical | SSIS_RfCks.dtsx — FlatFile connection DTS:ConnectionString |
| SQLNCLI11.1 legacy OLE DB driver (TLS 1.0 risk) | High | GP Server.conmgr and ODS.conmgr |
| QA server hardcoded in .conmgr files | High | ATLYS_RvCR.conmgr, GP Server.conmgr, ODS.conmgr |
| FTP destination empty | High | Project.params — pFTPFolder default empty |
| No error handling / Send Mail task | Medium | SSIS control flow — no failure notification |
| File overwrite without backup | Medium | SSIS_CODA_GPFeed.dtsx — Overwrite=true |
| Citigroup-era VB.NET script component (2012) | Medium | SSIS_CODA_GPFeed.dtsx — embedded script |
| No CI/CD pipeline | Low | Repo contains no pipeline files |
| "Temporary project" with no decommission plan | Low | README.md line 3 |

## Gen-3 Migration Requirements
1. Determine if this pipeline is still operational and if CODA/OAS is still active; if not, decommission.
2. If still required: replace SSIS with ADF (Azure Data Factory) pipeline or Python-based ETL.
3. Replace SQLNCLI11.1 with MSOLEDBSQL or pyodbc with Microsoft ODBC Driver 18.
4. Replace flat-file FTP handoff with API-based push or SFTP with TLS 1.2+.
5. Replace `C:\GIT\rfcks.csv` with a proper data source (database table, API endpoint, or managed file landing zone).
6. Implement error alerting (email or PagerDuty integration) for failed runs.
7. Store all connection strings and credentials in Azure Key Vault or equivalent secrets manager.

## Code-Level Risks (File:Line References)
| Risk | File | Approx Line |
|---|---|---|
| Hardcoded C:\GIT\rfcks.csv | `CODA ETL\SSIS_RfCks.dtsx` | ~33 (FlatFile DTS:ConnectionString) |
| QA server hardcoded (q-db04) | `CODA ETL\ATLYS_RvCR.conmgr` | 8 |
| QA server hardcoded (q-db04) | `CODA ETL\GP Server.conmgr` | 8 |
| QA server hardcoded (q-db03) | `CODA ETL\ODS.conmgr` | 8 |
| SQLNCLI11.1 OLE DB | `CODA ETL\GP Server.conmgr` | 5 (DTS:CreationName=OLEDB) |
| Overwrite=true on output | `CODA ETL\SSIS_CODA_GPFeed.dtsx` | ~320 |
| Citigroup 2012 assembly copyright | `CODA ETL\SSIS_CODA_GPFeed.dtsx` | ~397-400 |
