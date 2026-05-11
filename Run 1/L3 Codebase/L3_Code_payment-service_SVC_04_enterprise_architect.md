# Enterprise Architect — payment-service_SVC

## Platform Generation
**Gen-1 (core legacy)** — Spring Framework (XML context), Spring MVC, XML-RPC servlet, Java 21 (compiler only; runtime patterns are Gen-1). No Spring Boot, no auto-configuration, no Actuator. Deployed as a WAR on Tomcat. Configuration via filesystem property files and Spring XML. This is the foundational payment processing service of the ecount/EcountCore platform.

## Business Domain
**Core Payments — Certificate Issuance, Transaction Management, Stop Payment**
The payment service is the authoritative backend for creating, stopping, and managing payment instruments (certificates/prepaid cards) and associated transaction records within the ecount platform. It is a central dependency for all payment flows across all Onbe products that use the EcountCore platform.

## Architectural Role
- **Core payment domain service**: Provides payment lifecycle operations via XML-RPC.
- **XMLRPC server**: Exposes `EPaymentProxy` via `XmlRPCServlet` at `/dispatch.asp` — the standard ecount platform entry point.
- **Database gateway**: All `cbaseapp` payment-related stored procedures are accessed through this service.
- **Notification orchestrator**: Triggers email notifications for payment events via `NotificationServiceHelper`.
- **Dependency for `oneplatform-rest_API`**: The REST API's payment-related operations ultimately route to this service via the director-service XMLRPC dispatcher.

## System Dependencies
| System | Direction | Protocol |
|--------|-----------|----------|
| `oneplatform-rest_API` (and other callers) | Upstream consumers | XMLRPC HTTP |
| `director-service` | Routing intermediary | XMLRPC dispatch |
| `cbaseapp` SQL Server | Downstream data store | JDBC/TLS 1.2 |
| member XMLRPC service | Downstream | XMLRPC |
| device XMLRPC service | Downstream | XMLRPC |
| transfer XMLRPC service | Downstream | XMLRPC |
| profile service | Downstream | XMLRPC client |
| notification service | Internal | In-process `NotificationManagerImpl` |
| `AffiliateMapSkin` / `AffiliateLocaleSkinHelper` | Internal | In-process JDBC to cbaseapp |

## Integration Patterns
- **XML-RPC server pattern**: The `XmlRPCServlet` dispatches incoming XML-RPC calls to registered handler beans (`EPaymentProxy`).
- **Spring XML bean wiring**: All beans defined in XML context files; no annotation-based configuration.
- **Delegate pattern**: `PaymentServiceImpl` delegates to `PaymentServiceLibraryImpl` which delegates to DAO — classic Gen-1 layered architecture.
- **Shared data source**: `CbaseappDataSource` bean shared across the payment service DAO and the affiliate skin helper — tight coupling through shared DB connection.
- **Context map pattern**: Business context (agent, affiliate, etc.) passed as raw `Hashtable` — no type-safe context object.

## Strategic Status
- **Production-critical / active maintenance** (version `4.1.2-SNAPSHOT`; `.gitlab-ci.yml` with active deployment pipeline to QA hosts).
- This service is a **modernization blocker** — the entire ecount XMLRPC architecture must be replaced or wrapped before Gen-3 microservices can independently manage payments.
- The SNAPSHOT version indicates ongoing development despite being a Gen-1 service.
- Java 21 compiler target represents incremental modernization but the runtime patterns remain entirely Gen-1.

## Migration Blockers
1. **XMLRPC protocol**: No REST API layer on this service; all consumers use XMLRPC. Migrating requires adding a REST facade or replacing the service entirely.
2. **XML Spring context**: All configuration in XML (`appCtx-PaymentService.xml`, `DataSources.xml`, etc.) — must be converted to Java/annotation-based configuration.
3. **Stored procedure depth**: ~20 stored procedures in `cbaseapp` encapsulate critical payment business logic — each must be analyzed and migrated to application-layer logic.
4. **Shared cbaseapp data source**: Multiple services share `cbaseapp`; changing the schema requires coordinated migration across all consumers.
5. **No automated tests** (all tests skipped in CI): Zero test coverage safety net for migration work.
6. **Notification system coupling**: `NotificationManagerImpl` and `AffiliateMapSkin` are in-process; extracting them requires separate service decomposition.
7. **Hardcoded default values** (bulk user address/email/phone): These values are embedded in business logic and would need to be externalized during migration.
8. **Jakarta servlet shim**: Custom `jakarta/servlet/http/HttpUtils.java` — a workaround for Jakarta EE migration that must be resolved properly.
