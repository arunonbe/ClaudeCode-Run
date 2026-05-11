# DevOps & Operations Report — DS_DP_db08

## Repository Identity

**Repository:** DS_DP_db08  
**Deployment Model:** Manual ad-hoc SQL script execution against production SQL Server instance  
**Change Tracking:** File-name date prefix + Jira ticket reference  
**CI/CD Pipeline:** None detected in repository  

---

## Build and Deployment Model

### No Automated Pipeline
DS_DP_db08 contains **no build files, no CI/CD configuration, no Jenkinsfile, no Azure DevOps YAML, no Flyway/Liquibase migration configuration, and no deployment scripts**. Every `.sql` file is a standalone, manually executed change script.

### Naming Convention as the Only Version Control
Scripts follow the pattern:
```
YYYYMMDD_<TICKET>_<DB><Description>.sql
```
This naming provides an implicit execution order by date, but there is **no enforced migration tracking table** (such as `schema_versions` or `migrations`). There is no way to programmatically determine which scripts have been applied to a given environment.

### Rollback Coverage
Rollback scripts are present for only two script pairs:
- `20191002_namdatasvc-1089_rollback_Can_UpdateLegalNameSalesVerticals.sql`
- `20191002_namdatasvc-1089_rollback_US_UpdateLegalNameSalesVerticals.sql`

All subsequent scripts (~90+ files) have **no corresponding rollback**. This is a significant operational risk: if a change causes production issues, manual reversal requires ad-hoc T-SQL authored under incident pressure.

---

## SQL Server Agent Jobs Managed

### DBMP - DBAdmin - Cleanup Audit_blocked_ip_user
| Property | Value |
|---|---|
| Job Name | `DBMP - DBAdmin - Cleanup Audit_blocked_ip_user` |
| Database | `DBAdmin` |
| Schedule | Weekly, Saturday at 05:00 AM |
| Retention | 90 days |
| Owner | `sa` |
| Notification | `DataServicesGroup-Operator` (on failure) |
| Source File | `20200917_WDNAMCBTS-517_003_SQLAgent-DBMP - DBAdmin - Cleanup Audit_blocked_ip_user.sql`, lines 19–75 |
| Environment Logic | `@enabled = CASE WHEN @@SERVERNAME LIKE 'C-%' THEN 0 ELSE 1 END` — auto-disables on servers with name prefix `C-` (likely QC/non-production) |

### SSIS Job Configuration Updates
Multiple scripts update `Banker.dbo.SSISJobConfigurations` for jobs:
- `SO Ordersvc` — Sales Order fulfilment via order service
- `SO Jobsvc` — Job service orchestration
- `SO Void` — Void processing
- `SO Fee Invoicing` — Fee invoice generation
- `SO Fee Invoicing ALL` — Bulk fee invoicing

These jobs are executed by the SQL Server Agent on the shard and interact with SSIS packages deployed on the instance. Email addresses are embedded in XML job parameters; the SMTP server was updated from `@wirecard.com` → `@northlane.com` domain in November 2020 (`SQ-124`).

---

## Certificate Management Operations
Two certificate thumbprint rotation scripts exist:
- `20191019_NATS-5490_UpdateCert_in_Banker_SSISJobConfigurations.sql` — rotates thumbprint from `9c 51 13 eb...` to `8c 79 b4 bf...`
- `20210923_NATS-12287_UpdateCert_in_Banker_SSISJobConfigurations.sql` — subsequent rotation

These are manual update scripts, not automated certificate lifecycle management. There is no evidence of automated certificate renewal or ACME/PKI integration.

---

## Environment Strategy

### Server Naming Pattern
From the agent job script (line 17):
```sql
@enabled = CASE WHEN @@SERVERNAME LIKE 'C-%' THEN 0 ELSE 1 END
```
Production servers do **not** start with `C-`. The `C-` prefix appears to designate a non-production (QC/dev) tier. This is the only environment differentiation logic found in the repository.

### No Environment-Specific Config Files
There are no `.env` files, no environment parameter files, and no SSIS project parameter overrides. Configuration is managed entirely through `SSISJobConfigurations` table entries, which must be updated separately per environment.

---

## Operational Patterns and Incidents

### Recurring GP Journal Deletion
The most frequent operation category is deleting unposted GP journal entries and sales transaction work table entries. These scripts appear at roughly quarterly intervals across 2019–2022:
- Mar 2020, Apr 2020, Jul 2020, Sep 2020, Nov 2020, Dec 2020, Jan 2021, Mar 2021, Apr 2021, Aug 2021, Feb 2022, Mar 2022

This frequency indicates a **systemic issue with GP batch posting** rather than isolated incidents. The root cause is not addressed in the repository. Each fix is a one-off script with no automated detection or prevention.

### Order Reset Operations
Scripts reset errored orders across the job service and order service tables:
- `20210411_DB08 reset errored orders...`
- `20210718_DB08 reset errored orders...`
- `20210907_NATS12151_DB08 reset errored orders...`
- `20210920_NATS12250_DB08 reset errored orders...`

This pattern suggests order processing failures requiring manual database intervention approximately every 1–3 months.

---

## Backup and Recovery

No backup scripts are present in this repository. Backup configuration is expected to be managed at the SQL Server instance level (maintenance plans or separate DBA tooling). The DR failover procedures for this shard's databases are managed in the separate `DS_DR_FAILOVER` repository.

---

## Monitoring and Alerting

- SQL Server Agent jobs notify `DataServicesGroup-Operator` on failure
- The `Audit_blocked_ip_user` table provides passive monitoring for blocked login attempts; no active alerting on that table is configured within this repo
- No Application Performance Monitoring (APM) integration is present

---

## Deployment Risk Assessment

| Risk | Severity | Description |
|---|---|---|
| No migration tracking | HIGH | Cannot determine applied state of any environment |
| No rollback scripts | HIGH | 90%+ of scripts have no reversal mechanism |
| Manual execution only | HIGH | Human error risk on every deployment |
| No CI/CD gate | MEDIUM | No automated testing before production deployment |
| SA-owned jobs | MEDIUM | SQL Agent jobs owned by `sa` rather than a service account; violates least-privilege |
| Recurring manual remediation | MEDIUM | GP journal deletion and order resets suggest unresolved upstream defects |
