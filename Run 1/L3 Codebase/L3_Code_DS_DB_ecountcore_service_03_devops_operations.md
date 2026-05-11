# DS_DB_ecountcore_service — DevOps / Operations View

## 1. Build System

| Attribute | Detail |
|-----------|--------|
| Project type | SQL Server Data Tools (SSDT), Visual Studio `.sqlproj` format |
| Project file | `Ecountcore_service.sqlproj` |
| Solution file | `Ecountcore_service.sln` |
| MSBuild tool version | 4.0 |
| Schema provider | `Microsoft.Data.Tools.Schema.Sql.Sql110DatabaseSchemaProvider` (SQL Server 2012 compatibility) |
| Target framework | .NET 4.6.1 |
| Output type | Database (produces a DACPAC on build) |
| `DeployToDatabase` | `True` — build artefact targets a database directly |
| `SqlServerVerification` | `False` — compile-time SQL validation is disabled |
| `IncludeCompositeObjects` | `True` — cross-database object references are included in the model |

The SSDT project produces a `.dacpac` artefact which can be deployed via `SqlPackage.exe` or Visual Studio publish profiles.

---

## 2. CI/CD Pipeline

**No CI/CD pipeline configuration files are present in this repository.** There are no:
- GitLab CI `.gitlab-ci.yml` files
- Jenkins `Jenkinsfile`
- Azure DevOps `azure-pipelines.yml`
- GitHub Actions `.github/workflows/` directory

Based on the broader Onbe platform (see `CONFIG_ci-templates`, `CONFIG_jenkins-file` repos in the estate), deployments likely follow a Jenkins-based pipeline that consumes the DACPAC artefact and calls `SqlPackage.exe` for differential deployment. However, this is not confirmed from evidence within this repo.

**Gap**: Without a pipeline definition, there is no automated quality gate (SQL linting, drift detection, security scanning) before deployment to production.

---

## 3. Database Change Management

Changes to this database are managed through the SSDT model approach: developers modify `.sql` DDL files under `dbo/` (Tables, Stored Procedures, Functions), and the DACPAC diff engine calculates the migration script at deploy time. This is a **state-based** (declarative) deployment model.

Implications:
- No explicit migration versioning (no Flyway, Liquibase, or numbered migration scripts).
- No rollback scripts are present. Rollback requires deploying a previous DACPAC or manual reversal.
- The `development` branch is the working branch observed in the git log. It is not clear whether a `main`/`master` branch exists; only `development` is referenced in the packed-refs.

---

## 4. Environment Strategy

Based on the security files, the following environments / login types are present:
| Login Pattern | Environment |
|---------------|-------------|
| `NAM_UAT` | UAT / pre-production |
| `NAM_PPA_PRD_*` | Production application service accounts |
| `NAM_PROD_CPP`, `NAM_PROD_CPP_APAC` | Production — CPP / APAC teams |
| `emer_*` accounts (~17) | Individual developer/emergency access — production |

The presence of **individual developer SQL logins** (`emer_*`) committed to the Security scripts is a finding. These should be managed via Active Directory group membership rather than individual SQL logins, and emergency access should be time-boxed and audited.

---

## 5. Service Broker Operational Notes

| Topic | Detail |
|-------|--------|
| Queue activation | `TaskQueue` has activation enabled: `STATUS = ON`, `PROCEDURE_NAME = app_task_agent`, `MAX_QUEUE_READERS = 2` |
| Poison message handling | `POISON_MESSAGE_HANDLING(STATUS = OFF)` — disabled. A malformed message will not be moved to a dead-letter queue automatically; instead it will be retried until the queue is manually drained or the message times out. |
| Service Broker encryption | Disabled (`WITH ENCRYPTION = OFF`) in dialog conversations. Acceptable for intra-instance use, not acceptable for cross-instance. |
| Queue monitoring | No dedicated monitoring stored procedures are defined in this repo. Ops teams must query `sys.transmission_queue` and `sys.conversation_endpoints` manually. |

**Operational Risk — Poison Messages**: With `POISON_MESSAGE_HANDLING = OFF`, a message that consistently causes `app_task_agent` to fail (e.g. a malformed XML task) will block the queue reader, halting all batch processing (dormancy fees, escheatment). This is a high-severity operational risk.

---

## 6. CLR Assembly Deployment

The file `Assemblies/EcountUtility.dll` is committed as a binary to the repository. SSDT will deploy this assembly when the DACPAC is applied. Requirements:
- The SQL Server instance must have `clr enabled` set to 1 (`sp_configure 'clr enabled', 1`).
- The assembly must be signed and trusted, or the database must have `TRUSTWORTHY = ON` — the latter is a security risk.
- No source code for the assembly is present in the repo; any change to `programCount` behaviour requires a separate build pipeline.

---

## 7. Operational Risks Summary

| Risk | Severity | Detail |
|------|----------|--------|
| Dynamic SQL execution in task agent | Critical | `app_task_agent` calls `sp_executesql @taskstr` where `@taskstr` is extracted from a Service Broker message body. Any actor who can inject a message onto the queue can execute arbitrary T-SQL under the queue's `EXECUTE AS OWNER` context. |
| Poison message queue blockage | High | `POISON_MESSAGE_HANDLING = OFF` means a bad message blocks the activation chain indefinitely. |
| No CI/CD pipeline | High | Manual or undocumented deployment process; no automated regression or security gates. |
| Individual SQL logins in Security scripts | Medium | `emer_*` logins represent persistent individual access; access should be managed via AD groups. |
| TRUSTWORTHY / CLR dependency | Medium | CLR assembly deployment requires careful trust configuration; binary-only in repo means no source audit. |
| No log retention policy | Medium | `TaskLog` TEXT column will grow indefinitely. |
| Hard-coded cross-database three-part names | Low | Prevents portability to different SQL Server instances without code changes. |
