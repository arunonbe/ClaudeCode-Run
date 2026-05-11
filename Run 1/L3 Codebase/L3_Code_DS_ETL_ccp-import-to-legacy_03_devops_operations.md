# DS_ETL_ccp-import-to-legacy — DevOps and Operations Report

## 1. Build System

| Attribute | Value |
|-----------|-------|
| Project type | SSIS 2012 Project Deployment Model |
| Solution file | `ccp-import-to-legacy.sln` |
| Project file | `ccp.import2012.dtproj` |
| SSIS version | SQL Server 2012 SSIS (11.0.5058.0) |
| Output artefact | SSIS `.ispac` package (Integration Services Project Archive) |
| CI/CD pipeline | **None** — no `.gitlab-ci.yml`, no Jenkins pipeline |

The SSIS project is built with Visual Studio / SQL Server Data Tools (SSDT). Build produces an `.ispac` file deployable to the SSIS Integration Services Catalog (`SSISDB`).

---

## 2. Deployment Mechanism

**Inferred (no pipeline present):** Manual SSDT deployment or SSISDB catalog deployment.

Deployment steps:
1. Build `.ispac` in SSDT (Visual Studio with SQL Server Data Tools installed).
2. Deploy `.ispac` to SSISDB Catalog on the target SQL Server SSIS instance using the SSIS Deployment Wizard or `isdeploymentwizard.exe`.
3. Configure project-level parameters (`MailServerAccount`, `NotifyEmailAddress`) in the SSISDB catalog for each environment.
4. Configure environment references in SSISDB catalog (pointing to dev/QA/prod SQL Server connections).

**No automated deployment tooling** is present in this repository. No deployment scripts, PowerShell deployment automation, or CI/CD pipeline definitions exist.

---

## 3. Configuration Management

| Configuration Item | Location | Assessment |
|---|---|---|
| `MailServerAccount` | `Project.params` — value: `NoReply@wirecard.com` | Wirecard-era email; should be overridden in SSISDB environment config per environment |
| `NotifyEmailAddress` | `Project.params` — value: `namds@wirecard.com` | Wirecard-era notification address; must be reconfigured in SSISDB |
| Database connection | `CCP-SQLDB.conmgr` — `d-na-db01.nam.wirecard.sys\db01,2232` | Hardcoded server name; must be overridden via SSISDB environment reference |
| SMTP connection | `SMTP Connection Manager.conmgr` | SMTP server details for failure emails; server name not visible (binary `.conmgr`) |
| Source file paths | Hardcoded within `.dtsx` packages | `C:\ETL\In\WDCCP\` paths; must match actual SSIS server directory layout |

**Critical finding**: Both project parameters reference `wirecard.com` email addresses — the Wirecard organisational domain pre-dating Onbe rebranding. These must be updated to Onbe-managed addresses in production environments.

---

## 4. Observability

- **Failure notification**: Project parameter `NotifyEmailAddress` (`namds@wirecard.com`) receives emails when source files do not exist.
- **SSIS catalog logging**: SSIS built-in execution logging via `SSISDB` catalog (level configurable: `None`, `Basic`, `Performance`, `Verbose`).
- **No custom logging**: No Log4j, custom audit tables, or application-level logging is defined in visible package configurations.
- **No monitoring integration**: No SCOM alerts, SQL Agent job status monitoring, or third-party APM integration.
- **Operational visibility gap**: Without a monitoring dashboard, operators must query SSISDB execution views (`[catalog].[executions]`, `[catalog].[event_messages]`) to investigate failures.

---

## 5. Infrastructure Dependencies

| Dependency | Type | Details |
|-----------|------|---------|
| SSIS server | Compute | Windows Server with SQL Server Integration Services 2012 installed |
| `d-na-db01.nam.wirecard.sys\db01,2232` | SQL Server (staging) | `CCP` database — `nam.wirecard.sys` domain indicates Wirecard legacy network |
| `C:\ETL\In\WDCCP\` | File system | Source file drop location on SSIS server |
| `DS_CCP_ccp-export-to-legacy` | Upstream pipeline | Produces the flat files consumed by this pipeline |
| Legacy eCount (`ECNT`, `ECAN`) | Downstream | Receives imported data |
| SMTP server | Email | Failure notification delivery |
| Windows AD (`nam.wirecard.sys` domain) | Authentication | `Integrated Security=SSPI` on `CCP-SQLDB` connection |

**Dependency risk**: The connection manager references `d-na-db01.nam.wirecard.sys` — a server in the legacy Wirecard domain. If this server or domain has been decommissioned as part of Onbe's infrastructure migration, the pipeline cannot function.

---

## 6. Operational Risks

| Risk | Severity | Detail |
|------|---------|--------|
| No CI/CD pipeline | HIGH | Manual deployment; no automated testing or environment promotion enforcement |
| Wirecard-domain dependencies | HIGH | Server `d-na-db01.nam.wirecard.sys` and email `namds@wirecard.com` are Wirecard-era; may be decommissioned |
| SQLNCLI11.1 EOL driver | HIGH | SQL Server Native Client 11 reached end of support; security patches are not provided |
| SSIS 2012 version | HIGH | SQL Server 2012 is EOL (July 2022); no security patches |
| No data validation | HIGH | Packages lack row count checks, hash verification, or reconciliation against source |
| Source file path hardcoded | MEDIUM | `C:\ETL\In\WDCCP\` path hardcoded; breaks on server change |
| Single SMTP contact | MEDIUM | `namds@wirecard.com` — if this inbox is abandoned, failures are silently missed |
| No rollback mechanism | MEDIUM | No truncate-and-reload logic or rollback scripts for failed partial imports |
| Flat file encoding | MEDIUM | No explicit encoding declaration in visible config; non-ASCII characters in names may cause truncation |

---

## 7. CI/CD Assessment

**Current state**: No CI/CD.

**Recommended pipeline for SSIS projects**:

```yaml
stages:
  - build
  - validate
  - deploy-dev
  - deploy-qa
  - deploy-prod

build:
  script:
    - msbuild ccp-import-to-legacy.sln /p:Configuration=Release
  artifacts:
    paths:
      - ccp.import2012/bin/Release/*.ispac

deploy-dev:
  script:
    - powershell.exe -File scripts/Deploy-SSIS.ps1 -Environment dev -IsPackage ccp.import2012.ispac
  only:
    - develop
```

**Minimum viable improvements**:
1. SSISDB environment references must be created for dev, QA, UAT, and production — separating connection strings and email addresses from the project package.
2. Pre-deployment smoke test: verify source file exists before package runs.
3. Post-execution validation: row count check comparing source file row count to staging database import count.
4. Replace SMTP `namds@wirecard.com` with an Onbe-managed DL and configure at the SSISDB environment level.
