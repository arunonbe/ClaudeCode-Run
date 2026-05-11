# cicd-gala_SVC — Solution Architect View

## Technical Architecture

### Module Layout
```
cicd-gala (pom, version 1.0.5-SNAPSHOT)
├── banker-common          JAR — API interface + DTOs + exceptions + client Spring config
├── banker-impl            JAR — business logic + all DAO implementations
├── banker-service         WAR — web descriptor + Spring XML wiring (instance 1)
├── banker-service2        WAR — web descriptor + Spring XML wiring (instance 2, identical)
└── banker-tester          WAR — web-based test harness using service-test-web framework
```

### Layering
```
SOAP Layer         BankerServiceAPIImpl (extends ServletEndpointSupport)
                        |  delegates 1:1 to
Service/Manager    BankerServiceManagerImpl (singleton, AOP-wrapped)
                        |  dispatches to
Action Layer       BankerServiceAction subclasses (Authorize, GetAvailableFunds, ...)
                        |  use
DAO Layer          BankerDAOServiceImpl, UserDAOServiceImpl, FinanceDAOServiceImpl
                        |  execute
DB Layer           StoredProcedure / JdbcTemplate / DynamicFinanceStoredProcedure
                        |  against
Databases          Banker DB (SQL Server), User DB (SQL Server), GP DB (SQL Server, multiple)
```

### Key Design Decisions
- **Singleton manager with JVM-cached state**: `BankerServiceManagerImpl.getInstance()` returns a static singleton holding four in-memory maps loaded at `init()`. Thread safety relies on SERIALIZABLE DB transactions and the singleton initialization being `synchronized`.
- **Action pattern**: Each of the 22 API operations has a dedicated action class in `banker-impl/src/main/java/com/ecount/service/banker/core/action/`. All extend `BankerServiceAction`, which holds the reference to the singleton manager and provides shared utilities (validate, findBankerUser, hasBankerAuthAccess, populateActualParentAndActivePromos, updateBankerReservedSources, etc.).
- **Dynamic finance stored procedure factory**: `ProgramStoredProcedureFactory` holds a map of `programExpression → FinanceStoredProcedures`. For each configured program expression, it instantiates all 12 finance stored procedure classes against the corresponding GP datasource at startup. The factory selects the correct set by matching the programId (exact, then longest-regex). This supports multi-tenant GP deployments without code changes.
- **Noop client proxy**: `banker-common` ships a Spring client configuration (`bankerService-client.xml`) that wraps the Axis JAX-RPC proxy in a `ReloadableBean`. If Banker Service is down at the consuming application's startup, a `NoopBankerService` (throws `BankerServiceException`) is used instead of preventing startup. On the next invocation the real proxy is retried.

## API Surface

### SOAP Endpoint
- **Servlet**: `org.apache.axis.transport.http.AxisServlet` at `/Banker/*` (web.xml, line 47–56)
- **Service name**: `BankerServiceAPIImplService`
- **Port name**: `bankerServiceAPI`
- **Namespace**: `urn:com.ecount.service.banker.api`
- **WSDL**: `${banker.service.wsdl.url}` (external property)

### API Operations (BankerServiceAPI interface — 22 methods)

| Method | Input | Output | Throws |
|---|---|---|---|
| `auth` | `ClientSourceDTO` | `AuthReturnStatusDTO` | `BankerServiceException`, `BankerValidationException`, `BankerInvalidUserException`, `BankerAuthTestException`, `BankerMultiplePromotionsException`, `BankerMultipleOriginalSalesOrdersException`, `BankerNoActivePromotionsException` |
| `authMultiple` | `ClientSourceDTO[]` | `AuthReturnStatusDTO[]` | Same as auth |
| `unAuth` | `SourceDTO` | void | `BankerServiceException`, `BankerValidationException` |
| `getActivePromotions` | `BankerRequestDTO` | `Integer[]` | `BankerServiceException`, `BankerValidationException` |
| `getPresetFundsConfig` | `BankerRequestDTO` | `PresetFundsConfigDTO` | `BankerServiceException`, `BankerValidationException` |
| `updatePresetFundsConfig` | `PresetFundsConfigDTO` | `int` | `BankerServiceException`, `BankerValidationException` |
| `getProgramInfo` | `BankerRequestDTO` | `ProgramInfoDTO` | `BankerServiceException`, `BankerValidationException` |
| `getFinanceBalances` | `BankerRequestDTO` | `FinanceBalancesDTO` | `BankerServiceException`, `BankerValidationException`, `BankerNoActivePromotionsException`, `BankerMultiplePromotionsException` |
| `reservePresetFunds` | `ClientSourceDTO` | `long` | `BankerServiceException`, `BankerMultiplePromotionsException` |
| `updatePresetFunds` | `ClientSourceDTO` | `UpdatePresetFundsResponse` | `BankerServiceException`, `BankerInvalidUserException`, `BankerSourceNotFoundException`, `BankerUpdatePresetFundsExceedAmountException` |
| `getAvailableFunds` | `BankerRequestDTO` | `AvailableFundsDTO` | `BankerServiceException`, `BankerValidationException`, `BankerMultiplePromotionsException`, `BankerMultipleOriginalSalesOrdersException`, `BankerNoActivePromotionsException` |
| `useOutstandingPayments` | `BankerRequestDTO` | `boolean` | `BankerServiceException`, `BankerValidationException` |
| `getFinanceDocumentsBySources` | `SourceDTO[]`, `DocTypeDTO[]` | `FinanceDocumentDTO[]` | `BankerServiceException`, `BankerValidationException` |
| `getFinanceDocumentsBySource` | `SourceDTO`, `DocTypeDTO[]` | `FinanceDocumentDTO[]` | `BankerServiceException`, `BankerValidationException` |
| `getFinancePaymentsBySources` | `SourceDTO[]` | `FinancePaymentDTO[]` | `BankerServiceException`, `BankerValidationException` |
| `getFinancePaymentsBySource` | `SourceDTO` | `FinancePaymentDTO[]` | `BankerServiceException`, `BankerValidationException` |
| `get321DaysPayments` | `BankerRequestDTO` | `Payments321DaysDTO` | `BankerServiceException`, `BankerValidationException`, `BankerMultiplePromotionsException`, `BankerNoActivePromotionsException` |
| `getReservedSources` | `BankerRequestDTO` | `ReservedSourceDTO[]` | `BankerServiceException`, `BankerNoActivePromotionsException`, `BankerInsufficientFundsException`, `BankerMultiplePromotionsException` |
| `settleReservedSources` | `BankerRequestDTO` | `UnsettledAmountsInfoDTO[]` | `BankerServiceException`, `BankerValidationException`, `BankerNoActivePromotionsException`, `BankerMultiplePromotionsException` |
| `getUserGroupAuthorizationAmountLimt` | `String` (userGroupCode) | `long` | `BankerServiceException`, `BankerValidationException` |
| `sendApprovalNotification` | `BankerNotificationDTO` | `int` | `BankerValidationException`, `BankerServiceException` |
| `getDefaultPromoExceptionPrograms` | — | `String[]` | `BankerServiceException` |
| `getApprovalNotificationCounter` | `SourceDTO` | `int` | `BankerServiceException` |
| `cancelReservedSource` | `SourceDTO` | `int` | `BankerServiceException`, `BankerValidationException` |
| `forceSettleReservedSource` | `SourceDTO` | `int` | `BankerServiceException`, `BankerValidationException`, `BankerInvalidUserException` |
| `updateProgramExpressionsDatasourceNames` | `ProgramsDatasourcesDTO` | `int[]` | `BankerServiceException` |
| `deleteProgramExpressionsDatasourceNames` | `ProgramsDatasourcesDTO` | `int[]` | `BankerServiceException` |
| `getACHDelayDays` | `BankerRequestDTO` | `int` | `BankerServiceException` |
| `getMultipleSalesOrders` | `BankerRequestDTO` | `FinanceDocumentDTO[]` | `BankerServiceException` |
| `deleteMultipleSalesOrders` | `SourceDTO` | `int` | `BankerServiceException` |
| `insertMultipleSalesOrder` | `FinanceDocumentDTO` | `int` | `BankerServiceException` |

### Stored Procedures Invoked (Finance DB — Great Plains)
Names embedded in `BankerQuerys` constants (class not read but referenced in `StoredProcBankerGetFreeFunds.java` line 26):
- `banker_get_free_funds`
- `banker_get_unsettled_funds`
- `banker_get_all_unsettled_funds`
- `banker_get_active_promotions`
- `banker_get_program_info`
- `banker_get_documents`
- `banker_get_payments`
- `banker_get_321_payments`
- `banker_get_ach_delay`
- `banker_get_multiple_sos`
- `banker_delete_multiple_sos`
- `banker_insert_multiple_so`

### Stored Procedures Invoked (Banker DB)
Inferred from `StoredProc*` class names:
- `banker_get_reserved_sources`, `banker_get_reserved_source`
- `banker_update_reserved_source`, `banker_delete_reserved_source`, `banker_delete_reserved_sources`
- `banker_get_preset_funds_configs`, `banker_update_preset_funds_configs`
- `banker_get_approval_notification_counter`, `banker_update_approval_notification`
- `banker_update_program_datasource`, `banker_delete_program_datasource`

### Stored Procedures Invoked (User DB)
- `banker_get_user_info` (by userId + applicationId)
- `banker_get_user_info_by_group_name` (by groupName + applicationId)

## Security Posture

### Authentication & Authorization
- **No transport-layer authentication**: The SOAP endpoint has no HTTP Basic Auth, client certificates, or API keys configured in `web.xml`. Any network-reachable client can call `auth()`.
- **Application-level user validation**: Callers supply `userId` and `applicationId` in the DTO; the service validates these against the user DB. This provides logical access control but not transport security.
- **Role-based operation control**:
  - `auth` / `authMultiple`: Requires at least `bankerlevelone` (or `bankerauthforce`) group membership.
  - `forceSettleReservedSource`: Requires `bankersettleforce` group.
  - `updateProgramExpressionsDatasourceNames` / `delete...`: Requires `bankerupdatefinancedatasources` group.
  - `cancelReservedSource`: No role check beyond valid user lookup.
  - Read-only queries (`getProgramInfo`, `getFinanceBalances`, etc.): No role check — any valid userId/applicationId can query.
- **Currency multiplier for test sources**: `Authorize.authorizeTestSource()` applies a currency multiplier before comparing against `MAX_TEST_SOURCE_AMOUNT = 50000`, preventing easy bypass via foreign-currency programs.

### Transport Security
- Service runs on HTTP (port 31337 per CI config `PROJECT_SERVICE_DEV_PORT: 31337`, `PROJECT_SERVICE_PROTO: http`). SOAP payload containing financial amounts and user data is unencrypted in transit.
- Nexus artifact repository accessed over HTTP.
- No TLS/HTTPS configured at the application level.

### Dependency Vulnerabilities
- **Apache Axis 1.4** (2006): End-of-life; multiple known CVEs exist (e.g., deserialization, SSRF in WSDL processing). The WSDL URL is externally configurable (`${banker.service.wsdl.url}`), creating SSRF risk in the client.
- **Spring 2.0.8** (2007): End-of-life; numerous CVEs resolved in later versions.
- **JUnit 3.8.1**: Not a runtime concern.
- **commons-lang 2.2** (2006): CVE-2017-15708 (remote code execution via serialization in Quartz) — not directly applicable but the library is very old.
- **xstream 1.2.1**: XStream has a long history of deserialization CVEs; version 1.2.1 is severely out of date.
- CodeQL scans are configured (`.github/workflows/codeql.yml`) to catch new findings weekly.
- Dependabot configured for weekly Maven updates — will open PRs but currently all dependency updates appear un-merged (SNAPSHOT version suggests active development, but no recent commit history is visible).

### Injection Risk
- All database access goes through Spring `StoredProcedure` and `JdbcTemplate` with parameterized inputs. No string-concatenated SQL is observed in the read code.
- `ProgramStoredProcedureFactory.getInstance()` uses `programExpression.matches(key)` where `key` is a regex from the database. If an attacker could insert a malicious regex into `banker_program_datasource`, ReDoS is possible. Access to this table is controlled by the `bankerupdatefinancedatasources` role.

### Audit
- AOP `BankerAuditMethodInterceptor` on all manager methods.
- `updatedBy` userId recorded in `banker_reserved_source` on every mutation.
- No centralized audit log sink (SIEM) visible in this code.

## Technical Debt

1. **Axis 1.4 / JAX-RPC**: The SOAP stack is 18+ years old. `BankerServiceAPIImpl` extends `ServletEndpointSupport`, which was deprecated in Spring 2.x and removed in Spring 3.x. Migration to JAX-WS, REST, or gRPC is required.

2. **Spring 2.0.8**: Incompatible with Java 17+. Cannot run on modern JVMs without significant patches. Spring security patches have not been available since Spring 2.x went EOL.

3. **Singleton with mutable state** (`BankerServiceManagerImpl`): The static singleton pattern is incompatible with containerized/multi-instance deployments. Multiple JVM instances would each have independent caches that could diverge.

4. **`BankerServiceAction` holds static singleton reference** (line 45: `bankerServiceManagerImpl = BankerServiceManagerImpl.getInstance()`): All action classes directly access the singleton. This makes unit testing without integration infrastructure impossible.

5. **No unit tests running**: `MAVEN_TEST_OPTS: "-Dmaven.test.skip=true -Pno-it"` across all CI stages. The test infrastructure exists (`banker-impl/src/test/resources/`) but is never executed in CI.

6. **`System.out.println` in production code** (`SendApprovalNotification.java`, line 274): Unguarded stdout write in a financial service method.

7. **Commented-out validation** (`BankerServiceAction.java`, lines 434–436): `validateReferencedSourceAmount` is permanently disabled with a comment indicating a business decision. This removes a guard against over-authorization of reference sources.

8. **Two identical WARs** (`banker-service`, `banker-service2`): No differentiation in source. Maintenance burden of keeping both in sync; any configuration divergence creates inconsistent behavior.

9. **`xstream 1.2.1`**: Used by `LoggingUtil.toXML()` to serialize DTOs for debug logging. This version has multiple deserialization CVEs and is 15+ years old.

10. **`Payments321DaysDTO` class name**: The class name encodes a business concept in a non-descriptive numeric form (`321` days). This naming reduces maintainability.

11. **`banker-tester` module uses Java 1.5 source/target** (pom.xml, line 53): Inconsistent with the parent's Java 1.8 target. The tester module was not updated when the main service moved to Java 8.

12. **`MAVEN_DEPLOY_OPTS` name collision**: In `.gitlab-ci.yml`, `MAVEN_DEPLOY_OPTS` is defined at the job variable level AND inherited from the included template. The project-level override value is `"-Dmaven.test.skip=true -Pno-it"` but this shadows the template value, making the effective behavior non-obvious.

## Gen-3 Migration Requirements

To migrate this service to Onbe's Gen-3 platform (assumed: Spring Boot 3.x, REST/gRPC, containerized, cloud-native):

| Requirement | Effort | Notes |
|---|---|---|
| Replace Axis 1.4 SOAP with REST or gRPC | High | Requires API contract changes for all callers; new DTO serialization (JSON/Protobuf) |
| Upgrade to Spring Boot 3.x | High | Requires Java 17+; complete rewrite of Spring XML config to annotations/Java config |
| Replace `DirectorConfiguredDBCPdatasourceCreator` | High | Needs cloud-native DB connection management (Secrets Manager, HikariCP, etc.) |
| Replace cbase profile services | High | Identify Onbe Gen-3 equivalents for currency, notification, and label profile APIs |
| Externalize and TTL in-memory caches | Medium | Use distributed cache (Redis) or event-driven refresh for authorization rules |
| Replace manual singleton with Spring-managed bean | Medium | Remove `getInstance()` pattern; use `@Service` + dependency injection |
| Redesign SERIALIZABLE TX for distributed deployment | Medium | Use optimistic locking or distributed lock (Redisson) for `banker_reserved_source` |
| Replace JUnit 3.8.1 with JUnit 5 | Low | Also requires writing actual unit tests |
| Replace xstream 1.2.1 with a safe serializer | Low | For logging only; switch to Jackson or SLF4J structured logging |
| Remove `System.out.println` | Low | Replace with `logger.debug()` |
| Consolidate `banker-service` and `banker-service2` | Low | Single WAR/container image; environment differences via config |
| Enable CI test execution | Low | Remove `-Dmaven.test.skip=true`; implement and run tests |
| Implement HTTPS/TLS | Medium | Configure TLS at load balancer or service mesh level |

## Code-Level Risks

1. **`BankerServiceManagerImpl.java` line 80**: Static field `bankerServiceManagerImpl` is the singleton. The `getInstance()` method is `synchronized`, but the fields set in `init()` (lines 136-140) are not synchronized. If `init()` is called concurrently with a service call (e.g., after `updateProgramExpressionsDatasourceNames` triggers a `financeDAOService.init()`), there is a potential for reading partially-initialized state.

2. **`Authorize.java` line 274** (in `createProgramRelationMgrs`): `System.out.println(labelTypeId + ": " + appLabelTypeCollection.getAppPromotionLabel(labelTypeId).getLabelText())` — this is unconditional stdout output in a financial operation method. If the label text contains sensitive program information, this is an uncontrolled data leak.

3. **`ProgramStoredProcedureFactory.java` line 108** (`getInstance` is `synchronized`): The entire factory method is synchronized. Under high concurrency, all GP database calls queue on this single lock, creating a throughput bottleneck.

4. **`BankerServiceAction.java` lines 560-570** (`validateClientSourceAmount`): When an existing source has a higher amount than the to-be-authorized source, the to-be-authorized source's amount is silently replaced with the existing amount (`toBeAuthedSource.setSourceAmount(existingSourceDTO.getSourceAmount())`). The caller is not notified of this substitution, which could result in authorizing more than requested.

5. **`Authorize.java` lines 237-241**: `approxSourceAmount` stores the original client-provided amount before GP lookup. After `findSalesOrderAndPopulateSourceAmount` updates `clientSourceDTO.setSourceAmount(...)` with the GP sales order subtotal, `clientSourceDTO.setSourceAmount(approxSourceAmount)` restores the original. The GP amount is used internally for the funds check but the original amount is returned to the caller. This is intentional per the comment but creates a subtle dual-amount state in the same mutable DTO.

6. **`NoopBankerService.java`**: All 31 methods throw `BankerServiceException("Banker is not available")`. If the service is unavailable and the `ReloadableBean` fallback is triggered, callers get an exception on every operation with no retry logic in this layer.

7. **`BankerRoleSetting.java` line 58** (`getHighestBankerAuthorizationLevel`): Returns `null` if none of the user's roles match `BANKER_LEVELS`. The caller (`Authorize.checkAvailableFunds` via `hasAuthorizationPrivileges`) then passes `null` to `getUserGroupAuthorizationAmountLimit`, which could produce a `NullPointerException` or incorrect authorization decision if the caller's role-checking logic has a gap.

8. **`FinanceDAOServiceImpl.java` line 41**: `init()` calls `programStoredProcedureFactory.init()` which creates live database connections for all program expressions. This is called from `BankerServiceManagerImpl.init()` at application startup — if any configured datasource is unavailable, startup fails entirely.

9. **`banker-transaction.xml` line 24-26**: Transaction propagation is `REQUIRED` with `SERIALIZABLE` isolation and 120-second timeout applied to every method matching `BankerServiceManager.*`. Read-only queries (e.g., `getProgramInfo`, `getActivePromotions`) are unnecessarily included, adding transaction overhead to read operations.
