# order_SVC — Enterprise Architect View

## Platform Generation

**Generation**: Gen-2 — Legacy Core Service, Active Migration in Progress

`order_SVC` is a Gen-2 service at the heart of Onbe's prepaid card platform. It carries the legacy `com.citi.prepaid` Maven groupId, indicating its Citi-era heritage. The version (`4.1.13-SNAPSHOT`) and module structure (XML-RPC + JMS + WAR deployments to named Tomcat hosts) are characteristic of the Gen-2 on-premises architecture. The addition of `order-rest-controller` and the current build exclusion of the legacy XML-RPC modules signal an active Gen-2 → Gen-3 migration in progress.

## Business Domain

**Domain**: Card Fulfilment and Order Management

`order_SVC` is the central lifecycle manager for all card fulfilment events in the Onbe platform. It holds the authoritative state for:

- **Plastic card orders** (bulk emboss files to card bureaus — FiServ/FDR)
- **Instant-issue orders** (real-time card personalisation at point-of-sale or digital issuance)
- **Sweep orders** (programme-level fund movement)
- **Quick and scratch orders** (ad-hoc card fulfilment)

The `order_detail` table is the canonical order ledger. Every card ever issued by Onbe flows through this service's state machine (`SUBMITTED → PROCESSED → COMPLETED / CANCELLED`).

## Role in the Platform

### Position in the C4 Architecture
```
clientzone_WAPP / cs-api_API / jobservice_SVC
    │
    ├── IBM MQ (async order submission)
    │         │
    │         ▼
    │   order_SVC (order-service WAR, port 9003)
    │
    └── XML-RPC (legacy sync)
              │
              ▼
         order-xmlrpc (WAR, port 9007)

order_SVC internal:
    ├── ordersvc SQL Server database (DS_DB_ordersvc)
    ├── SASI / FiServ layer → Card bureau (FDR) — emboss files / PAN retrieval
    ├── inventory-mgmt_LIB → card stock management
    └── billing-integration_LIB → banker/billing events
```

### Key Upstream Consumers
| Consumer | Interface | Use |
|---|---|---|
| `jobservice_SVC` | IBM MQ + XML-RPC | Submits file orders, queries order status |
| `cs-api_*` | REST (`/order-manager/`) | Customer service operations (cancel, reopen, correct) |
| `clientzone_WAPP` | REST (indirectly via BFF) | Client admin views order status |
| Batch layer (`ecore-batch_LIB`) | IBM MQ | Batch order processing |

### Key Downstream Dependencies
| Dependency | Type | PCI Sensitivity |
|---|---|---|
| `DS_DB_ordersvc` (SQL Server) | Database | Internal operational — no PANs in ordersvc schema directly |
| FiServ/FDR card bureau | SASI protocol | Critical — PAN retrieval and emboss file transmission |
| `inventory-mgmt_LIB` | Internal JAR | Medium — physical card stock tracking |
| `billing-integration_LIB` | Internal JAR | Medium — billing events per order |
| IBM MQ (`com.ibm.mq.jakarta.client:9.4.0.0`) | Messaging | Medium — async order events |

## Integration Patterns

| Pattern | Implementation | Generation |
|---|---|---|
| XML-RPC (legacy) | `order-xmlrpc` WAR on port 9007 | Gen-1/2 |
| JMS (async) | IBM MQ with `client-OrderJMSContext.xml` | Gen-2 |
| REST API (new) | `order-rest-controller` on port 9003 | Gen-2/3 |
| SASI card bureau | FiServ/FDR SASI protocol via `FiServActivity` | Gen-1/2 legacy |
| Billing events | `PostInvoiceOrderActivity`, `PostSalesOrderOrderActivity` | Gen-2 |
| Domain event listeners | `OrderCompletionListener` (JMS) | Gen-2 |

The dual XML-RPC + REST interface is the clearest signal of a migration in progress. The REST API (`OrderManagerController`) is the target interface; XML-RPC is maintained for backward compatibility with `jobservice_SVC`.

## Strategic Status

**Status**: Load-Bearing Gen-2 Service — Actively Migrated

`order_SVC` cannot be switched off — every card issuance in the Onbe platform depends on it. The migration strategy is:
1. The new `order-rest-controller` module provides a REST facade over the existing order management domain.
2. As consumers migrate from XML-RPC/MQ to REST, the legacy interfaces can be decommissioned.
3. The SASI/FiServ bureau integration must eventually be replaced with a Gen-3 async event-driven card bureau integration.

The current `4.0.0-beta` build exclusion of `order-manager`, `order-processor`, `order-xmlrpc`, `order-service`, and `order-tester` indicates the REST-only build path is being validated before full module inclusion.

## Migration Blockers

| Blocker | Impact | Detail |
|---|---|---|
| `com.citi.prepaid` groupId | Naming debt | Reflects Citi-era heritage; should be migrated to `com.onbe.*` namespace |
| IBM MQ dependency (`9.4.0.0`) | Platform coupling | IBM MQ is a Gen-2 infrastructure component; Gen-3 uses Azure Service Bus / Kafka |
| XML-RPC protocol (`order-xmlrpc`) | Interface lock-in | `jobservice_SVC` depends on XML-RPC; both must migrate together |
| SASI/FiServ protocol | Bureau integration lock-in | SASI is a proprietary FiServ protocol; Gen-3 requires modern card bureau API |
| Tomcat WAR deployment | Deployment model | Gen-2 WARs on named Tomcat hosts (`q-na-app03/04`); Gen-3 requires container/Kubernetes deployment |
| CVE-2025-24813 suppressed (Tomcat RCE) | Security risk | Highest-priority patching item before Gen-3 migration |
| `ordersvc` database (SQL Server, on-prem likely) | Data migration | Gen-3 migration must include database migration plan |
| Tests skipped in CI | Quality gate | Cannot confidently refactor without automated regression |
| `com.parents:prepaid-parent:6.0.13` | Parent POM dependency | Does not use `onbe-spring-boot-parent` — must migrate to align with Gen-3 platform standard |
