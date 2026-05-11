# Data Architect View — DS_ETL_generic-etl

## Repository Overview

**Repo path:** `E:\OnbeEast363\repos\DS_ETL_generic-etl`
**Package count:** 9
**Connection managers:** 7 (`.conmgr` files) + inline package-level connections

---

## Connection Manager Inventory

| File | Object Name | Server | Catalog | Type | Auth | Notable |
|---|---|---|---|---|---|---|
| `alchemy-srv-dev.conmgr` | `alchemy-srv-dev` | `alchemy-srv-dev.database.windows.net` | `dw_api` | OLEDB SQLNCLI11.1 | **SQL Authentication** | **FLAG: Encrypted password blob present; Azure SQL** |
| `cbaseapp.conmgr` | `cbaseapp` | `d-na-db01.nam.wirecard.sys\db01,2232` | `cbaseapp` | OLEDB SQLNCLI11.1 | Windows SSPI | Dev server |
| `cf_report.conmgr` | `cf_report` | `q-db03.nam.wirecard.sys,2232` | `cf_report` | OLEDB SQLNCLI11.1 | Windows SSPI | QA server |
| `Ecountcore_Process.conmgr` | `Ecountcore_Process` | `d-na-db01.nam.wirecard.sys\db01` | `Ecountcore_Process` | OLEDB SQLNCLI11.1 | Windows SSPI | Dev server |
| `ecountcore_rollback.conmgr` | `ecountcore_rollback` | (file present, not fully read) | `ecountcore_rollback` | OLEDB | SSPI | Rollback DB |
| `Vendor.conmgr` | `Vendor` | `d-na-db01.nam.wirecard.sys\db01` | `Vendor` | OLEDB SQLNCLI11.1 | Windows SSPI | Vendor reference DB |
| `ETL.database` | (project DB) | — | — | SSAS | — | Project analysis database |

---

## CRITICAL FINDING: SQL Authentication Password in `alchemy-srv-dev.conmgr`

**File:** `E:\OnbeEast363\repos\DS_ETL_generic-etl\ETL\alchemy-srv-dev.conmgr`
**Lines 7–11:**

```xml
<DTS:ConnectionManager
  DTS:ConnectionString="Data Source=alchemy-srv-dev.database.windows.net;User ID=rc_contact_log_user;Initial Catalog=dw_api;Provider=SQLNCLI11.1;Persist Security Info=True;Auto Translate=False;">
  <DTS:Password
    DTS:Name="Password"
    Sensitive="1">AQAAANCMnd8BFdERjHoAwE/Cl+sBAAAAb3R5mOGu8UyAeV1m5LuXwAAAAAACAAAAAAADZgAAwAAAABAAAABz9Moz...</DTS:Password>
```

**This is a DPAPI-encrypted password stored in a `.conmgr` file committed to git.** The connection is to an Azure SQL Database (`alchemy-srv-dev.database.windows.net`) using SQL authentication with:
- **User ID:** `rc_contact_log_user`
- **Password:** DPAPI-encrypted blob (`AQAAANCMnd8BFdERjHoAwE/Cl+sB...`)

The DPAPI encryption protects the password from casual inspection but is tied to the Windows user key of the developer who saved it. This password cannot be used by other systems without the original developer's DPAPI context. However:
1. The blob is committed to git — accessible to anyone with repo access
2. If the original developer's machine or domain credentials are compromised, the password could be decrypted
3. The Azure SQL endpoint (`alchemy-srv-dev.database.windows.net`) with the username `rc_contact_log_user` is fully exposed

**Regulatory impact:** This constitutes a **credentials-in-source-control violation**, which is flagged by PCI DSS Requirement 6.3.3 (protect credentials) and is a NIST CSF PR.AC-1 failure.

---

## Source Systems

| System | Type | Server | Purpose |
|---|---|---|---|
| FDR settlement files | Flat file (text/binary) | File share or local path | Card processor DD031 settlement files |
| `dw_api` (Azure SQL) | Azure SQL Database | `alchemy-srv-dev.database.windows.net` | Data warehouse API — contact log source |
| `cbaseapp` | On-premise SQL Server | `d-na-db01.nam.wirecard.sys\db01,2232` | Core application database |
| `Ecountcore_Process` | On-premise SQL Server | `d-na-db01.nam.wirecard.sys\db01` | Transaction processing staging DB |
| `ecountcore_rollback` | On-premise SQL Server | `d-na-db01` | Rollback/undo staging DB |
| `Vendor` | On-premise SQL Server | `d-na-db01.nam.wirecard.sys\db01` | Vendor reference data |
| `cf_report` | On-premise SQL Server | `q-db03.nam.wirecard.sys,2232` | Reporting aggregation DB |
| STAR network Excel file | Excel (.xlsx) | `C:\ETL\In\STARsf\STARSf_10_2020.XLSX` | STAR network settlement report |
| IVR call centre system | (inferred — call log files or DB) | — | IVR call records |

---

## Target Systems

| System | Package | Notes |
|---|---|---|
| `cf_report` | IVR_CallLogs, RC_Contact_Log | Reporting DB target |
| `Ecountcore_Process` | FDR_Import_DD031 | Settlement records loaded here |
| `cbaseapp` | Multiple | Core app write-back |
| Salesforce CRM | StarSf (via Script Task) | STAR network data pushed to Salesforce |
| File system | Folder_File_CleanUp | Files deleted/archived |
| Sunrise bank | Export_Network_Settlement_Sunrise | Settlement export to banking partner |

---

## SSIS Package Inventory

### `FDR_Import_DD031.dtsx` (556,916 bytes)

The **second-largest package across all six repos** (after SSIS_FDR.dtsx in finance-gp). Handles the complete FDR DD031 file import pipeline.

**Expected data flow:**
1. Read FDR DD031 flat file from file share
2. Parse fixed-width or delimited transaction records
3. Apply transformation rules (date conversion, amount normalisation)
4. Load to `Ecountcore_Process` staging tables
5. Execute post-load stored procedures for reconciliation matching

**Sensitive data:** Transaction amounts, possibly masked PANs (first 6/last 4 in DD031 format), merchant data, interchange amounts.

---

### `RC_Contact_Log.dtsx` (156,968 bytes)

Connects to **Azure SQL** (`alchemy-srv-dev.database.windows.net`, `dw_api`) using SQL authentication (`rc_contact_log_user`). This is the only package in the six repos that connects to an Azure cloud service from on-premise SSIS. It pulls contact log records from the Azure data warehouse API and loads them to an on-premise reporting database.

**Architecture pattern:** Hybrid cloud-to-on-premise ETL — Azure SQL → on-premise SQL Server. This is a modern data integration pattern inserted into a legacy SSIS framework.

---

### `IVR_CallLogs.dtsx` (227,720 bytes)

IVR call log import. Reads call records (timestamps, cardholder interactions) and loads to `cf_report`. May contain cardholder-identifiable data.

---

### `StarSf.dtsx` (61,136 bytes)

Excel to Salesforce integration. Notable findings:

**Inline SMTP connection (dtsx line 41–43):**
```
ConnectionString="SmtpServer=smtp.nam.wirecard.sys;UseWindowsAuthentication=False;EnableSsl=False;"
```
SMTP with no SSL/TLS (`EnableSsl=False`) and no authentication (`UseWindowsAuthentication=False`). Email notifications are sent over an unencrypted, unauthenticated SMTP relay.

**Email addresses hardcoded in package parameters:**
- `david.tran@northlane.com` (CC)
- `techds@northlane.com` (From)

These are Northlane-era email addresses. Post-rebrand to Onbe, these may be stale and notifications may be undeliverable.

**Hardcoded Excel file path (dtsx line 29):**
```
C:\ETL\In\STARsf\STARSf_10_2020.XLSX
```
Local path with a specific month/year in the filename hardcoded as default. This file path must be updated for each execution — suggesting manual intervention is required before each monthly run.

---

## Sensitive Data Assessment

| Data Element | Package | Sensitivity |
|---|---|---|
| FDR transaction records | `FDR_Import_DD031` | **HIGH — PCI scope** (masked PAN, amounts, interchange) |
| Cardholder contact records | `IVR_CallLogs`, `RC_Contact_Log` | **HIGH — GLBA/CCPA** (cardholder identity, interaction history) |
| Card activation events | `IVR_card_activation_update` | Medium — card lifecycle data |
| Settlement amounts (Sunrise) | `Export_Network_Settlement_Sunrise` | Medium — financial settlement |
| Azure SQL credentials | `alchemy-srv-dev.conmgr` | **CRITICAL — SQL password in git** |
| Email addresses (Northlane) | `StarSf.dtsx` | Low — stale contact details |

---

## Encryption in Transit Assessment

| Connection | Encryption | TLS | Finding |
|---|---|---|---|
| Azure SQL (`alchemy-srv-dev`) | SQL Auth | `Persist Security Info=True` — no `Encrypt=True` | **FLAG: Azure SQL without forced TLS** |
| On-premise SQL connections | Windows SSPI | No `Encrypt=True` | Medium risk |
| SMTP (`StarSf`) | None | `EnableSsl=False` | **FLAG: Unencrypted email with potentially sensitive notification content** |
| FDR file share | None | File-level no encryption | Medium risk |
