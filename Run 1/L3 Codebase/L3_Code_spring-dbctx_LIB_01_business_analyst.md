# Business Analyst Report: spring-dbctx_LIB

## Business Purpose

spring-dbctx_LIB is a shared Java library that provides pre-configured Spring XML bean definitions for database DataSource connections used across the Onbe/eCount/Wirecard Gen-1 and Gen-2 platform. Its groupId `com.citi.prepaid.spring-dbctx` reveals its origin in the Citi/eCount period. The library eliminates copy-paste Spring DataSource configuration by publishing standardised, version-controlled DataSource bean definitions as Maven classpath resources. Each consuming service imports the relevant `appCtx-[dbname]-ds.xml` fragment rather than writing its own database wiring.

## Capabilities

The library provides DataSource configurations for nine named databases, in two variants each:

| Database Short Name | Purpose |
|---|---|
| `cbaseapp` | CBase application (core card and product management) |
| `ecountcore` | ECount core (balance, transaction, cardholder master data) |
| `greatplains` | Microsoft Great Plains (financial accounting/GL) |
| `jobsvc` | Job service (batch job scheduling, Quartz) |
| `order` / `ordersvc` | Order service (disbursement fulfilment) |
| `repositorysvc` | Repository service (document/file storage) |
| `request` | Request service (API request tracking) |
| `strongbox` | StrongBox (cryptographic key store) |
| `webcertomaha` | WebCert/Omaha (card network certification data) |

Each database has two distribution variants:
- **JNDI variant** (`appCtx-[name]-ds-jndi.xml`): Production and container deployments — delegates to a JNDI name registered in the application server (Tomcat, JBoss)
- **Container variant** (`appCtx-[name]-ds.xml`): Includes `JndiTemplate` bean for use when JNDI bootstrap is available within the Spring context

Additionally, a **mock/test variant** (`appCtx-[name]-ds-test.xml`) is provided in `spring-dbctx-mock` for unit and integration testing without a real JNDI context.

## Client and Cardholder Impact

Because `spring-dbctx_LIB` is a transitive compile-time dependency of nearly every Gen-1 and Gen-2 service, any change to this library's DataSource configuration affects the entire service fleet. The database connections configured here are the data access pathway to systems holding cardholder PAN data (ecountcore, cbaseapp), financial balances, cryptographic keys (strongbox), and operational records. A misconfiguration in this library could cause widespread service outages.

## Business Rules in Code

- Default transaction timeouts for all databases are 600 seconds (10 minutes) as defined in `database.default.properties`
- Each DataSource is wrapped in a `TransactionAwareDataSourceProxy`, ensuring Spring-managed transactions are honoured across the data access layer
- Each DataSource has its own `DataSourceTransactionManager`, enabling per-database transaction management
- JNDI lookup uses `resourceRef=true`, indicating the JNDI names are relative (`java:comp/env/jdbc/...` prefix applied automatically)

## Regulatory Obligations

- **PCI DSS Requirement 7**: The DataSource beans control access to cardholder data environments; the JNDI connection pool parameters (max connections, timeouts) must be sized appropriately to prevent denial-of-service conditions that could affect cardholder transaction processing
- **PCI DSS Requirement 8**: Connection credentials are managed at the application server (Tomcat/JBoss) JNDI resource level, not in this library; responsibility for credential management falls on the container configuration
- **PCI DSS Requirement 10**: Database connection activity through these DataSources feeds into audit logging at the service layer
- **GLBA**: The `greatplains` connection to the GL/accounting system falls under GLBA financial data protection obligations

## Key Business Risks

1. **Single library controls all database access**: A version bump in this library — even a minor one — propagates connection pool changes and JNDI name changes to all consuming services simultaneously; a breaking change could cause platform-wide database connectivity failure
2. **10-minute transaction timeout**: The default 600-second timeout is very long for a payments system; long-running transactions holding database locks could cause deadlocks in high-concurrency card transaction processing scenarios
3. **No connection pool configuration visible**: The library delegates pool management entirely to the JNDI container; pool sizing, validation queries, and leak detection are configured per-service in Tomcat/JBoss server.xml, creating inconsistent pool configurations across the fleet
4. **StrongBox DataSource in standard library**: The StrongBox database (cryptographic key store) is co-located in the same DataSource library as all other operational databases; this means any service that imports the wrong DataSource fragment could inadvertently gain access to the key store
