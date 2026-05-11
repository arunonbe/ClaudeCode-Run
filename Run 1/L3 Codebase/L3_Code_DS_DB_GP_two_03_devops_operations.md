# DS_DB_GP_two — DevOps & Operations Report

## 1. Project Build Configuration

| Attribute | Value | Source |
|-----------|-------|--------|
| Project type | SQL Server Database Project (SSDT) | `two.sqlproj` |
| MSBuild schema provider | `Microsoft.Data.Tools.Schema.Sql.Sql100DatabaseSchemaProvider` | `two.sqlproj` line 11 |
| Target SQL Server version | SQL Server 2008 (compatibility 100) | `two.sqlproj` line 11 |
| Target framework | .NET 4.5 | `two.sqlproj` line 20 |
| Output type | Database (DACPAC) | `two.sqlproj` line 12 |
| Deploy to database | True | `two.sqlproj` |
| Project GUID | `c4bbbd7f-0136-4e30-8a51-494c17c67359` | `two.sqlproj` line 10 |

## 2. Build Artifacts

- **DACPAC**: `bin/Debug/two.dacpac` or `bin/Release/two.dacpac`
- No `publish.xml` profile files present — deployment target parameters not committed.
- No solution-level pipeline configuration committed.

## 3. CI/CD Pipeline

**No CI/CD configuration files are committed to this repository.** The same Jenkins-based inference applies as for GP_EMXN:
1. GitLab commit triggers Jenkins build
2. MSBuild compiles SSDT project to DACPAC
3. `SqlPackage.exe` generates deployment report
4. DBA manual review gate
5. Controlled deployment to UAT, then PROD

The absence of a committed CI/CD pipeline configuration is a governance gap affecting change audit traceability.

## 4. Change Management

GP_two also lacks a `DeltaSql/` folder for incremental migration scripts. All changes are managed via DACPAC diff-and-deploy. Key risks:
1. **DACPAC drift**: If database was modified directly in production (hotfix, emergency DBA change), the DACPAC will generate destructive DROP/ALTER statements on next deployment.
2. **No per-change rollback**: Rollback requires full database restore from backup.
3. **GP patch dependencies**: Dynamics GP service packs may alter stored procedures; these must be captured back to source control.

## 5. Environment Configuration

Security principals reveal the environment topology for GP_two:

| Principal | Environment Role |
|-----------|-----------------|
| `NAM_PROD` | Production domain group — all production access |
| `NAM_svc_gp_prd` | Production GP service account (API/integration tier) |
| `NAM_sitescope_AD` | Production monitoring via HP SiteScope |
| `DYNGRP` | Application group for GP client users |
| `DYNWORKFLOWGRP` | Workflow module users |
| `RAPIDGRP` | Integration/automation accounts |

The absence of UAT-specific accounts suggests either:
- A separate UAT database exists with a different security configuration (not in this repo), or
- UAT uses the same credentials as production (a control gap).

## 6. Database Configuration Assessment

| Setting | Value | Risk Note |
|---------|-------|-----------|
| `CompatibilityMode` | 100 | **CRITICAL** — SQL 2008 EOL |
| `IsEncryptionOn` | False | **HIGH** — TDE not enabled |
| `AllowSnapshotIsolation` | False | **MEDIUM** — reader-writer blocking |
| `ReadCommittedSnapshot` | False | **MEDIUM** — shared lock contention |
| `PageVerify` | CHECKSUM | Good — corruption detection |
| `AutoShrink` | False | Correct |
| `IsChangeTrackingOn` | False | **HIGH** — no audit trail |
| `AnsiNulls` | False | **MEDIUM** — non-standard SQL behaviour |
| `QuotedIdentifier` | False | **MEDIUM** — compat concern |
| `DelayedDurability` | DISABLED | Correct for financial data |

(Settings inferred from `two.sqlproj` matching the same DSP and property pattern as `emxn.sqlproj`.)

## 7. Security Model Quality

GP_two has a **significantly better security posture** than GP_EMXN in terms of access model:
- **No individual named SQL logins** — only group and service account logins
- Group-based access via `DYNGRP`, `DYNWORKFLOWGRP`, `RAPIDGRP`
- Report-role separation (`rpt_accounting manager`, `rpt_payroll`, etc.)
- Service account segregation (`NAM_svc_gp_prd` for integrations)

This is consistent with PCI DSS Requirement 7 (need-to-know) and closer to Requirement 8 (unique IDs). The remaining gap is confirming that `NAM_PROD` Windows group membership is actively governed.

## 8. Operational Risks

| Risk | Severity | Description |
|------|----------|-------------|
| SQL 2008 compatibility level | **CRITICAL** | EOL; missing 16 years of performance and security improvements |
| TDE not enabled | **HIGH** | Employee SSN and financial data unencrypted at rest |
| No CI/CD pipeline | **HIGH** | Manual deployments; no automated change audit trail |
| No DeltaSql rollback scripts | **MEDIUM** | Per-change rollback requires full restore |
| DACPAC drift risk | **MEDIUM** | Emergency hotfixes may not be captured in source control |
| 15,923 stored procedures | **MEDIUM** | Long DACPAC diff times; risk of unintended drops |
| ANSI settings disabled | **MEDIUM** | Non-standard T-SQL behaviour |

## 9. Monitoring

Security roles indicate:
- `NAM_sitescope_AD` — HP SiteScope monitoring agent (availability/performance)
- FortiDB is not explicitly present in GP_two Security folder (unlike GP_EMXN which has `FortiDBRptRole`). **This is a potential DAM coverage gap** — confirm whether FortiDB is configured at the SQL Server instance level for GP_two.

## 10. Backup and Recovery

Same recommendations as GP_EMXN:
- Full backup: Daily minimum
- Transaction log backup: Every 15 minutes
- Backup tested restore: Monthly
- RTO: ≤ 4 hours; RPO: ≤ 1 hour

The `DS_DB_database_maintenance` repository is expected to house maintenance plans for all GP databases including GP_two.
