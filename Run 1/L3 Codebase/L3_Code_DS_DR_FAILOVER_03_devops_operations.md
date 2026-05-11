# DevOps & Operations Report — DS_DR_FAILOVER

## Repository Identity

**Repository:** DS_DR_FAILOVER  
**Deployment Model:** Fully manual — DBA executes scripts in order against specific SQL Server instances  
**CI/CD Pipeline:** None  
**Automation Level:** Zero — no automated failover, no monitoring integration

---

## Failover Execution Model

The failover procedure is entirely manual. A DBA must:
1. Open SQL Server Management Studio (SSMS)
2. Connect to each server in the correct order
3. Execute the scripts in step order (0010 → 0020 → 0030 → 0040 → 0050 → 0060 → 0070)
4. Manually substitute passwords in the replication script (`0060/002`)
5. Validate after each step

There is **no automation, no orchestration, no runbook tooling** (e.g., no Rundeck, no Ansible, no Azure Automation). This means the failover duration depends entirely on DBA speed and accuracy under pressure.

---

## Estimated Failover Steps and Timing

Based on the script contents, the approximate manual execution timeline:

| Step | Action | Est. Duration | Notes |
|---|---|---|---|
| 0010 | Disable log shipping jobs on all servers | 5–10 min | Cursor over all servers |
| 0020 | Take tail-log backups (7 servers) | 15–45 min | Dependent on database sizes and IO throughput |
| Transit | Copy backup files from prod UNC to DR | Variable | **Critical dependency** — if source server is down, UNC is unavailable |
| 0030 | Restore tail-log backups on DR (7 servers) | 20–60 min | Parallel per server possible |
| 0040 | Apply data patches (3 servers) | 5–15 min | Server name resets in config tables |
| 0050 | Setup mirroring (4 servers) | 15–30 min | Requires mirror endpoints to be configured |
| 0060 | Recreate replication (password substitution required) | 30–60 min | Most complex step; manual password entry |
| 0070 | Enable jobs on all DR servers | 5–10 min | Cursor-driven |
| **Total** | | **95–230 min** | **Estimated RTO: 1.5–4 hours** |

**No documented RTO or RPO targets are present in the repository.** This is a gap relative to PCI DSS Req 12.3.4, which requires documented and tested recovery procedures with time objectives.

---

## RPO Analysis

### Log Shipping RPO
RPO is determined by the log shipping interval — the frequency at which transaction logs are copied and applied to DR. The log shipping job frequency is not defined in this repository (it is defined in the SQL Server Agent jobs on the production servers). Based on typical enterprise log shipping configurations, intervals of 1–15 minutes are common, meaning RPO could be between 1 and 15 minutes of data loss.

However, the tail-log backup procedure (step 0020) is intended to capture the last committed transactions, bringing RPO close to zero — **if and only if the production server is accessible** to take the tail-log backup. If the server fails catastrophically (hardware failure, storage loss), the tail-log backup may not be possible.

### Database Mirroring RPO
For mirrored databases (`Ecountcore`, `Ordersvc`, `JobSvc`, `Cbaseapp`, `NotificationSvc`), synchronous mirroring provides near-zero RPO. Asynchronous mirroring provides RPO equal to the mirror lag.

---

## Operational Gaps and Risks

### CRITICAL RISK: Passwords Must Be Manually Entered at Failover Time

File: `0060_recreate_replication/002_pc-az2-db05_create_replication.sql`  
The replication script contains two plaintext password placeholders:
```
**replace_with_password**      -- distributor admin password
**replace_sqlsvc_password**    -- NAM\sql_svc service account password
```

During a DR event (likely under significant time and business pressure), a DBA must:
1. Know where to find these passwords (likely a password vault/PAM system)
2. Open the script file and find/replace the placeholders
3. Execute without accidentally committing the passwords to the Git repository

This is an operational anti-pattern. Passwords should be retrieved from a secrets manager at runtime, not embedded in a script even as placeholders. The risk of the script with real passwords being accidentally committed to source control is present at every failover test and actual event.

### HIGH RISK: UNC Backup Share Co-Located with Source Server

Tail-log backups are written to `\\<server>\shipping\` — the UNC share is hosted on the same server as the database. If the production server is physically unavailable (power failure, hardware failure, network partition), the UNC share is also unavailable and step 0030 (restore on DR) cannot proceed.

The design assumes a **graceful failover** (e.g., planned DR test or data centre migration) rather than a **catastrophic failure** scenario. In a true disaster, this architecture may not function as intended.

### HIGH RISK: Deprecated Database Mirroring Technology

SQL Server Database Mirroring was deprecated in SQL Server 2012 and fully removed from SQL Server 2019. The scripts in step 0050 configure mirroring for `Cbaseapp`, `NotificationSvc`, `Ecountcore`, `ECountCore_Service`, `Ecountcore_Process`, `Ordersvc`, and `JobSvc`. If the platform has been upgraded to SQL Server 2019 or later, these scripts will fail. This repository may be **out of date** with the actual production HA configuration.

### MEDIUM RISK: No Automated Failover Trigger

There is no automated mechanism to detect a production outage and initiate failover. The entire process depends on a human detecting the outage, escalating, obtaining authorization, and manually executing the scripts. This extends the effective RTO beyond the script execution time to include detection and escalation time.

### MEDIUM RISK: No Failover Validation Tests

No test execution logs, test schedules, or test procedures are documented in the repository. PCI DSS Req 12.3.4 requires periodic testing of recovery procedures. Without evidence of testing, the runbook's accuracy and completeness cannot be confirmed.

---

## DR Server Naming Convention

| Production | DR Counterpart |
|---|---|
| `p-az-db14` | `p-az2-db14` |
| `pc-db01` | `pc-az2-db01` |
| `pc-db02` | `pc-az2-db02` |
| `pc-db03` | `pc-az2-db03` |
| `pc-db05\PI_DB05` | `pc-az2-db05\pi_az2_db05` |
| `P-AZ-FS01` (file share) | `P-AZ2-FS01` |

The `az2` suffix indicates the DR servers are in a second Azure availability zone or region, which is a sound DR geography strategy. The naming is consistent and predictable.

---

## Log Shipping Job Management

Step 0010 disables log shipping jobs using:
```sql
where description like 'log shipping%'
```
This pattern relies on job descriptions being correctly set. If any log shipping job has a non-standard description, it will not be disabled, potentially causing data conflicts during restore. A more robust approach would use the `msdb.dbo.log_shipping_*` system tables directly.
