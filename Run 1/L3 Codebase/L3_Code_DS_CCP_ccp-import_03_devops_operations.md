# DevOps / Operations View — DS_CCP_ccp-import

## Build / Deployment Tooling
- **Solution:** `ccp-import.sln` (SSDT 2017)
- **Project file:** `ccp.import.dtproj` (SSIS Project Deployment Model)
- **Target SSIS version:** SQL Server 2017 (SSDT 14.x) and SQL Server 2019 (SSDT 15.x) — mixed versions present
- **Additional file:** `DTEXEC-SFTP-Receive.dtsxp` — DTEXEC parameters file for the SFTP receive step (pre-configured execution arguments for dtexec.exe)
- **Oracle dependency:** Oracle Client 12 (32-bit and 64-bit) for DWH connection

## Configuration Parameters (`Project.params`)
### FIS Parameters
| Parameter | Default/QA | Sensitive |
|-----------|-----------|-----------|
| `FIS_SFTP_HostName` | `sftp-qa.nam.wirecard.com` | No |
| `FIS_SFTP_Username` | `ccp-uat` | No |
| `FIS_SFTP_Password` | Empty (DPAPI) | Yes |
| `FIS_SFTP_SSHKey` | Empty | No |
| `FIS_SFTP_SSHPassphrase` | Empty (DPAPI) | Yes |
| `FIS_SFTP_Port` | `22` | No |
| `FIS_SFTP_Enable` | `false` | No |

### Mastercard Parameters
| Parameter | Default/QA | Sensitive |
|-----------|-----------|-----------|
| `MC_SFTP_HostName` | `sftp-qa.nam.wirecard.com` | No |
| `MC_SFTP_Username` | `ccp-uat` | No |
| `MC_SFTP_Password` | Empty (DPAPI) | Yes |
| `MC_SFTP_SSHKey` | Empty | No |
| `MC_SFTP_SSHPassphrase` | Empty (DPAPI) | Yes |
| `MC_SFTP_Port` | `22` | No |
| `MC_SFTP_Enable` | `false` | No |

### WDP Parameters
| Parameter | Default/QA | Sensitive |
|-----------|-----------|-----------|
| `WDP_SFTP_HostName` | `sftp-qa.nam.wirecard.com` | No |
| `WDP_SFTP_Username` | Empty | No |
| `WDP_SFTP_Password` | Empty (DPAPI) | Yes |
| `WDP_SFTP_SSHKey` | Empty | No |
| `WDP_SFTP_SSHPassphrase` | Empty (DPAPI) | Yes |
| `WDP_SFTP_Port` | `22` | No |
| `WDP_SFTP_Enable` | `false` | No |
| `WDP_PGPKey` | Empty | No |
| `WDP_PGPPassphrase` | Empty (DPAPI) | Yes |

### Shared Parameters
| Parameter | Default | Sensitive |
|-----------|---------|-----------|
| `SFTP_Server` | `t-phl-db01.wirecard.lan` | No |
| `MailServerAccount` | Empty | No |
| `NotifyEmailAddress` | Empty | No |

## Scheduling / Execution
- Daily batch; should run early morning to ingest previous day's files.
- `ccp_import_aggnetworksettlement.dtsx` has a `T_minus=1` default — imports T-1 data.
- `DTEXEC-SFTP-Receive.dtsxp` suggests a separate scheduled execution for the SFTP receive step (possibly via a Windows scheduled task or SQL Agent DTEXEC job type).
- Execution order: SFTP receive → flat file import packages → aggregation.

## Observability
- SSIS SSISDB logging (`catalog.event_messages`).
- `CompletionMessage` variable in `ccp_import_aggnetworksettlement.dtsx` confirms record count.
- Email notifications for missing files.
- No external monitoring integration.

## Operational Risks
1. **All SFTP enables default to `false`** — a deployment without environment overrides would silently skip all imports; no error is raised.
2. **WDP PGP key file path is empty** — production deployment requires the key to be provisioned and path set; if not done, WDP imports will fail.
3. **Legacy Wirecard SFTP server** (`t-phl-db01.wirecard.lan`) used for SFTP module execution — this host may not exist post-migration.
4. **DPAPI machine-binding** — credentials cannot be migrated without manual re-entry.
5. **No duplicate detection** — re-running an import for the same day will insert duplicate rows into ODS.
6. **Mastercard fixed-width format** — field alignment is critical; any vendor format change will silently produce corrupted data.
