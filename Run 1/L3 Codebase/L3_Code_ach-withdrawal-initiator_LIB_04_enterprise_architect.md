# ach-withdrawal-initiator_LIB — Enterprise Architect View

## Platform Generation (Gen-1/Gen-2/Gen-3)

This component is **Gen-1/Gen-2**. The evidence:

- Spring Framework 2.0.3 (released 2007) — XML-only Spring context, no annotations, no Spring Boot.
- `ecount-system:2.0.0` and `xPlatform:7.0.16` — internal ecount/cbase platform libraries that are characteristic of the legacy Gen-1/2 stack.
- jTDS JDBC driver (`jtds:1.2`) — a legacy SQL Server JDBC driver superseded by Microsoft's official JDBC driver.
- `com.cbase.*` and `com.ecount.*` namespaces throughout — the original ecount/cbase monolithic platform naming conventions.
- No REST APIs, no OpenAPI, no microservices patterns, no containerization.
- Configuration via classpath properties and hard-coded filesystem paths (`d:/c-base/...`).
- Legacy `commons-dbcp:1.2.2` and `commons-pool:1.4` for connection pooling.
- Direct `StoredProcedure` class usage (Spring JDBC 2.x pattern) rather than any ORM or repository abstraction.
- Version `2.0.9-SNAPSHOT` with parent `service-parent:9.0.0` — consistent with the Gen-2 versioning scheme observed across Onbe legacy services.

The partial Gen-2 marker is the presence of MSAL4J (Microsoft Authentication Library) and a Tabapay REST API call, which are newer additions bolted onto the legacy process.

## Business Domain

**Payment Disbursement / ACH Rail Orchestration**

This component sits in the payment execution layer: it takes pre-queued disbursement instructions and drives them through the ACH network and push-to-debit rails. It is a critical path component for:

- Cardholder bank account withdrawals (prepaid card to bank account via ACH)
- Recurring auto-claim disbursements
- Push-to-debit card funding (Tabapay/Sunrise Bank pathway)
- Stop-payment processing for ACH transactions

Business domains touched: Consumer Disbursements, Prepaid Card Operations, ACH Payment Rail, Push-to-Card Rail.

## Role in Platform

This process occupies the **Payment Execution** layer between the **Order/Event Queue** (job tables in JobsvcDataSource and event tables in EcountCoreDataSource) and the **Payment Network** (ACH via ecount core platform, card networks via Tabapay).

```
Upstream Systems                   This Component                    Downstream
(web apps, APIs,        ──────►   ach-withdrawal-initiator_LIB   ──────►  ACH Network
 other batch jobs)                  (batch polling + execution)            (via ecount core)
                                                                    ──────►  Tabapay API
                                                                            (Push-to-Debit)
                                                                    ──────►  Notification Service
                                                                            (email to cardholder)
```

It is a **consumer** of queued job records and an **initiator** of actual payment network calls. It has no inbound API surface — it is entirely event-driven through database polling.

## Dependencies

### Upstream (produces data this component consumes)
- Web application or API layer that inserts rows into `JobsvcDataSource` ACH job tables and `EcountCoreDataSource` app-event tables.
- `autoclaimsplit-svc` / `autoclaimsplit-common` (`2.0.2-SNAPSHOT`) — the AutoClaim split service that produces claimable records.
- `brandedCurrency-common` / `brandedCurrency-impl` (`1.0.12`) — branded currency transaction management.

### Downstream (this component calls/writes)
- **ecount Core Platform** (`ecount-system:2.0.0`, `xPlatform:7.0.16`): `TransferManagerImpl`, `MemberManagerImpl`, `DeviceManagerImpl` — the central banking/transfer engine.
- **Tabapay/PushPay API**: External REST service for push-to-debit disbursements (authenticated via Microsoft Entra ID OAuth2).
- **Notification Service** (`NotificationManagerImpl`): Email notifications to cardholders.
- **Profile Service** (`ClassRetrieve` RPC): Program/label configuration lookup.
- **Comment Service** (`comment:2019.1.4`): Audit comment insertion for IDD auto-claim events.
- **Affiliate Service** (`xAffiliateService:2016.1.1`): Program branding and presentation data.
- **Director Service**: Runtime credential resolution for all three SQL Server data sources.

### Peer (shared infrastructure)
- SQL Server instances hosting `JobsvcDataSource`, `EcountCoreDataSource`, `CbaseappDataSource`.
- Microsoft Entra ID (Azure AD) tenant for OAuth2 client credentials.

## Integration Patterns

1. **Database Polling (Pull-based batch)**: The primary integration pattern. `IterativeProcess` polls SQL Server stored procedures in a loop, extracting batches of N records per iteration. There is no message queue, event bus, or push notification — purely poll-based.

2. **Stored Procedure Gateway**: All database interactions are through named stored procedures (`dbo.ach_transfer_initiate_extract`, `dbo.update_ach_transfer_detail_status`, etc.), implementing a stored-procedure gateway pattern. No direct table access.

3. **Internal RPC via Platform Library**: Calls to `TransferManagerImpl`, `MemberManagerImpl`, `DeviceManagerImpl` are synchronous in-process calls to library code that itself makes network calls to the ecount core platform. This is an opaque RPC pattern — no contract is visible in this repository.

4. **REST/HTTP for Tabapay**: `SharedServiceHelper` uses raw `HttpURLConnection` (no HTTP client library such as Apache HttpClient or OkHttp) to POST JSON to the Tabapay API.

5. **Spring XML Dependency Injection**: All wiring is through Spring 2.x XML bean definitions in `appContext-ach.xml`. No annotation-driven injection.

6. **Thread-Pool Fan-Out**: `ACHWithdrawalProcessMain` creates `Controller` threads per request type; each `Controller` creates a sub-thread pool of `RequestProcessorThread` workers. This is a manual producer-consumer pattern.

## Strategic Status

**Legacy — Maintenance Mode / Migration Candidate**

Indicators:
- Spring 2.0.3 (EOL since 2013); no migration to Spring Boot.
- jTDS JDBC driver (abandoned project since 2013).
- Java batch polling pattern predates modern event-driven architectures.
- Hard-coded Windows path (`d:/c-base/`) is incompatible with container or cloud-native deployment.
- SNAPSHOT dependencies (`autoclaimsplit 2.0.2-SNAPSHOT`) suggest ongoing but fragile maintenance.
- Tests skipped in CI, suggesting low confidence in test coverage.
- Dead code in `Load.java` `loadAutoClaimRequests()` (commented-out implementation replaced by `System.out.println`).
- The addition of MSAL4J and Tabapay API call as a "bolt-on" to an otherwise legacy codebase is a risk indicator — mixing modern OAuth2 auth with a decade-old batch framework.

The repository name suffix `_LIB` may indicate this is the shared library component of a larger batch system, with the actual scheduler/runner in a separate repository.

## Migration Blockers

The following issues must be resolved before this component can be migrated to a Gen-3 architecture:

1. **Hard-coded Windows filesystem path**: `file:///d:/c-base/config/achwithdrawal/achwithdrawal.properties` must be replaced with environment-variable-driven or secrets-manager-driven configuration before containerization is possible.

2. **Director service dependency**: The `DirectorConfiguredDBCPdatasourceCreator` is a proprietary ecount/cbase pattern for credential injection. A Gen-3 migration must either port this to a supported secrets manager (Azure Key Vault, AWS Secrets Manager) or refactor to standard JDBC connection properties.

3. **Internal RPC library coupling**: Calls to `TransferManagerImpl`, `MemberManagerImpl`, `DeviceManagerImpl` via `ecount-system:2.0.0` represent deep coupling to the Gen-1/2 core platform. Gen-3 migration requires either:
   - Exposing these capabilities as REST APIs from a Gen-3 core service, or
   - Parallel-running until the transfer engine is also migrated.

4. **Spring 2.x XML context**: `appContext-ach.xml` and the `ClassPathXmlApplicationContext` pattern must be replaced with Spring Boot / annotation-driven configuration.

5. **SNAPSHOT dependencies**: `autoclaimsplit-common:2.0.2-SNAPSHOT` and `autoclaimsplit-svc:2.0.2-SNAPSHOT` must be released to fixed versions before any production migration.

6. **jTDS JDBC driver**: Must be replaced with the Microsoft JDBC Driver for SQL Server (`mssql-jdbc`) before SQL Server 2019+ compatibility is guaranteed.

7. **Stored procedure coupling**: 10+ stored procedures form the integration surface between this component and the database. Gen-3 migration must document and potentially replace or wrap these procedures.

8. **No containerization**: No Dockerfile, no health endpoint, no Kubernetes readiness/liveness probes. A Gen-3 deployment would need all of these added before orchestration is feasible.

9. **Dead code risk**: `Load.java` `loadAutoClaimRequests()` returns `null` after a debug print statement. This must be investigated and resolved before any migration that changes the active processing path.

10. **Log PII exposure**: Full card/cardholder data logged to disk file — must be remediated before production deployment in a PCI DSS compliant Gen-3 environment.
