# DS_DP_db07 — Enterprise Architect View

## Platform Generation
**Gen-1 / Gen-2 hybrid** — SQL Server 2012 infrastructure (MSSQL11.DB07), scripts date from 2019–2021. The platform is the SSIS/SQL-Agent orchestration layer for the eCount/NorthLane/Wirecard legacy estate. No cloud-native or containerized components.

## Business Domain
**Data Platform — Batch Orchestration & Monitoring**
- Sub-domain: Financial data pipelines (Warehouse, Finance/Forecast, ETL, ATM reconciliation)
- Sub-domain: Operational security controls (IP allowlisting, login audit)
- Serves: Finance, Data Services, IT Operations teams

## Architectural Role
DB07 is the **SSIS Integration Services execution node** that sits between source operational databases (DB02/DB04/DB06/DB08) and downstream analytical/reporting targets (Prepaid_Warehouse, OAS/CODA). It does not own business data; it orchestrates data movement and enforces job scheduling discipline.

```
[Source DBs: DB02/DB04/DB06/DB08]
       |
[DB07 — SSIS Execution Host + SQL Agent Scheduler]
       |              |               |
[Prepaid_Warehouse] [File Shares] [Finance DBs]
       |
[SSRS Reports / CODA]
```

## Integration Patterns
- **Scheduler-Invoked Batch** (SQL Agent → SSIS `dtexec`) — predominant pattern
- **SSIS Catalog deployment** (`/ISSERVER` switch with SSISDB-stored packages)
- **Environment-conditional DDL** (inline `CASE @@SERVERNAME`) — non-standard config injection
- **Email notification** (sp_send_dbmail) for operational alerting
- **Server-level LOGON trigger** for network-layer access control

## External System Dependencies
| System | Integration Type | Notes |
|---|---|---|
| Salesforce | SSIS ETL (Salesforce_Update_Atlys_Forecast.dtsx) | Weekday 10AM sync |
| Atlys (ATLYS_FcCR, ATLYS_RvCR) | SQL connection via SSIS | Finance forecast system |
| Cardtronics / Maritime ATM | SSIS ETL | ATM inventory and reconciliation |
| Fiserv | SSIS ETL (ImportFiservInventory) | Card inventory |
| NTT / IVR | SSIS ETL (NTT_IVR_CallLog) | IVR call log export |
| Sykes | SSIS ETL (call summary) | Customer service call data |
| 53rd Bank (5/3 Bank) | File export (DailyRecon PBR) | Program Balance by Bank report |
| OAS / CODA | SSIS ETL feed (via DS_ETL_great-plains-to-oas-coda) | Finance feed |
| Great Plains | SSIS ETL | GP_Export_CCP_PBR |

## Strategic Status
- **Sunset/Legacy** — SQL Server 2012 is end-of-life. This instance is a critical bottleneck: all ETL jobs for Finance, Warehouse, and vendor reconciliation depend on its availability.
- NorthLane/Wirecard branding still present in email addresses and server DNS names — indicates incomplete migration to Onbe infrastructure.
- No equivalent Gen-3 microservice or cloud-native orchestration (e.g., Azure Data Factory, Apache Airflow) has been observed replacing these workflows.

## Migration Blockers
1. **SSISDB catalog lock-in** — all package parameters are stored in the SSISDB catalog; migrating packages requires re-parameterizing all SSIS projects.
2. **Hardcoded server DNS names** — `*.nam.wirecard.sys` domain names embedded in connection strings; DNS cutover required before any cloud migration.
3. **LOGON trigger security control** — `TR_check_ip_address_functional_user` is an instance-level trigger; no equivalent exists in cloud-native databases; must be replaced by network security group rules or IAM policies.
4. **sa ownership of jobs** — must be remediated before any compliance-approved migration.
5. **Legacy email domain** — recipient lists must be updated to `onbe.com` domain before going live on new infrastructure.
6. **Undocumented SSIS packages** — packages live in SSISDB on DB07, not in this repo; source code of the actual ETL logic is not version-controlled here.
