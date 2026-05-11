# DS_DB_notificationsvc — Enterprise Architect Report

## 1. Platform Generation

| Attribute | Value |
|-----------|-------|
| Platform generation | Gen-1 / Gen-2 (legacy eCount/Wirecard platform) |
| Technology stack | Microsoft SQL Server 2012, SSDT, DeltaSql |
| Naming convention | `DS_DB_` prefix = Data Services Database project |
| Database paradigm | Stored-procedure-heavy relational; minimal ORM |
| Deployment model | DACPAC + manual DeltaSql scripts |

This database was built on the Wirecard/eCount technology stack. The `DS_DB_` repository prefix and the SSDT SQL project format are characteristic of the pre-Onbe Gen-1/Gen-2 infrastructure. Active investment (DeltaSql migration dated 2026-04-26) confirms this database is still actively maintained in production.

---

## 2. Business Domain

**Domain**: Customer Communications — Notification Delivery  
**Subdomain**: Multi-channel notification (email + SMS) for prepaid card lifecycle events

This database is the **system of record** for all notification configuration, delivery state, and consent management across Onbe's prepaid card portfolio. It supports:
- Cardholder communication (activation, transaction alerts, balance alerts)
- Compliance communications (TCPA consent, quiet hours, opt-out)
- Client-facing notification setup (program-level template and event configuration)

---

## 3. System Role in the Enterprise

| Role | Description |
|------|-------------|
| Persistence layer | Sole database for `notification-framework_SVC` (the notification engine) |
| Configuration store | Holds all per-program notification configuration consumed by the notification engine |
| TCPA compliance store | Authoritative store for SMS opt-out and consent state — feeds TCPA audit |
| Delivery audit trail | Records all notification attempts, outcomes, and Mailgun events |
| Quartz scheduler store | Provides persistent job scheduling for the notification service instance |

---

## 4. Dependencies

### Upstream (writes to NotificationSvc)
| System | Integration | Data Written |
|--------|------------|-------------|
| `notification-framework_SVC` | Direct JDBC | `notification_event`, `notification_queue`, `mailgun_events_queue` |
| `ordersvc` | Via notification service | Upstream triggers notification events |
| `jobsvc` | Via notification service | Job completion triggers notification events |
| `ecountcore` | Via notification service | Card lifecycle events trigger notifications |
| SMS Provider | Webhook → notification service | `sms_opt_out`, `ch_consent` |
| Mailgun | Webhook → notification service | `mailgun_events_queue` |

### Downstream (reads from NotificationSvc)
| System | Integration | Data Read |
|--------|------------|----------|
| `notification-framework_SVC` | Direct JDBC | Configuration, templates, queue, consent |
| `notification-service-client_SVC` | API | Configuration data |
| Reporting tools | `report` / `report_full` roles | Operational reporting |

### Cross-Database Reference Tables
The presence of `CbaseApp_*`, `EcountCore_*`, and `JobSvc_*` prefixed tables suggests **cross-database data synchronisation** — these tables are either snapshot copies or linked-server reads materialised as local tables. This creates a **data coupling risk**: if source databases change schema, these local copies become stale.

---

## 5. Integration Patterns

| Pattern | Where Used | Assessment |
|---------|-----------|------------|
| Stored procedure API | All reads/writes via SPs | Gen-1 pattern; no REST API on the database |
| Webhook ingestion | Mailgun events → `mailgun_events_queue_process` SP | Event-driven via HTTP webhook → SP |
| DeltaSql migration | `DeltaSql/` folder | Schema versioning pattern; manual execution |
| DACPAC deploy | SSDT project | Full schema deployment for initial or baseline deployments |
| SSPI / Windows Auth | CCP-SQLDB connection uses `Integrated Security=SSPI` | Windows AD authentication for DB connections |
| SQL logins | `notificationsvc`, `b2c`, `report` logins in `Security/` | Mixed-mode authentication |

---

## 6. Strategic Status

**Current**: Active production — receiving schema migrations as recently as April 2026.

**Assessment**: This database is a **strategic Gen-2 asset** — it is the active notification service database for the production eCount platform. It is not a candidate for immediate decommission, but it is a candidate for **strategic modernisation** as part of the Gen-3 platform evolution:

- The Gen-3 architecture (evidenced by `exemplar-cross-border-transfer-service_WAPP` and `nexpay-*` repositories) uses Spring Boot + Liquibase + SQL Server with externalised configuration. The `NotificationSvc` database would need to be re-implemented with Liquibase-managed schema, Spring Data JPA/JDBC repositories, and secrets vault integration.
- The April 2026 BZGD-0000 migration (consent management overhaul) demonstrates that the notification system is being actively extended — this is a **stabilisation and compliance investment** on the Gen-2 platform, not a migration signal.

---

## 7. Migration Blockers for Gen-3

| Blocker | Detail |
|---------|--------|
| Stored procedure dependency | 41 stored procedures called by `notification-framework_SVC`; all must be re-implemented as Java service layer before migration |
| Quartz persistence in SQL | `QRTZ_*` tables are tightly coupled to the Java Quartz instance; migration requires moving to a cloud-native scheduler or migrating Quartz to the Gen-3 DB |
| Cross-database reference tables | `CbaseApp_*`, `EcountCore_*`, `JobSvc_*` copies must be replaced with API calls to those services' Gen-3 equivalents |
| SMS opt-out and consent data | `sms_opt_out` and `ch_consent` tables contain TCPA-critical data; migration requires zero-loss data migration with audit continuity |
| `email_details` PII data | Full email bodies stored in `email_details`; GDPR-compliant migration requires right-to-erasure handling |
| No automated tests | No test suite in this repo; migration validation relies entirely on manual testing |
