# DevOps / Operations View — DS_CCP_ccp-export-to-legacy

## Build / Deployment Tooling
- **Solution:** `ccp-export-to-legacy.sln` (Visual Studio / SSDT 2017)
- **Project file:** `ccp.export2legacy.dtproj` (SSIS Project Deployment Model)
- **Target SSIS version:** SQL Server 2017 (SSDT 14.x) and SQL Server 2019 (SSDT 15.x; `LastModifiedProductVersion="15.0.0900.30"` seen in `Export_billing_audit.dtsx` and `Export_fvd_revenue.dtsx`)
- **Oracle dependency:** Oracle Client 12 (32-bit and 64-bit) on the SSIS host; `tnsnames.ora` required

## Configuration Parameters (`Project.params`)
| Parameter | Default/QA Value | Sensitive |
|-----------|-----------------|-----------|
| `TempFolder` | `C:\ETL\Work\` | No |
| `SFTP` | `true` | No |
| `Legacy_SFTPHostName` | `sftp-qa.nam.wirecard.com` | No |
| `Legacy_SFTPUserName` | `ccp-uat` | No |
| `Legacy_SFTPPort` | `22` | No |
| `Legacy_SFTPKeyFile` | (empty) | No |
| `Legacy_SFTPPassword` | DPAPI-encrypted (empty in dev) | Yes |
| `Legacy_SFTPPassphrase` | DPAPI-encrypted (empty in dev) | Yes |
| `SFTPTimeout` | `600` (seconds) | No |
| `NotifyEmailAddress` | (empty — must be set) | No |
| `MailServerAccount` | (empty — must be set) | No |

Note: `SFTP=true` is the default (unlike ccp-export where it defaults to `false`), indicating this project is always configured to push to the legacy SFTP.

## Key Operational Differences vs. ccp-export
- Includes an **archiving step** (`Archive_Processed_Files.dtsx`) — files are moved after delivery.
- SFTP is **enabled by default** (`SFTP=true`).
- Targets the **legacy Ecount platform** as destination, not external bank partners.
- Two SSDT versions used (packages edited in both SSDT 14 and SSDT 15), suggesting ongoing maintenance across multiple SQL Server environments.

## Scheduling / Execution
- Executed via SQL Server Agent jobs (scheduled daily, post-import pipeline).
- Should run **after** `ccp-import` has populated ODS with the day's data.
- No SQL Agent job definitions stored in this repository.

## Observability
- SSIS built-in logging via SSISDB (`catalog.event_messages`).
- Email notifications on missing files.
- Archive step provides file-level audit trail.
- No external monitoring or alerting integration.

## Operational Risks
1. **DPAPI machine-binding** — same risk as ccp-export; passwords cannot be migrated to a new server without manual re-entry.
2. **QA/Wirecard hostnames** — production override required; default hostname is QA-branded.
3. **SFTP=true default** — if misconfigured environment variables are not applied, QA packages could attempt delivery to the wrong endpoint.
4. **SFTPTimeout=600s** — 10-minute timeout; if the legacy SFTP is slow, packages will fail rather than waiting.
5. **Archive before confirmation** — it is possible that archiving occurs before SFTP delivery is fully verified; a file could be archived but not delivered.
6. **Mixed SSDT versions (14 and 15)** — packages may behave differently if opened and saved with different SSDT versions; risk of format drift.
