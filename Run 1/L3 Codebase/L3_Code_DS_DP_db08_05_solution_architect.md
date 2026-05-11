# Solution Architect Report — DS_DP_db08

## Repository Identity

**Repository:** DS_DP_db08  
**Risk Profile:** HIGH — operational payment-processing shard with manual change management and recurring data remediation

---

## Complete Object Inventory

| Object Name | Database | Type | Purpose |
|---|---|---|---|
| `dbo.Audit_blocked_ip_user` | DBAdmin | Table | Login block audit log |
| `IX_Audit_blocked_ip_user_created` | DBAdmin | Index | Retention-query index on `created` |
| `TR_check_ip_address_functional_user` | master (ALL SERVER) | LOGON Trigger | IP allowlist enforcement for functional accounts |
| `usernames_functional_accounts` | master | Table (ref) | Functional account names subject to IP check |
| `ValidIPAddress` | master | Table (ref) | Approved IP address allowlist |
| `dbo.SSISJobConfigurations` | Banker | Table | SSIS job XML parameter store |
| `dbo.PrepaidBankInformation` | ECNT | Table | Bank/email config for prepaid invoicing |
| `dbo.RM00101` | ECNT | Table (GP) | GP Customer master — bank name assignments |
| `dbo.ASITables` | ECNT | Table | Atlys configuration items |
| `dbo.PrepaidBankInformation` | ECAN | Table | Canadian equivalent of ECNT table |
| `dbo.RM00101` | ECAN | Table (GP) | Canadian GP customer master |
| `dbo.ASITables` | ECAN | Table | Canadian Atlys configuration |
| Various GP work tables | ECNT/ECAN | Tables (ref) | GP batch/journal entry work tables |
| Atlys settings/periods/controls tables | ATLYS_* (7 DBs) | Tables | Reporting configuration |
| `dbo.enabled_production_jobs` | DBAdmin | Table (ref) | Production job name list for DR enablement |
| `DBMP - DBAdmin - Cleanup Audit_blocked_ip_user` | msdb | SQL Agent Job | Weekly cleanup of audit log |

---

## Security Vulnerabilities

### CRITICAL

**1. Server-Level LOGON Trigger Runs as `sa`**  
File: `20200917_WDNAMCBTS-517_002_master.TR_check_ip_address_functional_user.sql`, line 14  
```sql
ALTER TRIGGER [TR_check_ip_address_functional_user]
ON ALL SERVER
WITH EXECUTE AS 'sa'
```
The trigger executes with `sa` privileges. If the trigger code itself has a SQL injection vulnerability, or if an attacker can manipulate the `ValidIPAddress` or `usernames_functional_accounts` tables, they can escalate to `sa`. The trigger should execute as a dedicated low-privilege account. PCI DSS Req 7 (least privilege) is violated.

**2. CATCH Block Silently Swallows Errors**  
File: same file, lines 48–49  
```sql
BEGIN CATCH
    PRINT CAST(ERROR_NUMBER() AS VARCHAR(5)) + ' ' + ERROR_MESSAGE();
END CATCH
```
If the trigger fails (e.g., due to a table lock or connectivity issue writing to `DBAdmin`), the error is printed to the client connection but the login is **not blocked** — the ROLLBACK in the TRY block does not execute. This means the control can silently fail open, allowing blocked logins to succeed without audit. This is a **security bypass condition**.

### HIGH

**3. SQL Agent Jobs Owned by `sa`**  
File: `20200917_WDNAMCBTS-517_003_SQLAgent-DBMP - DBAdmin - Cleanup Audit_blocked_ip_user.sql`, line 31  
```sql
@owner_login_name=N'sa',
```
Jobs owned by `sa` run with maximum SQL Server privilege. Least-privilege principles (PCI DSS Req 7, NIST CSF PR.AC-4) require jobs to run under dedicated service accounts.

**4. No Schema Migration Tracking**  
With no migration framework, there is no guarantee that production DB08 exactly reflects any version of the scripts in this repository. An undocumented out-of-band change applied during an incident cannot be detected. PCI DSS Req 6.4 (change control) is not fully satisfied.

**5. Recurring Manual Data Correction Pattern**  
GP unposted journal deletion and order reset scripts appear ~10 times across the 28-month window. Each manual intervention carries risk of mis-targeting the wrong records. No pre-script `BEGIN TRANSACTION` / `ROLLBACK` pattern is used in most scripts.

### MEDIUM

**6. `BakerTilly_Auditors` Group Granted Broad Read Access Across 11 Databases**  
File: `20200731_NAMDATASVC-2399_DB08 Grant permissions to audit users AD group.sql`, lines 6–99  
`db_datareader` across `AcctgWf`, `ATLYS_E`, `ATLYS_Fc_NCA`, `ATLYS_Fc_NUS`, `ATLYS_FcCR`, `ATLYS_Rv_NCA`, `ATLYS_Rv_NUS`, `ATLYS_RvCR`, `Banker`, `Banker_NA`, `DYNAMICS`, `ECAN`, `ECNT`  
Provides auditor read access to all data including any card-adjacent or financial data. Scope of access should be limited to the minimum required for each specific audit engagement. PCI DSS Req 7 principle of need-to-know applies.

**7. Individual Developer Named in Scripts**  
File: `20200731_NAMDATASVC-2399_DB08 Grant permissions to audit users AD group.sql`, lines 127–467  
Individual AD accounts (`NAM\eric.neiman`, `NAM\dave.duvarney`, `NAM\rob.long`, `NAM\daniel.woods`, `NAM\nathan.olson`) were granted direct database permissions, then later revoked. This pattern of granting individual rather than group-based access increases the risk of orphaned permissions if an employee departs.

**8. Certificate Thumbprint Stored in Database (not HSM/Key Vault)**  
File: `20191019_NATS-5490_UpdateCert_in_Banker_SSISJobConfigurations.sql`, line 3  
Certificate thumbprints stored in an XML column in `Banker.dbo.SSISJobConfigurations` are not managed through an enterprise PKI or secrets manager. Manual rotation requires a SQL script deployment.

---

## Technical Debt Inventory

| Item | Debt Type | Priority |
|---|---|---|
| No migration tracking (Flyway/Liquibase) | Process | P1 |
| `sa`-owned SQL Agent jobs | Security | P1 |
| LOGON trigger runs as `sa` | Security | P1 |
| Silent-fail CATCH block in LOGON trigger | Security | P1 |
| No rollback scripts for 90%+ of changes | Process | P1 |
| Manual GP journal deletion (recurring) | Architecture | P2 |
| Individual permission grants (not group-only) | Security | P2 |
| Certificate management via SQL script | Operations | P2 |
| No automated DR test for this shard | Operations | P2 |
| SMTP server not using TLS (`EnableSsl=False` observed in sibling ETL repos) | Security | P2 |
| Cross-database queries without service boundaries | Architecture | P3 |
| 11+ databases co-hosted on one instance | Architecture | P3 |
| Residual Wirecard/North Lane branding in config | Operations | P3 |

---

## Remediation Priorities

### Immediate (P1)
1. Replace the `sa` execution context on `TR_check_ip_address_functional_user` with a dedicated low-privilege service account. Rewrite CATCH block to ROLLBACK on trigger failure to ensure fail-closed behaviour.
2. Convert all SQL Agent jobs from `sa` ownership to dedicated service account logins.
3. Implement a migration tracking table or adopt Flyway/Liquibase to establish applied-state traceability.
4. Require `BEGIN TRANSACTION` / `ROLLBACK` wrapping for all future data-patch scripts, with an explicit `COMMIT` only after manual validation.

### Short-Term (P2)
5. Investigate root cause of recurring GP journal entry failures; implement application-level retry and alerting to eliminate manual database intervention.
6. Migrate certificate management to Azure Key Vault or equivalent secrets manager; remove thumbprints from `SSISJobConfigurations`.
7. Enforce group-only (no individual account) database permission grants; conduct access review for all current individual grants.
8. Schedule and document DR failover test for this shard; confirm RTO/RPO meets SLA.

### Longer-Term (P3)
9. Evaluate decomposing ECNT/ECAN GP integration to a modern ERP connector, reducing manual SQL data patches.
10. Implement formal change-approval workflow (ITSM gate) before production execution of any data-patch script.
