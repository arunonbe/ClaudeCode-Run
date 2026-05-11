# ecore-batch_LIB — Enterprise Architect View

## Platform Generation
**Gen-1** — Java 5, Spring Framework 2.5.6, Spring Batch 2.1.1.RELEASE (released ~2010), commons-dbcp 1.2.2, Apache Commons Logging 1.1. Original development by OFSS offshore team, June 2010. This is among the oldest active Java codebases in the estate. While it has a GitHub repository and Dependabot configured (suggesting some modern DevOps tooling awareness), the core library remains unchanged from its 2010 state.

## Business Domain
**Payments Processing — eCount Core Batch Automation**
- Sub-domain: ACH Withdrawal Notifications (NACHA/Reg E)
- Sub-domain: IEFT (International Electronic Funds Transfer) Notifications
- Sub-domain: Core Transaction Processing (Commit/Cancel)
- Sub-domain: Card/Device Provisioning

Serves: eCount payment processing platform; cardholder-facing notification pipeline.

## Architectural Role
The **asynchronous event processor and notification dispatcher** for eCount Core. This library bridges the gap between eCount's transactional database (EcountCore) and its notification/communication services. It is invoked as a standalone batch process (JAR + `.bat` / `.vbs` launcher), not as an embedded library.

```
[EcountCore SQL Server — pending events/transactions]
        |
[ecore-batch JAR — Spring Batch]
        |
        +--[read]--> EcountCore stored procs (events, transactions)
        +--[call]--> StrongboxService (bank credentials)
        +--[call]--> eMember service (cardholder data)
        +--[call]--> Profile service (program config)
        +--[call]--> Notification service (email delivery)
        +--[write]--> EcountCore stored procs (dispatch begin/end)
```

## Integration Patterns
- **Spring Batch partitioned reader-processor-writer** — standard batch ETL pattern
- **Stored procedure-based data access** — `StoredProcedureItemReader` for all DB reads
- **Service locator factory** (`NotificationEventHandlerFactory`) — handler selection by event name string matching
- **Director-managed connection pooling** — `DirectorConfiguredDBCPdatasourceCreator` abstracts connection management to an eCount-specific service registry
- **Spring 2.x XML configuration** — pre-annotation, XML-driven IoC container
- **Fire-and-forget notification** — notifications dispatched via `NotificationManagerImpl.deliver()` with result receipt but no retry mechanism visible

## External System Dependencies
| System | Dependency Type | Notes |
|---|---|---|
| EcountCore (SQL Server) | JDBC | Primary data source |
| Director service | Service registry / connection factory | Required for all DB connections |
| Strongbox (cbase RepositoryService) | Proprietary cbase API | Bank credential store |
| ECountCore eMember service (EMemberInquiryExtendedService) | Proprietary cbase service | Cardholder data |
| Profile service (AppPromotionLabelProfileClass) | Proprietary cbase service | Program labels |
| Notification service (NotificationManagerImpl) | Proprietary cbase service | Email delivery |
| xPlatform (com.ecount.xPlatform 3.0.16) | Internal library | Cross-platform utilities |
| director-client (com.ecount.service.Core2.director 1.0.11) | Internal library | Director client |
| ecount-system (com.ecount.service.Core2 1.0.10) | Internal library | eCount system library |

## Strategic Status
- **Active Gen-1 — Critical path** — this library directly processes ACH and IEFT payment notifications, making it a **Reg E compliance-critical component**. It cannot be decommissioned without a fully tested replacement.
- Spring Batch 2.1.1 and Spring 2.5.6 are end-of-life (Spring Framework 2.x EOL was 2013); no security patches available from Spring.
- Java 5 target is unsupported; Java 5 was EOL in 2009.
- The library is tightly coupled to proprietary eCount/cbase internal APIs (`com.cbase.*`, `com.ecount.*`) — reuse outside the eCount platform is not feasible without major refactoring.

## Migration Blockers
1. **cbase proprietary API dependency** — all `com.cbase.*` service calls (Strongbox, eMember, Notification, Profile) must be replaced with Onbe platform APIs before migration.
2. **Director service dependency** — `DirectorConfiguredDBCPdatasourceCreator` is an eCount-specific DB connection factory; must be replaced with standard connection pool (HikariCP) or cloud-native secret store.
3. **Spring Framework 2.5.6 / Spring Batch 2.1.1** — major upgrade (to Spring Boot 3.x / Spring Batch 5.x) required; XML config must be converted to annotation-based or Java config.
4. **Reg E compliance continuity** — no gap in ACH notification processing is acceptable; replacement must be fully tested before cutover.
5. **Notification template logic** — IDD reject flow, ACH template logic, and IEFT template logic are embedded in Java classes; must be extracted and replicated in the new platform's notification engine.
6. **Hardcoded Windows deployment paths** — migration to Linux/container requires removal of `D:\c-base\` path references.
7. **OFSS/unknown current ownership** — migration requires an engineer who understands the processing logic; knowledge transfer needed.
