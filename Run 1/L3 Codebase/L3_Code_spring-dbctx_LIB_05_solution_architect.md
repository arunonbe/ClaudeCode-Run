# Solution Architect Report: spring-dbctx_LIB

## API Surface

This is a library with no HTTP API surface. Its "interface" is the set of Spring bean definitions exported as classpath resources and the named beans available for injection after import:

| Bean ID | Type | DataSource |
|---|---|---|
| `CbaseappDataSource` | `TransactionAwareDataSourceProxy` | cbaseapp SQL Server |
| `CbaseappDataSourceTransactionManager` | `DataSourceTransactionManager` | cbaseapp |
| `EcountcoreDataSource` | `TransactionAwareDataSourceProxy` | ecountcore SQL Server |
| `StrongBoxDataSource` | `TransactionAwareDataSourceProxy` | strongbox SQL Server |
| `JobsvcDataSource` | `TransactionAwareDataSourceProxy` | jobsvc SQL Server |
| `OrderDataSource` | `TransactionAwareDataSourceProxy` | order SQL Server |
| *(similar pattern for all 9 databases)* | | |

## Security Posture

**Adequate for a library; risks arise in consuming services.**

- The library correctly delegates credential management to JNDI containers — no hardcoded credentials
- The library does not log SQL statements or data, so it does not directly create a log-based data disclosure risk
- However, the library provides no access control between databases: a service that imports both `appCtx-ecountcore-ds.xml` and `appCtx-strongbox-ds.xml` gets DataSource beans for both the cardholder database and the cryptographic key database in the same application context, with no isolation between them

**Key security concern — StrongBox DataSource co-location**:

The `appCtx-strongbox-ds.xml` file (`spring-dbctx-container/src/main/resources/com/ecount/resources/db/appCtx-strongbox-ds.xml`) imports the same JNDI pattern used for all operational databases. Any developer can add `appCtx-strongbox-ds.xml` to their service's Spring context and obtain a DataSource to the cryptographic key database. There is no discovery mechanism in the library that lists which services are currently importing the strongbox DataSource, making access control auditing very difficult.

## Critical Findings

1. **StrongBox DataSource bundled with operational DataSources** (`spring-dbctx-container/src/main/resources/.../appCtx-strongbox-ds.xml`):
   - The cryptographic key store database is accessible via the same library mechanism as all operational databases; no special access control or approval process is enforced at the library level
   - PCI DSS Requirement 7 requires that access to cardholder data environments be restricted by business need — the library architecture makes it trivially easy to add access to the key database without a security review

2. **Default 10-minute transaction timeout** (`spring-dbctx-root/src/main/resources/.../database.default.properties`, lines 1–9):
   - A 600-second transaction timeout is 60x longer than typical OLTP transaction targets; this risks long-held database locks on PAN-containing tables in the ecountcore database during transaction failures

3. **No connection pool parameters in library**:
   - Pool sizing, max connections, validation queries, and connection leak detection are not standardised in the library; each consuming service's JNDI container configuration may have inconsistent or missing pool settings, creating operational risk

4. **`TransactionAwareDataSourceProxy` on every DataSource**:
   - This wrapper is appropriate for single-database services but can cause unexpected behaviour (phantom enlistment in transactions) when multiple DataSources are active in the same thread; services using multiple databases from this library require careful transaction boundary management

## Technical Debt

- **Spring XML-only**: All configuration is in XML; no Java config, no Spring Boot autoconfiguration; incompatible with `spring-boot-starter-data-jpa` without custom `DataSourceAutoConfiguration` exclusion in consuming services
- **GroupId reflects Citi origin**: `com.citi.prepaid.spring-dbctx` should be renamed to `com.onbe.*` or `com.ecount.*` to reflect current ownership; changing the groupId requires a coordinated upgrade across all consumers
- **Mock DataSource using `ExpectedLookupTemplate`**: The test module's `ExpectedLookupTemplate` (`spring-dbctx-mock/src/main/java/com/ecount/resources/db/mock/jndi/ExpectedLookupTemplate.java`) is a bespoke JNDI mock; modern testing would use H2 in-memory databases or Testcontainers, removing the JNDI dependency even in tests
- **Version 2.0.1 with SNAPSHOT in parent**: The parent POM references SNAPSHOT versions for some internal dependencies (based on other repos' patterns); consuming services that transitively pull SNAPSHOT dependencies introduce build non-reproducibility
- **Java 21 compiler target with Spring XML**: Spring XML bean definition parsing is heavy reflection-based code that requires `--add-opens` JVM flags in Java 21; this is a hidden operational burden on all consuming services
