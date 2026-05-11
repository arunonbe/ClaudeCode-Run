# api-config-repo — DevOps & Operations View

## Build & Packaging

This repository contains **no build artifacts, no pom.xml, no Gradle files, and no compiled code**. It is a pure configuration repository. There is no build or packaging step. All files are consumed as-is by application servers at runtime.

The `config/` directory is the deployable unit. The GitHub Actions workflow uploads its entire contents to an Azure Storage File Share.

## Deployment

### Deployment Mechanism
A GitHub Actions workflow (`.github/workflows/file_share_sync.yml`) deploys configuration on every push to `master`:

1. Checks out the repository.
2. Installs Azure CLI via `apt-get`.
3. Authenticates to Azure Storage using `STORAGE_ACCOUNT_KEY` (injected from GitHub secret `STORAGE_ACCOUNT_KEY`).
4. Storage account: `ecntqastorgage` (note: apparent typo — likely `ecntqastorage`).
5. File share: `east-soap-config`.
6. Deletes all existing files from the share (`az storage file delete-batch`), then uploads the full `config/` directory (`az storage file upload-batch`).

**Risk**: The delete-then-upload pattern creates a window during which no config files exist on the share. If an application server reads config during this window, it will fail. There is no blue/green or atomic swap mechanism.

### Deployment Trigger
- Push to `master` branch (all paths in `config/`).
- Pull requests to `master` also trigger the workflow (potentially uploading PR branch configs to the shared QA environment).
- Manual `workflow_dispatch` trigger is available.

### Target Environment
All property values reference QA/stage hostnames (`q-db01.nam.wirecard.sys`, `login-qa.northlane.com`, `qa.nam.wirecard.sys`, `B2CSTAGE` agent names). This repository as cloned represents the **stage/QA environment** configuration. Production configuration files (if they exist) are not present in this clone.

### Runtime Config Consumption
Application servers mount the Azure File Share (`east-soap-config`) at a local path (referenced in properties as `D:/c-base/config/` or `/c-base/config/`). Services read properties from this shared path on startup and (for some services) at runtime.

## Configuration Management (Services Configured)

The following services have configuration stored in this repository, organised under `config/config/`:

| Directory | Service | Config Files |
|---|---|---|
| `accountmanagementapi/` | Account Management API | accountmanagementapi.properties, APIValidation.properties, api-security.properties, service.monitor.properties, log4j2.xml, OrderService_Connection.xml, postman_collection.json |
| `account-management/` (root) | Account Management API (alternate/legacy path) | application.properties |
| `clientapi/` | Client API (Instant Issue) | clientapi.properties, api-security.properties, accountmanagementapi.properties, service.monitor.properties, log4j.xml, log4j2.xml, OrderService_Connection.xml, postman_collection.json |
| `CSWS/` | Card Services Web Service (v1 and v3/Payout) | applicationContext-CSWS.properties, applicationContext-V1.properties, log4j2.xml, log4j2-Payout.xml, log4j2-V3.xml |
| `debitapi/` | Debit API | debitapi.properties, debitapi.xml, log4j.xml, log4j2.xml |
| `ivrws/` | IVR Web Service | ivrws.properties, precheck-ws.properties, log4j.xml, log4j2.xml |
| `cardnotification/` | Card Notification Service | CardNotification.properties, log4j.xml, log4j2.xml |
| `AcceptPrechecks/` | Accept Prechecks Service | AcceptPrechecks.properties, log4j2.xml, postman_collection.json |
| `FDVSPrecheck/` | FDVS Precheck (IVR check management) | precheck-ws.properties |
| `oneplatform/` | OnePlatform (Cardholder portal) | applicationContext-oneplatform.properties, migratedPrograms.properties, timeout-config.properties, multiple log4j XML variants |
| `op508/` | OnePlatform 508 (ADA-accessible portal) | applicationContext-op508.properties, applicationContext-op508.mfaOn.properties, timeout-config.properties, log4j.xml |
| `enroll/` | Enrollment / GE Portal | applicationContext-enrollment.properties, applicationContext-enrollment.mfaOn.properties, service.monitor.properties, log4j.xml |
| `cz/` | ClientZone (client administration portal) | clientzone.properties, clientzoneHub.properties, clientzone-03092021.properties, clientzonebackup.properties, edeliveryrequest.properties, messagecenter.properties, monitor.properties, login_page_alert_message.properties, debitapi.xml, log4j.xml, order-SynchronousCommunication.xml |
| `csa/` | Card Services Admin | applicationContext-csa.properties, build.properties, dropDownsData-csa.properties, log4j.xml, log4j_Public.xml |
| `rebate-cardinquiry/` | Rebate Card Inquiry | rebate.properties |
| `core2/ecountcore/` | eCount Core service | ecountcore.properties, FDRConfig.properties, debitServices.properties, debitServices.xml, fdrods.xml, states.xml, log4j.xml, log4j2.xml |
| `core2/Strongbox/` | Strongbox (crypto key service) | config.properties, system.properties, log4j.xml, log4j2.xml |
| `core2/profile/` | Profile service | system.properties, log4j.xml, log4j2.xml |
| `inventoryMgmt/` | Inventory Management | InventoryMgmt.properties, InventoryMgmtBatchClient.properties, AutoreorderExpirationLog4j.properties, InvEmailNotifyLog4j.properties, PopulateShippingInfoBatchLog4j.properties |
| `service/account/` | Account service | account.properties |
| `service/autofile/` | Autofile service (bulk disbursement) | autofile.properties, autofile.client.properties, log4j.properties |
| `service/banker/` | Banker service | banker.properties, banker.client.properties |
| `service/directory/` | Directory service | directory.properties |
| `service/edelivery/` | eDelivery service | edelivery.properties |
| `service/httpCryptoService/` | HTTP Crypto service (PGP) | httpCryptoService.properties |
| `service/job/` | Job service | database.properties |
| `service/jobAgent/` | Job Agent service | JobAgentSVC.properties |
| `service/jobManager/` | Job Manager service | JobManagerSVC.properties |
| `service/jobscheduler/` | Job Scheduler service | jobscheduler.properties, log4j.properties |
| `service/message/` | Message Centre service | message.properties |
| `service/mfa/` | MFA service | mfa.properties |
| `service/notificationStrategy/` | Notification Strategy (mailer, event handler, rules engine) | notification.properties, mailer.properties, smtp.email.channel.properties, eventHandler.properties, rulesEngine.properties, rulesengine.client.properties |
| `service/order/` | Order service | service.properties, service.jms.properties, service.jms.ibmmq.properties, service.jms.tibco.properties, service.monitor.properties, database.properties, notificationClient.properties, roll.properties |
| `service/payment/` | Payment service | payment.properties |
| `service/prepaidJms/` | Prepaid JMS configuration | ibmmqjms.properties, tibcojms.properties |
| `service/repository/` | Repository service | repositorysvc.properties, service.properties, log4j.properties |
| `service/request/` | Request service | core.addenda.properties, database.properties, service.jms.ibmmq.properties |
| `dfapiclient/` | DFAPI client (Citi wire/ACH) | httpclient.properties, jms.properties |
| `IEFTRules/` | IEFT international transfer rules (60+ country XMLs) | IEFTCountries.xml, CommonRules.xml, DefaultValues.xml, AcceptedRules.xml, CountrySpecificRules.xml, USDCountries.xml, USDInternationalRules.xml, + 50 country-specific rule XMLs |
| `postman/` | Postman test collections | collections (10 API collections), environments/qa_environment.json |
| Root datasource files | Shared JDBC datasources | cbaseapp-ds.properties, cbaseappsubaru-ds.properties, ecountcore-ds.properties, ecount-db.properties, greatplains-ds.properties, jobsvc-ds.properties, order-ds.properties, request-ds.properties, director-client.properties, ecount-config.xml |

## Observability

### Logging
Each service has one or more Log4j / Log4j2 XML configuration files:
- Log4j2 XML files (`log4j2.xml`) are present for all major services.
- Some services retain both Log4j 1.x (`log4j.xml`) and Log4j2 (`log4j2.xml`) configurations, suggesting in-progress migration.
- CSWS has three Log4j2 variants: standard (`log4j2.xml`), payout-variant (`log4j2-Payout.xml`), and v3 variant (`log4j2-V3.xml`).
- Inventory management has separate log4j configs per batch process (auto-reorder, email notify, populate shipping info).
- `LocalLoggingLevel=DEBUG` and `RemoteLoggingLevel=DEBUG` are set in `ecount-config.xml`, indicating DEBUG-level logging is active — a potential PCI DSS concern (verbose logs may capture sensitive data).
- Syslog target: `localhost` (local syslog only in this config; no centralised SIEM endpoint configured here).

### Health Monitoring
`service.monitor.properties` files provide SQL-based health probes:
- Row existence checks on `order_detail`, `request_detail`, `job_account_map`, `fdr_profile_symbols`, `program_promotion`.
- Core service health checks probe eTransfer, eDevice, eMemeber, and ProfileService via Director agent (`B2CSTAGE`).
- Strongbox health check uses a reference ID (`V100146DF10014A5AC00000001`).

### Circuit Breakers
Resilience4j circuit breaker settings are configured for:
- `accountmanagementapi`: failure rate threshold 5%, wait 30s, slow call threshold 30s, min 5 calls.
- `ecountcore` (in CSWS): same parameters.
- `order service`: same parameters.

### No Metrics / Tracing Config
No APM agent configuration (Dynatrace, AppDynamics, OpenTelemetry), distributed tracing, or metrics export configuration is present in this repository. Observability appears limited to log files and SQL health probes.

## Infrastructure Dependencies

| Component | Connection Details (from config) |
|---|---|
| SQL Server (primary) | q-db01.nam.wirecard.sys:2431, q-db01.nam.wirecard.sys (db01 instance) |
| SQL Server (secondary) | q-db02.nam.wirecard.sys (db02 instance), q-db02.stage.ecount.com:2112 |
| IBM MQ | Q-MQ01:51516, queue manager Q_NA_MQ_HA, channel WD.FDR.SVRCONN |
| TIBCO EMS | gtstibemsuat.nam.nsroot.net:50643 (UAT) |
| Director Service | directorsvc.onbe.io (service registry / dispatch) |
| eCount Core Service | ecountcoresvc.onbe.io |
| Order Service | ordersvc.onbe.io |
| Banker API | bankerapi.onbe.io |
| Strongbox XMLRPC | strongboxxmlrpcsvc.onbe.io |
| Crypto Key Service | cryptokeysvc.onbe.io |
| Notification Subscriber | notificationsubscribersvc.onbe.io |
| Notification Rules Engine | notificationrulesenginesvc.onbe.io |
| Job Scheduler | schedulersvc.onbe.io |
| Job Scheduler Callback | jobschedulersvc.onbe.io |
| Autofile Service | autofilesvc.onbe.io |
| Message Centre | messagecentersvc.onbe.io |
| CMS / Cardholder Portal | login-qa.northlane.com (QA), ppnaut.nam.wirecard.sys (internal) |
| FiServ Debit API | localhost:8082 (sidecar pattern in current config) |
| Citi DFAPI SOAP | citigroupsoauat.citigroup.com (UAT) |
| Citi eDelivery SOAP | edvap1p (PRODUCTION endpoint in config) |
| Citi MFA | ctimfa.stg.nam.citigroup.net |
| Citi RSA Adaptive Auth | nariskuat.wlb3.nam.nsroot.net |
| Azure App Configuration | appcs-shared-qa-ss.azconfig.io |
| Azure Storage | ecntqastorgage (File Share: east-soap-config) |
| Mailgun | smtp.mailgun.org:587, api.mailgun.net |
| Sinch/SAP SMS | eu.sms.sdi.sinch.com |
| KYC Portal API | app-activationportalapi-qa-westus2-001.azurewebsites.net |
| Google reCAPTCHA | google.com/recaptcha |
| Western Union | westernunion.com |
| Biocatch (fraud scoring) | api-osiristest.us.v2.customers.biocatch.com (switch OFF) |
| CBTS (Cross-Border Transfer) | cbts-web-qa.amer1.wirecard.com |
| Microsoft Entra (OAuth) | login.microsoftonline.com/c5b749f2... (KYC app) |

## Operational Risks

1. **Atomic deployment gap**: The `delete-batch` + `upload-batch` deployment strategy leaves a window where the file share is empty. Applications reading config during this window will fail.
2. **Single-environment config**: All configs are QA/stage. There is no separation of environments in the repository structure (no `prod/`, `dev/` subdirectories). Production configs appear to be managed separately or not at all in this repo — creating a documentation gap.
3. **Production endpoint leak**: `edelivery.properties` active (uncommented) config points to `edvap1p` (production eDelivery SOAP). This could cause QA/stage services to invoke production Citi eDelivery endpoints.
4. **Hard-coded filesystem paths**: Multiple configs reference `D:/c-base/` (Windows) or `/c-base/` (Linux), indicating a legacy on-premises deployment model. Cloud-native deployments would need path externalisation.
5. **WebLogic dependency remnant**: `csa/build.properties` references WebLogic (`bea900/weblogic90`) as the application server — a very old dependency suggesting legacy WAR deployment for CSA.
6. **Log4j 1.x present**: Several services still have Log4j 1.x XML config files, which reached end-of-life. Log4Shell (CVE-2021-44228) applicability should be verified for all Log4j2 configs.
7. **DEBUG logging in production config**: `ecount-config.xml` sets `LocalLoggingLevel=DEBUG` — this could log sensitive card/PII data to log files.
8. **No secrets rotation mechanism**: No vault integration (HashiCorp Vault, Azure Key Vault) is referenced for runtime secret injection. All secrets are static in files.

## CI/CD

| Workflow | File | Trigger | Action |
|---|---|---|---|
| File Share Upload | `.github/workflows/file_share_sync.yml` | Push/PR to master; workflow_dispatch | Uploads `config/` directory to Azure Storage File Share `east-soap-config` on account `ecntqastorgage` using storage account key from GitHub secret |
| CodeQL Analysis | `.github/workflows/codeql.yml` | Push/PR to master; weekly schedule (Friday 22:19 UTC) | Delegates to `Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main` with Java runner on ubuntu-latest |

**Observations:**
- No unit tests, integration tests, or validation pipeline steps exist for config changes before deployment.
- No diff-review automation or policy-as-code checks (e.g., for detecting new hardcoded secrets) are configured.
- CodeQL is configured but runs on Java code — this is a config-only repo with no Java source, so CodeQL will produce no meaningful results unless it is scanning the shared workflow template.
- Pull requests to master trigger the file share upload, meaning unmerged PR configs can be deployed to the shared QA environment — a significant operational risk.
