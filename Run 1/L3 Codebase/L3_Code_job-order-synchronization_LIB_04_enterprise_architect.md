# Enterprise Architect View — job-order-synchronization_LIB

## Platform Generation and Heritage

This library is a first-generation eCount/Citi Prepaid service-layer artifact. Evidence:
- Parent POM is `com.citi.prepaid.service:service-parent:8` (`pom.xml` line 4-7), indicating Citi Prepaid heritage predating the Onbe brand
- Package root is `com.ecount.service.jobordersync` — the `ecount` namespace traces to the original eCount prepaid platform acquired by Citi/Northlane
- Hibernate annotations dependency (`hibernate-annotations:3.2.0.cr3`, `pom.xml` line 95) is a 2007-era artifact used only as `provided` scope — a vestigial dependency from an earlier ORM-based design
- Spring 2.0 XML namespace in `applicationContext.xml` (`spring-beans-2.0.xsd`) — despite the codebase evolving, the Spring wiring schema has not been updated to modern syntax
- SCM URL references GitLab `northlane/` namespace, indicating the Northlane/Wirecard acquisition lineage

The library is currently at version **2.0.3-SNAPSHOT**, suggesting it has undergone at least one major refactor (v1.x → v2.x).

## Role in the Batch Backbone Architecture

This component sits at the **seam between two independent state machines**:

```
[Client Upload] → [Repository SVC] → [Job Service (job_file)] → [Job Order Synchronizer] → [Order Service (file_order)]
                                                                      ↑
                                                            (scheduled reconciliation)
```

The Job Service owns batch execution state; the Order Service owns the commercial/billing view of the same work. This library is the **sole reconciliation mechanism** between those two views. Without it, the Order Service would never know that a batch has completed, blocking client billing and reporting.

## System Dependencies

### Upstream (reads from)
- **Job Service DB** (`jobsvc` SQL Server): `job_file`, `job_order`, `job_order_sync_event` tables
- **`job-common` LIB** (`com.citi.prepaid.service.job:job-common:2.0.13`): Domain value objects for job state — notably `JobStatistics` used in `hasErrors()` check
- **`order-common` LIB** (`com.citi.prepaid.service.order:order-common:3.0.21`): `FileOrder`, `OrderStatus` domain types

### Downstream (writes to)
- **Order Service HTTP API** (`FileOrderManager` Spring HttpInvoker): Creates and updates `file_order` records. The HTTP timeout is configurable via `job.order.sync.file.order.manager.read.timeoutMillis` and `connect.timeoutMillis`
- **`job_order_sync_event` table**: Audit records of each run

### Infrastructure
- **Director Service** (`director-client:1.0.11`): Provides dynamic data source configuration (connection strings, credentials) at runtime from a central configuration server — critical for multi-environment deployment

## Inter-Service Coupling Analysis

The design uses **HTTP Invoker** (Java-serialization-based RPC) to call the Order Service, rather than REST or messaging. This is a tightly-coupled, brittle integration pattern. If the Order Service serialization contract changes, this library will fail at runtime with `ClassNotFoundException` or `InvalidClassException`, often without a clear error message. This is the primary modernization risk.

## Migration Complexity Assessment

| Factor | Assessment |
|---|---|
| Java version | Java 8-era code; migrating to 17+ requires removing `hibernate-annotations:3.2.0.cr3` and auditing reflection usage |
| Spring version | Spring 2.0 XML wiring; no `@Component` scanning — full XML rewrite needed for Spring Boot migration |
| HTTP Invoker | Must be replaced with REST client (WebClient, RestTemplate, Feign) — breaking change to Order Service contract |
| Database access | Plain JDBC via Spring `JdbcTemplate` — relatively clean; could be migrated to Spring Data JDBC |
| CLI entry point | `Main.java` uses Spring ClassPathXmlApplicationContext — needs to become a Spring Boot `CommandLineRunner` |
| Test coverage | No test files observed in this library — high regression risk for any change |
| Operational dependency | Any change to `JobStatus`/`OrderStatus` enum values in `order-common` or `job-common` would silently break the status mapping in `applicationContext.xml` |

**Overall migration complexity: HIGH** — the library is load-bearing for billing accuracy, has no tests, uses obsolete RPC patterns, and has an implicit contract with two other services that themselves need migration.

## Compliance Positioning

Under PCI DSS v4.0 Requirement 12.3 (targeted risk analysis for batch jobs touching payment data), this component should be formally documented as a **payment data processing control** because:
1. It determines when disbursement batch records are marked `PROCESSED` in the Order Service
2. `PROCESSED` status is the trigger for client billing and settlement reporting
3. Silent failures in this component could allow double-billing or missed billing

SOC 1 audit controls for completeness and accuracy of disbursement processing should include controls over this reconciler's run frequency, failure alerting, and reconciliation thresholds.
