# Enterprise Architect View — CONFIG_dev

## Platform Generation
**Generation 2 (Gen-2)** — Legacy Windows/Tomcat monolithic Java platform. The DEV environment configuration reflects a full Gen-2 stack: Windows servers (`d-na-*`), Apache Tomcat, JDK 7/8, SQL Server, IBM MQ, externalized `.properties` files in `D:\c-base\config\`.

The presence of a Spring Boot service (CBTS on `d-na-app04`) with YAML configuration and resilience4j circuit breakers indicates the beginning of a Gen-3 microservice pattern being introduced alongside the legacy stack.

## Business Domain Coverage
The DEV environment configuration covers the full Onbe platform portfolio:
- **Prepaid card management** (CardManagement, AccountManagement, ClientAPI, DebitAPI)
- **Cardholder portals** (ClientZone, ClientZone5, ClientZoneHub, Enrollment, OnePlatform)
- **Client service tools** (CSA, Workbench, Wizard)
- **Payments and transfers** (Payment, DFAPI/remittance, CBTS cross-border)
- **Notifications** (CardNotification SMS, IVR, eDelivery)
- **Back-office and batch** (InventoryMgmt, Scheduler, AutoFile, various client batch programs)
- **Infrastructure services** (Strongbox/crypto, CMS/xContent, Director dispatch, eCount core, Strongbox)

## Role in Platform
The DEV configuration repo is the development environment counterpart to CONFIG_qa, CONFIG_uat, and CONFIG_prod. It enables the full platform to be deployed and operated in isolation for development purposes. Every service configuration in PROD has a corresponding DEV variant in this repo.

## Dependencies
| Dependency | Environment | Notes |
|------------|-------------|-------|
| `d-na-db01.nam.wirecard.sys` | DEV SQL Server | Legacy Wirecard DNS |
| `d-na-app01/02/03/04.nam.wirecard.sys` | DEV app servers | Internal server DNS |
| IBM MQ (`gppswmqu`, REMIT_QM.UAT) | **UAT MQ** (cross-env!) | DEV DFAPI client connects to UAT queue |
| Cambridge FX `beta.cambridgelink.com` | DEV/Beta | Third-party FX API |
| KYC Portal `app-activationportalapi-qa-westus2-001.azurewebsites.net` | **QA Azure** (cross-env!) | DEV KYC connects to QA Azure |
| Mailgun `smtp.mailgun.org` | Shared (not env-specific) | Email for CBTS notifications |
| CMS / xContent (d-na-app03) | DEV | Content management |
| Strongbox (d-na-app03:9301) | DEV | Crypto key service |
| Logstash (`logstash.util.northlane.com`) | Shared | Log shipping |

## Integration Patterns
- **Externalized configuration**: Spring/Tomcat config files on `D:\c-base\config\` — classic Gen-2 externalized config pattern
- **JDBC datasources**: Declared via `-ds.properties` files; standard Spring JDBC connection pooling
- **IBM MQ / JMS**: DFAPI client uses IBM MQ for remittance message passing
- **XML-RPC**: Strongbox uses XML-RPC protocol for crypto operations
- **REST/HTTP**: Director dispatch, CMS xContent, Cambridge FX, KYC portal — all HTTP/HTTPS
- **Spring Boot + Resilience4j**: CBTS service (d-na-app04) uses Gen-3 patterns with circuit breakers
- **Agent-based identity**: Services identify themselves via `agent` parameter (B2CTEST in DEV)

## Strategic Status
**Active legacy development environment.** The DEV configuration is the reference point for development work on the Gen-2 platform. The introduction of CBTS as a Spring Boot service signals the beginning of a microservices migration, but the vast majority of services remain in the legacy Tomcat/properties pattern.

The presence of JDK 1.7.0.65 in the repo alongside JDK 1.8 indicates that some services may still target Java 7, which is severely EOL.

## Migration Blockers
- **Credentials in config files** — migration to a cloud-native vault is a prerequisite for any cloud deployment
- **JDK 7/8** — must upgrade to JDK 17/21 for modern frameworks and TLS support
- **IBM MQ** — DFAPI remittance integration depends on IBM MQ; requires migration to cloud-native messaging (e.g., Azure Service Bus, AWS SQS)
- **Windows filesystem dependency** (`D:\c-base\`) — all services assume a Windows path; containerisation requires path abstraction
- **SQL Server on-premises** — database migration required for cloud-native deployment
- **Director dispatch service** — internal routing service; must be replaced or re-architectured for cloud
- **Strongbox XML-RPC** — crypto key service using XML-RPC; must be replaced with modern secrets management
- **Multiple hardcoded server DNS names** — all internal `wirecard.sys` and `northlane.sys` DNS must be replaced
