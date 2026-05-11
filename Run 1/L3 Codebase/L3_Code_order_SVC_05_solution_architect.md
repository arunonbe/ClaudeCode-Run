# order_SVC — Solution Architect View

## Technical Architecture

`order_SVC` is a multi-module Maven project (Java 21, Spring 5.x era) deploying two separate WARs to Apache Tomcat. It uses Spring XML context configuration (`.xml` context files) for JMS and dependency wiring — a Gen-2 pattern. The new `order-rest-controller` module introduces Spring Boot-style REST controllers alongside the legacy Spring XML context.

### Module Dependency Graph
```
order-parent (pom.xml)
├── order-common          ← Shared domain model (Order, FileOrder, activities, JMS client interfaces)
├── order-manager         ← Order management implementation (OrderManager interface + impl)
├── order-processor       ← Order processing logic
├── order-xmlrpc          ← XML-RPC endpoint WAR (port 9007)
│     └── depends: order-common, order-manager, order-processor
├── order-war             ← REST endpoint WAR (port 9003)
│     └── depends: order-common, order-manager, order-rest-controller
├── order-service         ← Spring XML context + web application layer
├── order-rest-controller ← Spring REST controllers (new layer, port 9003)
└── order-tester          ← Test harness WAR (excluded from 4.0 beta)
```

### Domain Model Architecture

The central design is a **JPA joined inheritance hierarchy** rooted at `Order`:

```
Order (@Table: order_detail)
  ├── FileOrder (@Table: order_file)          — emboss batch orders
  ├── InstantIssueBulkLoadOrder (@Table: order_instant_issue_bulk_load)
  ├── SweepOrder                              — fund sweep orders
  ├── QuickOrder                              — ad-hoc orders
  └── BillingSubOrder                         — billing events
```

Activity pattern: each state transition is implemented as an `OrderActivity` subtype stored in `order_activity`, with `PostFileOrderActivity` having its own join table `order_activity_post_file`. This pattern provides a full audit trail of order state transitions — relevant for PCI DSS Req 10.2 (audit trails).

## API Surface

### REST API (`order-rest-controller`, port 9003)
All endpoints use `POST` method with JSON request/response bodies:

| Endpoint | Handler | Business Operation |
|---|---|---|
| `POST /order-manager/close-order` | `CloseOrderActivity` | Close a completed order |
| `POST /order-manager/cancel-order` | `CancelOrderActivity` | Cancel an open order |
| `POST /order-manager/create-scratch-order` | `CreateScratchOrderActivity` | Create ad-hoc order |
| `POST /order-manager/reopen-order` | `ReopenOrderActivity` | Reopen a closed/cancelled order |
| `POST /order-manager/correct-order` | `CorrectOrderActivity` | Apply data correction |
| `POST /order-manager/set-order-memo` | `OrderMemo` | Set key-value metadata on order |
| `POST /order-manager/submit-instant-issue-bulk-load-order` | `InstantIssueBulkLoadOrder` | Bulk instant-issue card load |
| `POST /order-manager/order-summary` | Query | Order summary (v0) |
| `POST /order-manager/order-summary-v1` | Query | Order summary (v1) |
| `POST /order-manager/get-order-activity-history` | `OrderActivity` | Full audit trail for an order |
| `POST /order-manager/order-inquiry` | Query | Order inquiry |
| `POST /order-manager/find-order` | Query | Find order by criteria |
| `POST /order-manager/save-order` | `SaveOrderActivity` | Create/save a new order |
| `POST /order-manager/submit-order` | `SubmitOrderActivity` | Submit order to processing |

**Notable design choice**: All endpoints use `POST` regardless of whether the operation is a query or mutation. This is a Gen-2 pattern (XML-RPC parity) — Gen-3 migration should adopt proper HTTP verbs (`GET` for queries, `POST`/`PUT`/`DELETE` for mutations).

### XML-RPC API (`order-xmlrpc`, port 9007)
The XML-RPC interface is maintained for backward compatibility with `jobservice_SVC`. The path is `/order-xmlrpc/`. Specific method signatures are defined in the `xml-rpc_LIB` dependency.

### IBM MQ Interface
| Queue | Direction | Message Type |
|---|---|---|
| Order submission queue | Inbound | Order submission request |
| Order completion queue | Outbound | `OrderCompletedMessage` |
| Request processor queue | Internal | `RequestProcessorListener` managed |

## Security Posture

### PCI DSS Scope
`order_SVC` is **PCI DSS in-scope** because:
1. It orchestrates the transmission of emboss files containing PANs to FiServ/FDR.
2. The `SASI_FDR_CARD_NUMBER_GET` operation retrieves a live PAN from the card bureau.
3. DDA account numbers flow through `sasi_fdr_dda_account_create`.

### Security Controls Present
- JPA joined inheritance ensures PAN-containing emboss file references (`fileId`) are UUID-only — the actual emboss file is not stored in `ordersvc`.
- `SasiThreadLocal` isolates per-request bureau data to prevent cross-request data leakage.
- Maven Enforcer `requireReleaseDeps` prevents SNAPSHOT dependencies in production builds.
- CodeQL SAST scanning via `.github/workflows/codeql.yml`.
- `order_detail` and related tables contain only order metadata (IDs, status, programme references) — not PANs.

### Security Gaps and Risks

| Finding | Severity | PCI DSS Ref | Detail |
|---|---|---|---|
| CVE-2025-24813 (Tomcat partial PUT RCE) suppressed | Critical | Req 6.3.3 | Actively exploitable RCE if partial PUT not disabled; must patch or document mitigation |
| `OrderMemo.value` potentially stores PAN/DDA | High | Req 3.5 | `order_memo.value` is plain varchar; if CARD_NUMBER or DDA_NUMBER is stored here it must be encrypted |
| Tests skipped in all CI phases | High | Req 6.2 | No automated regression; JaCoCo coverage never collected |
| 24 CVEs suppressed in `.trivyignore` | High | Req 6.3.3 | Jackson Databind and Xalan XSLT CVEs deferred; must review with security team |
| IBM MQ connection strings in XML context | Medium | Req 8.3 | JMS connection factory credentials in `server-OrderJMSContext.xml` — verify no plaintext passwords |
| XML-RPC endpoint has no authentication details visible | Medium | Req 6.2 | XML-RPC path `/order-xmlrpc/` — must confirm authentication is enforced at Tomcat or reverse proxy |

## Technical Debt

| Item | Severity | Detail |
|---|---|---|
| CVE-2025-24813 suppressed | Critical | Tomcat partial PUT RCE — highest priority patch |
| `com.citi.prepaid` groupId | Medium | Legacy naming; should migrate to `com.onbe.*` |
| Spring XML context configuration | Medium | `client-OrderJMSContext.xml`, `server-OrderJMSContext.xml` are Gen-1/2 patterns; replace with `@Configuration` classes |
| All-POST REST API | Medium | Non-RESTful design; Gen-3 migration should adopt proper HTTP verbs |
| IBM MQ dependency | Medium | Gen-2 messaging infrastructure; Gen-3 target is Azure Service Bus / Kafka |
| Tests skipped in CI | High | JaCoCo configured but never executed; no regression safety net |
| No Pact contract tests | Medium | No formal API contract with consumers |
| `order-tester` excluded from beta | Low | Test harness not built — reduces confidence in refactoring |
| Javadoc HTML in `/doc/` directory | Low | Generated Javadoc committed to version control — belongs in CI artifact storage |

## Gen-3 Migration Assessment

`order_SVC` is the most complex Gen-3 migration target in this analysis set. The migration must be sequenced carefully:

### Phase 1 — Security Stabilisation (Immediate)
- Patch CVE-2025-24813 (Tomcat update or partial PUT disable + documentation).
- Re-enable test execution in CI; achieve baseline coverage for REST controller layer.
- Audit `order_memo.value` for any stored PANs or DDA numbers; apply column-level encryption if found.

### Phase 2 — Interface Modernisation (Near-term)
- Migrate `jobservice_SVC` consumers from XML-RPC to REST (`/order-manager/`).
- Replace IBM MQ JMS with Azure Service Bus Spring Cloud Stream binding (aligned with `petstore-spring-mvc-rest-server` pattern).
- Decommission `order-xmlrpc` WAR.

### Phase 3 — Platform Alignment (Medium-term)
- Update parent POM from `com.parents:prepaid-parent` to `onbe-spring-boot-parent`.
- Migrate Spring XML context files to `@Configuration` Java classes.
- Containerise (Docker + Kubernetes) replacing Tomcat WAR deployments to named hosts.
- Migrate `ordersvc` database to Azure SQL Managed Instance.

### Phase 4 — SASI Bureau Integration (Long-term)
- Replace SASI/FiServ protocol with modern card bureau API (vendor-dependent).
- This is the highest-risk migration step — FiServ/FDR integration carries PAN data and must maintain zero data loss during transition.

## Code-Level Risks

### `Order.java` `findMemoValue(String type)` — Unencrypted Memo Storage
The `order_memo` table stores arbitrary key-value pairs. `SasiConstants` defines `CARD_NUMBER` and `DDA_NUMBER` keys. If any code path stores actual card numbers or DDA numbers in `order_memo.value` (a plain varchar column), this constitutes unencrypted CHD storage — a PCI DSS Req 3.5 violation. This must be audited by reviewing all callers of `setMemoValue(CARD_NUMBER, ...)` and `setMemoValue(DDA_NUMBER, ...)`.

### `SasiActivityContext.java` / `SasiThreadLocal.java` — ThreadLocal with Virtual Threads
If `order_SVC` is migrated to Java 21 virtual threads, `ThreadLocal` variables used for request-scoped SASI context must be reviewed. Virtual threads can be remounted on different carrier threads, potentially causing `ThreadLocal` values to be inherited incorrectly. Java 21's `ScopedValue` API is the recommended replacement.

### `.trivyignore` CVE-2025-24813 — Tomcat Partial PUT RCE
This CVE (CVSS 9.8 on some scoring systems) allows remote code execution on Tomcat if the partial PUT feature is enabled. The suppression comment must be accompanied by documented evidence (in a security runbook or JIRA ticket) that partial PUT is explicitly disabled in all `server.xml` configurations. Without this documentation, the suppression constitutes an undocumented PCI DSS Req 6.3.3 compensating control.
