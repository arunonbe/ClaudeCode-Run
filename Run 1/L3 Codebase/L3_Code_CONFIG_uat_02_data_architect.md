# Data Architect View — CONFIG_uat

## Data Stores Configured
UAT has fewer committed datasource (`*-ds.properties`) files than DEV or QA. The datasource configuration may be managed via JAVA_OPTIONS or other mechanism not stored here. Services connect to UAT-specific database servers inferred from hostnames.

| Service / Data Store | Connection Details | Notes |
|---------------------|-------------------|-------|
| CSWS / CMS | `https://login-uat.northlane.com:443/xContent` | UAT CMS via branded URL |
| CSWS internal | `http://ppnau.nam.wirecard.sys:9001` | Internal UAT xContent |
| Account Management | `accountmanagementapi.properties` — references order service connection | No explicit DB connection in committed files |
| Client API | `clientapi.properties` — routing/DFI details; `routingNA=011001234` (ACH routing) | ACH routing number present |
| Card Notification | SAP Mobile Services: `sms-pp.sapmobileservices.com` (UAT endpoint) | SMS gateway |
| Debit API | Spring XML program list — programs `04014096`, `04019215` | No DB connection visible |
| IVR Web Service | `ecount-config.xml` at `d:\\c-base\\config\\` | Config file reference |

## Schema
Two structural layers:
1. **`.properties` files** — same as DEV/QA for application configuration
2. **`tomcat/registry/{server}/JAVA_OPTIONS/{SERVICE}.txt`** — Tomcat JVM launch options stored as text files per service; unique to UAT repo (not found in DEV or QA repos in this analysis)

### JAVA_OPTIONS Registry (per service on u-na-app01)
| Service | JMX Port | Heap Settings |
|---------|----------|---------------|
| AcceptPrechecks | 9967 (inferred) | Standard |
| AccountManagement | 9968 | MaxPermSize=256m, NewSize=84m |
| AccountManagementPayout | Separate instance | Separate Tomcat home |
| CardManagementCSAPI | Separate instance | Separate Tomcat home |
| CardManagementCSAPIPayout | Separate instance | Separate Tomcat home |
| CardNotificationSMSPull | Separate instance | Separate Tomcat home |
| ClientAPI | 9971 | MaxPermSize=128m, NewSize=85m |
| DebitAPI | 9975 | MaxPermSize=64m, MaxNewSize=32m |
| IVRWS | Separate instance | Separate Tomcat home |

## Sensitive Data Handling

**Credentials committed to source control (file locations, values not reproduced):**

1. **`tomcat/registry/u-na-app01/JAVA_OPTIONS/AccountManagement.txt`**:
   - `javax.net.ssl.keyStorePassword` — Tomcat keystore password (JKS file for `u-na-app01`)
   - `javax.net.ssl.trustStorePassword` — Truststore password
2. **`tomcat/registry/u-na-app01/JAVA_OPTIONS/ClientAPI.txt`** — same keystore and truststore passwords as AccountManagement
3. **`tomcat/registry/u-na-app01/JAVA_OPTIONS/DebitAPI.txt`** — same keystore and truststore passwords
4. **`config/u-na-app01/config/cardnotification/CardNotification.properties`** — SAP Mobile Services SMS gateway username and password
5. **`config/u-na-app01/config/ivrws/ivrws.properties`** — IVR `appKey` (API key committed)
6. **`config/u-na-app01/config/clientapi/clientapi.properties`** — ACH routing details (`dfiNA=553`, `routingNA=011001234`)

## Encryption
- TLS: Keystores at `D:\c-base\opt\tomcat\resources\u-na-app01.jks` and `truststore.jks`; passwords committed in JAVA_OPTIONS files
- JMX: `jmxremote.ssl=false` — JMX management interface not TLS-protected
- JMX authentication: `jmxremote.authenticate=true` with password/access files at `D:\c-base\opt\tomcat\resources\`

## Data Flow
```
UAT request → Tomcat (Tomcat 8.5.57, D:\c-base\opt\tomcat\servers-8.5.57\{SERVICE}\)
  → application config (D:\c-base\config\{service}\)
  → UAT databases (inferred: u-na-db* servers)
  → CMS (login-uat.northlane.com)
  → Director (ppnau.nam.wirecard.sys:8080)
  → SAP SMS gateway (sms-pp.sapmobileservices.com — UAT endpoint)
```

## Quality
- Config for only 2 servers (`u-na-app01`, `u-na-app02`) — smaller than QA
- JAVA_OPTIONS registry provides precise JVM tuning per service — this is more mature than DEV/QA

## Compliance Gaps
- Keystores and truststore passwords in committed source control — significant PCI DSS concern (Req 8: protect authentication credentials)
- JMX SSL disabled — management interface exposed without encryption
- ACH routing details committed (routing number `011001234`) — financial infrastructure data in source control
- SMS gateway credentials committed
- IVR `appKey` committed
