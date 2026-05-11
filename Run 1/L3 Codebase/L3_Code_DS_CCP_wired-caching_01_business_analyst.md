# Business Analyst Report — DS_CCP_wired-caching

## Repository Overview

DS_CCP_wired-caching is an **SSIS project** containing the ETL packages responsible for populating and refreshing all cache tables in the WIRED database. It represents the data pipeline layer between upstream data sources (Oracle CCP DWH, Great Plains ERP, SFTP-delivered files) and the WIRED database's pre-aggregated cache tables used for report generation.

The Visual Studio Integration Services project (`wired-caching.dtproj`, Product Version 14.0.3002.113 = VS 2017 SSDT) contains 9 SSIS packages and a shared Package Part, two connection managers, and a project parameters file.

## Business Processes Supported

### 1. Programme Balance Report (PBR) Cache Refresh
The `cache_pbr.dtsx` and `cache_refresh.dtsx` packages populate `WIRED.dbo.cache_pbr` with programme balance data from the Oracle CCP DWH (`ccp_dwh` connection — Oracle, via SSH tunnel to `DWH_AWS_SSH`). This is the most business-critical cache — the Programme Balance Report is a core client deliverable showing each client's programme financial position.

`usp_Wired_Cache_PBR_INS` in the WIRED database performs the stage-and-swap atomic load: staging table is populated first, then the production cache is replaced, ensuring clients never see a partially-loaded cache during report generation.

### 2. GP (Great Plains) PBR Cache Refresh
`import_cache_pbr_GP.dtsx` imports Great Plains financial data from an SFTP-delivered file (from the `GP_SFTP_*` SFTP endpoint) to populate `WIRED.dbo.cache_pbr_GP`. Great Plains is the accounting ERP system; PBR clients require GL-reconciled balance data. The GP cache is populated on the 2nd and 3rd of each month (month-end close timing) and daily at 5:30 PM via the `wired_cache_GP` SQL Agent job.

### 3. Aggregate Spending Cache Refresh
`cache_agg_spend.dtsx` populates `WIRED.dbo.cache_AggSpend` from the Oracle CCP DWH. This cache supports the Aggregate Spending Report — a programme-level transaction spending summary delivered to clients on weekly or monthly schedules.

### 4. Card Ship Date Cache Refresh
`cache_card_ship_date.dtsx` populates `WIRED.dbo.cache_CardShipDate` with card fulfilment/shipment tracking data from the CCP DWH. This supports the Card Ship Date Report used by client operations teams to track card order fulfilment.

### 5. RAPID Undeliverable Cards Cache Refresh
`cache_rapid_undeliverable_cards.dtsx` populates `WIRED.dbo.cache_RapidUndeliverableCards` with data on cards returned as undeliverable by the postal service. This supports the RAPID Undeliverable Cards Report — used by client services to manage card replacement workflows.

### 6. Corporate Client Brand Reference Cache
`cache_refresh.dtsx` (as the master orchestration package) also triggers population of `WIRED.dbo.cache_corp_client_brands`, which provides a reference mapping of brand codes to display names used throughout the WIRED report system.

### 7. SFTP File Retrieval for GP Data
`Receive_SFTP.dtsx` and `Files_sftp.dtsx` handle the inbound SFTP operations to retrieve GP financial data files before they are processed by `import_cache_pbr_GP.dtsx`. This integrates with DS_CCP_sftp generic SFTP components.

## Parameters (Project.params)

| Parameter | Default | Purpose |
|---|---|---|
| `SourceFolder` | `C:\ETL\In\` | Local landing zone for inbound files |
| `ArchivedFolder` | `C:\ETL\Archived\` | Archive for processed inbound files |
| `GP_SFTP_Enable` | `false` | Toggle: enable GP SFTP source |
| `GP_SFTP_HostName` | **`sftp-qa.nam.wirecard.com`** | GP SFTP server — **defaults to QA!** |
| `GP_SFTP_Password` | empty (sensitive) | GP SFTP password |
| `GP_SFTP_Port` | `22` | GP SFTP port |
| `GP_SFTP_SSHKey` | empty | Path to GP SSH private key |
| `GP_SFTP_SSHPassphrase` | empty (sensitive) | SSH key passphrase |
| `GP_SFTP_Username` | empty | GP SFTP username |
| `NotifyEmailAddress` | empty | Alert email address |
| `MailServerAccount` | empty | DB Mail account |

## Connection Managers

| Connection | Object | Type | Connection String |
|---|---|---|---|
| `wired_db` | SQL Server WIRED database | OLE DB (SQLNCLI11.1) | `Data Source=d-phl-db01; Initial Catalog=WIRED; Integrated Security=SSPI` |
| `ccp_dwh` | Oracle CCP DWH | ADO.NET OracleClient | `Data Source=DWH_AWS_SSH; User ID=RM_BI_USER` — **credential stored** |
| `SMTP Connection Manager` | Email delivery | SMTP | (config not fully read) |

**Critical finding in `ccp_dwh.conmgr`**: The Oracle connection manager stores `User ID=RM_BI_USER` in plaintext in the connection string. The password field uses SSIS sensitive encryption (`<DTS:Password Sensitive="1"></DTS:Password>`) with an empty value — meaning the password must be supplied via SSISDB environment variable at runtime. However, the Oracle username `RM_BI_USER` is committed as plaintext in source control.

## Data Flows

```
Oracle CCP DWH (DWH_AWS_SSH, RM_BI_USER)
    ↓ ccp_dwh.conmgr (OracleClient ADO.NET)
    ├─► cache_pbr.dtsx → WIRED.cache_pbr_STG → usp_Wired_Cache_PBR_INS → cache_pbr
    ├─► cache_agg_spend.dtsx → WIRED.cache_AggSpend_STG → usp_Wired_Cache_AggSpend_INS
    ├─► cache_card_ship_date.dtsx → WIRED.cache_CardShipDate_STG → ...
    └─► cache_rapid_undeliverable_cards.dtsx → WIRED.cache_RapidUndeliverableCards_STG → ...

GP SFTP Server (sftp-qa.nam.wirecard.com [QA default])
    ↓ Receive_SFTP.dtsx / Files_sftp.dtsx
    └─► import_cache_pbr_GP.dtsx → WIRED.cache_pbr_GP

cache_refresh.dtsx (master orchestrator)
    └─► Executes all individual cache packages in sequence
```

## Regulatory Relevance

| Regulation | Relevance |
|---|---|
| **PCI DSS** | WIRED cache tables do not contain PANs or cardholder data — this project is **outside CDE scope** for data content. However, the Oracle DWH connection uses a shared service account (`RM_BI_USER`) which should be reviewed for minimum privilege compliance. |
| **SOC 1 Type II** | Cache accuracy is critical for Programme Balance Report financial data delivered to clients. Data completeness controls (verifying cache refresh succeeded before report generation) are relevant SOC 1 controls. |
| **GDPR / CCPA** | No personal data is visible in the cache tables (brand-level aggregates only). |

## Integration Points

| System | Direction | Protocol |
|---|---|---|
| Oracle CCP DWH (`DWH_AWS_SSH`) | Inbound data | ADO.NET OracleClient over SSH tunnel |
| GP SFTP server | Inbound files | SFTP (SSH) |
| WIRED SQL Server (`d-phl-db01`) | Write cache | OLE DB |
| DS_CCP_sftp (sibling repo) | Component reuse | SSIS package part |
| SMTP server | Notifications | SMTP |
| SQL Agent on p-db09 | Orchestration | Executes this project's packages |
