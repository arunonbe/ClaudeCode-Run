# Enterprise Architect View — inventory-mgmt-batch-client_LIB

## Platform Generation
**Gen-1** — Java 6 compiler target, Spring 2.5.4, Commons DBCP 1.x, TIBCO JMS, log4j 1.2.14, `System.exit()` batch pattern, hardcoded Windows filesystem paths. This is a first-generation batch processing component from the ecount/C-Base era.

## Business Domain
**Card Inventory Management — Batch Operations** — Scheduled/on-demand batch execution layer for card inventory: auto-reorder triggers, card expiration alerts, shipping info population, and email notification processing.

## Role
- **Primary role**: Batch client driving `inventory-mgmt_LIB` operations on a scheduled basis.
- **Relationship to inventory-mgmt_LIB**: This library is the batch executor; inventory-mgmt_LIB is the domain library.
- **Critical path**: Auto-reorder batch must run reliably or card stock at distribution sites will not be replenished, causing card issuance failures.

## Dependencies
### Inbound (consumers)
- OS-level scheduler (cron / Windows Task Scheduler) via direct JVM invocation.

### Outbound (runtime)
| Dependency | Type |
|-----------|------|
| inventory-mgmt_LIB 1.0.14 | Domain library (pinned older version) |
| ecountCore SQL Server | DDA card state queries |
| JobSvc SQL Server | Inventory and email queue tables |
| cbaseapp SQL Server | C-Base application data |
| Director service registry | DB connection resolution |
| TIBCO JMS (tibjms 5.0) | ELF logging |
| xSecurity 1.1.19 | Security context |
| ecount-system 2.0.0 | Core system utilities |
| director-client 1.0.11 | Service registry client |

## Integration Patterns
- **Batch execution**: Direct JVM invocation with `main()` entry point.
- **Spring XML context**: Application context loaded from classpath XML files.
- **JDBC stored procedures**: Via inventory-mgmt_LIB DAO.
- **File-based configuration**: `.properties` files on local filesystem.
- **Email**: Via InventoryEmailNotification bean (SMTP or JMS-based, configured externally).

## Strategic Status
**Active but high migration priority** — This batch client drives critical card reorder operations. However, it is severely outdated and represents significant operational and security risk.

Migration path:
- Replace batch JVM with a Spring Batch job running on a modern Java (17/21) Spring Boot application.
- Replace OS scheduler with Kubernetes CronJob or Azure Scheduler.
- Replace Director-based DBCP with Spring Boot DataSource + Azure Key Vault credentials.
- Replace TIBCO JMS ELF logging with Azure Monitor / Application Insights.
- Decouple from the `C-Base` directory structure.

Note: `inventory-mgmt-batch-client_LIB` pins `inventory-mgmt` at version 1.0.14, while `inventory-mgmt_LIB` is at 2.0.x — the batch client is running on an older version of the domain library and has not been updated to the current API.

## Migration Blockers
1. Java 6 runtime requirement — forces deployment on legacy JVM hosts.
2. Hardcoded `D:/c-base/config/` paths — incompatible with containerised or Linux deployment.
3. `inventory-mgmt` version pinned at 1.0.14 — must be updated to current 2.0.x before migration.
4. Spring 2.5.4 XML context — must be ported to Spring Boot 3 application context.
5. TIBCO JMS 5.0 dependency — requires access to TIBCO license and library; must be replaced.
6. `System.exit()` pattern — prevents embedding in a managed container or testing framework.
