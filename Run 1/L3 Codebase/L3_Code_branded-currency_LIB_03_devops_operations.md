# branded-currency_LIB — DevOps & Operations View

## Build & Packaging

### Build System
- **Maven** multi-module project. Root POM at `E:\OnbeEast363\repos\branded-currency_LIB\pom.xml`.
- **Java version**: Compiler source and target both set to **Java 21** (`maven.compiler.source=21`, `maven.compiler.target=21`) in root `pom.xml`.
- **Maven Wrapper**: Present (`.mvn/wrapper/maven-wrapper.properties`, `maven-wrapper.jar`). Enables consistent build without a globally installed Maven.
- **Parent POM**: `com.parents:prepaid-parent:6.0.12` — an internal Onbe parent POM hosted in the GitHub packages registry (`https://maven.pkg.github.com/onbe/onbe_maven_releases`).

### Modules
| Module | Artifact | Packaging | Purpose |
|---|---|---|---|
| `branded-currency-common` | `branded-currency-common-3.0.3.jar` | JAR | Interfaces, VOs, DAO interfaces, exceptions, helper utilities |
| `branded-currency-impl` | `branded-currency-impl-3.0.3.jar` | JAR | Spring implementations of all interfaces, Spring XML context |

### Version
- Current version: **3.0.3** (defined in root `pom.xml`).

### Key Dependencies (from `pom.xml` files)
| Dependency | Version | Notes |
|---|---|---|
| `com.ecount:xplatform` | 6.1.9 | ECountCore / MoneyTransferHelper platform (internal) |
| `com.ecount:xplatformlibrary` | 4.0.1 | Additional ecount utilities |
| `com.wirecard.crossbordertransferservice:cbtsclient` | 2.1.4 | Cross-border transfer service client (Wirecard brand — legacy) |
| `org.springframework:spring-context` | from prepaid-parent | Dependency injection, `StoredProcedure`, `JdbcTemplate` |
| `junit` | from prepaid-parent (test scope) | Unit testing (JUnit 4/5 mix — tests use `@Test` from `junit.jupiter`) |
| Lombok | transitive via prepaid-parent | `@Slf4j` annotations used in `ClaimTransactionImpl`, `SpringCertificateDAO`, etc. |

### Enforcer Rules
- Both modules use `maven-enforcer-plugin` with `banTransitiveDependencies` to prevent unintended transitive dependency leakage. Exclusions are explicitly enumerated in each module's POM.

### Build Command
```
mvn clean install -Dmaven.test.skip
```
Tests are skipped during the standard build (documented in `README.md` and GitHub Actions workflow).

---

## Deployment

- This is a **library**, not a deployable application. It is published to the GitHub packages Maven registry (`https://maven.pkg.github.com/onbe/onbe_maven_releases`) and consumed by upstream services/applications.
- **Runtime prerequisite** (from `README.md`): Java 21, Tomcat 10.x+ (consumer application requirement), Windows OS recommended for local development.
- **Spring XML context**: `brandedCurrencyContext.xml` (in `branded-currency-impl/src/main/resources/`) must be imported by the consuming application's Spring context. The `CbaseappDataSource` bean must be provided by the consuming application's context (it is referenced by `<ref bean="CbaseappDataSource"/>` in all implementation beans).
- **Spring bean scope**: All transaction and service beans (`certificate`, `payment`, `claimTransaction`, etc.) are `scope="prototype"` in `brandedCurrencyContext.xml`, ensuring per-request instances. The `springBrandedCurrencyDAO` bean is not scoped (defaults to singleton).
- `BrandedCurrencyDAOFactory` uses a static singleton pattern; it is initialized once and reused across the JVM lifetime.

---

## Configuration Management

### Spring XML Configuration
- Production: `branded-currency-impl/src/main/resources/brandedCurrencyContext.xml`
- Test: `branded-currency-impl/src/test/resources/brandedCurrencyTestContext.xml`

**Critical finding**: `brandedCurrencyTestContext.xml` contains a hardcoded production-like SQL Server connection string and credentials:
```xml
<property name="url"><value>jdbc:jtds:sqlserver://ppamwdcdifsql1.nam.nsroot.net:2232/cbaseapp</value></property>
<property name="username"><value>[REDACTED — rotate immediately]</value></property>
<property name="password"><value>[REDACTED — rotate immediately]</value></property>
```
These credentials are committed to the repository in plaintext. The commented-out block above also references `ecsqldev1:1433/cbaseapp` with credentials `[REDACTED — rotate immediately]/[REDACTED — rotate immediately]`.

### Maven Settings
- `.mvn/wrapper/settings.xml` configures:
  - GitHub packages registry for dependency resolution.
  - Authentication uses `${env.GITHUB_TOKEN}` environment variable (correct pattern for CI).

### System Properties (from test classes)
Test classes (`CertificateTest`, `BulkPurchaseTransactionTest`) reference:
- `ecount.configfile` → `D:/c-base/config/ecount-config.xml`
- `cbase.systemid` → MAC address `00:50:DA:20:19:8F`
- `cbase.home` → `D:/c-base`

These are Windows-local development paths, confirming that integration tests require a local CBase installation.

### No Externalized Configuration
There are no `.properties`, `.yaml`, or environment-variable-driven configuration files in the library itself. All configuration is Spring XML and relies on the consuming application to inject the datasource.

---

## Observability

### Logging
- **Framework**: SLF4J with Lombok `@Slf4j` annotation used in:
  - `ClaimTransactionImpl` — logs pre-process, velocity check, begin, commit, post-process failure codes; logs transfer-ID details at ERROR level.
  - `SpringCertificateDAO` — logs member info errors.
  - `CreateCertificateSpringImpl`, `ClaimPaymentSpringImpl`, `CreatePaymentHistorySpringImpl`, etc. — `log.debug("{}", out)` for stored procedure output maps.
  - `UpdateTransactionStatus2SpringImpl` — `log.info()` with the raw SQL string including parameter values (potential sensitive data exposure — transferId, resultMessage are logged).
- **Test logging**: `log4j2-test.xml` present in both module test resources. Log4j2 is used for testing.

### Metrics
- No metrics instrumentation (no Micrometer, no Prometheus, no JMX MBeans) present in the library.

### Tracing
- No distributed tracing (no OpenTelemetry, no Zipkin/Sleuth) present.

### Health Checks
- No health check endpoints — this is a library, not a service.

### Audit Trail
- Business-level audit: `dbo.create_payment_action_item` records lifecycle events per payment. `dbo.create_user_transaction_history_item` and `dbo.update_transaction_status2` record transaction start and completion.

---

## Infrastructure Dependencies

| Dependency | Type | Version/Details |
|---|---|---|
| SQL Server `cbaseapp` | RDBMS | Via jTDS JDBC; server `ppamwdcdifsql1.nam.nsroot.net:2232` (test context) |
| ECountCore / xplatform | Internal platform | `xplatform:6.1.9` — money transfer engine |
| CBase platform (`com.cbase.*`) | Internal platform | Member management, transfer management, device management — not a Maven dep, resolved via xplatform/xplatformlibrary |
| cbtsclient (Wirecard CBTS) | Internal/legacy | `com.wirecard.crossbordertransferservice:cbtsclient:2.1.4` — cross-border transfer; likely legacy Wirecard integration |
| Notification service (`com.cbase.services.notification.StopNotificationService`) | Internal platform | Virtual card stop-notification |
| GitHub Maven Registry | Build/CI | `https://maven.pkg.github.com/onbe/onbe_maven_releases` |
| Java 21 JDK | Runtime | Required by compiler settings |
| Tomcat 10.x | Consumer app server | Noted in README but not a direct library dependency |

---

## Operational Risks

1. **Hardcoded credentials**: `brandedCurrencyTestContext.xml` contains SQL Server credentials in plaintext. If this file reaches a production build classpath, the credentials are directly accessible.
2. **jTDS driver (legacy)**: `net.sourceforge.jtds.jdbc.Driver` is the jTDS driver for SQL Server — an unmaintained open-source project. Microsoft's own MSSQL JDBC driver (`com.microsoft.sqlserver:mssql-jdbc`) is the supported alternative.
3. **No connection pool**: `DriverManagerDataSource` (Spring's non-pooling datasource) is used in the Spring context. This creates a new JDBC connection for every stored procedure call. Under load, this will exhaust database connections. A `HikariCP` or equivalent pool is absent.
4. **Static singleton DAO factory**: `BrandedCurrencyDAOFactory` holds a static reference to `brandedCurrencyDAO`. Redeployment without full JVM restart may retain stale state.
5. **Silent exception swallowing**: Multiple `catch (Exception e)` blocks in `ClaimTransactionImpl.execute()` log errors but do not re-throw, meaning callers receive a `TransactionStatusVO` that may indicate success even when downstream operations failed.
6. **SQL logged in plain text**: `UpdateTransactionStatus2SpringImpl.createPreparedStatement()` (line 84–98) logs the full SQL including `transactionId`, `resultCode`, `resultMessage`, and `ecountTransferId` via `log.info()`. This may expose transfer IDs in log aggregation systems.
7. **No circuit breaker**: No resilience pattern (Hystrix, Resilience4j) wraps calls to ECountCore or CBase MemberManager. Network failures will propagate as unhandled exceptions.
8. **Wirecard CBTS client**: Reference to `com.wirecard.crossbordertransferservice:cbtsclient:2.1.4` uses the Wirecard brand — a company that went bankrupt in 2020. This dependency's provenance and maintenance status should be confirmed (it may be an internal artifact renamed from a Wirecard codebase).

---

## CI/CD

### GitHub Actions Workflows

#### `github-package-publish.yml`
- **Triggers**: Push to `main`, pull request to `main`, manual `workflow_dispatch`.
- **Build args**: `-s ./.mvn/wrapper/settings.xml -Dmaven.test.skip` — tests always skipped in CI.
- **Reusable workflow**: Calls `Onbe/om-ci-setup/.github/workflows/java-package-publish.yml@main` — a centralized CI template.
- **Inputs supported**: version-tag override, auto-increment, dry-run, update-dependencies flags.
- **Secrets**: `secrets: inherit` — all repository secrets are passed through to the reusable workflow.
- **Publish destination**: GitHub Packages (`onbe_maven_releases`).

#### `codeql.yml`
- **Triggers**: Weekly schedule (Thursdays at 10:31 UTC), manual dispatch.
- **Runner**: `ubuntu-latest`.
- **Reusable workflow**: Calls `Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main`.
- CodeQL scans run on Java code.

#### `dependabot.yml`
- Weekly Maven dependency version checks.
- Targets root directory `/`.

### Missing CI Gates
- **No test execution in CI** (tests skipped via `-Dmaven.test.skip`). Tests appear to require live database and CBase infrastructure unavailable in CI.
- **No SAST beyond CodeQL** (no OWASP dependency-check, Snyk, etc.).
- **No container scanning** (library only — no Dockerfile present).
- **No artifact signing**.
