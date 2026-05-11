# Enterprise Architect View — CONFIG_uat

## Platform Generation
**Generation 2 (Gen-2)** — Identical technology stack to DEV and QA: Windows, Tomcat 8.5.57, JDK 8, CMS GC, `.properties` externalised config. UAT is the pre-PROD gate environment with `B2C` agent code (same as PROD), making it the most PROD-representative non-production environment.

## Business Domain Coverage
UAT covers the externally-facing API and notification layer:
- Card management APIs (Account Management, Client API, Card Management CSAPI, Debit API)
- Card notification and SMS
- IVR integration
- Card acceptance prechecks

UAT does NOT appear to configure portal/web application services (ClientZone, CSA, OnePlatform) based on the config folder structure. It focuses on the B2B API and notification stack.

## Role in Platform
**Final pre-production validation gate.** UAT is where:
- Client API consumers validate their integration before production
- Card management API changes are business-validated
- SMS notification program lists are verified against full production set
- Go/No-Go decisions are made for production deployments

The presence of `B2C` agent code (not `B2CTEST` or `B2CSTAGE`) in most UAT services means UAT behaves identically to PROD at the eCount/platform API authentication level. This is appropriate for UAT sign-off but increases the risk of environment confusion.

## Dependencies
| Dependency | Notes |
|------------|-------|
| Tomcat 8.5.57 | Legacy app server on Windows |
| Java 8 | Runtime |
| `login-uat.northlane.com:443` | Branded UAT CMS URL |
| `ppnau.nam.wirecard.sys:8080` | UAT Director dispatch |
| `sms-pp.sapmobileservices.com` | SAP UAT SMS gateway |
| JKS keystores at `D:\c-base\opt\tomcat\resources\` | Per-server SSL certificates |
| JMX password files at `D:\c-base\opt\tomcat\resources\` | JMX authentication |

## Integration Patterns
- Same Gen-2 patterns as DEV/QA
- JAVA_OPTIONS registry pattern (unique to UAT) — Tomcat JVM parameters stored as text files per service; suggests Windows service wrapper configuration (Apache Procrun or similar)
- No CI/CD automation — entirely manual config management

## Strategic Status
**Active but manually managed.** UAT is critical for production promotion gates, yet it has no automated config deployment pipeline. This creates risk of configuration drift between UAT and PROD and between `u-na-app01` and `u-na-app02`.

The duplicate config for `u-na-app02` (same files as `u-na-app01`) is a maintenance burden that will persist until proper config templating or container-based deployment is adopted.

## Migration Blockers
- **Keystores and TLS passwords in source control** — must be migrated to vault before any cloud migration
- **JMX SSL disabled** — needs TLS before cloud exposure
- **Legacy JVM flags** (`-XX:MaxPermSize`, CMS GC) — must be updated for JDK 17+
- **Manual deployment** — requires automation before production-confidence cloud deployment
- **Tomcat 8.5.57** — EOL August 2024; must upgrade to Tomcat 10.x or migrate to embedded Spring Boot server
- **Duplicate server configs** (`u-na-app01` and `u-na-app02` identical) — replace with templated/automated config generation
- **`B2C` agent code in UAT** — appropriate for validation but complicates separation; need clear agent code strategy for cloud
