# DevOps / Operations View — DS_ETL_finance-gp

## Repository Overview

**Repo path:** `E:\OnbeEast363\repos\DS_ETL_finance-gp`
**Git branch:** `development`
**Remote:** `origin` (shallow clone)

---

## CI/CD Pipeline

**No CI/CD configuration is present.** This is the largest and most operationally critical of the six repos, yet it has no automated build, test, or deployment pipeline. All 18 packages must be manually deployed.

The financial criticality of this repo (ACH file generation, GL batch creation, client invoicing) makes the absence of automated deployment testing especially risky. A mis-deployed package in this repo could:
- Send incorrect ACH debits to client bank accounts
- Post incorrect GL journal entries to Great Plains
- Generate incorrect fee invoices

---

## SSIS Deployment Approach

**Package Deployment Model** (older model, NOT Project Deployment Model) for most packages in this repo, based on the presence of the `SSISConfigurations.conmgr` pointing to a `Banker` database configuration table. This indicates the classic SSIS 2008/2012 **package deployment with configuration tables** pattern.

Evidence: `SOFeeAggregation.dtsx` header shows `DTS:EnableConfig="True"` (line 9), indicating that package configuration is read from an external table at runtime. This is the older SSIS 2005/2008/2012 pattern, where a SQL table (`dbo.SSISConfigurations` or similar in the `Banker` database) overrides connection strings and variable values at execution time.

**Contrast with DS_ETL_database-maintenance and DS_ETL_finance:** Those repos use Project Deployment Model with SSIS catalog environments. This repo uses the older configuration-table approach. **This is a significant architecture inconsistency** — two different deployment models in the same ETL suite.

---

## Configuration Table Pattern

The `Banker.dbo.SSISJobConfigurations` table (referenced by `SOFeeAggregation.dtsx` parameter description: "Job Type passed from Loop Process. See Banker.dbo.SSISJobConfigurations") drives job orchestration. The `SSISConfigurations.conmgr` connects to this table.

This means:
- Runtime parameters are stored in the `Banker` database, not in SSIS catalog environment variables
- Changes to job types or billing periods require database table updates, not re-deployment
- The configuration table becomes an undocumented control surface — changes to it affect all packages without requiring code changes or deployment

**Operational risk:** The `Banker.dbo.SSISJobConfigurations` table is effectively part of the ETL's business logic but exists outside version control. There is no way to track changes to job configuration from git history.

---

## Environments

**Default server in connection managers (all .conmgr files):** `q-db03.nam.wirecard.sys` (Q = QA) and `q-db02.nam.wirecard.sys` (Q = QA).

**Project.params paths:**
- `FolderPath` = `\\d-na-stk01.nam.wirecard.sys\GP_Files\` — development-era path (d-prefix)
- `DirectoryPath` = `\\d-na-bat03.nam.wirecard.sys\C-Base\Runtime\Clients\GXS\inbound\` — development-era batch server

No separate prod/QA/dev configuration files are present. Production overrides must happen via SSIS configuration table entries in the production `Banker` database — which is not version-controlled.

---

## SQL Agent Job Scheduling

No SQL Agent job scripts are present. Expected scheduling based on business process:

| Package | Frequency | Bank Deadline |
|---|---|---|
| `CitiDirectACH.dtsx` | Daily | CitiDirect cut-off (typically 4–5 PM ET) |
| `CACitidirectACH.dtsx` | Daily | Canadian CitiDirect cut-off |
| `CitidirectDrawdown.dtsx` | Daily | CitiDirect drawdown window |
| `FeeInvoicingACH.dtsx` | Monthly or billing cycle | ACH same-day deadline |
| `FeeInvoicingDrawdown.dtsx` | Monthly | Drawdown batch window |
| `CPPLoopProcess.dtsx` | Monthly | Month-end billing close |
| `SOFeeAggregation.dtsx` | Called by CPPLoopProcess | N/A |
| `SOFeeInvoicing.dtsx` | Called by CPPLoopProcess | N/A |
| `SSIS_FDR.dtsx` | Daily | FDR file delivery (typically 6–8 AM) |
| `SSIS_GLBatchE.dtsx` | Monthly | GP accounting close |
| `ClientRefund.dtsx` | On-demand | Per refund approval |
| `PRD_CustomerBalance.dtsx` | Monthly | Month-end close |

---

## Failure Handling

### `CPPLoopProcess.dtsx` (orchestrator)
As a loop orchestrator reading from `Banker.dbo.SSISJobConfigurations`, failures in child packages are expected to propagate up and halt the loop, marking the SQL Agent job as failed.

### `SOFeeAggregation.dtsx`
Has a log file connection manager (`SOFeeAggregation.log` at `\\q-na-stk01.nam.wirecard.sys\GP_Files\`) and a text-file SSIS log provider (dtsx line 40: `DTS.LogProviderTextFile.3`). This means package execution events are logged to a flat file — a basic but functional audit trail.

### ACH packages
ACH failures are operationally critical — a missed CitiDirect submission window means delayed fund movement. These packages likely have error path logic and SQL Agent operator notifications (not visible from package headers alone).

---

## Alerting

- **SMTP Server connection manager** is present (`SMTP Server.conmgr`, 410 bytes) — email notifications are wired into at least some packages
- Log files written to `\\q-na-stk01.nam.wirecard.sys\GP_Files\` (text-file logging provider in SOFeeAggregation)
- SQL Agent job failure notifications provide backup alerting if configured

---

## Known Operational Risks

| Risk | Severity | Notes |
|---|---|---|
| No CI/CD for ACH/invoicing packages | Critical | Manual deployment of ACH file generators risks production errors |
| Configuration table not version-controlled | High | `Banker.dbo.SSISJobConfigurations` changes are untracked |
| Mixed deployment models (Project vs Package) | High | Operational confusion — two different deployment/configuration patterns in same ETL suite |
| Hardcoded local path in PrepaidDigitalInvoice | Medium | `D:\Jobs_Files\Outbound\` must exist on execution host |
| ACH time-sensitivity | High | Daily CitiDirect cut-off; failures require immediate escalation |
| FDR file dependency | Medium | SSIS_FDR waits for FDR settlement file; late delivery causes cascade failure |
| No encryption on GP file share outputs | High | GL batch files and ACH-related files on plaintext UNC shares |
| Development-era server names in connection managers | Medium | Q-prefix and d-prefix servers checked in; production overrides via SSIS config table |
