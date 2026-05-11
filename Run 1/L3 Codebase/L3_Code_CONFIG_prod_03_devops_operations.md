# DevOps / Operations View — CONFIG_prod

## Repository Role
Provides all externalised configuration files for the PRODUCTION environment on the Azure-hosted (`p-az-*`) production server fleet. This is the live production configuration for all cardholder-facing and client-facing services.

## Server Fleet (PROD)
| Servers | Notes |
|---------|-------|
| `p-az-app01` through `p-az-app21` | 21 production app servers |
| `p-az-app01a`, `p-az-app01b`, `p-az-app02a`, `p-az-app02b`, `p-az-app03a`, `p-az-app03b` | Sub-instances of primary servers (HA/cluster) |
| `p-az-bat02`, `p-az-bat03` | Production batch servers |

**Total**: 21 primary + 6 sub-instances + 2 batch = 29 server config directories.

The `p-az-*` naming convention indicates Azure-hosted infrastructure (vs `d-na-*` for DEV on-premises and `q-na-*` for QA on-premises). PROD runs in Azure.

## Services Configured (p-az-app01/config/)

| Service | Config Folder | Key Notes |
|---------|--------------|-----------|
| AcceptPrechecks | `AcceptPrechecks/` | `agent=B2C`, log4j |
| CSWS | `CSWS/` | V1 and CSWS variants, CMS via `login.northlane.com` |
| FDVS Precheck | `FDVSPrecheck/` | Production FDVS |
| IEFTRules | `IEFTRules/` | Electronic funds transfer rules |
| Account Management API | `accountmanagementapi/` | Production member IDs, KYC prod credentials, region=NA |
| Card Notification | `cardnotification/` | Production SMS program list, production SAP credentials |
| Client API | `clientapi/` | Production API, api-security |
| CSA | `csa/` | Production CBTS, BioCatch, KYC credentials |
| ClientZone | `cz/` | `mfaSwitch=ON`, `clientzone.mypaymentadmin.com`, `B2C` agent |
| Debit API | `debitapi/` | Production debit |
| DFAPI Client | `dfapiclient/` | **Production IBM MQ (`dofrmwpmq.nam.wirecard.sys`, DF_QM)** |
| Director client | `director-client.properties` | `ppazp.nam.wirecard.sys:8080` |
| Enrollment | `enroll/` | `mfa.required=Y`, production enrollment |
| Inventory Mgmt | `inventoryMgmt/` | Production inventory batch |
| IVRWS | `ivrws/` | Production IVR |
| OnePlatform | `oneplatform/` | **BioCatch production, KYC prod, CBTS prod credentials** |
| OP508 | `op508/` | OP508 app |
| OnePlatform Hub | `ophub/` | Hub config |
| Rebate Card Inquiry | `rebate-cardinquiry/` | Production rebate |
| Service sub-configs | `service/` | edelivery, job (DB, JMS, properties), message, mfa |
| SubaruRewards | `subaru-rewards/` | Subaru program |
| xContent | `xContent/` | Content management |

## Configuration Management
- **No `.gitlab-ci.yml` found** — no automated config deployment pipeline for PROD
- Config changes deployed manually to production servers
- `ecount-config.xml.erb` present — suggests Chef/ERB templating was used historically
- 21+ server directories must all be updated when a config change is made — high manual effort and drift risk

## Observability
- GitHub Actions CodeQL present (`.github/workflows/codeql.yml`) for static analysis
- No Filebeat input YAMLs found directly in this glob (may be in other server dirs)
- PROD Filebeat inputs referenced in CONFIG_filebeat-agent README

## Infrastructure (PROD — Azure)
- All servers: `p-az-*` — Azure-hosted VMs
- Production Director: `ppazp.nam.wirecard.sys:8080`
- Production CMS: `login.northlane.com:443`
- Production IBM MQ: `dofrmwpmq.nam.wirecard.sys:1414`
- Production internal CMS: `ppazp.nam.wirecard.sys:9001`
- Production CBTS: `ppazp.nam.wirecard.sys:9443` (HTTP internally)
- BioCatch production: `api-9a7a72ec.us.v2.we-stats.com`
- KYC production: `app-activationportalapi-prod-westus2-001.azurewebsites.net`
- SAP SMS production: `sms-pp.sapmobileservices.com/citi/citi_prepa31535/`
- Western Union: `www.westernunion.com`

## Java Runtime
- JDK 1.8.0_265 binary present in `Java/JDK-AWS-8/` directory — same as DEV/QA; JDK committed to Git
- Java 1.7.0.65 also present as `Java/Java/` — legacy Java 7 in production repository

## Operational Risks (HIGH SEVERITY)
- **Production credentials committed to Git** — single highest-risk finding; immediate rotation and vault migration required
- **No automated config deployment** — 21+ servers require manual updates; high drift risk
- **Java 7 binary in production repo** — indicates some production services may run on Java 7 (EOL 2015)
- **CBTS uses HTTP** for internal production traffic — unencrypted internal financial service
- **IVR appKey same value as UAT** — environment isolation failure
- **`CardNotification-UAT.properties` file in PROD folder** — file naming confusion in production config
- **`ecount-config.xml.erb` template** alongside regular `.xml` — mixed config management approaches
- **29 server directories** — extremely high config management burden without automation
