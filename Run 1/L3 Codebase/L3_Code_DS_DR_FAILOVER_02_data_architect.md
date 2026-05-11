# Data Architect Report — DS_DR_FAILOVER

## Repository Identity

**Repository:** DS_DR_FAILOVER  
**Scope:** SQL Server Disaster Recovery — covers multiple production SQL Server instances  
**DR Mechanism:** Log Shipping (primary) + Database Mirroring (secondary) + Transactional Replication (tertiary)

---

## Production Database Instance Inventory

The failover scripts reveal the following production SQL Server instances and their hosted databases:

### Instance: p-az-db14 (Azure VM — DB14)
**DR counterpart:** p-az2-db14

| Database | Business Purpose |
|---|---|
| `AcctgWf` | Accounting Workflow |
| `ATLYS_E` | Atlys Enterprise reporting hub |
| `ATLYS_Fc_NCA` | Forecast — Canada |
| `ATLYS_Fc_NUS` | Forecast — US |
| `ATLYS_FcCR` | Forecast variant |
| `ATLYS_Rv_NCA` | Revenue — Canada |
| `ATLYS_Rv_NUS` | Revenue — US |
| `ATLYS_RvCR` | Revenue variant |
| `DBAdmin` | DBA utilities |
| `DYNAMICS` | Microsoft Dynamics GP |
| `ECAN` | eCount Canada |
| `ECNT` | eCount North America (US) |
| `Banker_NA` | Banker NA |
| `Banker` | Back-office job config |
| `TWO` | GP Two company |
| `EMEAM` | EMEA Mexico operations |
| `EMXN` | Mexico entity |

**Source:** `0020_take_tail_log_backup/p-az-db14_take_tail.sql`

### Instance: pc-db01
**DR counterpart:** pc-az2-db01

| Database | Business Purpose |
|---|---|
| `Ordersvc` | Order service (prepaid card orders) — MIRRORED |
| `JobSvc` | Job service (batch orchestration) — MIRRORED |
| `DBAdmin` | DBA utilities |
| `jobsvc_rollback` | Job service rollback state |
| `Repositorysvc` | Repository service |
| `repositorysvc_rollback` | Repository rollback state |

### Instance: pc-db02
**DR counterpart:** pc-az2-db02

| Database | Business Purpose |
|---|---|
| `Ecountcore` | eCount core processing — MIRRORED |
| `ECountCore_Service` | eCount core service layer — MIRRORED |
| `Ecountcore_Process` | eCount processing — MIRRORED |

### Instance: pc-db03
**DR counterpart:** pc-az2-db03

| Database | Business Purpose |
|---|---|
| `Cbaseapp` | C-base application database — MIRRORED |
| `NotificationSvc` | Notification service — MIRRORED |

### Instance: pc-db05 (Named Instance: PI_DB05)
**DR counterpart:** pc-az2-db05\pi_az2_db05

| Database | Business Purpose |
|---|---|
| `Analysis` | Analysis/reporting |
| `Cbaseapp_Archive` | C-base archived data |
| `CCP` | Card/Client Processing Platform |
| `cf_report` | CF reporting database |
| `Dbadmin` | DBA utilities |
| `Ecountcore_Archive` | eCount core archived data |
| `EcountIds` | eCount identity/account IDs |
| `ODS` | Operational Data Store |
| `RiskDB` | Risk management |
| `RS2008` | Report Server 2008 |
| `RS2008TempDB` | Report Server temp |
| `Vendor` | Vendor data |
| `ECNT_R` | ECNT replication subscriber |
| `ECAN_R` | ECAN replication subscriber |
| `ATLYS_E_R` | ATLYS_E replication subscriber |
| `ATLYS_Fc_NCA_R` | ATLYS_Fc_NCA subscriber |
| `ATLYS_fc_NUS_R` | ATLYS_fc_NUS subscriber |
| `ATLYS_rv_NCA_R` | ATLYS_rv_NCA subscriber |
| `ATLYS_rv_NUS_R` | ATLYS_rv_NUS subscriber |

**Source:** `0020_take_tail_log_backup/pc-db05_take_tail.sql`; `0030_restore_tail_log_backup/pc-az2-db05_restore.sql`

---

## High Availability Architecture Map

```
PRODUCTION                              DR
==========                              ==

p-az-db14           ─(log ship)──→     p-az2-db14
  AcctgWf, ATLYS_*, ECNT, ECAN          (restore + data patches)
  Banker, DYNAMICS, etc.                 ↓ step 0060: recreate replication
                                          Publisher for ATLYS_* → R databases

pc-db01             ─(log ship)──→     pc-az2-db01
  Ordersvc, JobSvc  ─(mirror)───→      (NORECOVERY restore → add mirror)

pc-db02             ─(log ship)──→     pc-az2-db02
  Ecountcore*       ─(mirror)───→

pc-db03             ─(log ship)──→     pc-az2-db03
  Cbaseapp, NotifSvc─(mirror)───→

pc-db05/PI_DB05     ─(log ship)──→     pc-az2-db05/pi_az2_db05
  CCP, RiskDB, ODS, cf_report, etc.    (restore + become replication distributor)
```

**Three redundancy mechanisms in use simultaneously:**
1. **Log Shipping** — all databases; provides bulk RPO guarantee (log ship interval determines data lag)
2. **Database Mirroring** — selected OLTP databases (Ecountcore, Ordersvc, JobSvc, Cbaseapp, NotificationSvc); synchronous or asynchronous mirror for tighter RPO on critical transaction tables
3. **Transactional Replication** — ATLYS_* databases replicated from p-az2-db14 to _R subscriber databases on pc-az2-db05

**Note:** SQL Server Database Mirroring was deprecated in SQL Server 2012 and removed in SQL Server 2019. If the platform is on SQL Server 2019, mirroring may have been replaced by Always On Availability Groups, which this repository would not reflect.

---

## Sensitive Data in Scope During Failover

The following CDE-candidate databases are included in the failover scope:

| Database | Sensitivity | PCI DSS Relevance |
|---|---|---|
| `ECNT` | HIGH | Prepaid card processing ledger — potential PAN/account data |
| `ECAN` | HIGH | Canadian card processing ledger |
| `Ecountcore` | HIGH | Core card transaction processing engine |
| `CCP` | HIGH | Card/Client Processing Platform — card transaction data |
| `EcountIds` | HIGH | Account/identity store — card account identifiers |
| `ODS` | MEDIUM | Operational Data Store — aggregated transaction data |
| `RiskDB` | MEDIUM | Risk analytics including emboss history (card-adjacent) |

**All log shipping backup files** for these databases transit UNC paths (`\\server\shipping\`) over the internal network. The encryption status of these network paths (SMB signing, IPsec) is not visible from this repository.

---

## Backup File Storage Locations

| Server | UNC Share Path |
|---|---|
| p-az-db14 | `\\p-az-db14\shipping\` |
| pc-db01 | `\\pc-db01\shipping\` |
| pc-db02 | `\\pc-db02\shipping\` |
| pc-db03 | `\\pc-db03\shipping\` |
| pc-db05 | `\\pc-db05\shipping\` |
| pc-db01 (mirror) | `H:\Backups\` (local drive) |

The use of UNC shares hosted on the same server (`\\pc-db01\shipping\` backing up databases on `pc-db01`) means that a server failure that makes the database unavailable also makes the backup share unavailable. The tail-log backup files would not be accessible from the DR server if the source server is completely down. This is a significant **DR data access gap**.
