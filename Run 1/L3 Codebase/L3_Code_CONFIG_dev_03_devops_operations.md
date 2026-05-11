# DevOps / Operations View — CONFIG_dev

## Repository Role
Provides all externalised configuration files for the DEV environment. Files are deployed to `D:\c-base\config\` on each application server. Services read configuration at Tomcat startup from these paths.

## Server Fleet (DEV)
| Server | Role | Services Configured |
|--------|------|---------------------|
| `d-na-app01` | App server 1 | ClientZone (cz, cz5), ClientZoneHub, CSA, OnePlatform, OnePlatformHub, OP508, Enrollment, Payment, Scheduler, InventoryMgmt, RebateCardInquiry, AccountManagementAPI, DFAPI Client, DailyReport, IEFT Rules, RequestFileBulkCardGen, xContent, SubaruRewards, Workbench |
| `d-na-app02` | App server 2 | AcceptPrechecks, CSWS, FDVSPrecheck, Strongbox, AccountManagementAPI, CardNotificationSMSPull, ClientAPI, ConsumerLoad, DebitAPI, IVRWS, InventoryMgmt, Wizard, Workbench, xSSO, xSearch-XMLRPC, SubaruRewards, edeliveryapi |
| `d-na-app03` | App server 3 | Banker, CryptoKeySvc, EventHandler, Mailer, MessageCenter, OrderSvc, Payment, RulesEngine, Strongbox, Subscriber, UserManagement, repository, xSearchXMLRPC, xSSO (from Filebeat configs) |
| `d-na-app04` | App server 4 / Spring Boot | CBTS (Spring Boot, port 9443), JSValidator, AutoFile, Profile, ecount-core, jobAgent, jobManager, jobScheduler |
| `d-na-bat02` | Batch server | Batch processing services |

## Services Configured (Complete List by Config Folder)

### d-na-app01/config/
- `accountmanagementapi/` — Account Management API (region=INT, timeout settings, order service connection)
- `cbaseapp-ds.properties` — SQL Server datasource (cbaseapp DB)
- `clientzonehub/` — ClientZone Hub (PPSTAGE agent, citiprepaid.com URLs)
- `core2/Strongbox/` — Strongbox service connection config
- `csa/` — Client Service Application (CBTS client, KYC, delivery codes, MFA)
- `cz/` — ClientZone web portal (MFA OFF, B2CTEST agent, DEV URLs)
- `cz5/` — ClientZone 5 (mfaSwitch=ON, B2CTEST agent)
- `dfapiclient/` — DFAPI JMS/MQ client (IBM MQ to UAT REMIT queue)
- `director-client.properties` — Director dispatch service URL
- `enroll/` — Enrollment application (MFA OFF, DEV Tomcat URLs)
- `inventoryMgmt/` — Inventory management batch (card expiry, auto-reorder)
- `jobsvc-ds.properties` — Job service SQL Server datasource
- `oneplatform/` — OnePlatform app (Cambridge FX, CBTS, KYC, Western Union, reCAPTCHA)
- `op508/` — OP508 application context
- `ophub/` — OnePlatform Hub
- `order-ds.properties`, `request-ds.properties` — Order/Request datasources
- `payment/` — Payment service
- `rebate-cardinquiry/` — Rebate card inquiry
- `requestfile-bulk-card-gen/` — Bulk card request file generation
- `scheduler/` — Job scheduler
- `service/` — Sub-services (XContentAutomation, account, autofile, etc.)
- `subaru-rewards/`, `DailyReport/`, `IEFTRules/`, `xContent/` — Client-specific and content configs
- `workbench/` — Workbench portal

### d-na-app02/config/
- `AcceptPrechecks/` — Accept prechecks (Certegy), agent=B2CTEST
- `CSWS/` — Card Services Web Service (cbaseapp JDBC)
- `ConsumerLoad/` — Consumer load processing
- `FDVSPrecheck/` — FDVS precheck web service
- `Strongbox/` — Strongbox XML-RPC service config
- `accountmanagementapi/` — Account Management API
- `cardnotification/` — Card Notification SMS Pull (SMS disabled in DEV)
- `clientapi/` — Client API
- `core2/` — Core2 / ecount core
- `debitapi/` — Debit API
- `inventoryMgmt/` — Inventory management
- `ivrws/` — IVR web service
- `service/` — Various sub-services
- `wizard/`, `workbench/`, `xContent/`, `xSSO/`, `xSearch-xmlrpc/` — Portals and search
- `subaru-rewards/` — Subaru rewards program
- `edeliveryapi/` — Electronic delivery API

### d-na-app04/config/
- `service/cbts/application.yml` — Cross-Border Transfer Service (Spring Boot, SQL Server, Cambridge FX, Mailgun)

### d-na-bat02/config/ (batch)
- `HartfordFilesProcessor/`, `alg/`, `batch/`, `bulk/`, `hyundai/`, `sprint-raf/`, `thankyou/`, `w3c/`, `webcertomaha-ds.properties/` — Batch job configs for various client programs

## Configuration Management
- Files deployed to `D:\c-base\config\` on each Windows server
- Services read config at Tomcat startup — config changes require service restart
- No configuration management tool (Ansible, Chef, DSC) — manual file deployment
- GitLab CI integration present: `CONFIG_qa/.gitlab-ci.yml` references ci-templates for `DEPLOY_PROPERTIES=true` with `DEPLOY_ENV=qa` — suggests automated config deployment via CI exists (at least for QA)
- DEV may use a similar mechanism; no `.gitlab-ci.yml` found in CONFIG_dev itself

## Observability (Filebeat Inputs)
All application services have Filebeat input YAMLs configured under `{server}/filebeat_application.yml/` in this repo. Log data flows to Logstash/Kibana/ChaosSearch.

## Infrastructure Dependencies
- SQL Server: `d-na-db01.nam.wirecard.sys:2232` — DEV database server (legacy Wirecard DNS)
- Director service: `d-na-app01.nam.wirecard.sys:8080`
- CMS: `d-na-app03.nam.wirecard.sys:9001`
- Strongbox: `d-na-app03.nam.wirecard.sys:9301`
- IBM MQ: `gppswmqu:1514` (REMIT_QM.UAT) — **points to UAT MQ, not a DEV-specific MQ**
- Cambridge FX: `https://beta.cambridgelink.com` — third-party DEV/beta endpoint
- KYC Portal: `https://app-activationportalapi-qa-westus2-001.azurewebsites.net` — Azure QA endpoint
- Mailgun SMTP: `smtp.mailgun.org:587` — CBTS email for notifications
- GitHub Actions: CodeQL workflow present for code scanning

## Java Runtime
- JDK 1.8 and JDK 1.7.0.65 binaries present in `Java/` folder — JDKs committed to the repository
- Tomcat 8.5.57 referenced in JAVA_OPTIONS files (UAT repo)
- JVM flags use legacy GC (`-XX:+UseConcMarkSweepGC`, `-XX:MaxPermSize`) — Java 8 era

## Operational Risks
- Credentials committed to Git (see Data Architect view) — major security risk
- IBM MQ connection points to UAT queue — DEV messages may flow to UAT infrastructure
- KYC portal uses QA Azure endpoint from DEV — cross-environment boundary violation
- JDK binaries stored in Git — large binary artifacts inflate repo size
- Manual config deployment — no automated sync between Git and server filesystem in DEV
- Config changes require Tomcat restart — no hot-reload mechanism
