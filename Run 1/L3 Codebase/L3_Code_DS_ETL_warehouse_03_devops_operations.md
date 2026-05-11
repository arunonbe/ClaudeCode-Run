# DS_ETL_warehouse — DevOps and Operations Perspective

## Repository Scale

The Warehouse project is substantially larger than `DS_ETL_sykes`:
- ~100 SSIS packages across domestic, international, and multi-tenant variants
- `Warehouse.dtproj` manifest: 889,977 bytes (890 KB)
- Largest packages: `Intl_PrePopulate_Tables.dtsx` (1.36 MB), `ClaimablePaymentHistory.dtsx` (654 KB), `Intl_DimAccountHolder_HistoryLoad.dtsx` (807 KB)
- Solution file: `Warehouse.sln` (730 bytes)

## SSIS Protection Level — Security Finding

**File**: `Warehouse.dtproj`, line 15:
```xml
SSIS:ProtectionLevel="EncryptSensitiveWithUserKey"
```

**File**: `Warehouse.dtproj`, line 29:
```
<SSIS:Property SSIS:Name="PasswordVerifier" SSIS:Sensitive="1">
  AQAAANCMnd8BFdERjHoAwE/Cl+sBAAAAIafl9+Hl2k2NGXEEoPIwww...
```

Identical issue to `DS_ETL_sykes`: the project uses `EncryptSensitiveWithUserKey`, which ties all sensitive property encryption to the Windows DPAPI key of `NAM\nick.doan` (the creator, `Warehouse.dtproj` line 25) on machine `P-NA-DB11` (line 26). Deployment by any other user will lose all sensitive values.

The `Warehouse.dtproj` project manifest defines numerous `CM.*.Password` sensitive parameters — for `Prepaid_DW_OLAP`, `Prepaid_Warehouse`, `Ecountcore_SS`, `cf_report`, `Jobsvc_SS`, and `ECountcore_ss_PROD` (lines 210, 298, 404, 492, 598, 686, 792, 880, 986, 1074, etc.). The repetition across dozens of packages implies these password parameters were added for every package individually rather than as project-level overrides, dramatically increasing the maintenance burden.

**Note on `ECountcore_ss_PROD`**: Line 2220 references `CM.ECountcore_ss_PROD.Password` — a connection named `ECountcore_ss_PROD`, distinct from `Ecountcore_SS`. This suggests a direct production connection manager was explicitly labelled `_PROD` at some point, further confirming production connections are present in the project.

## Configuration File Dependency

All master and most child packages reference external `.dtsConfig` files:

| Package | Config File |
|---|---|
| `DW_Incremental_ETL_Master.dtsx` | `C:\SSISConfig\DW_ETL_Master.dtsConfig` |
| `CardDetailHistory.dtsx` | `C:\SSISConfig\DW_ETL_Master.dtsConfig` |
| `ClaimablePaymentHistory.dtsx` | `C:\SSISConfig\DW_IncETL_Master.dtsConfig` |
| `DimAccountHolder_Incremental.dtsx` | `C:\SSISConfig\DW_AccountHolderHistory.dtsConfig` |

These XML configuration files are stored on `C:\SSISConfig\` on the execution server and are **not version-controlled in this repository**. This is the fundamental configuration management gap for this project: the actual runtime behaviour is determined by files that exist only on production servers.

## Notification Configuration

`Project.params` defines:
```xml
<SSIS:Property SSIS:Name="Value">colin.treat@northlane.com</SSIS:Property>  <!-- SuccessEmailTo -->
<SSIS:Property SSIS:Name="Value">colin.treat@northlane.com</SSIS:Property>  <!-- FailEmailTo -->
<SSIS:Property SSIS:Name="Value">noreply@northlane.com</SSIS:Property>       <!-- EmailFrom -->
```

SMTP server from `Send Mail.conmgr`:
```
SmtpServer=nl-smtp-01.nam.wirecard.sys;UseWindowsAuthentication=False;EnableSsl=False;
```

**Flag**: `EnableSsl=False` on the SMTP connection means email notifications are transmitted without TLS. While internal SMTP relay is typically within a trusted network perimeter, this is a configuration weakness. PCI DSS Requirement 4.2.1 requires all transmissions of sensitive data over open public networks to be encrypted, but internal SMTP is typically within scope only if PAN or other SAD is transmitted in email bodies.

**Flag**: `UseWindowsAuthentication=False` with `EnableSsl=False` means the SMTP connection is anonymous. This could be exploited for SMTP relay abuse if the `nl-smtp-01` server is misconfigured.

## Package Authorship and Version History

| Creator Domain | Packages | Notes |
|---|---|---|
| `NAM\pm25591` | `DW_Incremental_ETL_Master.dtsx` (2012-01-12), `DimAccountHolder_Incremental.dtsx` | Original warehouse developer |
| `NAM\fn27496` | `CDC_stagingdata.dtsx` (2012-03-30), `EnterpriseWideRA.dtsx` (2013-09-10) | Second original developer |
| `NAM\nick.doan` | Project creator (Warehouse.dtproj, 2017-09-18) | Re-packaged project into Project Deployment Model |

All packages use `SSIS.Package.3` (SQL Server 2012 SSIS format) with `DTS:LastModifiedProductVersion="11.0.7001.0"` or `11.0.5583.0`. The warehouse ETL has been running on SQL Server 2012 tooling since 2012 — over a decade on end-of-life technology.

## Scheduling Architecture

No SQL Agent job definitions are present in the repository. Based on the master package design, the expected scheduling pattern is:

1. SQL Server Agent job calls `DW_Incremental_ETL_Master.dtsx` nightly
2. The master package calls child packages in sequence
3. `DW_ETL_Completion_Tasks.dtsx` runs post-load finalisation
4. `Process_Cubes.dtsx` refreshes SSAS cubes after fact load

The `Handle_Failure.dtsx` and `Intl_Handle_Failure.dtsx` packages suggest a standardised failure-handling procedure is invoked from master packages on error events.

## EWRA Flat-File Dependency

`EnterpriseWideRA.dtsx` reads from UNC paths (lines 33–35):
```
\\ppinmwpdetl1\c-base\runtime\ndmroot\svc-cdwinnt\upload\EWARA\
```

This hardcoded UNC path to `ppinmwpdetl1` (presumably a production ETL server) is not parameterised. If that server is renamed, decommissioned, or if the share path changes, the EWRA package will fail. The ICG/CTS/TTS format filenames (`_ICG_CTS_TTS_PREPAIDGTPLAINS_012019.cntl`) suggest this is an interchange with ICG (now First Data/Fiserv) counterparty systems.

## Operational Risk Summary

| Risk | Severity | Detail |
|---|---|---|
| `EncryptSensitiveWithUserKey` | High | All sensitive properties tied to `nick.doan`'s DPAPI key |
| `.dtsConfig` not in source control | High | Runtime config undocumented; production-only knowledge |
| `ECountcore_ss_PROD` named connection | High | Explicit production connection embedded in project |
| Individual email address for alerts | Medium | Single point of failure for ops notifications |
| SMTP without TLS | Medium | `EnableSsl=False` on mail connection |
| UNC path for EWRA not parameterised | Medium | Hardcoded server path `\\ppinmwpdetl1\...` |
| SSIS 2012 EOL toolchain | Medium | No Microsoft support since July 2022 |
| ~100 packages; no CI/CD | Medium | Manual deployment risk at scale |
