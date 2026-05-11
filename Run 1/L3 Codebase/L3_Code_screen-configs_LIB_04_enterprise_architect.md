# Enterprise Architect View — screen-configs_LIB

## Platform Generation

**Gen-1** (eCount/Citi lineage). This library is a direct artifact of the original eCount platform, evidenced by:
- Package namespace `com.ecount.service.instissueczscreencfgs`
- Parent POM `com.citi.prepaid.service:service-parent:7`
- Spring 2.0.4 dependency (2007 vintage)
- Version scheme `2016.2.1` (date-based versioning consistent with eCount release practices)
- Internal Nexus URL referencing Wirecard/Northlane infrastructure (`d-na-stk01.nam.wirecard.sys`)
- JUnit 3.8.1 and Spring Mock test dependencies (pre-JUnit 4 era)

## Integration Patterns

- **Stored procedure call pattern**: All data access is through named SQL Server stored procedures via Spring JDBC (`JdbcTemplate` or equivalent). This is the canonical Gen-1 eCount data access pattern.
- **Spring XML configuration**: Application context wiring is via XML (`applicationContext-instIssueCZScreenCfg.xml`). No annotation-based or Java configuration.
- **Library consumption**: The library is a shared JAR consumed by multiple web applications via Maven dependency. It has no network interface of its own.
- **No REST, SOAP, or XML-RPC interface**: This library exposes a pure Java API only; it is not a service.

## External Dependencies

| Dependency | Version | Status |
|---|---|---|
| Spring Framework | 2.0.4 | Severely EOL (2007) |
| commons-logging | 1.1 | EOL |
| commons-lang | 2.3 | EOL |
| commons-collections | 3.2 | EOL + known CVE-2015-6420 |
| xPlatform | 2.5.28 | Internal eCount lib |
| sqljdbc | 1.1 | Ancient; EOL |
| junit | 3.8.1 | EOL |
| easymock | 2.3 | EOL |

All external dependencies are significantly EOL. The library is frozen in time.

## Position in the Broader Platform

screen-configs_LIB sits in the configuration layer of the Gen-1 instant-issue workflow:

```
clientzone_WAPP / cs-api family
  → screen-configs_LIB (configuration retrieval)
    → SQL Server (ecountcore / cbaseapp)
```

It is consumed by the Customer Zone (CZ) and Customer Service Agent (CSA) applications to drive the per-program instant-issue screen layout. It is a dependency of the eCount front-end web applications, not of the core processing pipeline.

Known or likely consumers:
- `clientzone_WAPP`
- `csa_WAPP` or `cs-api-*` family
- `bmcwizard_WAPP` (instant issue wizard)
- `enrollment_WAPP`

## Migration Blockers

1. **Spring 2.0.4**: Cannot be migrated to Spring Boot without a complete rewrite of the Spring XML configuration and all stored procedure call patterns.
2. **Generic column model**: The `column2..column5` pattern in `InstIssueCZScreenCfgRecord` cannot be trivially mapped to a typed domain model without understanding the stored procedure contracts, which are in SQL Server.
3. **Stored procedure coupling**: All business logic (filtering, status codes, flag key strings) is split between this library and SQL Server stored procedures. Migration requires refactoring both simultaneously.
4. **No tests beyond integration tests**: The test class (`InstIssueCZScreenCfgDaoTest`) appears to be an integration test requiring a live SQL Server connection. There are no unit tests that could validate behavior during a rewrite.
5. **eCount platform dependency** (`xPlatform:2.5.28`): This internal library must also be available or replaced during migration.

## Strategic Status

**Retire / Replace**. This library should not be migrated to Gen-3 as-is. The recommended path is:

1. **Short term**: Freeze all changes; patch `commons-collections` to 3.2.2 to mitigate CVE-2015-6420; document all stored procedure contracts.
2. **Medium term**: Replace screen configuration storage with Azure App Configuration or a dedicated configuration microservice. The business logic (flag merging, reason code filtering) should be re-implemented in the consuming service or a new Gen-3 configuration service.
3. **Long term**: Retire this library entirely once all consumers have migrated to the replacement configuration source.

The `2016.2.1` version indicates this library has been stable for approximately 9 years — a sign that the consuming applications have not changed their screen configuration requirements significantly, which makes replacement more feasible (low churn).
