# cancel-transaction-process_LIB — Enterprise Architect View

## Platform Generation (Gen-1/Gen-2/Gen-3)

**Classification: Gen-1**

Evidence:
- Spring Framework 2.5.6 (2008-era) declared in `pom.xml` `<spring.version>2.5.6</spring.version>`.
- Spring XML-only configuration (no annotations, no Spring Boot, no `@Configuration` classes).
- JUnit 3 test framework (`junit:junit:3.8.1`).
- Apache Commons Logging / Log4j (pre-SLF4J/Logback era stack).
- `org.springframework.util.Log4jConfigurer` (deprecated/removed in Spring 5+).
- Fat JAR with `maven-assembly-plugin` using the legacy `attached` goal (deprecated in Maven Assembly Plugin 2.2+).
- Dependency on `com.ecount:xPlatform:2013.1.2` and `com.ecount.service.Core2:ecount-system:2.0.0` — proprietary ecount Gen-1 platform libraries.
- `SpringUtils` uses a double-checked locking `ClassPathXmlApplicationContext` pattern typical of pre-Spring-Boot era applications.
- Parent POM `com.citi.prepaid:prepaid-parent:3` and group IDs under `com.citi.prepaid` indicate Citi-era heritage (pre-Northlane, pre-Onbe branding).
- Artifact version `1.0.1-SNAPSHOT` with no semantic versioning strategy.

---

## Business Domain

**Payments Operations — Prepaid Card Disbursements**

This library belongs to the **transaction lifecycle management** subdomain within the prepaid card platform. Specifically, it handles the **cancellation** leg of the debit transfer lifecycle — cleaning up stale pending transfers that have not been committed or cancelled by the normal payment flow.

Relevant platform domains:
- Prepaid card issuance and lifecycle
- B2C disbursements (debit transfers to cardholder accounts)
- Financial reconciliation and audit

---

## Role in Platform

This is a **batch housekeeping library** that acts as a **compensating control** in the transaction lifecycle. Its role is:

1. **Recover from stuck/stale pending transfers** that the primary payment processing path failed to finalise (commit or cancel).
2. **Maintain data integrity** in the Core (ecount) transaction state machine by driving pending transfers to a terminal state (CANCELLED).
3. **Update debit audit records** in the CBase application database to reflect the cancellation outcome.

It does **not** serve real-time requests, expose APIs, or participate in message-driven flows. It is a scheduled batch process invoked by an external job scheduler.

In platform architecture terms, this is a **Gen-1 batch job library** that wraps a Spring-managed application context and is packaged as a fat JAR for CLI invocation.

---

## Dependencies

### Upstream (what this component depends on)

| Dependency | Type | Artifact / Identifier |
|---|---|---|
| Core (ecount) database | Infrastructure | `coreDataSource` / `${ecountcore.database}` via Director |
| CBase App database | Infrastructure | `cbaseappDataSource` / `${cbaseapp.database}` via Director |
| ecount Core2 system | Library | `com.ecount.service.Core2:ecount-system:2.0.0` |
| ecount xPlatform | Library | `com.ecount:xPlatform:2013.1.2` |
| ecount Director service | Infrastructure | `director.address` — provides DBCP-managed connection strings |
| ecount SpringUtils | Library | `com.citi.prepaid.springutils:springutils-generic:1.0.9` |
| spring-dbctx | Library | `com.citi.prepaid.spring-dbctx:spring-dbctx-container:1.0.6` |
| ecount director-client | Library | `com.ecount.service.Core2.director:director-client:1.0.11` |
| Core API (ecore) | Service call | `com.cbase.business.core.impl.TransferManagerImpl` / `ECoreTransfer` |
| prepaid-parent POM | Build | `com.citi.prepaid:prepaid-parent:3` |

### Downstream (what depends on this component)

This is a library/process with no inbound service interface. It is invoked by an external scheduler. No downstream consumers of its programmatic API are identifiable from this repository alone.

---

## Integration Patterns

| Pattern | Implementation | Notes |
|---|---|---|
| Stored procedure invocation (read) | `CorePendingTransactionsInquiry` extends Spring `StoredProcedure` | Calls `core_pending_transactions_inquiry` function against Core DB |
| Stored procedure invocation (write) | `UpdateDebitAuditInfo` extends Spring `StoredProcedure` | Calls `card_balance_debit_update_job` against CBase App DB |
| Service API call (synchronous) | `ITransferManager.cancel(Transfer)` via `ECoreTransfer` | Calls Core business layer to cancel transfer; response is synchronous |
| Spring XML IoC / DI | `cancelTransactionProcessContext.xml`, `dataSource.xml`, `appCtx-jmx.xml` | Classic Spring 2.x XML bean wiring; no annotation-driven injection |
| JMX management interface | `ControllerJMXExporter` / `MBeanExporter` | Runtime operational visibility and control via JMX |
| ThreadPoolExecutor (concurrent tasks) | `Controller` uses injected `ThreadPoolExecutor` | Parallelism level is configurable; default appears single-threaded in practice |
| Request context propagation | `IRequestContextHolder` + `MDCWriter` | Global Request UUID propagated across threads via ThreadLocal and Log4j MDC |
| Batch CLI process | `CancelTransactionProcessMain.main()` | Standard Java process, invoked from bat script |

There is **no messaging (JMS/Kafka/MQ), REST API, SOAP, or event-driven integration** in this library. All integration is synchronous: DB stored procedures and direct API calls.

---

## Strategic Status

**Status: Legacy — Gen-1, candidate for decommission or Gen-3 re-platforming**

Indicators:
- Group ID `com.citi.prepaid` reflects the Citi lineage; the platform has since been rebranded to Northlane and then Onbe.
- SCM URL references `gitlab.com/northlane` while GitHub CI references `Onbe/om-ci-setup`, confirming ongoing migration.
- Spring 2.5.6 and JUnit 3 are end-of-life technologies with no security patch support.
- ecount Core2 and xPlatform dependencies tie this component to the Gen-1 ecount platform stack, which is a known migration blocker.
- The library version is `1.0.1-SNAPSHOT` — it has never been formally released, suggesting active (if slow) development or operational drift.
- The disabled `-transfer` single-transfer mode (`"Bad boy."` validation comment) suggests incomplete functionality and low investment in ongoing development.
- No meaningful test coverage (one `assertTrue(true)` stub).

---

## Migration Blockers

1. **Hard ecount/cbase platform coupling.** The component directly depends on `com.ecount:xPlatform`, `com.ecount.service.Core2:ecount-system`, `com.cbase.business.core.ITransferManager`, and `com.cbase.business.core.spi.ecore.ECoreTransfer`. All of these are Gen-1 proprietary library dependencies with no Gen-3 equivalent identified in this repository. Migration requires either wrapping these APIs behind an abstraction layer or replacing them with Gen-3 service equivalents.
2. **ecount Director-managed data sources.** `DirectorConfiguredDBCPdatasourceCreator` is an ecount-specific connection pool factory. Gen-3 migration would require replacing this with a cloud-native data source (e.g., Spring Boot DataSource auto-configuration, connection pool via cloud secret manager).
3. **Spring XML configuration.** No annotation-driven or Spring Boot configuration exists. A Gen-3 equivalent would require full rewrite of IoC configuration.
4. **No API surface to migrate.** This is a CLI batch process, not a service. A Gen-3 equivalent might be implemented as a scheduled microservice (e.g., Spring Batch, Kubernetes CronJob, or AWS Lambda), representing a significant architectural change.
5. **Stored procedure dependency.** `core_pending_transactions_inquiry` and `card_balance_debit_update_job` are database-owned stored procedures. Migration requires either retaining stored procedures (less likely in Gen-3) or replacing them with service/repository layer equivalents.
6. **`com.cbase.pi.log.SystemLog`** referenced in `UpdateDebitAuditInfo.java` — another Gen-1 platform logging class that must be replaced.
7. **`CBASE_HOME_URL` environment variable convention.** Gen-3 would use cloud-native configuration management (e.g., AWS Parameter Store, Kubernetes ConfigMaps), not a filesystem path convention.
