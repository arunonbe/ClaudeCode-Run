# Enterprise Architect Report — DS_DR_FAILOVER

## Repository Identity

**Repository:** DS_DR_FAILOVER  
**Platform Generation:** Legacy SQL Server HA/DR architecture (Generation 1)  
**Role in Architecture:** Business continuity layer — ensures payment platform resilience

---

## DR Architecture Overview

The DS_DR_FAILOVER repository represents the operational runbook for a **layered, multi-mechanism SQL Server DR architecture**:

```
PRODUCTION TIER (Azure AZ1 / On-Prem)     DR TIER (Azure AZ2)
====================================       ====================
p-az-db14 ──log shipping──────────────→  p-az2-db14
  (ECNT, ECAN, Banker, DYNAMICS, ATLYS)    (data patches applied post-restore)
  
pc-db01 ──log ship + mirror──────────→   pc-az2-db01
  (Ordersvc, JobSvc)                        
  
pc-db02 ──log ship + mirror──────────→   pc-az2-db02
  (Ecountcore, ECountCore_Service,
   Ecountcore_Process)

pc-db03 ──log ship + mirror──────────→   pc-az2-db03
  (Cbaseapp, NotificationSvc)

pc-db05/PI_DB05 ──log shipping───────→   pc-az2-db05/pi_az2_db05
  (CCP, RiskDB, ODS, EcountIds,           (becomes replication distributor)
   cf_report, ATLYS_*_R subscriber DBs)
```

This architecture covers **the entire Onbe SQL Server data estate** — all major processing databases, all reporting databases, and the supporting administration databases. This is comprehensive in scope.

---

## DR Coverage Analysis

### Services Covered by This Failover
The failover scripts protect:

| Service Category | Databases | Criticality |
|---|---|---|
| **Core card transaction processing** | Ecountcore, ECountCore_Service, Ecountcore_Process, EcountIds | CRITICAL |
| **Card order and job orchestration** | Ordersvc, JobSvc, Repositorysvc | CRITICAL |
| **Card program management** | ECNT, ECAN, CCP | CRITICAL |
| **Payment network/ACH** | ODS, Ordersvc | HIGH |
| **Financial accounting** | DYNAMICS, AcctgWf, Banker, Banker_NA | HIGH |
| **Reporting and analytics** | ATLYS_* (7 databases), cf_report, RiskDB, Analysis | MEDIUM |
| **Notifications** | NotificationSvc | MEDIUM |
| **International operations** | EMEAM, EMXN, TWO | MEDIUM |
| **Reference/support** | Cbaseapp, Vendor, RS2008 | LOW |

### Services NOT Covered by This Repository
Databases and services not appearing in the DR scripts but present in the broader Onbe codebase:
- Microservices databases (nexpay-*, account-management, etc.) — these likely have separate HA/DR through cloud-native mechanisms
- Application tier (APIs, web apps) — not in scope for SQL-level DR
- Azure platform services (Key Vault, Service Bus, etc.) — separately managed

---

## Multi-Mechanism Redundancy Assessment

### Mechanism 1: Log Shipping
**Strengths:** Simple, well-understood, works across SQL Server versions  
**Weaknesses:** Manual failover (no automatic); RPO depends on shipping interval; backup share co-location risk  
**Appropriate for:** Reporting databases, lower-criticality processing databases  

### Mechanism 2: Database Mirroring
**Strengths:** Automatic failover possible (with witness); tighter RPO than log shipping  
**Weaknesses:** Deprecated since SQL Server 2012; removed in SQL Server 2019; two-node (requires witness for auto-failover)  
**Appropriate for:** Transaction-critical databases requiring fast failover  
**Concern:** If the platform has been partially or fully upgraded to SQL Server 2019+, mirroring no longer works. The scripts should be replaced with Always On Availability Group equivalents.

### Mechanism 3: Transactional Replication (on DR side)
**Role:** After failover, ATLYS reporting databases on `p-az2-db14` publish to `_R` subscriber databases on `pc-az2-db05`. This restores the read-replica pattern used in production for reporting.  
**Concern:** Replication requires password substitution at failover time (security risk) and is the most complex component to restore.

---

## Architecture Debt — Mirroring vs. Always On

The DR architecture is built on **SQL Server Database Mirroring**, which reached end-of-life in SQL Server 2012 and was removed in SQL Server 2019. The recommended replacement is **Always On Availability Groups (AAGs)**, which provide:
- Automatic failover without a witness server
- Multiple readable secondary replicas
- Support for multiple databases in a single Availability Group (simplifying multi-database failover)
- Integration with Azure SQL Managed Instance / SQL on Azure VMs

Migrating from Mirroring to AAGs is a significant but well-documented process. The DR scripts would need to be completely rewritten for AAG failover.

---

## Geographic DR Strategy

The `az2` suffix on DR servers indicates Azure Availability Zone 2 as the DR target. This is consistent with Azure best practices for regional redundancy. However:
- Tail-log backup files are written to the **production server's UNC share**, not to Azure Blob Storage or a geographically redundant location
- A full data centre loss at the production site would make the UNC shares inaccessible
- True geo-redundancy requires backup files in a separate Azure region or Azure Blob Storage

---

## Business Continuity Maturity Assessment

| Dimension | Current State | Target State |
|---|---|---|
| Failover automation | Manual scripts | Automated with Azure Site Recovery or AAG auto-failover |
| RTO documentation | Not documented | Documented SLA per service tier |
| RPO documentation | Not documented | Documented SLA per service tier |
| DR testing | No evidence of testing in repo | Annual full DR test + quarterly partial |
| Backup accessibility | Co-located UNC shares | Azure Blob Storage or geo-redundant share |
| HA technology | Deprecated mirroring | Always On Availability Groups |
| Password management | Manual substitution in scripts | Azure Key Vault integration |
| Monitoring | No automated detection | Azure Monitor alerts + PagerDuty escalation |
