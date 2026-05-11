# billing-integration_LIB — DevOps & Operations View

## Build & Packaging

### Build System
- **Maven** multi-module project with `mvnw` wrapper (Maven 3.9.1, via `.mvn/wrapper/maven-wrapper.properties`)
- Parent POM: `com.parents:service-parent:9.0.0` (external, not in this repo)
- Root artifact: `com.ecount.service.billingIntegration:billingIntegration:1.0.0-SNAPSHOT` (packaging: `pom`)

### Active Module
- **`billingIntegration-pojo`** — compiled to `billingIntegration-pojo.jar` (Java 1.5 source/target)
  - Packaging: `jar`
  - Key dependencies: Hibernate 3.2.0.cr4, Spring 2.0, ehcache 1.2.3, jtds 1.2, commons-lang 2.2

### Inactive Module (commented out in root `pom.xml`, line 41)
- **`billingIntegration-ejb`** — would produce `billingIntegration-ejb.jar` (EJB 3.0)
  - Packaging: `ejb`
  - Extra dependencies: JBoss EJB3 microcontainer alpha8, JavaEE 5.0, `com.ecount.springutils:springutils-ejb3:1.0.1-SNAPSHOT`
  - The EJB application descriptor is in `billingIntegration-ejb/app/META-INF/application.xml` naming the EAR artifact `ecount-bisvc-ejb.jar`
  - This module is **not built** by default

### Java Target Version
- Java 1.5 (`<source>1.5</source>` / `<target>1.5</target>` in both POMs) — extremely outdated; Java 5 reached EOL in 2009

### Maven Repository Configuration
- `.mvn/wrapper/settings.xml` configures:
  - Nexus proxy at `https://d-na-stk01.nam.wirecard.sys:8081` (legacy Wirecard/Paywire infrastructure)
  - GitHub Packages at `https://maven.pkg.github.com/onbe/onbe_maven_releases`
  - Central at `https://repo1.maven.org/maven2`
- **Contains hardcoded credentials** for `nexus-qa`, `ecount.release`, `ecount.snapshot` servers (see Data Architect view)

---

## Deployment

### Runtime Target
The EJB module targets **JBoss Application Server** (referenced by JBoss annotations `@LocalBinding`, `@RemoteBinding`, JBoss EJB3 microcontainer, and JNP naming factory in test classes). The JNDI bindings are:
- Local: `BIService/local`
- Remote: `BIService/remote`

### Datasource Provisioning
All three datasources (`OrderDataSource`, `GreatPlainsDataSource`, `JobSvcDataSource`) are provisioned via JNDI lookup (`java:jdbc/OrderDataSource`, etc.) — meaning they must be configured in the application server's deployment descriptors outside this codebase.

### Spring Context Initialization
Two bootstrap paths:
1. **EJB path**: `beanRefContext.xml` (loaded by `AbstractGenericEJB3` via `BIServiceConstants.BI_BEAN_FACTORY_KEY = "com.ecount.service.bi"`) loads all four context files: `appContext-datasource.xml`, `appContext-hibernate.xml`, `appContext-jdbc.xml`, `appContext-bisvc.xml`
2. **Standalone path**: `BIAppContext` singleton loads only three context files (missing `appContext-jdbc.xml`, which means `GPCustomersDao`, `GPInventoryDao`, and `RateCardDataDao` would not be wired — this is a bug in the standalone context initializer)

### Artifact
The final deployable is a JAR (`billingIntegration-pojo.jar`) consumed by other services. The EJB layer, when built, produces `billingIntegration-ejb.jar` deployed inside a JBoss EAR.

---

## Configuration Management

### Environment-Specific Configuration
- **All datasource URLs are resolved at runtime via JNDI**; no environment-specific database URLs are embedded in production Spring XML files.
- Test-only `datasourceTestContext.xml` and `jboss-bisvc-beans.xml` embed server addresses (`ecsqldev1`) and credentials — these are in source control.
- The Maven `settings.xml` in `.mvn/wrapper/` contains production repository credentials committed to source control.

### Runtime-Tunable Parameters
- None. Fee scheme names, item codes (e.g., `1000`, `1010`, `10100`-`10140`, `1031`), and strategy mappings are **hardcoded** in Java source (`IssuanceFeePercentStrategy`, `IssuanceFeeFixedStrategy`, `RateCardStrategy`, `ReloadFeeStrategy`, `CommonFeeAssessor`) and in `appContext-bisvc.xml`.
- EhCache TTL: `timeToIdleSeconds=120`, `timeToLiveSeconds=120` for the default cache. `FeeScheme` and `ShippingFee` caches are `eternal=true` with no TTL — a cache refresh requires a JVM restart.

### No Externalized Configuration
- No property files, no environment variables, no Spring profiles. The only configuration files are Spring XML beans and Maven POMs.
- SCM reference in root `pom.xml` points to an SVN repository at `ecsvn.office.ecount.com` — a legacy internal Subversion server. The codebase has been migrated to Git (`.git` directory present) but the POM SCM block was never updated.

---

## Observability

### Logging
- **Log4j** (`log4j.xml` in test resources) with `ConsoleAppender` to stdout/stderr
- Production logging configuration is **not present** in the repository — expected to be provided by the application server or parent context
- Log level in all source classes: `log.debug(...)` for method entry/exit only; no structured logging, no log correlation IDs, no MDC usage
- `hibernate.show_sql=true` and `hibernate.generate_statistics=true` are enabled in **all** Hibernate session factory configurations in `appContext-hibernate.xml`, including the production config. This will emit raw SQL and Hibernate statistics to the application log at `INFO`/`DEBUG` level, potentially exposing financial data in logs.

### Metrics
- No metrics instrumentation (no Micrometer, no JMX beyond the commented-out `OrderSessionFactoryStatisticsJmxExporter` in test config)
- No health check endpoint

### Tracing
- No distributed tracing (no OpenTelemetry, no Sleuth)

### Alerting
- No alerting hooks. Silent failures on missing fee structures or exception-listed customers produce no observable signal.
- `BIServiceException` is an unchecked exception; whether it is caught and alerted on depends entirely on the consuming service.

---

## Infrastructure Dependencies

| Dependency | Type | Notes |
|---|---|---|
| Microsoft SQL Server | Database | Three instances: OrderSvc DB, GP/cbaseapp DB, JobSvc DB |
| JBoss Application Server | Runtime | Version not specified; references to JBoss EJB3 microcontainer alpha8 and JBoss JNP naming |
| JNDI provider | Naming | JBoss JNP (`org.jnp.interfaces.NamingContextFactory`) |
| GP `dbo.get_contract_pricing` stored proc | GP DB | Commented out in production code but present in `CallGetContractPricing.java`; the replacement is direct JDBC |
| GP `dbo.rate_card_data_summary` stored proc | JobSvc DB | Active; called via `CallRateCardDataSummary` for rate-card clients |
| `com.ecount.service.order:order-pojo:1.0.1` | Upstream JAR | Order domain model; `provided` scope — must be on classpath at runtime |
| `com.ecount.springutils:springutils-ejb3:1.0.1-SNAPSHOT` | EJB module only | JBoss-specific Spring EJB3 integration; SNAPSHOT version |
| Legacy Nexus at `d-na-stk01.nam.wirecard.sys` | Artifact repo | Wirecard/Paywire-era infrastructure; likely decommissioned |
| GitHub Packages `onbe/onbe_maven_releases` | Artifact repo | Used for production Maven artifacts |

---

## Operational Risks

1. **Java 1.5 target**: The library is compiled for Java 5 (EOL 2009), making it incompatible with modern JVMs and frameworks without recompilation. Running on a newer JVM requires the consuming application server to accept Java 5 bytecode.
2. **Spring 2.0 and Hibernate 3.2.0.cr4**: These are candidate-release versions from approximately 2006–2007. They receive no security patches. Known vulnerabilities exist in both.
3. **`eternal=true` EhCache** for `FeeScheme` and `ShippingFee`: Changes to fee configuration in the database will not be reflected without a JVM restart.
4. **`hibernate.show_sql=true` in production config**: Financial data in SQL logs; potential compliance violation and log volume risk in production.
5. **EJB module disconnected**: `billingIntegration-ejb` is commented out of the parent build. If the EJB is needed, it must be built manually, and there is no guarantee the SNAPSHOT parent POM version reference (`${pom.parent.version}`) resolves correctly.
6. **Silent order-skipping**: Missing fee structure or exception list match causes silent `return` with only a `log.debug()` message. If the consuming caller does not check a return value (the interface returns `void`), there is no signal that billing was skipped.
7. **Legacy Wirecard Nexus**: The primary artifact mirror (`d-na-stk01.nam.wirecard.sys`) references Wirecard infrastructure. Wirecard filed for insolvency in 2020; this host is likely unreachable, blocking fresh builds that rely on this mirror.
8. **BIAppContext missing `appContext-jdbc.xml`**: The standalone `BIAppContext` singleton does not load `appContext-jdbc.xml`, so `GPCustomersDao`, `GPInventoryDao`, and `RateCardDataDao` will not be instantiated when this context is used directly.

---

## CI/CD

### GitHub Actions
- `.github/workflows/codeql.yml`: CodeQL security analysis job
  - Triggers: `workflow_dispatch` and weekly schedule (Saturdays at 05:48 UTC)
  - Reuses a centralized workflow: `Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main`
  - Runner: `self-hosted`, `X64`, `Linux`, `ubuntu-docker`
  - **No build, test, or deployment job** — the only CI workflow is security scanning

### Dependabot
- `.github/dependabot.yml`: Weekly Maven dependency version update checks
- No auto-merge rules visible in this repository

### Gaps
- No automated build verification (compile + test) on pull requests
- No artifact publication pipeline visible in this repository
- No deployment pipeline (no Ansible, Terraform, Helm, or Docker found)
- No `Dockerfile` present
- All tests that actually call the database are commented out (`BIServiceTest`, `BIServiceBeanTest`); the only active test (`testVerifyClientSetup`) requires a live `ecsqldev1` database connection and will fail in any CI environment without that connectivity
