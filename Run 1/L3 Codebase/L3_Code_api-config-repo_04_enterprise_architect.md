# api-config-repo — Enterprise Architect View

## Platform Generation (Gen-1/Gen-2/Gen-3)

**Assessment: Gen-1 / Gen-2 hybrid — predominantly Gen-1.**

Evidence supporting this classification:

| Indicator | Gen-1 Characteristics Observed |
|---|---|
| Application server | WebLogic (`bea900/weblogic90`) referenced in CSA build.properties; `t3://` WebLogic protocol used in job queue URLs |
| Service framework | Spring XML bean configuration (`<beans xmlns=...spring-beans.xsd>`) in all IEFT rule XMLs — traditional Spring XML IoC, not Spring Boot |
| Config externalisation | File-system properties files on a shared network drive (`\\q-na-stk01\c-base`) — not cloud-native secrets management |
| Database connectivity | jTDS JDBC driver for some databases; ODBC DSN for FDR ODS — very legacy connectivity |
| Service discovery | Proprietary Director service (`directorsvc.onbe.io`) used as service registry — not Kubernetes/Consul/Eureka |
| JMS | IBM MQ and TIBCO EMS — enterprise messaging, not cloud-native event streaming |
| SOAP web services | DFAPI SOAP, Banker SOAP WSDL, eDelivery SOAP, CitiMFA SOAP — predominant API style is SOAP/WSDL |
| Deployment pattern | WAR/EAR files deployed to application server via file share mount |

**Gen-2 elements present:**
- Azure Storage File Share for config distribution (partially cloud-aligned).
- Azure App Configuration service reference (`appcs-shared-qa-ss.azconfig.io`).
- GitHub Actions CI/CD pipeline.
- Some services now point to `*.onbe.io` domains (ecountcoresvc, ordersvc, directorsvc, bankerapi, etc.) suggesting containerised or cloud-deployed variants of core services.
- Resilience4j circuit breakers configured for accountmanagementapi, ecountcore, and order service — a Gen-2/Gen-3 pattern.
- KYC portal on Azure App Service (`azurewebsites.net`) — Gen-2 cloud.
- FiServ Debit API served from `localhost:8082` — suggests sidecar container pattern in a more modern deployment.

**No Gen-3 indicators observed.** No Kubernetes ingress, no OpenAPI 3.x, no service mesh configuration, no event streaming (Kafka/Event Hubs), no Spring Boot application properties.

## Business Domain

**Prepaid Card Lifecycle Management and Disbursements** — B2C and B2B2C prepaid card programs across North America. Specifically:

- **Cardholder-facing**: Account activation, balance inquiry, PIN management, international transfers, card-to-bank withdrawals, virtual card number issuance.
- **Client-facing**: Program administration, bulk order management, fund loading, reporting.
- **Operations**: Card inventory management, batch job scheduling, notification delivery, check acceptance.
- **Compliance services**: KYC / identity verification, MFA, OFAC email domain restriction, eDelivery for regulatory statements.

The IEFT rules for 160+ countries indicate a global disbursement use case, not a US-domestic-only platform.

## Role in Platform

`api-config-repo` is the **single source of truth for runtime configuration** of the entire Onbe East (formerly Wirecard North America / Citi Prepaid) services platform. It serves as:

1. **Config store**: Externalised configuration for 35+ named services.
2. **Rules repository**: Business rules for international transfer validation (IEFT XML).
3. **Environment registry**: Service endpoint URLs, database connection strings, queue names, and agent identifiers for the QA/stage environment.
4. **Integration specification**: Postman collections document the API surface of all major external-facing web services.
5. **Deployment vehicle**: GitHub Actions deploys this repository's contents directly to the infrastructure (Azure File Share) consumed by application servers.

Without this repository, all configured services would fail to start or would use default/embedded values — making it a **critical operational dependency**.

## Dependencies (Services this Config Repo Serves)

### Tier 1 — External-Facing APIs
| Service | Config Directory | Protocol | Notes |
|---|---|---|---|
| Account Management API | `accountmanagementapi/`, `account-management/` | SOAP (WSDL), HTTP Invoker | Primary B2B card management API |
| Client API (Instant Issue) | `clientapi/` | SOAP | Card issuance for instant-issue programs |
| CSWS v1 / v3 / Payout | `CSWS/` | SOAP | Citi-branded card services API (legacy + payout) |
| Debit API | `debitapi/` | SOAP | Debit card services |
| IVR Web Service | `ivrws/` | SOAP | IVR integration for phone-based card services |
| Accept Prechecks | `AcceptPrechecks/` | SOAP | Check payment precheck (Certegy integration) |
| FDVS Precheck | `FDVSPrecheck/` | SOAP | IVR check management |

### Tier 2 — Cardholder / Client Portals
| Service | Config Directory | Technology |
|---|---|---|
| OnePlatform (OP) | `oneplatform/` | Java web app (JSP/Spring MVC) |
| OnePlatform 508 | `op508/` | Java web app (ADA-compliant variant) |
| Enrollment / GE Portal | `enroll/` | Java web app |
| ClientZone (CZ) | `cz/` | Java web app |
| Card Services Admin (CSA) | `csa/` | Java web app (WebLogic) |
| Rebate Card Inquiry | `rebate-cardinquiry/` | Java web app |

### Tier 3 — Core Platform Services
| Service | Config Directory | Notes |
|---|---|---|
| eCount Core | `core2/ecountcore/` | FDR card processor integration; FiServ debit |
| Strongbox | `core2/Strongbox/` | Cryptographic key and PIN management |
| Profile Service | `core2/profile/` | Cardholder profile management |
| Order Service | `service/order/` | Order lifecycle management |
| Request Service | `service/request/` | Transaction request processing |
| Account Service | `service/account/` | Account management operations |
| Banker Service | `service/banker/` | Fund authorisation |
| Payment Service | `service/payment/` | Payment selection / disbursement |
| Autofile Service | `service/autofile/` | Bulk file-based disbursements |
| Job Scheduler | `service/jobscheduler/` | Scheduled batch job management |
| Job Manager | `service/jobManager/` | Real-time and batch job dispatch |
| Job Agent | `service/jobAgent/` | Job execution worker |
| Notification Service | `service/notificationStrategy/` | Email and SMS notification delivery |
| Card Notification | `cardnotification/` | Transaction-triggered SMS/push notifications |
| Message Centre | `service/message/` | Internal messaging |
| Repository Service | `service/repository/` | Service configuration registry |
| Directory Service | `service/directory/` | Service directory (J2 Director) |
| HTTP Crypto Service | `service/httpCryptoService/` | PGP key management |
| eDelivery Service | `service/edelivery/` | Electronic statement delivery (Citi) |
| MFA Service | `service/mfa/` | Multi-factor authentication |
| DFAPI Client | `dfapiclient/` | Citi DFAPI wire/ACH integration |
| Inventory Management | `inventoryMgmt/` | Physical card stock management |

### Shared Infrastructure Config
- Datasource files: `cbaseapp-ds`, `ecountcore-ds`, `ecount-db`, `greatplains-ds`, `jobsvc-ds`, `order-ds`, `request-ds`
- Director client: `director-client.properties`
- eCount config: `ecount-config.xml`

## Integration Patterns

| Pattern | Implementation |
|---|---|
| SOAP/WSDL (synchronous) | Primary external API style for all Tier 1 APIs; DFAPI client; Banker WSDL; eDelivery; CitiMFA |
| Spring HTTP Invoker (synchronous) | Order service and Request service internal communication (`service.order.service.url`) |
| IBM MQ (asynchronous) | Order submission, request processing, job agent queues — `Q_NA_MQ_HA` on port 51516 |
| TIBCO EMS (asynchronous) | Notification events/messages, job workflow — `PrepaidJMS_159547` on port 50643 |
| Proprietary Director Service (SOA registry) | `directorsvc.onbe.io` — all services register and discover via Director dispatch |
| Azure App Configuration (key-value) | FiServ / debit service endpoint configuration |
| REST / JSON (partial, emerging) | KYC portal OAuth, FiServ Debit API REST endpoints (`/customer/v4/`, `/maintenance/v2/`), Mailgun API |
| File-based batch (autofile) | Autofile service processes bulk disbursement files from a file system path |
| Cache (Ehcache) | Notification template and mapping caches (`ehCache3-template-*.xml`) — environment-switchable |

## Strategic Status

**Legacy / Maintenance mode — high technical debt, partial modernisation in progress.**

Key signals:
- Core package names are `com.citi.prepaid.*` (Citi legacy branding) — not yet fully rebranded to Onbe.
- Multiple references to `wirecard.sys` hostnames and `wirecard.com` domains (legacy Wirecard North America infrastructure).
- Simultaneous presence of `*.onbe.io` service URLs (new cloud endpoints) alongside `*.wirecard.sys` hostnames indicates an in-progress infrastructure migration.
- ODBC, jTDS, WebLogic, and TIBCO EMS are end-of-life or legacy technologies.
- The `clientzoneHub.properties` still references `uatnaclientzone.citiprepaid.com` (legacy Citi branding).
- `oneplatform/migratedPrograms.properties` has `migrated.bins=` (empty) — BIN migration has not been completed.
- The `IEFTRules/` Spring XML approach is consistent with a circa-2010 Spring Framework architecture.

## Migration Blockers

| Blocker | Detail | Effort |
|---|---|---|
| Secrets in plaintext config files | Before any cloud-native migration, all secrets must be moved to a secrets management service (Azure Key Vault, HashiCorp Vault). There are 20+ credentials stored in plaintext. | High |
| Hardcoded filesystem paths | `D:/c-base/` and `/c-base/` paths are embedded throughout configs. Cloud deployments require path externalisation or environment variable substitution. | Medium |
| Director service dependency | All services depend on `directorsvc.onbe.io` for registration and discovery. Migration requires replacing this proprietary registry. | High |
| ODBC / FDR ODS connectivity | `fdrODSDS.url=jdbc:odbc:CBASClntCATM` requires Windows ODBC driver — not portable to Linux containers. | High |
| WebLogic dependency (CSA) | CSA uses WebLogic application server. Containerisation requires migration to Tomcat/Spring Boot. | High |
| TIBCO EMS / IBM MQ coupling | All async messaging is tightly coupled to TIBCO EMS and IBM MQ. Cloud-native migration requires migration to a managed broker (Azure Service Bus, Kafka). | High |
| SOAP-first API style | All Tier 1 APIs are SOAP/WSDL. Consumer-facing migration to REST/JSON would require API versioning and client migration planning. | Very High |
| Citi legacy branding / package names | `com.citi.prepaid.*` Java packages require code-level refactoring, not just config changes. | Medium |
| Spring XML IoC (IEFT rules) | 60+ country rule XMLs use Spring XML bean definitions. Migration to annotation-based or programmatic config requires re-implementation. | Medium |
| `migrated.bins=` (empty) | BIN migration programme is incomplete. Until BINs are migrated, old card number series remain on legacy platform rails. | Business decision required |
| Production eDelivery endpoint in stage config | Must be resolved before any environment consolidation to prevent cross-environment contamination. | Low (config fix) |
| Log4j 1.x residue | Services with both log4j.xml and log4j2.xml need to confirm which is active and remove the Log4j 1.x dependency. | Low |
