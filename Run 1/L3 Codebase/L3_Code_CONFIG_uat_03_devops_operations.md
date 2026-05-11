# DevOps / Operations View — CONFIG_uat

## Repository Role
Configuration files for UAT environment on `u-na-app01` and `u-na-app02`. Unlike QA, UAT has **no `.gitlab-ci.yml`** — there is no automated deployment pipeline for UAT config changes. Config changes are deployed manually.

UAT is unique in that it includes a **`tomcat/registry/`** folder with per-service Tomcat JAVA_OPTIONS text files — these define JVM parameters, GC settings, JMX ports, and keystore/truststore paths for each Tomcat instance.

## Server Fleet (UAT)
| Server | Services |
|--------|---------|
| `u-na-app01` | AcceptPrechecks, AccountManagement, AccountManagementPayout, CardManagementCSAPI, CardManagementCSAPIPayout, CardNotificationSMSPull, ClientAPI, DebitAPI, IVRWS |
| `u-na-app02` | Same set of services (duplicate server for redundancy) |

## Services Configured

### Application Config (`config/u-na-app01/config/`)
| Service | Config Files | Key Settings |
|---------|-------------|--------------|
| AcceptPrechecks | `AcceptPrechecks.properties`, `log4j.properties`, `log4j.xml` | `agent=B2CTEST`, `facility=certegy` |
| CSWS | `applicationContext-CSWS.properties`, `applicationContext-V1.properties` | CMS via `login-uat.northlane.com`, `authSyncPrograms=04014631` |
| AccountManagementAPI | `accountmanagementapi.properties`, `APIValidation.properties`, `api-security.properties`, `service.monitor.properties`, `log4j.xml`, `log4j-payout.xml`, `OrderService_Connection.xml` | `region=NA`, `agent=B2C`, `memberId=5FCFFE5C-...` |
| CardNotification | `CardNotification.properties`, `CardNotification-UAT.properties`, `log4j.xml`, `web.xml` | `agent=B2C`, full production program list, SAP SMS credentials |
| ClientAPI | `clientapi.properties`, `api-security.properties`, `service.monitor.properties`, `log4j.xml`, `OrderService_Connection.xml` | `region=NA`, `memberId=208E01DE-...`, `routingNA=011001234` |
| DebitAPI | `debitapi.properties`, `debitapi.xml`, `log4j.xml` | `agent=B2C`, programs `04014096`+`04019215` |
| IVRWS | `ivrws.properties`, `log4j.xml` | `agent=B2C`, `appKey` (committed) |

### Tomcat Registry (`tomcat/registry/u-na-app01/JAVA_OPTIONS/`)
Per-service JVM settings for each Tomcat instance:

| Service | Tomcat Home | JMX Port | Key JVM Flags |
|---------|-------------|----------|---------------|
| AcceptPrechecks | `.../AcceptPrechecks` | — | Standard CMS GC flags |
| AccountManagement | `.../AccountManagement` | 9968 | MaxPermSize=256m, NewSize=84m, CMS GC |
| AccountManagementPayout | `.../AccountManagementPayout` | — | Payout variant |
| CardManagementCSAPI | `.../CardManagementCSAPI` | — | CSAPI variant |
| CardManagementCSAPIPayout | `.../CardManagementCSAPIPayout` | — | CSAPI Payout variant |
| CardNotificationSMSPull | `.../CardNotificationSMSPull` | — | SMS Pull service |
| ClientAPI | `.../ClientAPI` | 9971 | MaxPermSize=128m, NewSize=85m |
| DebitAPI | `.../DebitAPI` | 9975 | MaxPermSize=64m, MaxNewSize=32m |
| IVRWS | `.../IVRWS` | — | IVR service |

All instances use:
- Tomcat 8.5.57
- GC: `-XX:+UseConcMarkSweepGC` (CMS GC — legacy Java 8 GC)
- GC logging: `-Xloggc:D:\c-base\opt\tomcat\servers-8.5.57\{SERVICE}\logs\{SERVICE}-gc.log`
- SSL: `-Djavax.net.ssl.keyStore=D:\c-base\opt\tomcat\resources\u-na-app01.jks`
- JMX: `-Dcom.sun.management.jmxremote.ssl=false` (no SSL), with auth enabled

## Configuration Management
- **Manual deployment** — no GitLab CI pipeline in this repo
- Files deployed to `D:\c-base\config\` on UAT servers
- JAVA_OPTIONS files deployed to Windows Registry or Tomcat wrapper config
- Service restart required after config changes

## Observability
- GC log files per service: `D:\c-base\opt\tomcat\servers-8.5.57\{SERVICE}\logs\{SERVICE}-gc.log`
- No Filebeat input YAML files found in UAT config repo — log shipping may be configured separately
- No application-level metrics or health endpoint configs visible (beyond service monitor properties)

## Infrastructure Dependencies
- Tomcat 8.5.57 on `D:\c-base\opt\tomcat\servers-8.5.57\`
- Java 8 runtime
- Windows keystores at `D:\c-base\opt\tomcat\resources\`
- JMX password/access files at `D:\c-base\opt\tomcat\resources\`
- CMS: `login-uat.northlane.com:443`
- Director: `ppnau.nam.wirecard.sys:8080`
- SAP Mobile Services: `sms-pp.sapmobileservices.com`

## Operational Risks
- **No automated config deployment** — manual deployment increases risk of drift and human error
- **Keystore/truststore passwords in source control** — significant security risk
- **JMX SSL disabled** — management ports exposed without TLS
- **Legacy GC settings** (`-XX:MaxPermSize`, CMS GC) — PermGen was removed in Java 8+; these flags are no-ops or warnings in JDK 8 and will break in JDK 9+
- **Two servers only** — limited redundancy for UAT; no load balancing info visible
- **`u-na-app02` duplicates `u-na-app01` config** — duplicate files increase maintenance burden
