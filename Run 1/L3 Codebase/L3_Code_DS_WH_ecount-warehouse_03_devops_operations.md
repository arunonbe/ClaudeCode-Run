# DS_WH_ecount-warehouse — DevOps & Operations Report

## Build System

The `DS_WH_ecount-warehouse` repository is a **Microsoft SQL Server Data Tools (SSDT)** project, not a Maven or Gradle project. There is:
- No `pom.xml`, `build.gradle`, or `package.json`
- No CI/CD pipeline configuration (no `.gitlab-ci.yml`, no GitHub Actions workflow)
- No Dockerfile or containerization artifacts
- No deployment scripts

The solution file `ecount.warehouse.sln` is a Visual Studio solution file that groups the SSAS project (`Prepaid_DW_OLAP/Prepaid_DW_OLAP.dwproj`) and multiple SSRS report projects (`.rptproj` files in each `reports.*` folder).

---

## Deployment Model

### SSAS Deployment
SSAS Multidimensional projects are deployed using one of:
1. **Visual Studio SSDT "Deploy" action** — builds and deploys directly to a named Analysis Services server
2. **XMLA deployment scripts** — generated from `.dwproj` build output and executed via SQL Server Management Studio (SSMS) or SQLCMD
3. **SSAS Deployment Wizard** — GUI tool for managed deployment

Based on repository structure, there is no automated deployment — deployments are presumed to be **manual** and performed by a DBA or BI developer. This creates the following operational risks:
- No audit trail of who deployed what and when
- No rollback mechanism (SSAS does not support transactional deployment rollback)
- No deployment environment promotion gates (dev → UAT → prod)

The presence of `reports.uat/` and `reports.uat.Pre-Production Test/` folders suggests a UAT pre-production test environment exists, but the promotion path to production is not automated.

### SSRS Report Deployment
Reports (`.rdl` files) are deployed to a SQL Server Reporting Services server. The `.rds` data source files (`Prepaid Warehouse.rds`, `cf_report 4A1.rds`, `Prepaid_transactions.rds`) contain connection strings pointing to the warehouse database. These connection strings in the `.rds` files are plaintext in the repository:

- `reports.Client Services Reports/cf_report 4A1.rds` — references `cf_report` database (likely `DS_DB_cf_report`)
- `reports.Client Services Reports/Prepaid Warehouse.rds` and `Prepaid_transactions.rds` — reference the prepaid warehouse database

**Credential management risk**: If the `.rds` files contain embedded usernames/passwords for the warehouse database connection, they represent secrets committed to source control. These files should be audited.

---

## SSAS Cube Processing

Cube processing (full or incremental) is a scheduled operational task. Based on the cube structure:
- Full processing would require several hours given the volume (partition files up to 356 KB suggest large data volumes)
- Incremental processing is likely scheduled nightly or hourly via SQL Server Agent jobs
- The `Process Date.dim` dimension confirms that processing is tracked by date

There is no visible SQL Agent job definition, SSIS package, or scheduling configuration in this repository. The ETL/processing schedule is managed externally (likely in `DS_ETL_warehouse` repo).

---

## Operational Risks

### 1. No CI/CD Pipeline — **Critical**
Zero automation for build, test, or deployment. Any schema change requires:
- Manual SSDT build on a developer workstation
- Manual deployment to production SSAS server
- No peer review gate enforced at deployment time

This violates change management requirements for PCI DSS Requirement 6.4 (change management process for production deployments).

### 2. No Automated Testing
No test definitions for:
- Cube dimension key integrity (orphan dimension members)
- Measure calculation accuracy
- Report parameter validation

Schema changes in the underlying `prepaid_warehouse` database can break cube processing silently.

### 3. Stale Schema (Last Updated 2017)
The DSV last schema update is `2017-06-05` (`Prepaid Warehouse.dsv`, line 5). If the underlying `prepaid_warehouse` database schema has changed since 2017, dimension views may be silently returning incorrect data or failing to pick up new fields.

### 4. Report Data Source Credential Risk
The `.rds` files in each report project folder store database connection information. If these contain embedded SQL credentials, they represent:
- PCI DSS Requirement 8.3.1 violation (hard-coded passwords)
- GLBA Safeguards Rule violation (improper credential management)

### 5. SSAS Role Permissions — Limited Visibility
The only security role defined is `CubeReader.role`. There is no evidence of cell-level security, dimension-level security, or member filters to prevent cross-client data access. If `CubeReader` role members include external client portal service accounts, all clients could potentially query all programs' data.

### 6. No Partition Management Automation
The `Prepaid Transactions.partitions` file (356 KB) suggests multiple historical partitions exist. Partition maintenance (creating new monthly partitions, archiving old ones) appears to be a manual DBA task with no automation visible in this repository.

---

## Monitoring and Alerting

No monitoring configuration is present in this repository:
- No SSAS performance counters configuration
- No alerts for cube processing failure
- No query performance baselines
- No alerting for report delivery failures

Cube processing failures would result in stale data being served to all reports without notification to consumers. For a PCI DSS Level 1 service provider, the risk of presenting stale reconciliation data to the risk and finance teams is significant.

---

## Version Control Observations

- The `.gitignore` file is 6,384 bytes — indicates awareness of files to exclude, though SSAS `.bak` and processing log files should be confirmed as excluded
- No `CHANGELOG.md` or release notes
- The git history would be the only record of when SSAS schema changes were made
- Report file sizes range from 25 KB to 897 KB (`multiCAM.rdl`) — large reports may indicate embedded datasets or images that bloat the git history

---

## Recommendations

1. **Implement CI/CD using Azure DevOps or GitLab CI** — Use SSAS XMLA deployment scripts in a pipeline with environment gates (dev → UAT → prod)
2. **Externalize `.rds` data source credentials** — Use SSRS shared data sources with Windows Integrated Security or a secrets vault; remove any embedded credentials from `.rds` files committed to git
3. **Implement SSAS Role-Based Row-Level Security** — Add member filters to the Program and Access Level dimensions to enforce client data segregation
4. **Establish partition automation** — Create SQL Agent jobs or Azure Data Factory pipelines for monthly partition creation and historical partition archival
5. **Run SSAS Best Practices Analyzer** — Validate dimension key uniqueness, attribute relationships, and measure group bindings before next production deployment
6. **Document DSV refresh process** — The 2017-era DSV must be reconciled against the current `prepaid_warehouse` schema
