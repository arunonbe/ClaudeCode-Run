# DS_DP_db06 — Solution Architect Report

## Critical Security Vulnerabilities

### VULN-01: `card_number` Column in `Vendor.dbo.IVR_CallLog` — Potential PAN Storage
- **Severity:** CRITICAL
- **PCI DSS Requirement:** 3.2 — PAN must not be stored unless there is a legitimate need, and it must be rendered unreadable
- **Evidence:** `20210611-SQ-3087-BACKFILL-001-prepare backfill population.sql`, line 30: `RIGHT(I.card_number, 4) AS card_number_last4 FROM REPORTINGDBSERVER.Vendor.dbo.IVR_CallLog AS I`
- **Details:** The `card_number` column exists in `IVR_CallLog`. IVR systems capture card numbers for authentication (cardholders enter their card number via keypad). If the IVR platform stores the full 16-digit number in this column before truncating to last-4, the `Vendor` database on DB06 contains full PANs in a reporting/non-CDE database.
- **Risk:** DB06 would be a **PAN data store** with potentially lighter controls than DB02's CDE. This would be a P0 PCI DSS finding.
- **Remediation:**
  1. Immediately query: `SELECT TOP 100 card_number FROM Vendor.dbo.IVR_CallLog WHERE card_number IS NOT NULL`
  2. If 16-digit numeric values found: treat as P0 PCI DSS violation, initiate incident response
  3. If masked/truncated values: document the masking logic and confirm it's applied before write
  4. Regardless: rename column to `card_last_four` or equivalent to prevent future accidental full-number storage
- **Priority:** P0 — BLOCKING

### VULN-02: `xp_logininfo` Extended SP in Production SP
- **Severity:** MEDIUM
- **Evidence:** `20210609_SQ-501_stored_proc_sync_users.sql`, lines 43–51 and 63–72: `EXEC xp_logininfo @group, 'members'`
- **Risk:** `xp_logininfo` is an undocumented extended stored procedure. Its behavior may vary between SQL Server versions. More importantly, it requires broad AD read permissions for the SQL Server service account — increasing the attack surface if the service account is compromised.
- **Remediation:** Replace with a managed identity or dedicated AD service account query, or document the exact permissions required for the service account
- **Priority:** P2

### VULN-03: Potential Hardcoded Credentials in PowerShell Scripts
- **Severity:** HIGH (requires file review — not visible in current analysis)
- **Evidence:** Two `.ps1` files present in repository: `20200805-namdatasvc-2320-deploy_ps_delete_rm_subscriptions_csv.ps1` and `20200909_wdnamcbts-490_change_subscription_owners.ps1`
- **Risk:** PowerShell scripts for SSRS management frequently contain SSRS service URLs, Windows credentials, or SQL connection strings hardcoded in plaintext
- **Remediation:** Review both PS1 files for hardcoded credentials; move any credentials to a secrets manager (Azure Key Vault); rotate any exposed credentials immediately
- **Priority:** P1 — Review required

---

## Technical Debt Inventory

### TD-01: 4-Year Change Silence
- No repository changes since July 2021
- Same risk as DB05 — unknown current state of NACHA mappings, BINBANK configs, IVR schema
- Priority: P1

### TD-02: Cross-Node Deployment Coupling for NACHA
- Same Day ACH transaction code scripts must be deployed to DB02 AND DB06 simultaneously
- No atomic deployment mechanism exists
- A partial deployment produces incorrect NACHA files — a regulatory violation risk
- Priority: P1

### TD-03: `STARsf_Monthly` TRUNCATE Pattern
- `rpt_StarSF` SP truncates and reloads `STARSf_Monthly` on every run (line 70: `TRUNCATE TABLE [dbo].[STARSf_Monthly]`)
- If the SP fails mid-run, the table is empty with no recovery
- Priority: P2

### TD-04: No Backup Job in Repository for `cf_report` and `Vendor`
- Critical regulatory data (NACHA mappings, IVR call logs) in these databases
- No backup scripts present
- Priority: P1

### TD-05: SSRS Platform Aging
- SSRS 2012/2014 era technology
- Report subscriptions managed via PowerShell CLI tools
- No modern BI tool integration visible
- Priority: P3 (strategic)

### TD-06: `ecountcore_ss` Linked Server Not Documented
- Used in reporting SP but the linked server name/target is never defined in DB06 scripts
- Snapshot age, replication lag, and failover behavior unknown from repository
- Priority: P2

---

## Complete Object Inventory

### `cf_report` Database — `dbo` schema
| Object | Type | Purpose |
|---|---|---|
| `dbo.STARSf_Monthly` | Table | STAR SF network monthly aggregate report |
| `dbo.rpt_StarSF` | Stored Procedure | STARsf report generation + table population |
| `dbo.dim_transaction_type_12272016` | Table | Transaction type dimension for daily recon extract |
| `dbo.t_Report_Exception_list` | Table | Program exception tracking for account management |
| `dbo.MaritimeATM_Terminal_ID` | Table | Maritime ATM terminal registry |
| Other reporting tables | Tables | Exception reports, escheatment, negative balance |

### `cf_report` Database — `BINBANK` schema
| Object | Type | Purpose |
|---|---|---|
| `BINBANK.nacha_transaction_mapping` | Table | Source-to-NACHA entry mapping |
| `BINBANK.nacha_bank_source` | Table | ACH source configuration (enabled/disabled) |
| `BINBANK.TCode_Lookup` | Table | Transaction code lookup for BIN Bank extract |

### `Vendor` Database
| Object | Type | Purpose |
|---|---|---|
| `dbo.IVR_CallLog` | Table | All IVR call records (dda, card_number, flags) |
| `dbo.IVR_CallLog_STG` | Table | Staging for IVR_CallLog |
| `dbo.IVR_CallLog_MenuChoices` | Table | Menu selection per call |
| `dbo.IVR_CallLog_MenuChoices_STG` | Table | Staging |
| `dbo.IVR_Fraud_Call_Log` | Table | Fraud-flagged IVR calls |
| `dbo.IVR_Fraud_Call_Log_STG` | Table | Staging |

### `ODS` Database (transitional — data migrated to CCP)
| Object | Type | Purpose |
|---|---|---|
| `dbo.Billing_Audit` | Table | Billing event audit |
| `dbo.Billing_Detail` | Table | Billing line items |
| `dbo.Billing_Events` | Table | Fee type mapping |
| `dbo.FVD_Deferred` | Table | Financial value deposit deferred recognition |
| `dbo.FVD_Revenue` | Table | FVD revenue entries |
| `dbo.package_execution` | Table | ETL package execution log (with trigger) |
| `dbo.TR_package_execution_U` | Trigger | Update trigger on package_execution |
| `dbo.package_execution_log` | Table | Detailed ETL execution log |

### `master` Database
| Object | Type | Purpose |
|---|---|---|
| `dbo.uspSyncBusinessUsers` | Stored Procedure | AD group → SQL Server access sync |
| `dbo.BusinessUsers` | Table | Business user login registry |
| `dbo.BusinessUserGroups` | Table | AD group names + isLimited flag |
| All shared objects | Various | IP trigger, Ola Hallengren, as per other nodes |

---

## Schema Consistency vs. Other Nodes

DB06 is unique in the DS_DP set for:
1. The `BINBANK` schema within `cf_report` — no other node has a multi-schema reporting database
2. The `Vendor` database for IVR data — unique to DB06
3. PowerShell SSRS management scripts — unique to DB06
4. AD group membership sync via `xp_logininfo` — unique to DB06
5. Business user access model with `isLimited` flag — unique to DB06

---

## Remediation Priority Matrix

| Priority | Item | Effort | Risk Reduction |
|---|---|---|---|
| P0 | Audit `IVR_CallLog.card_number` for full PANs | LOW | PCI Req 3.2 — critical |
| P1 | Review PowerShell scripts for hardcoded credentials | LOW | Credential exposure |
| P1 | Add backup jobs for cf_report and Vendor | LOW | Data protection |
| P1 | Document and automate NACHA cross-node deployments | HIGH | Regulatory compliance |
| P2 | Replace `xp_logininfo` with modern identity integration | MEDIUM | Security posture |
| P2 | Handle `STARSf_Monthly` truncation safely (transaction wrap) | LOW | Data reliability |
| P2 | Document `ecountcore_ss` linked server config | LOW | Operational transparency |
| P3 | Evaluate SSRS modernization to Power BI | HIGH | Strategic |
