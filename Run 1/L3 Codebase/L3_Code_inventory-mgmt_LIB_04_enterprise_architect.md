# Enterprise Architect View — inventory-mgmt_LIB

## Platform Generation
**Gen-1 / Gen-2 transitional** — The library has a Java 21 compiler target (Maven POM) and uses Lombok and SLF4J, indicating recent maintenance upgrades. However, it retains deep dependencies on legacy Gen-1 frameworks: `com.cbase.*`, `com.ecount.one.service.security.*`, `xplatform`, `xsecurity`, `struts`, and Director-based service discovery. The domain logic itself (stored procedures, XML file generation, TIBCO-heritage logging) is Gen-1 vintage.

## Business Domain
**Card Inventory Management** — Core domain library for Onbe's prepaid instant-issue card operations. Manages physical card stock at retail/distribution locations, drives reorder workflows, and tracks card lifecycle (available → reserved → used).

## Role
- **Primary role**: Domain library for instant-issue card inventory operations.
- **Consumers**: ClientZone web application (ad-hoc reorder), inventory-mgmt-batch-client (scheduled batch), and any service that needs to issue or track instant-issue cards.
- **Critical path**: Directly drives prepaid card issuance operations — inventory exhaustion or failures here impact card issuance SLAs for clients.

## Dependencies
### Inbound (consumers)
| Consumer | Usage |
|---------|-------|
| inventory-mgmt-batch-client_LIB | Batch auto-reorder and expiry processing |
| ClientZone web application | Ad-hoc reorder, inventory inquiry |
| Other ecount platform services | Card issuance (getNewCard, updateInventory) |

### Outbound (runtime)
| Dependency | Type |
|-----------|------|
| JobSvc SQL Server | Core inventory tables |
| ecountCore SQL Server | Program and location profiles |
| Repository Service (XML-RPC) | Request file submission |
| xSecurity / PrivilegeManager | Access control for notifications |
| cbase / xplatform framework | C-Base business object framework |
| Director service registry | DB and service endpoint resolution |
| Filesystem | XML reorder file staging |

## Integration Patterns
- **JDBC Stored Procedures**: All database operations via Spring JdbcTemplate stored procedure inner classes.
- **XML Request Files**: Inventory reorder requests submitted as XML files to the Repository Service via `processJobFile` XML-RPC call.
- **Email notifications**: Via ReOrderNotification bean (injected Spring dependency).
- **Privilege-based access**: xSecurity PrivilegeManager for user lookup by role.

## Strategic Status
**Active but requiring migration planning** — This library is in active use by production card issuance operations. It cannot be retired without a replacement for instant-issue card inventory management.

Migration analysis:
- The domain logic (inventory tracking, reorder threshold checks, notification rules) is valuable and should be preserved in a Gen-3 service.
- The Gen-1 framework dependencies (cbase, xplatform, struts, Director) are the primary migration barrier.
- Java 21 compiler is already set — a positive step, but the runtime framework is still Gen-1.
- Target state: a Spring Boot 3 microservice with REST API, JPA/Hibernate, Azure Service Bus for notifications, and Azure Key Vault for credentials.

## Migration Blockers
1. Deep coupling to `com.cbase.*` business objects (Member, RequestContext, AppProgramInstantIssueProfile, etc.) — these must be replaced with new domain models.
2. Director service registry dependency for DB and service endpoint resolution — must be replaced with Spring Boot DataSource configuration and service mesh.
3. Stored procedure-heavy JDBC pattern — stored procedures on SQL Server would need to be migrated or replaced with JPA/Hibernate repositories.
4. XML request file-based integration with the Repository Service — this file-transfer pattern must be replaced with event-driven or REST API integration.
5. xSecurity/PrivilegeManager dependency for user lookup — must be replaced with a modern identity/RBAC service.
