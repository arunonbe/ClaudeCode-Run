# Data Architect View — DS_ETL_finance-gp

## Repository Overview

**Repo path:** `E:\OnbeEast363\repos\DS_ETL_finance-gp`
**Package count:** 18
**Connection manager files:** 10 (`.conmgr`)
**Total package size:** ~3.4 MB

---

## Connection Manager Inventory

All connection managers use Windows Integrated Security (`SSPI`) except `alchemy-srv-dev` (Azure SQL with SQL authentication).

| File | Object Name | Server | Database | Provider | Auth | Notes |
|---|---|---|---|---|---|---|
| `ATLYS_E.conmgr` | `ATLYS_E` | `q-db03.nam.wirecard.sys,2232\db03` | `ATLYS_E` | SQLNCLI11 | Windows SSPI | Atlys East/US programme DB |
| `ATLYS_RvCR.conmgr` | `ATLYS_RvCR` | `q-db03.nam.wirecard.sys,2232\db03` | `ATLYS_RvCR` | SQLNCLI11 | Windows SSPI | Atlys Revenue Reconciliation |
| `Banker.conmgr` | `Banker` | (inferred from SSISConfigurations) | `Banker` | SQLNCLI11 | Windows SSPI | Job configuration DB |
| `cf_report.conmgr` | `cf_report` | `q-db03.nam.wirecard.sys,2232\db03` | `cf_report` | SQLNCLI11 | Windows SSPI | Financial reporting DB |
| `Core.conmgr` | `Core` | `q-db02.nam.wirecard.sys,2232\db02` | `Ecountcore` | SQLNCLI11.1 | Windows SSPI | Core transaction DB |
| `ECAN GP.conmgr` | `ECAN GP` | `q-db03.nam.wirecard.sys,2232\db03` | `ECAN` | SQLNCLI11.1 | Windows SSPI | GP Canadian entity DB |
| `ECNT GP.conmgr` | `ECNT GP` | `q-db03.nam.wirecard.sys,2232\db03` | `ECNT` | SQLNCLI11 | Windows SSPI | GP US entity DB |
| `RSServer.conmgr` | `RSServer` | (file content not fully read) | `RS` | SQLNCLI11 | Windows SSPI | Revenue Share server |
| `SMTP Server.conmgr` | `SMTP Server` | — | — | SMTP | — | Email notifications |
| `SSISConfigurations.conmgr` | `SSISConfigurations` | `q-db03.nam.wirecard.sys,2232\db03` | `Banker` | SQLNCLI11 | Windows SSPI | Package configuration table |

---

## Source and Target Systems

### Source Databases

| Database | Server | Purpose |
|---|---|---|
| `ATLYS_E` | `q-db03` | Atlys East/US card programme transactions |
| `ATLYS_RvCR` | `q-db03` | Atlys revenue reconciliation |
| `cf_report` | `q-db03` | Financial reporting consolidation |
| `Ecountcore` | `q-db02` | Core transaction processing engine |
| `Banker` | `q-db03` | Job scheduling and SSIS configuration |
| `ECAN` | `q-db03` | Great Plains — Canadian entity (eCount Canada) |
| `ECNT` | `q-db03` | Great Plains — US entity (eCount) |
| `FDR` settlement files | File system | First Data Resources processor settlement files |

### Target Systems

| Target | Type | Location |
|---|---|---|
| Great Plains GL (ECAN/ECNT) | SQL Server (GP tables) | `q-db03` — written by GL batch packages |
| GP Files share | UNC file share | `\\d-na-stk01.nam.wirecard.sys\GP_Files\` (Project.params) |
| Client batch server | UNC file share | `\\d-na-bat03.nam.wirecard.sys\C-Base\Runtime\Clients\GXS\inbound\` (Project.params) |
| ACH files | NACHA flat files | Written to file share, submitted to Citibank CitiDirect |
| Invoice files | Digital invoice files | `D:\Jobs_Files\Outbound\` (PrepaidDigitalInvoice.dtsx) |

---

## Project-Level Parameters (`Project.params`)

| Parameter | Value | Purpose |
|---|---|---|
| `FolderPath` | `\\d-na-stk01.nam.wirecard.sys\GP_Files\` | GP file share path |
| `DirectoryPath` | `\\d-na-bat03.nam.wirecard.sys\C-Base\Runtime\Clients\GXS\inbound\` | Client/GXS file inbound path |
| `SecurityProtocol` | `3072` | Enum value for TLS 1.2 (`System.Net.SecurityProtocolType.Tls12`) — **POSITIVE FINDING** |

The `SecurityProtocol=3072` parameter is explicitly set to enforce TLS 1.2 for any HTTP/HTTPS connections made from Script Tasks. This is a positive security control indicating awareness of TLS protocol requirements, consistent with PCI DSS Requirement 4.2.1 (use strong cryptography for data in transit).

---

## SSIS Package Inventory with Data Flows

### `SOFeeAggregation.dtsx`

**Key connection:** `Core` (Ecountcore DB) + log file on `\\q-na-stk01.nam.wirecard.sys\GP_Files\`

**Parameters:**
| Parameter | Type | Default | Description |
|---|---|---|---|
| `EndDate` | DateTime | `1/31/2020` | Billing period end |
| `JobType` | Int32 | `31` | Job type from `Banker.dbo.SSISJobConfigurations` |
| `ProcessId` | Int32 | `1` | Process instance ID |
| `StartDate` | DateTime | — | Billing period start |

**Configuration source:** `SSISConfigurations` (Banker DB) — classic SSIS configuration table pattern.

**Sensitive data:** Fee amounts, date ranges, job configuration. No direct cardholder data.

---

### `PrepaidDigitalInvoice.dtsx`

**Parameters:** `FilePath` = `D:\Jobs_Files\Outbound\` (local path — hardcoded)

**Sensitive data:** Invoice amounts, client IDs, programme identifiers. Financial data.

**FLAG:** Local path `D:\Jobs_Files\Outbound\` is hardcoded. This is a server-local path — package must execute on a specific server. Not parameterised properly.

---

### `CPPLoopProcess.dtsx`

**Configuration source:** `SSISConfigurations.conmgr` pointing to `Banker` database — job orchestration configuration. The loop master reads job definitions and iterates child package execution.

---

### `SSIS_FDR.dtsx` (720,574 bytes — largest in the set)

First Data Resources settlement processing. The FDR file format is a proprietary card processor settlement format. This package likely:
1. Reads FDR settlement flat files from a file share
2. Parses transaction records (which may include masked PANs, transaction amounts, merchant data)
3. Matches against Onbe internal records
4. Posts reconciliation entries to cf_report or GP databases

**Sensitive data flag:** FDR settlement files typically contain:
- Masked PANs (first 6/last 4 — within PCI scope)
- Transaction amounts
- Merchant category codes
- Cardholder billing amounts

This package requires detailed review for PCI DSS data handling compliance.

---

### `SSIS_GLBatchE.dtsx` (223,599 bytes)

GL Batch Export — East (US) entity. Reads financial data from source databases and generates a GL batch file for import into GP. This is the SOX-critical financial reporting export.

---

### `Onus.dtsx` (397,110 bytes)

OnUs settlement. Uses `ATLYS_E` (Atlys East programme), `cf_report`, and writes to `\\d-na-stk01.nam.wirecard.sys\GP_Files\`. Processes intra-Onbe settlement.

---

## Sensitive Data Flowing Through ETL

| Data Element | Package(s) | PCI/Regulatory Risk |
|---|---|---|
| Fee amounts | All SO* packages | Financial data — SOX, GLBA |
| Invoice amounts | PrepaidDigitalInvoice, FeeInvoicingACH | Financial data — SOX |
| ACH routing/account numbers | CitiDirectACH, FeeInvoicingACH | **HIGH — NACHA ACH data; bank account numbers** |
| GL journal amounts | SSIS_GLBatchE | SOX-critical financial data |
| FDR settlement transaction records | SSIS_FDR | **HIGH — potential masked PAN data; PCI DSS scope** |
| Customer balances | PRD_CustomerBalance | GLBA non-public personal financial info |
| Client refund amounts | ClientRefund | Financial data |

---

## Encryption Assessment

- **SQL connections:** All use `Integrated Security=SSPI` — no SQL passwords; no `Encrypt=True` enforced
- **File outputs:** Written to UNC shares without encryption; ACH files and GL batch files are sensitive financial data on plaintext file shares
- **TLS 1.2 enforcement:** `SecurityProtocol=3072` parameter is set — positive control for HTTP/HTTPS connections from Script Tasks
- **SMTP:** `SMTP Server.conmgr` at 410 bytes — likely unencrypted SMTP (port 25); no TLS configuration visible

---

## Great Plains Database Schema

| Database | Entity | Description |
|---|---|---|
| `ECAN` | eCount Canada | GP company database for Canadian operations |
| `ECNT` | eCount | GP company database for US operations |
| `ATLYS_E` | Atlys East | Atlys programme US entity operational data |

GP uses a fixed schema: `SY`, `GL`, `RM`, `PM`, `IV` module prefixes for system, GL, receivables, payables, inventory. GL batch tables include `GL00100` (GL Account Master), `GL10000` (GL Transaction Work).
