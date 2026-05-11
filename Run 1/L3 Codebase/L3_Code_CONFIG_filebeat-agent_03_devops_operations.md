# DevOps / Operations View — CONFIG_filebeat-agent

## Repository Role
Distributes the Filebeat 7.9.2 Windows agent binary and base configuration for all Onbe application/batch servers across DEV, QA, UAT, and PROD environments. This is the shared base; per-application log input files are stored in the environment-specific CONFIG repos.

## Services Configured
The base `filebeat.yml` configures the Filebeat agent itself. The agent ships logs for ALL services deployed on each server. Per-service input files (stored in CONFIG_dev/qa/uat/prod under `{server}/filebeat_application.yml/`) define which log paths are shipped for each service.

From the CONFIG_dev repo, services known to have Filebeat input configs include:

**d-na-app01 (app server 1 — DEV)**: ClientZone, CSA, DirectorSvc, Oneplatform, RebateCard, ServiceTester  
**d-na-app02 (app server 2 — DEV)**: AcceptPrechecks, AccountManagement, AccountManagementPayout, CardManagementCSAPIPayout, CardManagementCSAPIV1, CardManagementCSAPIV3, CardNotificationSMSPull, ClientAPI, DebitAPI, IVRWS, Wizard, Workbench  
**d-na-app03 (app server 3 — DEV)**: Banker, Cryptokeysvc, EventHandler, Mailer, MessageCenter, Ordersvc, Payment, RulesEngine, Strongbox, Subscriber, UserManagement, repository, xSearchXMLRPC, xSSO  
**d-na-app04 (app server 4 — DEV)**: JSValidator, autofile, Profile, ecount-core, jobAgent, jobManager, jobscheduler

## Installation Method
Manual / semi-manual:
1. Copy `D:\filebeat\filebeat-7.9.2\` folder to target server's `D:\` drive
2. Add `{APPLICATION_NAME}.yml` input files to `D:\filebeat\filebeat-7.9.2\inputs.d\`
3. Run `install-service-filebeat.ps1` (included in repo) to register Windows service
4. Restart Filebeat service from Windows Services

## Base Configuration (`filebeat.yml`)
| Setting | Value |
|---------|-------|
| Input discovery | `${path.config}/inputs.d/*.yml` |
| Output | Logstash `logstash.util.northlane.com:5044` |
| TLS CA | `d:/filebeat/pki/ca.crt` |
| TLS cert | `d:/filebeat/pki/filebeat.northlane.com.crt` |
| TLS key | `d:/filebeat/pki/filebeat.northlane.com.key` |
| TLS verify mode | **none** (server cert not validated) |
| Log level | info |
| Log retention | 10 files |
| Log path | `d:\filebeat\logs\filebeat` |
| Queue | 4096 events in-memory; flush at 512 events or 5s |
| Event filter | Drop JSON parse error events |

## Observability
- Filebeat's own operational logs written to `d:\filebeat\logs\`
- Kibana dashboards for ~40+ modules included in the repo (not customised) — stock Elastic dashboards for Apache, Nginx, IIS, MySQL, syslog, AWS, Azure, etc.
- No custom Onbe Kibana dashboards are included in this repo

## Infrastructure Dependencies
- Windows servers (all app servers across all environments)
- Logstash endpoint: `logstash.util.northlane.com:5044`
- PKI infrastructure: CA cert + client cert/key at `d:/filebeat/pki/`
- Windows service management

## CI/CD
- GitHub Actions CodeQL workflow (`.github/workflows/codeql.yml`) is present — provides static analysis scanning on pushes/PRs
- No deployment automation — install is manual

## Operational Risks
- **Filebeat 7.9.2 is severely outdated** — this version was released September 2020; multiple CVEs have been disclosed in Elastic stack components since then
- **`ssl.verification_mode: none`** — all Logstash endpoint certificates are trusted unconditionally; no protection against MITM
- **Manual deployment** — no automation for deploying updated configs or new input files; process is error-prone and undocumented beyond the README
- **Shared binary across all environments** — a change to the base config requires manual re-deployment on every server
- **PKI cert paths hardcoded** — cert expiry or path changes require config file update and service restart on all servers
- **No health monitoring** of the Filebeat service itself — if the Windows service crashes, logs stop shipping silently
