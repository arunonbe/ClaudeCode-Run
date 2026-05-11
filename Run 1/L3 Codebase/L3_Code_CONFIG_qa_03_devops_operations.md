# DevOps / Operations View — CONFIG_qa

## Repository Role
Provides all externalised configuration files for the QA environment. Unlike DEV, QA has an active `.gitlab-ci.yml` that integrates with the ci-templates repo to automate config deployment.

## CI/CD Integration
```yaml
# .gitlab-ci.yml
include:
  - project: 'northlane/development/application-development/configuration/ci-templates'
    ref: 'SQ-4057-deploy-configuration-files'
    file: 'maven.gitlab-ci.yml'
variables:
  DEPLOY_PROPERTIES: 'true'
  DEPLOY_ENV: 'qa'
```
- Config deployment is automated via GitLab CI pipeline on pushes to this repo
- Uses a feature branch (`SQ-4057-deploy-configuration-files`) of ci-templates — not the `master` branch
- `DEPLOY_PROPERTIES=true` and `DEPLOY_ENV=qa` suggest a deployment mode specifically for config files (not artifact builds)

## Server Fleet (QA)
| Server | Notes |
|--------|-------|
| `q-na-app01` through `q-na-app09` | Primary app servers |
| `q-na-app12` | Additional app server |
| `q-na-bat02`, `q-na-bat03` | Batch servers |

QA has a larger fleet than DEV (12 app servers vs 4), reflecting production-like scale.

## Services Configured (q-na-app01/config/)
- `AcceptPrechecks/` — Accept prechecks (Certegy), agent=B2CSTAGE
- `CSWS/` — Card Services Web Service (V1 and CSWS contexts)
- `FDVSPrecheck/` — FDVS precheck
- `IEFTRules/` — Electronic funds transfer rules
- `accountmanagementapi/` — Account Management API
- `cardnotification/` — Card Notification SMS (SAP Mobile Services UAT endpoint active)
- `cbaseapp-ds.properties` — SQL Server cbaseapp datasource
- `cbaseappsubaru-ds.properties` — Subaru SQL Server datasource
- `clientapi/` — Client API
- `core2/` — Core2 (Strongbox, ecountcore, FDR config)
- `csa/` — Client Service Application (BioCatch, CBTS, KYC)
- `cz/` — ClientZone (MFA ON, B2CSTAGE agent, qa.northlane.com URLs)
- `debitapi/` — Debit API
- `dfapiclient/` — DFAPI JMS/MQ (UAT MQ queue manager)
- `director-client.properties` — Director dispatch (ppnaut server)
- `ecount-config.xml` — eCount configuration (present in QA, absent in DEV)
- `ecount-db.properties` — eCount database connection
- `ecountcore-ds.properties` — eCount core datasource
- `enroll/` — Enrollment (with and without MFA: `.mfaOn.properties` variant)
- `greatplains-ds.properties` — Great Plains ERP datasource
- `inventoryMgmt/` — Inventory management batch
- `ivrws/` — IVR web service (and precheck-ws)
- `jobsvc-ds.properties` — Job service datasource
- `oneplatform/` — OnePlatform (BioCatch enabled, CBTS, KYC, DFAPI config)
- `op508/` — OP508 application
- `order-ds.properties` — Order datasource
- `rebate-cardinquiry/` — Rebate card inquiry
- `request-ds.properties` — Request datasource
- `service/` — Sub-services (edelivery, job, mfa, message, etc.)
- `subaru-rewards/` — Subaru rewards
- `webcertomaha-ds.properties` — WebCert/Omaha datasource
- `xContent/` — Content management

Additional servers (`q-na-app02` through `q-na-app12`) hold the same or subset of service configs.

## Observability
No Filebeat input YAMLs found in CONFIG_qa (they would be under `{server}/filebeat_application.yml/`). The QA Filebeat config may be managed separately or may be absent. This is a potential gap vs DEV which has Filebeat inputs for all services.

GitHub Actions CodeQL workflow present (`.github/workflows/codeql.yml`).

## Infrastructure Dependencies
- SQL Server: `q-db01.nam.wirecard.sys:2431` — QA database server
- Director: `ppnaut.nam.wirecard.sys:8080`
- CMS: `login-qa.northlane.com:443`
- IBM MQ: `dflnxswmqu.nam.wirecard.sys:1414` (QM=`WLDF_UAT_QMGRS`)
- CBTS: `q-na-app08.nam.wirecard.sys:9443`
- BioCatch: `api-osiristest.us.v2.customers.biocatch.com`
- KYC Portal: `app-activationportalapi-qa-westus2-001.azurewebsites.net` (Azure)
- SAP Mobile Services: `sms-pp.sapmobileservices.com` (SMS gateway)

## Java Runtime
- JDK 1.8.0_265 and JDK (Java folder with unnamed version) present in `Java/` directory — same pattern as DEV

## Operational Risks
- Feature branch (`SQ-4057`) referenced in `.gitlab-ci.yml` — if that branch is deleted or diverges from master, QA config deployments fail
- JDK binaries in Git (large binary artifacts)
- No Filebeat input files found — if QA logging is not configured, log visibility in QA is degraded
- Same credential values as DEV for multiple services — credential rotation in one env requires rotation in both
- `cz/clientzonebackup.properties` suggests a manual backup/rollback practice is in use
- Enrollment MFA variant file (`.mfaOn.properties`) suggests manual config switching for MFA testing
