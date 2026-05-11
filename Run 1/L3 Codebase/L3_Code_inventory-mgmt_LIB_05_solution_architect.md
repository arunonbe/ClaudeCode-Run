# Solution Architect View — inventory-mgmt_LIB

## Technical Architecture

**Stack**: Java 21 (compiler), Spring Framework (spring-context, spring-jdbc via prepaid-parent BOM), JdbcDaoSupport / StoredProcedure (Spring JDBC), Lombok, SLF4J, commons-lang, commons-collections, xplatform 6.3.0, xsecurity-common/impl 4.0.3, requestfile-impl 2.0.0, repository-common/client 3.0.1, Struts (via prepaid-parent BOM).

**Design pattern**: 
- Domain service library with DAO interface + JDBC implementation pattern.
- All database operations use Spring `StoredProcedure` subclasses as private inner classes of `InventoryManagementJDBCDao` — each stored procedure is a dedicated inner class with typed `execute()` method.
- `InventoryManagementManagerImpl` is the main orchestrator; it is setter-injected (no constructor injection) and wired via Spring XML in consuming applications.

**Key classes**:
| Class | Role |
|-------|------|
| `InventoryManagementManagerImpl` | Core orchestration: low inventory check, reorder trigger, expiry alerts |
| `InventoryManagementJDBCDao` | All JDBC/stored-procedure operations (17+ inner SP classes) |
| `IDGeneratorImpl` | DB-sequence-based ID generation with block allocation |
| `InstantIssueRequestFileBuilderImpl` | XML reorder file construction |
| `InstantIssueActivityJournalManagerImpl` | Activity journal write operations |

## API Surface
Library — no HTTP endpoints.

**Public interfaces**:
- `InventoryManagementManager`: checkInventory, checkLowInventory, placeAdHocReorder, getNewCard, getUnreservedCard, updateInventory, inquiry, isCardReserved, findInstantIssueProfile
- `InstantIssueActivityJournalManager`: journal write/query operations
- `IDGenerator`: getNextIDBlock(sequenceName, count)
- `InstantIssueRequestFileBuilder`: buildRequestList(...)

## Security Posture

### Authentication / Authorisation
- `PrivilegeManager.getUsersByPrivilege()` used to look up users with `ROLE_INVENTORY_VIEW` privilege for notifications — role-based access enforced via xSecurity framework.
- No HTTP authentication (library, not service).

### Cryptography
- No cryptography in this library.
- `card_number` field is handled as a plain String throughout; no encryption or tokenisation.

### Secrets
- No secrets in this library's source code.
- DataSource credentials provided by Director-configured DBCP factory at runtime (injected by consuming Spring context).

### CVEs / Dependency Risks
- **Struts** (via prepaid-parent BOM): Apache Struts has critical historical CVEs (CVE-2017-5638, CVE-2017-9805). Version from BOM unknown without resolving prepaid-parent:6.0.12. Must verify version.
- **commons-lang** (unversioned, from BOM): If commons-lang 2.x, CVE-2020-15250 (DoS). Commons-lang 3.x is preferred.
- **commons-collections** (unversioned, from BOM): If commons-collections 3.x, CVE-2015-6420 (deserialization) — critical. Must verify version.
- **xplatform 6.3.0**: Internal library; CVE status managed internally.
- Jakarta XML Bind API included — indicates JAXB usage for XML serialisation.

## Technical Debt
1. All setter-injected dependencies (no constructor injection) — makes `InventoryManagementManagerImpl` mutable and harder to reason about.
2. `InstantIssueLocationRequest` uses mutable setter pattern — no immutability.
3. `InventoryManagementManagerImpl` is 1366 lines — god class with too many responsibilities.
4. Raw types (`Map`, `Collection`, `List` without generics) throughout DAO layer.
5. `@SuppressWarnings({"unchecked", "unused"})` annotations mask type-safety issues.
6. XML file generation using string concatenation (`StringBuilder`) without XML serialisation library — brittle and injection-prone.
7. `file.delete()` return value checked via boolean flag but only logged — silent failure if temp file deletion fails.
8. Commented-out code blocks throughout `InventoryManagementManagerImpl` (lines 126-141, 648-652, 1350-1355).
9. `e.printStackTrace()` in `sendLowInventoryNotification` instead of `log.error()`.

## Gen-3 Migration Requirements
1. Replace all `com.cbase.*` dependencies with new domain models.
2. Replace Director-DBCP DataSource with Spring Boot DataSource + Azure Key Vault.
3. Replace stored-procedure JDBC with Spring Data JPA repositories.
4. Replace XML request file pattern with Azure Service Bus message publishing.
5. Replace xSecurity PrivilegeManager with Azure AD group-based or Spring Security RBAC.
6. Replace email notification via ReOrderNotification bean with Azure Communication Services or similar.
7. Expose as a REST microservice (Spring Boot 3, Java 21).
8. Add PAN masking/tokenisation for `card_number` field before any logging or persistence.
9. Constructor-inject all dependencies.

## Code-Level Risks

| File | Line | Risk |
|------|------|-------|
| `InventoryManagementManagerImpl.java` | 963 | `e.printStackTrace()` in `sendLowInventoryNotification` — swallowed exception, no re-throw or structured logging |
| `InventoryManagementManagerImpl.java` | 155 | `log.debug("removeFromInventoryByECountId " + card)` — if card's `toString()` includes card_number, PAN logged at DEBUG |
| `InventoryManagementJDBCDao.java` | 100-104 | SQL UPDATE includes `card_number = ?` in batch update — card number persisted to DB in plaintext |
| `InventoryManagementJDBCDao.java` | 108-110 | `card_number` inserted into `instant_issue_inv_email_log` via batch — card number in email log table |
| `InventoryManagementManagerImpl.java` | 277-278 | `new File(filePath + "\\" + filename)` — Windows path separator hardcoded; non-portable |
| `InventoryManagementManagerImpl.java` | 534-560 | `OpenHeadersTags()` uses string concatenation with program data in XML — potential XML injection if programId or filename contains special characters |
| `IDGeneratorImpl.java` | (not read) | Sequence exhaustion must be handled without data loss — verify `IDsExhaustedException` propagation |
