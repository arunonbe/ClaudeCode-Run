# DevOps / Operations View — DS_CCP_ccp-export

## Build / Deployment Tooling
- **Solution:** `ccp-export.sln` (Visual Studio / SQL Server Data Tools 2017)
- **Project file:** `ccp.export.dtproj` (SSIS project, SSIS Catalog deployment model)
- **Target SSIS version:** SQL Server 2017 (SSDT 14.x; `LastModifiedProductVersion="14.0.3002.113"`)
- **Dependencies:** Oracle Client 12 (32-bit and 64-bit) must be installed on the SSIS server; `tnsnames.ora` must be in the Oracle home.
- **Deployment model:** Project Deployment Model (packages deployed together to SSISDB catalog).

## Development Requirements
As documented in `README.md`:
1. Install SQL Server Data Tools 2017
2. Install Oracle Client 12 (32-bit and 64-bit)
3. Copy `tnsnames.ora` to Oracle home directory

## Configuration Management
| Parameter | Value (default/QA) | Sensitive |
|-----------|-------------------|-----------|
| `BankTempFolder` | `C:\ETL\Work\` | No |
| `SFTP` (enable) | `false` | No |
| `Bank_SFTPHostName` | `ftp.sunrisebanks.com` | No |
| `Bank_SFTPUserName` | `wirecardccpdev` | No |
| `Bank_SFTPPassword` | DPAPI-encrypted blob in params | Yes |
| `Bank_SFTPPassphrase` | DPAPI-encrypted blob | Yes |
| `Bank_SFTPKeyFile` | `C:\ETL\Cert\id_sunrise_rsa` | No |
| `Bank_SFTPPort` | `22` | No |
| `FinanceCopy_SFTP` | `false` | No |
| `FinanceCopy_SFTPHostName` | `sftp-qa.nam.wirecard.com` | No |
| `FinanceCopy_SFTPUserName` | `ccp-uat` | No |
| `FinanceCopy_SFTPPassword` | DPAPI-encrypted blob | Yes |
| `FinanceCopy_RemotePath` | `Inbound\ToFinance\` | No |
| `OAS_SFTP` | `false` | No |
| `NotifyEmailAddress` | (empty — must be set) | No |
| `MailServerAccount` | (empty — must be set) | No |

All SFTP flags default to `false`; they must be set to `true` in environment-specific SSIS catalog configurations for production.

## Scheduling / Execution
- Packages are intended to run via SQL Server Agent jobs on a scheduled basis (daily).
- The `DTEXEC` utility or SQL Server Agent SSIS step type executes individual packages.
- No SQL Server Agent job definitions are stored in this repository.

## Observability
- SSIS built-in logging: package execution logs available in SSISDB (`catalog.executions`, `catalog.event_messages`).
- Email notification via SMTP connection manager when expected files are absent.
- No integration with external monitoring/alerting (e.g., no PagerDuty, no Splunk forwarder configured here).

## Infrastructure Dependencies
- SSIS server (Windows) with SQL Server 2017 Integration Services
- Oracle Client 12 on the SSIS server
- Network access to `d-phl-db01.wirecard.lan` (ODS) and Oracle TNS alias `dwh_aws_ssh`
- SFTP connectivity to Sunrise Banks, Finance Copy, and OAS endpoints
- File system path `C:\ETL\Work\` and `C:\ETL\Cert\` on the execution server

## Operational Risks
1. **DPAPI machine-binding** — encrypted passwords in `.conmgr` and `Project.params` are tied to a specific Windows machine's key. Moving the deployment to a new server requires all passwords to be re-entered.
2. **QA hostnames in repo** — `sftp-qa.nam.wirecard.com` and `wirecardccpdev` username appear to be QA/legacy values; production values must be overridden via SSIS catalog environment variables.
3. **No file-cleanup step confirmed** — `C:\ETL\Work\` may accumulate plaintext PAN-containing files.
4. **Oracle Client 32-bit requirement** — legacy architecture constraint that complicates server upgrades.
5. **No source-controlled SQL Agent job definitions** — job schedules and dependencies are not version-controlled.
