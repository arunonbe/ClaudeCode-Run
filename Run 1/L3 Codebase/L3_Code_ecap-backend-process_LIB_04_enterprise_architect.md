# ecap-backend-process_LIB — Enterprise Architect Report

## Platform Generation

`ecap-backend-process_LIB` is a **Generation 1 (Gen-1) component** of the Onbe East platform. Evidence:
- Author attribution "OFSS" (Oracle Financial Services Software, formerly i-flex Solutions) appears throughout Javadoc comments — this indicates the library was originally developed by an offshore OFSS team for eCount/Citibank Prepaid circa 2007–2012
- Parent POM `com.citi.prepaid:prepaid-parent:3` confirms Citibank prepaid origin
- Spring 2.0.8 was released in 2007; Java 1.7 target is characteristic of development frozen circa 2012–2013
- The xPlatform version (`2.5.28`) and ecount-system version (`2.0.0`) are Gen-1 library versions
- The SCM URL (`gitlab.com/northlane/development/application-development/libraries/ecap-backend-process`) shows it has been migrated from CVS/SVN to GitLab at some point

---

## Role in the Enterprise Architecture

### Layer: Batch Processing / Card Issuance
ECAP occupies the **asynchronous card issuance processing layer** — it is the workhorse that fulfills queued card creation requests. It is the Gen-1 predecessor to the more modern `auto-card-batch_LIB` and order fulfillment patterns visible in the broader repo inventory.

```
┌──────────────────────────────────────────────────────────────┐
│  Cardholder Portal / ECAP Web Layer (separate service)       │
│  (Receives card creation requests from purchasers)           │
└──────────────────────────┬───────────────────────────────────┘
                           │ queues requests in DB
┌──────────────────────────▼───────────────────────────────────┐
│  ecap-backend-process_LIB (THIS LIBRARY)                     │
│  - Reads pending requests from DB                            │
│  - Executes state machine (create member, create card, etc.) │
│  - Sends email notifications                                 │
│  - Updates status in DB                                      │
└──────────────────────────┬───────────────────────────────────┘
                           │ delegates to
┌──────────────────────────▼───────────────────────────────────┐
│  eCount Core (xPlatform / ecount-system / cbase layer)       │
│  - EnrollmentManagerImpl (member creation)                   │
│  - DeviceManagerImpl (card device creation)                  │
│  - TransferManagerImpl (fund transfer)                       │
│  - NotificationManagerImpl (email delivery)                  │
└──────────────────────────────────────────────────────────────┘
```

### Dependency Map

**Services that depend on ecap-backend-process_LIB:**
- The ECAP web application / portal (not in this repo scope) — uses this as a library for processing
- Scheduled batch job executors (cron/job service) — invoke `EcapCardCreationClient.main()`

**Libraries ecap-backend-process_LIB depends on:**
- `com.ecount:xPlatform:2.5.28` — the core eCount business platform library (Gen-1)
- `com.ecount:xPlatformLibrary:1.0.11` — extended platform utilities
- `com.ecount.service.Core2:ecount-system:2.0.0` — EcountCore system integration
- `com.ecount.service.Core2.director:director-client:1.0.9` — data source routing
- `com.ecount.services:comment:1.0.0` — audit comment library
- `com.ecount.one.service.affiliate:xAffiliateService:1.0.6` — affiliate/program service
- `com.ecount.service.xmlrpc:xmlrpc:1.0.6` — XML-RPC communication (Gen-1 IPC protocol)

---

## Integration Points with Other Repositories

| Repository | Integration Type | Direction |
|---|---|---|
| `xplatform_LIB` / `xplatform-library_LIB` | Library dependency (xPlatform business layer) | ecap depends on xPlatform |
| `ecount-system_LIB` | Library dependency (EcountCore system) | ecap depends on ecount-system |
| `director-client_LIB` | Library dependency (DB routing) | ecap depends on director |
| `xml-rpc_LIB` / `xml-rpc-clients_LIB` | IPC protocol library | ecap depends on xmlrpc |
| `comment_LIB` | Audit comment library | ecap depends on comment |
| `xaffiliate-service_LIB` | Affiliate service client | ecap depends on xaffiliate |
| `East-EmailTemplates` | Email template content (indirect) | ecap uses template events resolved at runtime |
| `notification-framework_SVC` | Email delivery (indirect) | ecap triggers notifications via NotificationManagerImpl |

---

## Migration Complexity Assessment

### Complexity: VERY HIGH

Migrating this library to a modern architecture is one of the most complex undertakings in the Onbe East platform because:

1. **Deep cbase/xPlatform coupling**: Every state machine state calls `EnrollmentManagerImpl`, `DeviceManagerImpl`, `TransferManagerImpl` — all Gen-1 platform classes. These would need to be replaced with REST API calls to modern microservices.

2. **Stored procedure dependency**: The ECAP flow calls multiple stored procedures. Identifying all procedures and their parameters requires a full cbase database schema analysis.

3. **XML-RPC inter-process communication**: The `xmlrpc:1.0.6` dependency indicates some calls use XML-RPC — a 1990s-era IPC protocol. Any migration must replace XML-RPC calls with REST or messaging.

4. **State machine re-implementation**: The custom `StateMachine.java` / `AbstractEcapProcessState.java` pattern would need to be re-expressed in a modern workflow engine (e.g., Spring State Machine, Temporal, AWS Step Functions).

5. **Multi-language notification**: The English/Spanish branching logic must be carried forward in any migration.

A conservative estimate is **6–9 months** to replace this library's functionality in a modern microservices pattern, assuming the downstream xPlatform/cbase layer APIs are also being modernized concurrently.

---

## Recommended Migration Path

### Phase 1 (0–6 months): Stabilization
- Upgrade to Java 11 LTS minimum (requires Spring 4.x or 5.x upgrade simultaneously)
- Replace log4j 1.x with Log4j2 or Logback
- Upgrade mssql-jdbc to 12.x
- Implement proper connection pool sizing and health checks
- Fix `e.printStackTrace()` instances

### Phase 2 (6–18 months): Decoupling
- Replace direct xPlatform/cbase calls with REST API calls to the modern member, device, and transfer microservices
- Replace XML-RPC with modern IPC
- Add Spring Batch or Quartz-based job management to replace the manual thread pool

### Phase 3 (18–36 months): Replacement
- Re-implement as a cloud-native Spring Boot microservice with event-driven architecture
- Use message queue (SQS, Service Bus, Kafka) for card creation request queuing
- Implement idempotency via distributed transaction IDs
- Retire the SNAPSHOT JAR deployment model in favor of container deployment
