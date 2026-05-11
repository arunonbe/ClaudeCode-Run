# DS_ETL_warehouse — Data Architect Perspective

## Dimensional Model Architecture

The `Prepaid_Warehouse` implements a classic star/snowflake schema for prepaid card analytics. The package naming conventions reveal the following dimensional entities:

### Dimension Tables
| Dimension | Package(s) | Key Fields (inferred) |
|---|---|---|
| DimAccountHolder | `DimAccountHolder_Incremental.dtsx`, `Intl_DimAccountHolder_Incremental.dtsx`, `MT_DimAccountHolder_Incremental.dtsx` | Account holder demographics, address, programme linkage |
| DimBIN | `DimBIN_Incremental.dtsx`, `DimBIN_Update.dtsx` | Bank Identification Number, issuer, card network |
| DimGeography | `DimGeography_Incremental.dtsx`, `DimGeography_Update.dtsx` | State, region, postal code |
| DimMerchant | `DimMerchant.dtsx`, `DimMerchant_Incremental.dtsx` | Merchant name, MCC, network |
| DimProduct | `DimProduct_Incremental.dtsx`, `DimProduct_Update.dtsx` | Card product type, fee structure |
| DimProgram | `DimProgram_Incremental.dtsx`, `DimProgram_Update.dtsx`, `DimProgram_Inferred_Update.dtsx` | Client programme, GFCID, issuance configuration |

### Fact Tables
| Fact | Package(s) | Granularity |
|---|---|---|
| FactTransaction | `Fact_Transaction_Incremental_Update.dtsx`, `Fact_Transaction_Update.dtsx` | One row per card transaction |
| FactDataExtract | `FactDataExtract_Incremental.dtsx`, `Intl_FactDataExtract_Incremental.dtsx`, `MT_FactDataExtract_Incremental.dtsx` | Extracted fact data for analytics |
| ClaimablePayment | `ClaimablePaymentHistory.dtsx`, `ClaimablePaymentIncremental.dtsx` | One row per claimable payment event |
| CardDetail | `CardDetailHistory.dtsx`, `CardDetailIncremental.dtsx` | Card lifecycle snapshot |
| CompanionCard | `CompanionCardAccounts.dtsx`, `CompanionCardRegistration.dtsx` | Companion card relationships |
| AccountBalance | `DailyAccountBalance.dtsx` | Daily balance snapshot |
| JobSvc Actions | `JobSvc_Actions_History.dtsx`, `JobSvc_Actions_Incremental.dtsx` | Automated job service event log |

## Connection Architecture

### Production Database Servers

From `CardDetailHistory.dtsx` (lines 27–48) and `DimAccountHolder_Incremental.dtsx` (lines 26–48):

```
Source 1: Data Source=p-db06\db06   -> Ecountcore_SS  (card management ODS)
Source 2: Data Source=p-db06\db06   -> cf_report       (reporting support DB)
Target:   Data Source=p-db07\db07   -> Prepaid_Warehouse (data warehouse)
```

The `p-` prefix designates production servers. Packages connecting to `p-db06` and `p-db07` are reading directly from and writing to **production databases** using Windows Integrated Security.

### QA/Staging Servers

From `CDC_stagingdata.dtsx` (lines 27–38):

```
Data Source=q-db03.nam.wirecard.sys\db03 -> Ecountcore_SS (QA)
Data Source=q-db03.nam.wirecard.sys\db03 -> Prepaid_Warehouse (QA)
```

### Critical Finding: Mixed Environment Connection Strings in Version Control

The Warehouse project contains packages with both `p-db0x` (production) and `q-db0x` (QA) connection strings baked in at design time. Both sets of packages are in the same version-controlled repository. This means:

1. Developers working in QA are loading packages that contain production server hostnames.
2. The actual runtime connection is governed by the SSIS configuration file `C:\SSISConfig\DW_ETL_Master.dtsConfig` (referenced in `DW_Incremental_ETL_Master.dtsx` line 43 and `CardDetailHistory.dtsx` line 42), which overrides connection strings at runtime.
3. The `.dtsConfig` files are NOT in this repository — they live on the execution server filesystem. This creates a documentation gap: the repository does not fully describe how the packages are actually configured in production.

### Connection Manager Flag: Direct Production Database Access

**Flag**: `DW_Incremental_ETL_Master.dtsx` (line 27) shows:
```
Data Source=p-db06\db06;Initial Catalog=Ecountcore_SS;
Integrated Security=SSPI;Application Name=SSIS-DW_ETL_Master-{...}PPAMWDCUDSQL1C1\PPAMWDCUDSQL1C1.Ecountcore_SS
```

The `Application Name` parameter reveals the production SSIS server hostname: `PPAMWDCUDSQL1C1`. This is a production server identifier embedded in version-controlled source code — a minor information-disclosure concern. Combined with the `p-db06` and `p-db07` direct-connect strings, the warehouse ETL connects directly to production databases, bypassing any read-replica or data-access tier.

## CDC (Change Data Capture) Architecture

The warehouse implements CDC-based incremental loading through a two-package pattern:

1. **`CDC_stagingdata.dtsx`** — captures CDC changes from source tables. Variable `capture_instance = fdr_dda_account_detail` (line 69) and `capture_instance_2 = fdr_dda_account_detail_block_code_modified` (line 77) identify two CDC capture instances on the `fdr_dda_account_detail` table in `Ecountcore_SS`. The `fdr_` prefix suggests FDR (First Data Resources, now Fiserv) formatted data structures — indicating Onbe's operational platform interfaces with FDR card-management conventions.
2. **`initial_setup_cdc_control.dtsx`** and **`intial_setup_cdc_control_jobsvc.dtsx`** — CDC control table initialisation packages (note: `intial` is a typo in the filename).

The CDC pattern uses the SSIS CDC Control task and CDC Source to read change records between LSN (Log Sequence Number) watermarks stored in the warehouse control tables.

## ETL Orchestration and Master Packages

Three master orchestration packages control execution:

| Master Package | Scope |
|---|---|
| `DW_Incremental_ETL_Master.dtsx` | Domestic US incremental daily load |
| `Intl_DW_Incremental_ETL_Master.dtsx` | International incremental load |
| `MT_DW_Incremental_ETL_Master.dtsx` | Multi-tenant incremental load |

The master packages use `DTS:EnableConfig="True"` and reference `C:\SSISConfig\DW_ETL_Master.dtsConfig` (line 43–47 of `DW_Incremental_ETL_Master.dtsx`), following the older SSIS XML Configuration Model rather than the Project Deployment Model environments. This is the SSIS 2008/2012 configuration pattern, predating the Catalog-based approach.

Log provider: `DTS.LogProviderSQLServer.3` writing to `Prepaid_Warehouse` (line 50–60 of `DW_Incremental_ETL_Master.dtsx`). ETL execution logs are written to the warehouse database itself.

## Key Data Architecture Risks

| Risk | Detail | File Reference |
|---|---|---|
| Production DB direct connect | No read-replica; ETL reads from live OLTP | DW_Incremental_ETL_Master.dtsx line 27 |
| `.dtsConfig` not in repository | Runtime configuration undocumented in source control | Multiple packages |
| `Ecountcore_SS` legacy dependency | Single source of truth; decommission would break all ETL | All packages |
| `fdr_dda_account_detail` CDC | FDR-formatted DDA table — cardholder DDA data in CDC stream | CDC_stagingdata.dtsx lines 69–77 |
| `p-db07\db07` warehouse target | Direct write to production warehouse | CardDetailHistory.dtsx line 38 |
