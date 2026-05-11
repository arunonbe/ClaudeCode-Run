# DS_ETL_warehouse — Solution Architect Perspective

## Solution Design Overview

`DS_ETL_warehouse` implements a comprehensive dimensional warehouse ETL using SQL Server Integration Services. The solution is organised into three execution tiers — history loads (one-time or monthly), incremental daily loads, and OLAP processing — orchestrated by master packages. The design reflects evolution over a decade, with multiple authoring teams leaving distinct patterns in the codebase.

## Master-Child Orchestration Design

The `DW_Incremental_ETL_Master.dtsx` (100 KB) serves as the daily execution entry point. Based on connection manager definitions and the ETL Master control structure:

```
DW_Incremental_ETL_Master.dtsx
  |-> Reads/writes BusinessDate, ImportLogID, ProcessedDate (User variables)
  |-> References Ecountcore_SS (source) and Prepaid_Warehouse (target + log)
  |-> Child packages called via Execute Package Task (inferred)
  |-> On completion: DW_ETL_Completion_Tasks.dtsx
  |-> On error: Handle_Failure.dtsx
```

The `Handle_Failure.dtsx` (10 KB) pattern — a small dedicated failure-handling package — is good design: it centralises failure response logic (notification, logging, rollback steps) in a reusable component rather than duplicating it across child packages.

## Configuration Architecture — Two Models in Conflict

The project exhibits a hybrid configuration approach:

### Model 1: XML Configuration Files (SSIS 2008 pattern)
Packages set `DTS:EnableConfig="True"` and reference `C:\SSISConfig\*.dtsConfig` files:
- `DW_ETL_Master.dtsConfig` — used by most incremental packages
- `DW_IncETL_Master.dtsConfig` — used by `ClaimablePaymentHistory.dtsx`
- `DW_AccountHolderHistory.dtsConfig` — used by `DimAccountHolder_Incremental.dtsx`

### Model 2: Project Deployment Model (SSIS 2012 pattern)
`Warehouse.dtproj` uses `<DeploymentModel>Project</DeploymentModel>` and defines project parameters in `Project.params`. The `Warehouse.dtproj` manifest also defines connection manager password parameters for every package (`CM.Prepaid_Warehouse.Password`, `CM.Ecountcore_SS.Password`, etc.) — these are Project Deployment Model constructs for Catalog environment variable overrides.

**Design conflict**: The packages simultaneously use both the legacy XML config approach (`.dtsConfig` files) AND the Project Deployment Model parameters. This creates uncertainty about which configuration takes precedence at runtime. In SSIS 2012 Project Deployment Model, package configurations are typically ignored — but the `DTS:EnableConfig="True"` flag still activates them. This dual-configuration state should be rationalised.

## CardDetail ETL Design

`CardDetailHistory.dtsx` establishes the pattern for history loads:

```sql
-- Post-history-load task (line 75 of CardDetailHistory.dtsx)
UPDATE dbo.ETL_Master 
SET MaxCrfFileFileDate = DATEADD(d,-7,GETDATE())
```

The completion task updates `ETL_Master.MaxCrfFileFileDate` to 7 days prior to today. This watermark-reset design forces the next incremental load to reprocess the last 7 days of data, providing a rolling overlap window to catch any late-arriving records from the `cf_report` source. This is a deliberate design choice for data completeness at the cost of processing efficiency.

## CDC Staging Design

`CDC_stagingdata.dtsx` implements SQL Server CDC-based change capture:

- `capture_instance = fdr_dda_account_detail` (line 69)
- `capture_instance_2 = fdr_dda_account_detail_block_code_modified` (line 77)

The naming of `fdr_dda_account_detail_block_code_modified` indicates this CDC instance tracks changes to the `block_code` field specifically — a DDA account block code indicates whether a card/account is restricted, frozen, or has a hold. The existence of a dedicated CDC capture instance for block code changes suggests near-real-time sensitivity: block code changes (e.g., fraud blocks) need to propagate to the warehouse promptly for compliance reporting.

## ClaimablePayment ETL Design

`ClaimablePaymentHistory.dtsx` implements a multi-dataset extract:

The Data Flow task "Extract Branded Currency Issuance" (`DTSID {FF1647C3-D8E6-4105-96BA-64E850B661B0}`, line 77) reads from both `cf_report` and `Ecountcore_SS`. "Branded Currency Issuance" refers to the issuance of prepaid funds as a named brand — Onbe's claimable payment product where the client funds are held in a float account and individual recipient claims are processed against that float. This is a complex financial instrument requiring precise accounting.

The package's size (654 KB) relative to the other packages indicates extensive transformation logic — likely involving multiple joins, lookups, and derived column transformations to assemble the complete claimable payment record from distributed source tables.

## Security Design Assessment

### Sensitive Parameter Inventory

The `Warehouse.dtproj` defines sensitive password parameters for every package:

| Connection | Sensitive Param Line Range |
|---|---|
| Prepaid_DW_OLAP | ~210 |
| Prepaid_Warehouse | ~298, ~492, ~686, ~880, ~1074, ~1268, ~1462, ~1744, ~2026, ~2396 |
| Ecountcore_SS | ~404, ~792, ~986, ~1180, ~1656, ~1938, ~2132 |
| cf_report | ~1568, ~1850, ~2502 |
| Jobsvc_SS | ~1374, ~2308 |
| ECountcore_ss_PROD | ~2220, ~2678 |

The sheer volume of `Sensitive=1` password parameters (20+ occurrences across the project manifest) combined with `EncryptSensitiveWithUserKey` means the project carries a large attack surface of encrypted-but-fragile credentials. Since all connections use Windows Integrated Security (SSPI), the password parameters should all be empty — yet they are marked sensitive. This warrants an audit of what values, if any, are stored in these encrypted fields.

### SMTP Security Flags

`Send Mail.conmgr`:
```
SmtpServer=nl-smtp-01.nam.wirecard.sys
UseWindowsAuthentication=False
EnableSsl=False
```

Two flags are actionable:
1. `UseWindowsAuthentication=False` — the SMTP relay accepts anonymous connections. This should be changed to require authentication.
2. `EnableSsl=False` — mail is sent unencrypted. If any email content includes operational details (e.g., record counts, date ranges) that could disclose internal system topology, this is an information disclosure risk.

## Remediation Priorities

| Priority | Item | Detail |
|---|---|---|
| Critical | Audit sensitive parameter values | Confirm all `CM.*.Password` sensitive params are empty (SSPI connections should have no password) |
| Critical | Version-control `.dtsConfig` files | Add `C:\SSISConfig\*.dtsConfig` content to repository |
| High | Resolve dual-configuration conflict | Decide: Project Deployment Model OR XML configs, not both |
| High | Enable SMTP authentication and TLS | `UseWindowsAuthentication=True; EnableSsl=True` on `Send Mail.conmgr` |
| High | Change notification address to DL | Replace `colin.treat@northlane.com` with an ops distribution list |
| Medium | Consolidate Intl/MT package families | Parameterise domestic packages to serve all three environments |
| Medium | Replace SQLNCLI11.1 with MSOLEDBSQL | All connection managers in all packages |
| Low | Fix filename typo | `intial_setup_cdc_control_jobsvc.dtsx` -> `initial_setup_cdc_control_jobsvc.dtsx` |
