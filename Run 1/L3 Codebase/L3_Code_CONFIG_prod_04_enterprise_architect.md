# Enterprise Architect View — CONFIG_prod

## Platform Generation
**Generation 2 (Gen-2) — Production.** The production environment runs on Azure-hosted Windows VMs (`p-az-*`) with Apache Tomcat, JDK 7/8, IBM MQ, and externalized `.properties` file configuration. The `p-az-` naming confirms Azure IaaS — Windows VMs in Azure rather than cloud-native PaaS or containers.

The production environment is therefore an IaaS lift-and-shift of the original on-premises platform (the `nam.wirecard.sys` DNS for internal services confirms legacy Wirecard-era infrastructure co-existing with Azure VMs). This is a hybrid: Azure VMs running what are effectively on-premises application patterns.

## Business Domain Coverage
Full production platform — all Onbe payment platform capabilities in production:
- Prepaid card management and cardholder operations
- B2B client API for card program management
- Cardholder portals (ClientZone, OnePlatform, CSA)
- Remittance and cross-border transfers (DFAPI, CBTS/Cambridge FX)
- SMS and IVR notifications
- Fraud scoring (BioCatch production)
- Identity verification (KYC, Azure-hosted)
- Batch operations (inventory, reporting, client batch programs)

## Role in Platform
**Production — the live payment platform serving real cardholders and clients.** Every configuration value in this repo affects live transactions, active cardholders, and client SLAs. This is the highest-criticality repository.

## Dependencies
| Dependency | Type | Notes |
|------------|------|-------|
| Azure IaaS (`p-az-*` VMs) | Compute | Windows VMs; not container/PaaS |
| `ppazp.nam.wirecard.sys` | Internal Director + CMS | Legacy Wirecard DNS in production Azure |
| `dofrmwpmq.nam.wirecard.sys` | Production IBM MQ | Remittance infrastructure |
| `login.northlane.com` | Branded production CMS | Public-facing |
| `clientzone.mypaymentadmin.com` | Cardholder portal | Public-facing |
| Cambridge FX (via CBTS) | Third party | FX rates and international wire |
| BioCatch (`api-9a7a72ec.us.v2.we-stats.com`) | Third party | Production fraud scoring |
| KYC Portal (Azure, `prod-westus2`) | Azure-hosted | Production identity verification |
| SAP Mobile Services | Third party | Production SMS gateway |
| Western Union | Third party | Card-to-WU transfer integration |
| JDK 7/8 + Tomcat | Runtime | Legacy, EOL |

## Integration Patterns
- All Gen-2 patterns: externalized `.properties`, JDBC, IBM MQ JMS, XML-RPC (Strongbox), REST/HTTP
- `ecount-config.xml.erb` ERB template — historical Chef/Puppet CM integration
- BioCatch: REST API call per user session for fraud scoring
- Cambridge FX: REST API via CBTS microservice for FX rates and wire booking
- KYC: OAuth2 (Azure AD) token exchange + REST API for identity verification

## Strategic Status
**Active production — Gen-2.** This is the current live Onbe payment platform configuration. The `p-az-*` naming indicates the infrastructure has been migrated to Azure IaaS, but the application stack remains Gen-2 (Windows VMs, Tomcat, JDK 8, `.properties` files).

Some Gen-3 patterns are emerging:
- CBTS is a Spring Boot service with YAML config and resilience4j (partially migrated)
- KYC portal is an Azure App Service (`azurewebsites.net`) — cloud-native external dependency
- BioCatch is a cloud SaaS — cloud-native external dependency

The core platform itself remains Gen-2.

## Migration Blockers
All DEV/QA migration blockers apply, plus:
1. **Production credentials in Git** — MUST be resolved before any cloud-native migration; migrate to Azure Key Vault immediately
2. **IaaS VMs running Tomcat** — re-architecture to containers/AKS or Azure App Service required
3. **Legacy Wirecard DNS (`wirecard.sys`)** — still in use in production Azure environment; DNS migration required
4. **IBM MQ in production** — Azure Service Bus or equivalent cloud messaging migration required
5. **21+ server configs** — automated config templating required before any migration
6. **Java 7 binary** — if any production service runs on Java 7, emergency upgrade required
7. **Tomcat 8.5.57 EOL** — production web server is end-of-life
8. **CBTS uses HTTP internally** — must enforce TLS for all inter-service communication before any cloud migration
9. **ecount-config.xml.erb ERB template** — Chef/Puppet dependency must be resolved; templating approach must be standardised
