# banker_API — Solution Architect View

## Technical Architecture

### Module Structure

```
banker (parent POM, v4.0.4-SNAPSHOT, Java 21)
├── banker-common (JAR)
│   ├── com.ecount.service.banker.api        — BankerServiceAPI interface, NoopBankerService
│   ├── com.ecount.service.banker.domain     — BankerEmail, ProgramPromo, PromotionAmount, PromotionAttributes
│   ├── com.ecount.service.banker.dto        — 20 DTOs (request/response data objects)
│   ├── com.ecount.service.banker.exception  — 10 typed exceptions
│   ├── com.ecount.service.banker.utils      — LoggingUtil (XStream)
│   └── resources/com/ecount/banker/         — Spring XML for client-side proxy wiring
│
├── banker-impl (JAR)
│   ├── com.ecount.service.banker.api        — BankerServiceAPIImpl (extends ServletEndpointSupport)
│   ├── com.ecount.service.banker.core       — BankerServiceManagerImpl (singleton), PresetFundsConfig
│   ├── com.ecount.service.banker.core.action — 24 action classes (Command pattern)
│   ├── com.ecount.service.banker.dao.banker  — BankerDAOServiceImpl + 18 SP/JDBC wrappers
│   ├── com.ecount.service.banker.dao.finance — FinanceDAOServiceImpl + 14 SP wrappers + ProgramStoredProcedureFactory
│   └── com.ecount.service.banker.dao.user    — UserDAOServiceImpl + 2 SP wrappers
│
└── banker-service (WAR)
    ├── com.onbe.banker.health               — HealthCheck REST controller (GET /hc)
    └── jakarta.servlet.http.HttpUtils       — Compatibility shim for Axis on Jakarta EE 6
```

### Technology Stack

| Layer | Technology | Version |
|---|---|---|
| JVM | OpenJRE (Liberica) | 21 |
| Web container | Apache Tomcat | 10.1.28 |
| Servlet spec | Jakarta EE | 6.0 |
| SOAP framework | Apache Axis | 1.4 (Jakarta port, 2006 vintage) |
| IoC / DI | Spring Framework | XML-based (version from parent POM) |
| Transaction mgmt | Spring `DataSourceTransactionManager` | SERIALIZABLE, 120s timeout |
| JDBC | Spring `StoredProcedure`, `JdbcTemplate` | |
| Database | Microsoft SQL Server | mssql-jdbc 12.5.0.jre11-preview |
| Connection pool | HikariCP | 5.1.0 |
| Logging | Log4j2 + SLF4J + Lombok `@Slf4j` | |
| Serialization | XStream | (CVE-affected version, suppressed) |
| Build | Maven | 3.x |
| Container | Docker | Alpine-based |
| Orchestration | Kubernetes (AKS) | |

## API Surface

### SOAP Endpoint

- **URL pattern**: `/Banker/*` (Axis servlet mapping, `web.xml` line 56–59)
- **Service name**: `BankerServiceAPIImplService`
- **Port name**: `bankerServiceAPI`
- **Namespace**: `urn:com.ecount.service.banker.api`
- **WSDL**: Published to internal APIM via GitHub Actions (`PUBLISH_TO_APIM: true`, `INTERNAL_APIM: true`)
- **Backend suffix in APIM**: `/banker-service/Banker/bankerServiceAPI`
- **Protocol**: SOAP 1.1 over HTTP (RPC/encoded style, `http://schemas.xmlsoap.org/soap/encoding/`)

### SOAP Operations (from `BankerServiceAPI.java`)

| Operation | Input | Output | Key Exceptions |
|---|---|---|---|
| `auth` | `ClientSourceDTO` | `AuthReturnStatusDTO` | `BankerServiceException`, `BankerValidationException`, `BankerInvalidUserException`, `BankerAuthTestException`, `BankerMultiplePromotionsException`, `BankerMultipleOriginalSalesOrdersException`, `BankerNoActivePromotionsException`, `BankerInsufficientFundsException` |
| `authMultiple` | `ClientSourceDTO[]` | `AuthReturnStatusDTO[]` | Same as `auth` |
| `unAuth` | `SourceDTO` | void | `BankerServiceException`, `BankerValidationException` |
| `getActivePromotions` | `BankerRequestDTO` | `Integer[]` | `BankerServiceException`, `BankerValidationException` |
| `getPresetFundsConfig` | `BankerRequestDTO` | `PresetFundsConfigDTO` | `BankerServiceException`, `BankerValidationException` |
| `updatePresetFundsConfig` | `PresetFundsConfigDTO` | `int` | `BankerServiceException`, `BankerValidationException` |
| `getProgramInfo` | `BankerRequestDTO` | `ProgramInfoDTO` | `BankerServiceException`, `BankerValidationException` |
| `getFinanceBalances` | `BankerRequestDTO` | `FinanceBalancesDTO` | `BankerServiceException`, `BankerValidationException`, `BankerNoActivePromotionsException`, `BankerMultiplePromotionsException` |
| `reservePresetFunds` | `ClientSourceDTO` | `long` | `BankerServiceException`, `BankerMultiplePromotionsException` |
| `updatePresetFunds` | `ClientSourceDTO` | `UpdatePresetFundsResponse` | `BankerServiceException`, `BankerInvalidUserException`, `BankerSourceNotFoundException`, `BankerUpdatePresetFundsExceedAmountException` |
| `getAvailableFunds` | `BankerRequestDTO` | `AvailableFundsDTO` | Multiple |
| `useOutstandingPayments` | `BankerRequestDTO` | `boolean` | `BankerServiceException`, `BankerValidationException` |
| `getFinanceDocumentsBySources` | `SourceDTO[]`, `DocTypeDTO[]` | `FinanceDocumentDTO[]` | `BankerServiceException`, `BankerValidationException` |
| `getFinanceDocumentsBySource` | `SourceDTO`, `DocTypeDTO[]` | `FinanceDocumentDTO[]` | `BankerServiceException`, `BankerValidationException` |
| `getFinancePaymentsBySources` | `SourceDTO[]` | `FinancePaymentDTO[]` | `BankerServiceException`, `BankerValidationException` |
| `getFinancePaymentsBySource` | `SourceDTO` | `FinancePaymentDTO[]` | `BankerServiceException`, `BankerValidationException` |
| `get321DaysPayments` | `BankerRequestDTO` | `Payments321DaysDTO` | Multiple |
| `getReservedSources` | `BankerRequestDTO` | `ReservedSourceDTO[]` | Multiple |
| `settleReservedSources` | `BankerRequestDTO` | `UnsettledAmountsInfoDTO[]` | Multiple |
| `getUserGroupAuthorizationAmountLimt` | `String` (groupCode) | `long` | `BankerServiceException`, `BankerValidationException` |
| `sendApprovalNotification` | `BankerNotificationDTO` | `int` | `BankerValidationException`, `BankerServiceException` |
| `getDefaultPromoExceptionPrograms` | none | `String[]` | `BankerServiceException` |
| `getApprovalNotificationCounter` | `SourceDTO` | `int` | `BankerServiceException` |
| `cancelReservedSource` | `SourceDTO` | `int` | `BankerServiceException`, `BankerValidationException` |
| `forceSettleReservedSource` | `SourceDTO` | `int` | `BankerServiceException`, `BankerValidationException`, `BankerInvalidUserException` |
| `updateProgramExpressionsDatasourceNames` | `ProgramsDatasourcesDTO` | `int[]` | `BankerServiceException` |
| `deleteProgramExpressionsDatasourceNames` | `ProgramsDatasourcesDTO` | `int[]` | `BankerServiceException` |
| `getACHDelayDays` | `BankerRequestDTO` | `int` | `BankerServiceException` |
| `getMultipleSalesOrders` | `BankerRequestDTO` | `FinanceDocumentDTO[]` | `BankerServiceException` |
| `deleteMultipleSalesOrders` | `SourceDTO` | `int` | `BankerServiceException` |
| `insertMultipleSalesOrder` | `FinanceDocumentDTO` | `int` | `BankerServiceException` |

### REST Endpoint
- `GET /hc` → `"OK"` — Health check only (`HealthCheck.java`)

## Security Posture

### Authentication & Authorization
- **No transport-level authentication**: The Axis SOAP servlet (`/Banker/*`) has no `<security-constraint>` in `web.xml`. There is no HTTP Basic, OAuth, or mTLS configured at the application level.
- **Application-level authorization only**: Security relies entirely on the `userId` + `applicationId` passed inside each SOAP request body. `BankerServiceAction.findBankerUser()` validates these against the user DB stored procedure `banker_get_user_info`. If no user is found, `BankerInvalidUserException` is thrown.
- **Role enforcement**: `BankerRoleSetting` checks group membership strings against hardcoded role names (`bankerlevelone`, `bankerleveltwo`, `bankerlevelthree`, `bankerauthforce`, `bankersettleforce`, `bankerupdatefinancedatasources`). These are configurable via `banker.properties`.
- **Network trust boundary**: Security depends on network-level access controls (AKS network policies, internal load balancer) to prevent external access. The service should never be directly internet-accessible.

### Known Vulnerabilities (suppressed)

| CVE | Library | Suppression Location | Risk |
|---|---|---|---|
| CVE-2024-47072 | XStream | `.trivyignore` | XStream deserialization; Banker only serializes (write-only use in LoggingUtil), but shared library risk exists |
| CVE-2024-52316 | Tomcat | `.trivyignore` | Authentication bypass in certain Tomcat configurations |
| CVE-2024-22262 | Spring Framework | Both `.trivyignore` and `allowedlist.yaml` | Open redirect vulnerability |
| CVE-2024-38816 | Spring Web | `.trivyignore` | Path traversal |
| CVE-2024-50379 | Tomcat | `.trivyignore` | Race condition |
| CVE-2024-38819 | Spring MVC | `.trivyignore` | Path traversal |
| CVE-2024-56337 | Tomcat | `.trivyignore` | |
| CVE-2018-1000632 | XStream | `allowedlist.yaml` | XML injection |
| CVE-2020-10683 | dom4j (XStream dep) | `allowedlist.yaml` | XXE |

All suppressed CVEs should have formal risk acceptance documentation. Several are in actively used runtime components (Tomcat, Spring, XStream).

### Additional Security Observations
- `Authorize.java` lines 432–446: `BankerInsufficientFundsException` messages include `clientSourceDTO.getFinanceSourceId()` and `clientSourceDTO.getUserId()`. These are internal identifiers but should not appear in exception messages propagated to clients.
- `BankerRequestDTO.toString()` / `LoggingUtil.toXML()`: Full DTO serialization to logs at debug level. If logs are accessible to unintended parties, internal financial data is exposed.
- `Dockerfile` line 20: `storepass changeit` (the default JVM keystore password) is used to import the QA certificate. This is acceptable in QA but must not be used in production keystores.

## Technical Debt

| Item | Location | Severity | Description |
|---|---|---|---|
| Apache Axis 1.4 (2006) | `banker-impl/pom.xml`, `wsdl.xml` | Critical | SOAP framework abandoned in 2006; Jakarta port is a community workaround. No security updates. |
| `jakarta.servlet.http.HttpUtils.java` | `banker-service/src/main/java/jakarta/servlet/http/HttpUtils.java` | High | A class in the `jakarta.servlet.http` package placed directly in the application source. This overrides a platform class to provide compatibility for Axis, which is a fragile hack. |
| Spring XML configuration (no Spring Boot) | All `*-core.xml`, `*-dao*.xml`, `web.xml` | High | Entire Spring context wired via XML. No component scanning for business beans, no auto-configuration. Significant maintenance burden. |
| Static singleton `BankerServiceManagerImpl` | `BankerServiceManagerImpl.java` line 69–136 | High | Singleton pattern with manual `synchronized` getInstance(). In a multi-pod AKS deployment, each pod has an independent in-memory state. Live configuration updates (`updateProgramExpressionsDatasourceNames`) only affect the pod that processed the call. |
| Tests skipped in all CI | `.gitlab-ci.yml`, `github-package-publish.yml` | High | `maven.test.skip` prevents any regression detection in the build pipeline. |
| XStream in production DTO logging | `LoggingUtil.java`, all DTO `toString()` | Medium | Every DTO `toString()` call (including in log statements) uses XStream serialization. This is slow, produces verbose output, and has known CVEs. Standard `toString()` generation (Lombok `@ToString`) would be safer and faster. |
| Commented-out validation | `BankerServiceAction.java` lines 429–435 | Medium | `validateReferencedSourceAmount()` is commented out with a business justification comment. Dead code creates maintenance confusion. |
| Raw type usage | Multiple action classes | Low | Several `List<?>` casts (e.g., `StoredProcBankerGetReservedSources.java` line 80) use unchecked casts from stored procedure result maps. |
| Hard-coded IPs in docker-compose | `docker-compose.yaml` lines 19–20 | Low | `qa.nam.wirecard.sys:10.91.22.253` and `ppnaut.nam.wirecard.sys:10.91.22.254` are hard-coded legacy QA infrastructure IPs. |
| `mssql-jdbc:12.5.0.jre11-preview` | `banker-service/pom.xml` | Low | Using a preview/pre-release JDBC driver version. |
| Disabled PACT provider verification | `deployment.yml` line `VERIFY_PROVIDER_PACT: false` | Low | Contract drift between Banker and its consumers will not be caught automatically. |

## Gen-3 Migration Requirements

To migrate banker_API to a Gen-3 architecture (REST/JSON, Spring Boot, stateless, cloud-native), the following work is required:

### 1. API Layer Migration (SOAP → REST)
- Replace `BankerServiceAPIImpl extends ServletEndpointSupport` with Spring Boot `@RestController` classes.
- Replace `ClientSourceDTO`, `BankerRequestDTO` etc. with Jackson-serializable POJOs.
- Define OpenAPI 3.0 specification for all 30 operations.
- Remove Apache Axis 1.4, JAX-RPC, and WSDL entirely.
- Coordinate with all consumers (Job Service, Order Service, ClientZone) to migrate from SOAP client proxy (`bankerService-client.xml`) to REST clients.
- `PUBLISH_TO_APIM` workflow step needs to publish OpenAPI spec instead of WSDL.

### 2. Application Framework Migration
- Replace all Spring XML context files with Spring Boot auto-configuration and `@Configuration` classes.
- Replace `BankerServiceManagerImpl` singleton with a Spring-managed `@Service` bean (stateless or with proper cache management via Spring Cache abstraction / Redis for multi-pod consistency).
- Replace `web.xml` with `@SpringBootApplication` and embedded Tomcat.
- Remove `jakarta.servlet.http.HttpUtils.java` compatibility shim entirely.

### 3. Configuration Migration
- Replace `CBASE_HOME_URL` file-based property loading with Spring Boot `application.yml` / Kubernetes ConfigMaps and Secrets.
- Migrate Director-based datasource resolution to Spring Boot DataSource auto-configuration with AKS-managed secrets.

### 4. Stateless Cache Strategy
- Replace static singleton in-memory maps with a distributed cache (e.g., Azure Cache for Redis) to ensure consistency across AKS pod replicas.
- Implement cache invalidation on `updateProgramExpressionsDatasourceNames()` and program config changes.

### 5. Observability
- Add Micrometer metrics (authorization count, available-funds query latency, GP query latency).
- Add Spring Boot Actuator (`/actuator/health`, `/actuator/metrics`).
- Add distributed tracing (OpenTelemetry) for GP call instrumentation.
- Replace XStream-based DTO logging with structured logging (JSON fields).

### 6. Security Hardening
- Add authentication to the API (JWT/OAuth2 via Azure AD or an internal token service). Currently there is no transport-level authentication.
- Enable TLS at the container level (or enforce via AKS ingress with mTLS between services).
- Replace XStream in `LoggingUtil` with Lombok `@ToString` or custom `toString()` to eliminate CVE exposure and improve performance.
- Update all suppressed CVEs: evaluate each for actual exploitability and remediate or formally accept with documented rationale.

### 7. Testing
- Re-enable the existing JUnit tests in the CI pipeline (remove `maven.test.skip`).
- Write integration tests covering the authorization flow against an in-memory/mock GP datasource.
- Enable `VERIFY_PROVIDER_PACT: true` after migrating consumers.

### 8. Great Plains Abstraction
- The GP dependency is the deepest architectural coupling. For full Gen-3 readiness, a GP data access abstraction layer should be introduced (e.g., a Finance Data Service that encapsulates all GP stored procedure calls), so that if GP is replaced in future, Banker's core logic is isolated from the change.

## Code-Level Risks

1. **`BankerServiceManagerImpl.java` line 69**: `private static BankerServiceManagerImpl bankerServiceManagerImpl = null;` — Static singleton. In AKS with multiple replicas, `updateProgramExpressionsDatasourceNames()` only refreshes the pod that received the request. Other pods continue with stale datasource mapping until restarted.

2. **`Authorize.java` lines 432–446**: `BankerInsufficientFundsException` message constructed with `String.format(...)` including `clientSourceDTO.getFinanceSourceId()` and `clientSourceDTO.getUserId()`. This message is propagated to the SOAP client as a fault string. Internal operational identifiers are exposed in exception messages.

3. **`BankerServiceAction.java` line 98**: `BankerServiceAction()` constructor calls `BankerServiceManagerImpl.getInstance()` directly, creating a tight coupling between every action and the singleton. This makes unit testing of individual action classes impossible without the full singleton initialized.

4. **`ProgramStoredProcedureFactory.java` line 84**: `dynamicFinanceStoredProcedureClass.newInstance()` — Uses deprecated `Class.newInstance()` (removed in Java 17+; available in Java 21 via compatibility). Should be migrated to `Constructor.newInstance()`.

5. **`SendApprovalNotification.java` line 401**: `new NotificationManagerImpl()` — Direct instantiation of the notification manager, bypassing Spring DI. This prevents mocking in tests and creates a hidden dependency on eCountCore runtime being available.

6. **`LoggingUtil.java` line 7**: `private static XStream xStream = new XStream();` — Static XStream instance with no security configuration. Default XStream allows arbitrary class instantiation during deserialization. Even though Banker only uses it for serialization, the permissive configuration is a security hygiene concern.

7. **`banker-transaction.xml` line 24**: `timeout="120"` on all banker manager transactions. A 120-second lock hold on `SERIALIZABLE` isolation under high concurrency will cause severe lock contention. This was acceptable on low-volume Windows servers but may become a bottleneck at scale in AKS.

8. **`docker-compose.yaml` lines 19–20**: Hard-coded private IP addresses for legacy QA infrastructure (`10.91.22.253`, `10.91.22.254`). If QA infrastructure changes, local development using docker-compose will silently break.

9. **`StoredProcBankerGetReservedSources.java` line 110**: `sourceDTO.setNumPromosInSource((numPromosInSource == 0 ? 1 : numPromosInSource))` — Silently corrects a DB null/zero value by defaulting to 1. This is a data quality workaround embedded in the mapping layer without any warning log.

10. **`BankerServiceManagerImpl.java` lines 120–122**: Constructor body: `log.info("Test log.info call"); log.error("Test log.error call");` — Debug/test log calls left in the singleton constructor. These will emit a spurious `log.error` on every service startup, which may trigger alerting systems.
