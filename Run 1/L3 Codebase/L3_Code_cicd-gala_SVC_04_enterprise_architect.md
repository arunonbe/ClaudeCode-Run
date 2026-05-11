# cicd-gala_SVC — Enterprise Architect View

## Platform Generation (Gen-1/Gen-2/Gen-3)

**Generation: Gen-1**

Evidence:
- Spring Framework 2.0.8 (released 2007). No Spring Boot, no Spring MVC REST, no annotation-driven configuration.
- Apache Axis 1.4 SOAP/JAX-RPC transport (2006-era; Axis2 succeeded it around 2007; JAX-WS/JAX-RS are the modern standards).
- Spring XML-only configuration (no `@Component`, no `@Service`, no `@Autowired` in application code).
- Spring 2.x DTD-based bean definitions (`spring-beans-2.0.xsd`).
- Web descriptor `web-app_2_3.dtd` (Servlet 2.3, released 2001).
- JUnit 3.8.1 (released 2002). JUnit 4 and 5 are not used.
- `com.citi.prepaid.service:service-parent:8` parent POM — a Citibank-era prepaid platform artifact, confirming deep legacy lineage predating Wirecard, Northlane, and Onbe.
- Singleton pattern via `BankerServiceManagerImpl.getInstance()` (manual, non-Spring-managed singleton).
- No REST, no JSON, no Spring Boot, no containerization (Dockerfile absent).
- No security framework (Spring Security absent; no JWT, no OAuth2, no API key management).

The artifact group `com.ecount.test.gala` and the repo name `cicd-gala` suggest this was intended as a **CI/CD template and testing sandbox** based on the banker-service codebase, created by a developer named Galina (`README.md`: "Galina's testing area"). It represents the Gen-1 banker-service source used as a test harness for the Northlane/Onbe CI/CD pipeline automation effort.

## Business Domain

**Domain: Program Funds Management / Disbursement Authorization**

This service sits at the intersection of:
- **Prepaid card program operations**: Enforces program budget before any card load, ACH, or disbursement is authorized.
- **Financial ERP integration**: Direct integration with Microsoft Great Plains ERP (GP), querying ledger balances, invoices, payments, and sales orders.
- **Operator workflow**: Provides a role-based approval workflow (Level 1/2/3 banker, force-auth, force-settle) for human-in-the-loop disbursement authorization.
- **B2C disbursements**: Supports Onbe's core use cases of healthcare, insurance, auto finance, and rebate program payouts.

Within Onbe's platform taxonomy this is a **backend financial control service** — not a customer-facing service, not a card processing service. It enforces the "do we have money to pay this out?" check.

## Role in Platform

`cicd-gala_SVC` / Banker Service plays the following roles:

1. **Financial gatekeeper**: All disbursement-creating services (Job Service, Order Service) must call `auth()` before creating a card load or payment. The banker service is a synchronous, blocking checkpoint in every disbursement flow.
2. **GP ERP abstraction layer**: Provides a clean Java API that isolates upstream callers from the complexity of multiple GP databases, program-based routing, and GP stored procedure interfaces.
3. **Fund reservation ledger**: Maintains an intermediate local ledger (`banker_reserved_source`) that tracks authorized but not yet GP-settled amounts. This is a shadow ledger that bridges the gap between operational authorization and GP posting latency.
4. **Escalation trigger**: When a user's banker level is insufficient, the service triggers email notifications to higher-level banker users, enabling a manual approval workflow.
5. **CI/CD template (in this repo)**: In its current `cicd-gala` form, this repo was used by the platform team to develop and test the Northlane CI/CD pipeline templates (`scripts/maven.gitlab-ci.yml`, `scripts/mavenNexus.gitlab-ci.yml`, `tomcat/deployChild.gitlab-ci.yml`).

## Dependencies

### Upstream (services that call Banker Service)
- **Job Service** (inferred from `sourcePrefix` patterns and "Job Service" reference in `BankerServiceAction.validateReferencedOriginalSourceExistence`)
- **Order Service** (inferred from reference source logic)
- Any other Onbe internal service that issues disbursements against program funds

### Downstream (services Banker Service calls)
| Dependency | Interface | Coupling |
|---|---|---|
| Great Plains ERP | SQL Server stored procedures (multiple databases) | Tight — stored procedure names embedded in class names (e.g., `banker_get_free_funds`, `banker_get_unsettled_funds`) |
| Banker DB (jobsvc) | SQL Server stored procedures + JDBC | Tight |
| User DB (cbaseapp) | SQL Server stored procedures | Tight |
| Director service registry | `DirectorConfiguredDBCPdatasourceCreator` | Tight — all DB connections depend on this internal service |
| cbase profile services | `RequestContext`/`Member` pattern, proprietary API | Tight |
| cbase notification manager | `NotificationManagerImpl` | Tight |
| ECountCore system | `ecount-system` library | Tight — platform foundation classes |

### Shared Libraries
- `com.ecount.springutils:springutils-generic:1.0.6` — AOP audit interceptor, `ReloadableBean` for client proxy
- `com.ecount:xPlatform:2.5.47` — unknown content; excluded Spring to avoid conflict
- `com.citi.prepaid.module:request-context:1.0.0` — `RequestContext` class (Citi-era)
- `com.ecount.service.Core2:director-client:1.0.11` — Director DB connection factory client

## Integration Patterns

1. **SOAP/JAX-RPC over HTTP** (server-side): Apache Axis 1.4 servlet at `/Banker/*`. WSDL auto-generated. All 22 API operations exposed as a single SOAP service `BankerServiceAPIImplService`.
2. **SOAP client with noop fallback** (client-side, in `banker-common`): `bankerService-client.xml` uses Spring's `ProxyFactoryBean` + `ReloadableBean` to wrap the Axis JAX-RPC proxy. If the service is unavailable at startup, a `NoopBankerService` (throws `BankerServiceException("Banker is not available")`) is returned, preventing client app startup failure. On the next call, the proxy retries instantiating the real client.
3. **Stored procedure abstraction**: All DB operations go through Spring `StoredProcedure` subclasses (`DynamicFinanceStoredProcedure` for finance, `StoredProcedure` for banker/user). No ORM (no Hibernate, no JPA).
4. **Dynamic routing via regex map**: `ProgramStoredProcedureFactory` selects the correct GP database by matching the programId against a regex map loaded from `banker_program_datasource`. The longest matching regex wins. This is a bespoke service-discovery mechanism for multi-tenant GP databases.
5. **AOP for cross-cutting concerns**: Spring AOP (XML-configured) applies audit and exception handling to all manager-layer methods. Transaction management also applied via AOP.
6. **Command pattern for business actions**: Each API operation dispatches to a dedicated action class (e.g., `Authorize`, `GetAvailableFunds`, `SettleReservedSources`). All extend `BankerServiceAction` which holds the static reference to the singleton manager.
7. **Profile service integration**: Currency multiplier and program/relationship manager labels are fetched from cbase profile services using `RequestContext` + `Member` objects. Failures are silently caught and defaults applied — a defensive pattern appropriate for non-critical enrichment.

## Strategic Status

**Status: Legacy / Maintenance / CI-CD Template**

- This repo is explicitly named as a CI/CD testing area (README). Its primary production artifact (banker-service) is a Gen-1 service running on Axis 1.4 / Spring 2.0.8, which are severely end-of-life.
- The service is on **Wirecard/Northlane infrastructure** (`wirecard.sys` domain references throughout CI config), now migrated to Onbe's GitLab.
- CodeQL scanning has been enabled (`.github/workflows/codeql.yml`), and Dependabot is configured for weekly Maven updates — indicating active security maintenance.
- No evidence of active feature development; version `1.0.5-SNAPSHOT` has been in development for an indeterminate period.
- The "cicd-gala" naming and the two-WAR structure (`banker-service`, `banker-service2`) suggest this is also used for CI/CD pipeline development and validation using the banker codebase as a realistic but non-critical test subject.

## Migration Blockers

The following issues would need to be resolved before migrating this service to Gen-3 (cloud-native, REST/gRPC, Spring Boot):

1. **Axis 1.4 / JAX-RPC**: All callers depend on the SOAP WSDL contract (`urn:com.ecount.service.banker.api`). A REST rewrite requires API contract migration for all upstream consumers.
2. **Spring 2.0.8 / DTD-based XML config**: Requires full rewrite to annotation-driven or Java-config Spring Boot. No incremental upgrade path from 2.0.8 to 6.x.
3. **JVM singleton `BankerServiceManagerImpl`**: The singleton is initialized with in-memory state from DB at startup. Containerization (multiple pods) would require this state to be externalized or refresh logic added.
4. **`DirectorConfiguredDBCPdatasourceCreator` / Director registry**: This internal ecount service discovery mechanism has no equivalent in cloud-native stacks. All DB connections would need to be migrated to standard JDBC URL/credential management (e.g., AWS Secrets Manager, Vault).
5. **Multiple Great Plains DB routing**: The regex-based `ProgramStoredProcedureFactory` is a bespoke multi-tenancy solution. Migration requires designing a GP abstraction layer or moving to a consolidated database per environment.
6. **cbase platform dependencies**: `RequestContext`, `Member`, `AppProfileProgramCurrencyClass`, `NotificationManagerImpl`, `LabelTypesClass`, and `AppPromotionLabelProfileClass` are all internal ecount/cbase platform classes with no published API. These must be replaced with Onbe Gen-3 equivalents or microservice calls.
7. **SERIALIZABLE transaction isolation**: Must be re-evaluated for distributed/cloud deployment. SERIALIZABLE across multiple pods would require a distributed lock or optimistic concurrency redesign.
8. **`com.citi.prepaid.*` parent and dependencies**: Citi-era artifacts (`service-parent`, `request-context`) may not be available in Onbe's current artifact repositories without special handling.
9. **`xPlatform` dependency**: Unknown content of `com.ecount:xPlatform:2.5.47` creates undocumented risk if functionality is load-bearing.
10. **No unit or integration tests**: With `-Dmaven.test.skip=true` across all stages and commented-out test jobs, there is no automated regression safety net for migration.
