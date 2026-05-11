# Enterprise Architect View — DS_ETL_generic-etl

## Positioning in the Onbe Data Platform

`DS_ETL_generic-etl` serves as the **utility/miscellaneous ETL layer** of the platform. It provides packages that don't belong to a specific business domain but are essential supporting processes:

- **Inbound settlement import** (FDR DD031 — feeds reconciliation in finance-gp)
- **Call centre analytics** (IVR logs, contact logs — feeds operational reporting)
- **Card lifecycle management** (IVR activation updates — feeds card management)
- **Banking partner exports** (Sunrise settlement — feeds partner reporting)
- **Platform hygiene** (file cleanup, CSA archiving)

This repo functions as an **integration hub** between heterogeneous external systems (FDR processor, IVR platform, Azure cloud, Salesforce) and the on-premise Onbe databases.

---

## Platform Generation

| Attribute | Value |
|---|---|
| Creator domains observed | `WIRECARD\david.tran`, `INT\julia.ginzburg`, `WIRECARD\julia.ginzburg` |
| SSIS versions | SQL Server 2012 (v11.0.7001.0) — consistent across packages |
| Azure SQL connection | Present — indicates post-2018 cloud adoption |
| Northlane email addresses | `@northlane.com` — 2020–2021 era |

This is a **second-generation** repo with packages spanning the Wirecard (2020) and Northlane/Onbe (2020–2021) periods. The Azure SQL connection marks a hybrid cloud transition point.

---

## Architectural Significance: Hybrid Cloud Bridging

The `RC_Contact_Log.dtsx` package is architecturally significant because it connects an on-premise SSIS execution host to an **Azure SQL Database** (`alchemy-srv-dev.database.windows.net`). This represents Onbe's first step toward cloud data integration in the DS_ETL suite.

**Architecture pattern:**
```
Azure SQL Database (dw_api) — cloud
  ↓ (via on-premise SSIS + SQLNCLI11)
On-premise cf_report / cbaseapp — on-premise SQL Server
```

This is an anti-pattern for cloud-native architecture: using a legacy on-premise SSIS engine to pull data from a cloud database. The modern pattern would be to push data from Azure to on-premise via Azure Data Factory, or to centralise in Azure.

---

## Dependencies

### Upstream Dependencies

| Dependency | Type | Package | Criticality |
|---|---|---|---|
| FDR DD031 settlement files | Flat file delivery | `FDR_Import_DD031` | Critical — daily settlement |
| IVR system call logs | IVR platform export | `IVR_CallLogs` | High — daily call log batch |
| Azure SQL `dw_api` database | Azure SQL | `RC_Contact_Log` | High — contact data sync |
| `C:\ETL\In\STARsf\` Excel files | Manual file drop | `StarSf` | Medium — monthly |
| Sunrise settlement data | Internal DB query | `Export_Network_Settlement_Sunrise` | High — daily settlement |

### Downstream Dependencies

| Consumer | Package | What It Receives |
|---|---|---|
| `Ecountcore_Process` DB | `FDR_Import_DD031` | Reconciliation records |
| `cf_report` DB | `IVR_CallLogs`, `RC_Contact_Log` | Call log / contact records |
| Salesforce CRM | `StarSf` | STAR network data |
| Sunrise bank | `Export_Network_Settlement_Sunrise` | Settlement file |
| DS_ETL_finance-gp | `FDR_Import_DD031` output | FDR data consumed by SSIS_FDR.dtsx |

---

## Relationship to DS_ETL_finance-gp

There is a strong relationship between `FDR_Import_DD031.dtsx` in this repo and `SSIS_FDR.dtsx` in DS_ETL_finance-gp. Both deal with FDR (First Data Resources) data:

- `FDR_Import_DD031` (generic-etl) = **imports** FDR raw files into staging tables
- `SSIS_FDR` (finance-gp) = **reconciles and posts** FDR data to GL/reporting

This suggests a two-stage pipeline:
1. Stage 1: generic-etl imports raw FDR → `Ecountcore_Process`
2. Stage 2: finance-gp reconciles and posts → `cf_report`, GP

The dependency ordering is important for scheduling: `FDR_Import_DD031` must complete before `SSIS_FDR` can run.

---

## Migration Complexity Assessment

**Modernisation difficulty: MEDIUM**

Individual packages vary in complexity:
- `Folder_File_CleanUp`, `IVR_card_activation_update` — LOW complexity (simple utility tasks)
- `CSL_Activity`, `Add_CSA_Archive_Comment` — LOW-MEDIUM (stored procedure wrappers)
- `StarSf`, `Export_Network_Settlement_Sunrise` — MEDIUM (external integrations)
- `FDR_Import_DD031` — HIGH (large, complex FDR file parsing; 556 KB package)
- `IVR_CallLogs`, `RC_Contact_Log` — MEDIUM-HIGH (large data volumes, potential schema complexity)

**Modern replacement approaches:**
- `FDR_Import_DD031` → Azure Data Factory pipeline with FDR file format parsing custom activity
- `RC_Contact_Log` → Azure Data Factory pipeline (already touching Azure SQL — natural ADF candidate)
- `StarSf` → Power Automate or Logic Apps for Excel-to-Salesforce flow
- `IVR_CallLogs` → ADF or event-driven Azure Function triggered by IVR file arrival
- File cleanup → Azure Blob Storage lifecycle management policies (if migrated to Azure)

---

## Cross-Repo Relationships

| Repo | Relationship |
|---|---|
| DS_ETL_finance-gp | `FDR_Import_DD031` feeds `SSIS_FDR`; both repos share `cf_report` and `Ecountcore_Process` |
| DS_ETL_finance | Shares `cf_report` as target |
| DS_DB_ecountcore_process | Target database schema for FDR import |
| DS_DB_cbaseapp | Target database schema for core app data |
| DS_DB_vendor | Source/target for Vendor connection |

---

## Technical Concerns for Enterprise Architecture

1. **Azure SQL SQL Authentication** — The only cloud connection in the six repos uses SQL authentication with a DPAPI-encrypted password committed to git. This is inconsistent with modern cloud security posture (should use Azure AD/Managed Identity).

2. **SQLNCLI11 driver** — Microsoft has deprecated SQLNCLI for Azure SQL connections. The recommended driver is Microsoft ODBC Driver 18 or `Microsoft.Data.SqlClient`. Using deprecated drivers for cloud connections creates a future compatibility risk.

3. **On-premise-to-cloud bridge via legacy SSIS** — This architecture creates complexity in network security zone management (on-premise SSIS host must have outbound 1433 to Azure SQL), complicates monitoring, and limits scalability.

4. **No error recovery for FDR import** — If the daily FDR file is malformed or delayed, the downstream `SSIS_FDR` reconciliation in finance-gp will fail silently or produce incorrect results. There is no file validation or delivery confirmation logic visible.
