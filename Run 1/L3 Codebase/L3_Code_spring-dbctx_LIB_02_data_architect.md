# Data Architect Report: spring-dbctx_LIB

## Data Models

This library does not define data models or schemas; it defines Spring bean configurations for connecting to databases. The schema ownership lies with the individual services and databases. However, the library's existence reveals the complete set of logical database partitions in the Gen-1/Gen-2 data architecture:

| Database | Content Category | PCI/PII Sensitivity |
|---|---|---|
| `cbaseapp` | Core card product configuration, access entity data, certificate templates | High (card product rules) |
| `ecountcore` | Cardholder master, balances, transaction records, ECount ODS | Critical (PANs, balances) |
| `greatplains` | General ledger, financial reporting | Medium (financial) |
| `jobsvc` | Batch job definitions, Quartz scheduler state, profile symbols | Low–Medium |
| `ordersvc` | Order management, disbursement tracking, request details, action definitions | Medium (PII in order records) |
| `repositorysvc` | Document/file storage service | Medium |
| `request` / `ordersvc` | Request tracking (alias/variant of order service) | Medium |
| `strongbox` | Asymmetric and symmetric cryptographic key store, encrypted data blobs | Critical (encryption keys) |
| `webcertomaha` | Card network certification data | Medium |

## Sensitive Data

**Critical sensitive data is accessible through these DataSources:**

- `ecountcore` DataSource provides access to the ECount core database which, based on other repos' evidence (`EcountCoreDAO`, `DdaInquiryRepository`, `LegacyCryptoService`), contains card numbers (potentially PANs), DDA numbers, and cardholder account data. This is the primary PCI DSS in-scope database
- `strongbox` DataSource provides access to the StrongBox key store database (tables `sb_get_asymmetric_key`, `sb_get_symmetric_key`). This database holds RSA private/public keys and symmetric key values for the platform's encryption infrastructure — the most sensitive database in the fleet
- `cbaseapp` DataSource provides access to certificate templates and access entity configurations used for cardholder product management

## Encryption Status

The library itself does not implement or enforce encryption. Encryption of data in the listed databases is the responsibility of:
1. The StrongBox service (for application-level encryption)
2. The database infrastructure (SQL Server Transparent Data Encryption)
3. Individual services (for field-level encryption before writing to any database)

Credential management for these DataSources follows the JNDI pattern: usernames and passwords are configured in the application server (Tomcat `server.xml` or JBoss `standalone.xml`) and injected at runtime. The library itself contains no hardcoded credentials — credential handling is correctly externalised to the container.

However, the `database.default.properties` file commits default timeout values (600 seconds) into a library JAR that is published to the internal Maven repository and included in all consuming services. Changes to these defaults require a library version bump and redeployment of all consumers.

## DataSource Configuration Pattern

```xml
<!-- Production pattern (JNDI) -->
<bean id="CbaseappDataSource" class="TransactionAwareDataSourceProxy">
  <constructor-arg ref="CbaseappDataSourceTarget"/>
</bean>
<bean id="CbaseappDataSourceTarget" class="JndiObjectFactoryBean">
  <property name="jndiName" value="jdbc/CbaseappDataSource"/>
  <property name="resourceRef" value="true"/>
</bean>
<bean id="CbaseappDataSourceTransactionManager" class="DataSourceTransactionManager">
  <property name="defaultTimeout" value="${service.cbaseapp.database.default.timeout}"/>
</bean>
```

The `TransactionAwareDataSourceProxy` wrapping ensures that JDBC operations participate in Spring-managed transactions. This is correct but means the library enforces a specific transaction model on all consumers.

## Retention and Data Flow Concerns

- The library creates beans that are bound to the Spring application context for the lifetime of the consuming service instance; DataSource connections are pooled at the JNDI container level
- The `strongbox` DataSource connecting to the cryptographic key database is configured identically to all other operational databases — it has no additional access restriction mechanisms beyond JNDI credentials
- No data masking, query auditing, or connection-level encryption enforcement is visible in the library's DataSource beans
- The 10-minute default transaction timeout (`service.*.database.default.timeout=600`) could result in long-lived transactions holding locks on tables that contain PAN data, creating a compliance and operational risk

## PCI DSS Compliance Assessment

- **Req 1 (Network)**: The JNDI configuration relies on the container to connect to databases on internal networks; the library cannot enforce network segmentation
- **Req 7 (Access restriction)**: The library imports are the only access gate at the code level; services that import `appCtx-strongbox-ds.xml` gain database-level access to cryptographic keys — this should require a security review of each consumer
- **Req 8 (Authentication)**: Credential management is delegated to JNDI container configuration; individual container configurations must use unique, strong credentials per service
- **Req 10 (Audit)**: No connection-level audit logging is enforced by the library; this is deferred to the individual service and database server
