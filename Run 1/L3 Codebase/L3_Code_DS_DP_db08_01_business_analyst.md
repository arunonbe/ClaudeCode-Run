# Business Analyst Report — DS_DP_db08

## Repository Identity

**Repository:** DS_DP_db08  
**Classification:** Data Processing — Database Shard 08  
**Technology:** Microsoft SQL Server (T-SQL), SQL Server Agent Jobs  
**Ticket range observed:** NAMDATASVC-1089 (Oct 2019) through NATS-13634 (Mar 2022)  
**Total scripts:** ~95 ad-hoc SQL change scripts plus one DDL/trigger file  

---

## Business Purpose

DS_DP_db08 is the version-controlled change-script repository for **Processing Database Shard 08**, one of several numbered SQL Server instances that collectively form Onbe's (formerly Wirecard North America / North Lane Technologies) **core transaction-processing data plane**. The shard runs on the `p-db08` physical host and houses multiple logically separate databases:

| Database | Apparent Business Domain |
|---|---|
| `ECNT` | eCount North America (US prepaid processing ledger) |
| `ECAN` | eCount Canada (Canadian prepaid processing ledger) |
| `Banker` | Back-office orchestration for SSIS job configuration, SO Automation, GP integration |
| `Banker_NA` | North America variant of Banker metadata |
| `AcctgWf` | Accounting Workflow |
| `ATLYS_E` / `ATLYS_Fc_NCA` / `ATLYS_Fc_NUS` / `ATLYS_FcCR` / `ATLYS_Rv_NCA` / `ATLYS_Rv_NUS` / `ATLYS_RvCR` | Atlys reporting family — forecast and revenue views across Canada and US |
| `DYNAMICS` | Microsoft Dynamics GP (Great Plains) integration schema |
| `DBAdmin` | Database administration utilities (audit tables, maintenance jobs) |

The shard supports **B2C prepaid card disbursement, SO (Sales Order) automation, fee invoicing, and revenue/accounting reconciliation workflows** that are core to Onbe's FinTech business.

---

## Key Business Processes Supported

### 1. SO (Sales Order) Automation
Scripts configure `Banker.dbo.SSISJobConfigurations` for jobs named `SO Ordersvc`, `SO Jobsvc`, `SO Void`, `SO Fee Invoicing`, `SO Fee Invoicing ALL` (file `20201106_SQ-124-update-Banker.SSISJobConfigurations.sql`, line 4). These jobs drive prepaid card order fulfilment pipelines.

### 2. GP (Great Plains) Journal Entry and Batch Management
A recurring category of scripts deletes or corrects unposted journal entries and batch status records in the ECNT and ECAN databases that back Microsoft Dynamics GP. Examples:
- `20200429_NAMDATASVC-2104_DB08 Delete GP Unposted Journal Entry.sql`
- `20201208_NATS-9905_DB08 update GP Canada batches status.sql`
- `20220308_NATS-13634_delete_unposted_journal.sql`

These are operational remediation scripts run when GP batch posting errors occur, demonstrating a **manual, ticket-driven data correction workflow** rather than automated recovery.

### 3. Bank Information Management
Scripts update `ECNT.dbo.PrepaidBankInformation` and `ECAN.dbo.RM00101` (GP customer master), including bank name transitions from CitiBank to Sunrise and entity rebrands from Wirecard to North Lane Technologies / Onbe:
- `20200630_NAMDATASVC-2310_UpdateBankInfo.sql` — CitiBank → Sunrise migration
- `20201209_SQ-137_DB08 update PrepaidBankInformation new columns.sql` — email/company name rebrand

### 4. Atlys Reporting Configuration
Scripts maintain `ATLYS_*` databases used for financial forecasting (Fc) and revenue (Rv) reporting across North America (NUS) and Canada (NCA). Changes include:
- Adjusting invoicing period status resets
- Adding ASC 606 revenue recognition adjustments (`20210122_NATS-10330`)
- Updating cost allocation methods for new payment rails (Same Day ACH: `20210706_SQ-4056`)
- Program cost corrections and reporting filters

### 5. Emboss Rate / Stock Cost Management
Scripts update emboss rate configurations in Atlys settings and `ECNT.PrepaidBankInformation` for US and Canadian embossing programs (e.g., `20200902_WDNAMCBTS-140_CAEmbossRateInfo.sql`). These directly govern physical card production costs.

### 6. Fee & Transaction Code Management
Scripts add, remove, and update transaction codes for new payment products such as Same Day ACH:
- `20210121_SQ-456_DB08 add fee and item codes for same day ach.sql`
- `20210511_SQ-3539_DB08 Remove unused Transaction Codes for Same Day ACH.sql`

### 7. Security / Access Control
Scripts manage auditor access during BakerTilly audits and implement an IP-allowlist login trigger:
- `20200731_NAMDATASVC-2399_DB08 Grant permissions to audit users AD group.sql` — grants `db_datareader` to `NAM\BakerTilly_Auditors` across 11 databases
- `20200917_WDNAMCBTS-517_002_master.TR_check_ip_address_functional_user.sql` — server-wide LOGON trigger blocking functional service accounts connecting from unapproved IP addresses

---

## Regulatory Relevance

### PCI DSS
- `Banker.dbo.SSISJobConfigurations` stores SSIS job parameters as XML (including certificate thumbprints and email addresses). Any job parameter referencing card-processing systems extends the **Cardholder Data Environment (CDE) scope** to this database. PCI DSS Requirement 7 (restrict access) and Req 8 (identify and authenticate) are directly tested by the audit access scripts.
- The IP-allowlist LOGON trigger (`TR_check_ip_address_functional_user`) is a compensating control for PCI DSS Req 8.6 (restrict interactive logon) and Req 10.2 (audit trails for access attempts). The `DBAdmin.dbo.Audit_blocked_ip_user` table provides a limited audit log, retained for 90 days per the cleanup job (`20200917_WDNAMCBTS-517_003`).

### NACHA / ACH
- Same Day ACH transaction codes and fee codes introduced in 2021 scripts bring this shard into scope for **NACHA Operating Rules** compliance, specifically same-day settlement obligations.

### SOX / Financial Reporting
- The ASC 606 revenue recognition adjustments (`20210122_NATS-10330`) in Atlys confirm this shard holds data subject to **revenue recognition accounting standards**, making it relevant to SOX financial reporting controls.

### GLBA
- `ECNT.dbo.PrepaidBankInformation` and associated GP customer records contain bank routing information, falling under GLBA financial data protection requirements.

---

## Change Management Observations

Scripts are named with a date prefix and Jira ticket reference (NAMDATASVC, NATS, SQ, WDNAMCBTS, US ticket types), providing traceability but no formal approval workflow is evident in the repository. Rollback scripts exist only for a small subset (e.g., the `namdatasvc-1089` US/CAN pair). Most remediation scripts have no corresponding rollback, which is a **business continuity risk** if a correction needs to be reversed under time pressure.

The repository spans three corporate identity periods: Wirecard (pre-2020), North Lane Technologies (2020–2021), and Onbe (2021+), reflecting the corporate ownership transition.
