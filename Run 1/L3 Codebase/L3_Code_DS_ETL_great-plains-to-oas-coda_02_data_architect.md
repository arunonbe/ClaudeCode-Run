# DS_ETL_great-plains-to-oas-coda — Data Architect View

## Data Stores
| Store | Connection Name | Connection String |
|---|---|---|
| ATLYS_RvCR (ADO.NET) | ATLYS_RvCR | `q-db04.nam.wirecard.sys\db04,2232; Initial Catalog=ATLYS_RvCR; Integrated Security=True` |
| ATLYS_RvCR (OLEDB) | GP Server | `q-db04.nam.wirecard.sys\db04,2232; Initial Catalog=atlys_rvcr; Provider=SQLNCLI11.1; Integrated Security=SSPI` |
| ODS | ODS | `q-db03.nam.wirecard.sys\db03,2232; Initial Catalog=ODS; Provider=SQLNCLI11.1; Integrated Security=SSPI` |
| Flat File (CODA output) | Text File | Dynamic UNC path: `{usPath}{MM}{DD}{YYYY}\{usFName}` |
| Flat File (Refund Checks input) | Flat File | `C:\GIT\rfcks.csv` (hardcoded developer path) |
| FTP destination | (parameter pFTPFolder) | Empty — not configured |

## Schema / Tables Accessed
- **ATLYS_RvCR.dbo.sys_interface** (stored procedure) — parameterized by `@s_id`, `@ctype`, `@region_id`, `@end_date`, `@report`. Returns a row-set of file records to be exported.
- **ODS** (Operational Data Store on DB03) — connected but exact tables/views not visible in the reviewed .dtsx source (connection manager defined but usage in SSIS_RfCks not fully traced in first 150 lines).

## Sensitive Data Assessment
| Field | Source | Sensitivity Level |
|---|---|---|
| Amount | CODA feed / rfcks.csv | Financial — monetary amount |
| Acct | rfcks.csv | Potentially an account number — context unclear |
| Dda Number | rfcks.csv | DDA (Demand Deposit Account) number — bank account identifier, PII-adjacent |
| Program Id | rfcks.csv | Internal program identifier — low sensitivity |
| Check Status | rfcks.csv | Processing status — low sensitivity |
| Tx Descr / Tx Date | rfcks.csv | Transaction description and date — operational |

- DDA Number is a partial bank account identifier. Under **GLBA** and **PCI DSS Req 3**, DDA numbers should be treated as sensitive financial data.
- No PAN (16-digit card numbers) observed in the flat file schema or the SSIS variable definitions.
- The CODA feed file output contains financial ledger data (undetermined column mapping from `sys_interface`).

## Encryption
- All database connections use `Integrated Security=SSPI/True` — Windows authentication, no embedded passwords.
- SQLNCLI11.1 (SQL Native Client 11 = SQL Server 2012 era) — **TLS 1.0 era driver** with potential vulnerability to downgrade attacks.
- Output flat files written to a UNC share — no file-level encryption configured in the SSIS package.
- FTP parameter (`pFTPFolder`) is blank; if enabled, FTP (unencrypted) would be used — SFTP/FTPS not visible.
- SSIS package protection level not explicitly overridden; defaults to `DontSaveSensitive` based on SSIS.Package.3 (SQL 2012).

## Data Flow Quality
- Date loop uses `DATEADD("day", 1, @udPDate)` iteration — correct for sequential daily processing.
- `pOverwriteDates` flag controls whether to use explicit date range or rolling current-day processing.
- Flat file output uses `Overwrite=true` — existing files are silently replaced with no backup.
- Flat file text qualifier set to `<none>` — no quoting of string fields; delimiter-embedded values could corrupt output.
- VB.NET Script Component (AssemblyVersion 1.0.0.0, Citigroup copyright 2012) provides custom formatting — source is embedded in the dtsx XML.

## Compliance Gaps
1. **SQLNCLI11.1 driver** — legacy SQL Native Client potentially vulnerable to TLS 1.0; should be replaced with MSOLEDBSQL or Microsoft.Data.SqlClient.
2. **DDA numbers in flat files** — no masking applied; files on UNC share may expose account identifiers.
3. **File overwrite without backup** — no audit trail of what was previously exported.
4. **Hardcoded `C:\GIT\rfcks.csv`** — relies on a specific developer workstation path; not operationally viable; indicates incomplete productionization.
5. **No lineage or data catalog metadata** — no documentation of what `sys_interface` returns or how CODA consumes the files.
