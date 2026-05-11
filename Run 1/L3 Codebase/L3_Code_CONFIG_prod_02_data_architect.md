# Data Architect View — CONFIG_prod

## Data Stores Configured

| Database / Store | Connection | Environment |
|-----------------|------------|-------------|
| `cbaseapp` (SQL Server) | Production SQL Server (inferred from `ppazp.nam.wirecard.sys` cluster) | PROD |
| `jobsvc` (SQL Server) | Production — referenced in scheduler.properties | PROD |
| `CBTS` (SQL Server) | CBTS app on production server | PROD |
| `ecount-config.xml` | `D:/c-base/config/ecount-config.xml` (on server) | PROD |
| IBM MQ (DFAPI) | `dofrmwpmq.nam.wirecard.sys:1414`, QM=`DF_QM` — **production remittance** | PROD |
| CMS (xContent) | `https://login.northlane.com:443/xContent` | PROD |
| Internal CMS | `http://ppazp.nam.wirecard.sys:9001` | PROD |
| CBTS service | `http://ppazp.nam.wirecard.sys:9443/cross-border-transfer-service` | PROD |
| Cambridge FX | Production endpoint (via CBTS application) | PROD |
| BioCatch | `https://api-9a7a72ec.us.v2.we-stats.com` — **production fraud API** | PROD |
| KYC Portal | `https://app-activationportalapi-prod-westus2-001.azurewebsites.net` — **production KYC** | PROD |
| Director dispatch | `http://ppazp.nam.wirecard.sys:8080/service/dispatch.asp` — **production Director** | PROD |
| SAP Mobile Services (SMS) | `sms-pp.sapmobileservices.com/citi/citi_prepa31535/` — **production SMS** | PROD |
| eDelivery | `config/service/edelivery/edelivery.properties` | PROD |
| Great Plains | Referenced in PROD batch config | PROD |

## Schema
Same `.properties` / Spring XML / `application.yml` patterns as DEV/QA. PROD adds:
- `ecount-config.xml.erb` — ERB template variant (suggests a configuration templating tool like Chef/Puppet/ERB was used at some point for production config generation)
- `cardnotification/CardNotification-UAT.properties` present in PROD folder (name suggests a UAT variant file was committed to PROD config — potential maintenance confusion)

## Sensitive Data Handling

**CRITICAL: Production credentials committed to source control. File locations listed; values not reproduced.**

1. **`config/p-az-app01/config/oneplatform/applicationContext-oneplatform.properties`**:
   - Production CBTS service username and password (different from DEV/QA CBTS credentials)
   - Production KYC Microsoft Azure AD OAuth client secret
   - Production BioCatch customer ID and endpoint
   - Production Western Union static signing key
   - Google reCAPTCHA site key and secret
   - DFAPI client ID and configuration parameters

2. **`config/p-az-app01/config/dfapiclient/jms.properties`**:
   - Production IBM MQ hostname, port, channel name, queue manager name, send queue, receive queue
   - MQ principal (`df.mq.principal=prepaid`); blank password field

3. **`config/p-az-app01/config/cardnotification/CardNotification.properties`**:
   - Production SAP Mobile Services SMS gateway username and password

4. **`config/p-az-app01/config/ivrws/ivrws.properties`**:
   - Production IVR `appKey` (same value as UAT — key not environment-isolated)

5. **`config/p-az-app01/config/accountmanagementapi/accountmanagementapi.properties`**:
   - Production KYC Azure AD client secret (separate config file also contains this)

6. **`config/p-az-app01/config/csa/applicationContext-csa.properties`** (inferred from pattern):
   - CBTS credentials for production CSA

All of the above are duplicated across the 21 production app server config directories.

## Encryption
- CMS accessed via HTTPS (`https://login.northlane.com:443`) — encrypted
- CBTS accessed via HTTP internally (`http://ppazp.nam.wirecard.sys:9443`) — internal traffic not encrypted for CBTS
- DFAPI via IBM MQ TLS — channel TLS configuration managed by MQ server, not in this repo
- TLS keystore config managed via JAVA_OPTIONS (similar to UAT pattern)

## Data Flow (Production)
```
Live cardholder request → Tomcat (production fleet, p-az-app*)
  → Production SQL Server cluster
  → Director dispatch (ppazp:8080)
  → CMS (login.northlane.com)
  → IBM MQ DF_QM → Remittance (DFAPI)
  → CBTS (ppazp:9443) → Cambridge FX (production)
  → BioCatch production fraud API
  → KYC Portal (Azure production)
  → SAP SMS gateway (production)
```

## Quality
- `ecount-config.xml.erb` — ERB template suggests historical use of a CM tool for production config; the presence of both raw `.properties` and ERB templates indicates mixed configuration management approaches
- `CardNotification-UAT.properties` committed in PROD folder — file naming suggests it may be a vestige of UAT config management rather than a production config file; operational confusion risk

## Compliance Gaps (HIGH SEVERITY)
- **Production secrets in Git** — violates PCI DSS Requirement 6.3.3 (all software components protected from known vulnerabilities), Requirement 8.2.1 (individual user authentication), and Requirement 3.4 (protect stored cardholder data indirectly through ensuring no credential exposure)
- **Production IBM MQ topology exposed** — infrastructure enumeration risk
- **CBTS HTTP internally** — production financial transaction service accessed over unencrypted internal HTTP
- **IVR appKey shared with UAT** — no environment isolation for this credential
- **`df.mq.credentials=` blank** — production MQ connection uses blank password; either authentication is disabled or managed out-of-band (not in repo)
