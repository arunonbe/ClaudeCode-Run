# Solution Architect Report — DS_DR_FAILOVER

## Repository Identity

**Repository:** DS_DR_FAILOVER  
**Risk Profile:** CRITICAL — failure of this runbook during a DR event could result in extended payment processing downtime, regulatory breach, and customer impact

---

## Complete Object / Script Inventory

| File | Step | Server Target | Purpose |
|---|---|---|---|
| `0010/Disable_all_logshipping_jobs_run_on_all_servers.sql` | 1 | ALL PROD | Disable all log shipping SQL Agent jobs |
| `0020/p-az-db14_take_tail.sql` | 2 | p-az-db14 | Tail-log backup of 17 databases |
| `0020/pc-db01_take_tail.sql` | 2 | pc-db01 | Tail-log backup of 6 databases including mirrored DBs |
| `0020/pc-db02_take_tail.sql` | 2 | pc-db02 | Tail-log backup — Ecountcore family |
| `0020/pc-db03_take_tail.sql` | 2 | pc-db03 | Tail-log backup — Cbaseapp, NotificationSvc |
| `0020/pc-db04_take_tail.sql` | 2 | pc-db04 | Tail-log backup (content not fully read) |
| `0020/pc-db05_take_tail.sql` | 2 | pc-db05 | Tail-log backup of 20+ databases |
| `0020/pc-db06_take_tail.sql` | 2 | pc-db06 | Tail-log backup |
| `0030/p-az2-db14_restore.sql` | 3 | p-az2-db14 | Restore tail-log backups |
| `0030/pc-az2-db01_restore.sql` | 3 | pc-az2-db01 | Restore tail-log backups |
| `0030/pc-az2-db02_restore.sql` | 3 | pc-az2-db02 | Restore tail-log backups + NORECOVERY mirrored DBs |
| `0030/pc-az2-db03_restore.sql` | 3 | pc-az2-db03 | Restore tail-log backups |
| `0030/pc-az2-db04_restore.sql` | 3 | pc-az2-db04 | Restore tail-log backups |
| `0030/pc-az2-db05_restore.sql` | 3 | pc-az2-db05 | Restore tail-log backups (log-shipped + mirrored DBs) |
| `0030/pc-az2-db06_restore.sql` | 3 | pc-az2-db06 | Restore tail-log backups |
| `0040/p-az2-db14_data_patches.sql` | 4 | p-az2-db14 | Server name resets in ATLYS_E, Banker, ECNT, ECAN |
| `0040/pc-az2-db05_data_patch.sql` | 4 | pc-az2-db05 | Data patches on pc-az2-db05 |
| `0040/pc-az2-db06_data_patches.sql` | 4 | pc-az2-db06 | Data patches on pc-az2-db06 |
| `0050/001_pc-az2-db01_backup_mirror.sql` | 5 | pc-az2-db01 | Mirror log backups for JobSvc, Ordersvc |
| `0050/002_pc-az2-db02_backup_mirror.sql` | 5 | pc-az2-db02 | Mirror log backups for Ecountcore family |
| `0050/003_pc-az2-db03_backup_mirror.sql` | 5 | pc-az2-db03 | Mirror log backups for Cbaseapp, NotificationSvc |
| `0050/004_pc-az2-db05_restore_mirror.sql` | 5 | pc-az2-db05 | Restore mirror log backups with NORECOVERY |
| `0060/001_p-az2-db14_gen_create_replication.sql` | 6 | p-az2-db14 | Generate replication scripts |
| `0060/002_pc-az2-db05_create_replication.sql` | 6 | pc-az2-db05 | Create distributor, publisher, subscriptions — CONTAINS PASSWORD PLACEHOLDERS |
| `0060/003_p-az2-db14_create_subsctriptions.sql` | 6 | p-az2-db14 | Create replication subscriptions |
| `0070/EnableJobs_Run_All_Servers.sql` | 7 | ALL DR | Enable production-equivalent SQL Agent jobs |

---

## Security Vulnerabilities

### CRITICAL

**1. Password Placeholders in Source-Controlled Replication Script**  
File: `0060_recreate_replication/002_pc-az2-db05_create_replication.sql`, lines 21, 57  
```
@password = N'**replace_with_password**'
@distributor_password = N'**replace_with_password**'
@job_password = '**replace_sqlsvc_password**'
```
The script requires two service account passwords to be manually inserted. Risks:
- A DBA under DR pressure may use a weak password or reuse an old password
- The modified script with real passwords may be accidentally committed to the Git repository
- No audit trail of which password was used at each DR event
- Compliance gap: PCI DSS Req 8.3 (strong passwords) and Req 8.6 (no shared passwords) cannot be verified with this approach

**Recommended fix:** At failover time, retrieve passwords from Azure Key Vault or a PAM system via a separate script that injects them into SQL variables without touching the source file.

**2. Tail-Log Backup Files on Co-Located UNC Shares**  
All tail-log backups are written to UNC paths on the source servers (e.g., `\\pc-db05\shipping\`). In a catastrophic failure scenario:
- The source server is down
- The UNC share is inaccessible
- DR restore (step 0030) cannot proceed
- **All transactions since the last shipped log are permanently lost**

This is a data loss and compliance risk (PCI DSS Req 12.3 — recovery time targets cannot be met if backups are inaccessible).

### HIGH

**3. Deprecated Database Mirroring**  
Step 0050 configures SQL Server Database Mirroring via `BACKUP LOG` and `RESTORE LOG WITH NORECOVERY`. This technology is removed from SQL Server 2019. If any of the mirrored instances (`pc-az2-db01`, `pc-az2-db02`, `pc-az2-db03`) run SQL Server 2019+, these scripts will error at failover. **Scripts must be validated against the actual SQL Server version in production before any DR event.**

**4. No Automated Failover Monitoring**  
There is no automated detection of production failure that triggers the DR process. The time between a production outage and the start of DR execution is entirely dependent on human detection and escalation. For a payment platform, this unmonitored gap directly increases the effective RTO and cardholder impact duration.

**5. `ALTER DATABASE SET SINGLE_USER WITH ROLLBACK IMMEDIATE` Pattern**  
Files: `0020/pc-db05_take_tail.sql`, line 1 (and throughout tail-log backup scripts)  
This command forcibly disconnects all existing connections. During a DR event, applications may still be trying to connect to the production database. Forcing SINGLE_USER disconnects them without warning, which may cause data loss in applications that do not handle disconnection gracefully. The script should be preceded by a connection-termination and application-quiesce step.

### MEDIUM

**6. Log Shipping Job Detection by Description Pattern**  
File: `0010/Disable_all_logshipping_jobs_run_on_all_servers.sql`, line 8  
```sql
where description like 'log shipping%'
```
If any log shipping job has a custom or non-standard description, it will not be disabled. A missed job could continue applying logs to the DR instance mid-failover, causing data inconsistency.

**7. No Validation Steps Between Phases**  
The 7-step procedure has no built-in validation checkpoints. If step 0030 (restore) fails for one database, the DBA must manually detect this before proceeding to step 0040. A missed failure could result in a DR environment with inconsistent databases (some restored, some not).

---

## Technical Debt Inventory

| Item | Debt Type | Priority |
|---|---|---|
| Password placeholders in replication script | Security | P1 |
| UNC backup shares co-located with source servers | Architecture | P1 |
| Deprecated Database Mirroring | Architecture | P1 |
| No automated failover detection | Operations | P1 |
| No documented RTO/RPO | Compliance | P1 |
| No DR test evidence | Compliance | P1 |
| No validation steps between phases | Process | P2 |
| Log shipping detection by description (fragile) | Operations | P2 |
| SET SINGLE_USER without application quiesce | Operations | P2 |
| No parallel execution tooling (all serial) | Operations | P3 |
| No automated post-failover smoke tests | Quality | P3 |

---

## Remediation Priorities

### Immediate (P1)
1. Audit all production SQL Server versions. If any instance is SQL Server 2019+, rewrite mirroring scripts as Always On Availability Group failover procedures immediately.
2. Move tail-log backup targets from co-located UNC shares to Azure Blob Storage or a separate, always-available file share. This is the single biggest gap for catastrophic failure scenarios.
3. Implement a secrets management solution for replication passwords. Remove `**replace_with_password**` pattern; replace with Key Vault retrieval.
4. Document RTO and RPO targets per database tier (critical/high/medium) and publish to stakeholders.
5. Schedule and execute a DR failover test. Document results, issues, and lessons learned.

### Short-Term (P2)
6. Add database-level validation queries between steps (e.g., confirm restore succeeded, confirm database is in MULTI_USER mode before proceeding to next step).
7. Replace description-based log shipping job detection with `msdb.dbo.log_shipping_primary_databases` and `log_shipping_secondary_databases` system tables.
8. Add application quiesce steps before `SET SINGLE_USER` commands.

### Longer-Term (P3)
9. Evaluate Azure SQL Managed Instance or SQL Server Always On Availability Groups as a replacement for the log shipping + mirroring architecture, providing automatic failover with documented RTO.
10. Implement automated DR health monitoring (Azure Monitor / SQL Server health checks) to reduce detection-to-escalation time.
11. Create a post-failover validation playbook with specific smoke tests for each critical application (card authorisation, order processing, fee invoicing).
