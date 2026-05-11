# Data Architect Report — message-center_SVC

## 1. Data Architecture Overview

`message-center_SVC` operates a **stored-procedure-first** data access pattern. All persistence logic is delegated to a SQL Server database (via the `cbaseapp` database alias configured in `MessageCenter-datasource.xml`) through ten named stored procedures. There is no JPA entity model, no Flyway migration, and no ORM layer; the service is a thin Java wrapper over a pre-existing relational schema owned and managed externally (the `EcountCore` / `cbaseapp` SQL Server database).

## 2. Data Source Configuration

The Spring data source is configured through XML bean definition in two nearly identical files:
- `message-service/src/main/resources/MessageCenter-datasource.xml` (active)
- `message-service/src/main/resources/--applicationContextMessage.xml` (alternate/legacy, prefixed `--` suggesting disabled)

The data source bean `messageCbaseappDS` is constructed by a factory bean `directorDataSourcesFactory` of class `com.ecount.Core2.system.dal.ds.DirectorConfiguredDBCPdatasourceCreator`. This is the Gen-2 "Director" configuration pattern: connection parameters (JDBC URL, credentials) are **not** present in the repository; they are resolved at runtime by querying a Director service using `${director.address}`, `${agent}`, and `${cbaseappdatabase}` property placeholders loaded from `${CBASE_HOME_URL}\config\service\message\message.properties`. This indirection means credentials are never hard-coded, but the Director service becomes a critical dependency for startup.

## 3. Data Transfer Objects (DTOs)

The in-process data model is defined in `message-common/src/main/java/com/ecount/service/message/dto/`:

| DTO | Purpose | Key Fields |
|---|---|---|
| `MessageDataBean` | Primary message creation/update payload | `msgId`, `affiliate`, `userRole`, `msgType`, `msgStatus`, `startDate`, `endDate`, `content` |
| `MessageResponseBean` | Wrapper for list and single-item responses | `status`, result list or item |
| `MessageContentDataBean` | Locale-specific message content | `localeId`, `subject`, `body` |
| `CommentsDataBean` | Operational comment on status change | `commentText`, `updatedBy`, `updatedDate` |
| `StatusBean` | Status code/name pair | `statusId`, `statusName` |

No field-level length constraints, data type annotations, or input validation annotations (e.g., `@NotNull`, `@Size`) are present on these DTOs. Input validation is entirely delegated to the stored procedures.

## 4. Stored Procedure Data Access Layer

Each stored procedure class in `message-impl` extends the Spring `StoredProcedure` base (via `SimpleJdbcCall` or direct `StoredProcedure` extension). The pattern:

```
StoredProcGetMessagesList → GetMessagesListSP (new name)
StoredProcGetMessageDetails → RetrieveMessageDetailSP
StoredProcMessageCreateOrUpdate → CreateOrUpdateMessageSP
...
```

The two XML configuration files reveal a naming drift: the `--applicationContextMessage.xml` uses older `StoredProcXxx` naming conventions while `MessageCenter-datasource.xml` uses shorter `XxxSP` names. Both map to the same underlying SQL stored procedures on the `cbaseapp` database, but they expose different Spring bean names. This dual-config pattern is a technical debt indicator — it suggests the service went through a partial rename refactor that was not completed.

## 5. Data Flows and Read/Write Patterns

- **Reads** (`getMessagesList`, `retrieveMessageDetails`, `getMessagesListForApplication`): Query-only stored procedures, returning result sets mapped to `MessageResponseBean`.
- **Writes** (`createOrUpdate`, `changeMessageStatus`, `deleteMessageForUser`): Mutating stored procedures. No optimistic locking, version columns, or idempotency keys are visible at the DTO/SP interface level.
- **Config reads** (`getMessageConfigValues`, `getLocalesForAffiliate`): Reference/configuration data reads, likely cached by the caller.

## 6. Data Residency and Classification

| Data Category | PCI DSS Classification | Notes |
|---|---|---|
| `memberId` | Non-PAN cardholder data | In scope for Reg E / CCPA |
| `affiliateId` | Internal reference | Out of PCI scope |
| Message body/content | Potentially PII | Depends on content authored by operators |
| `msgType`, `msgStatus` | Operational metadata | Out of scope |

No card numbers, CVV, PIN, or track data flow through this service. The service is **not** within the PCI CDE (Cardholder Data Environment) for PAN storage, but it may be in scope as a system that processes or displays cardholder-identifying information (`memberId`, name in message body).

## 7. Data Risks and Gaps

1. **No schema versioning**: The underlying `cbaseapp` database schema is managed externally with no Flyway or Liquibase migrations in this repo. Schema changes are invisible to the service codebase, creating a latent compatibility risk.
2. **Unvalidated inputs at DTO layer**: DTOs lack JSR-303 annotations; malformed inputs reach the stored procedure layer where SQL Server handles (or silently truncates) them.
3. **Raw `ArrayList` return types** (line 40 in `MessageCenterCoreServiceImpl.java`): `getLocalesForAffiliate` and `getMessageConfigValues` return raw `ArrayList` without generics, indicating Java 5-era code that bypasses type safety and may cause `ClassCastException` at runtime.
4. **PII in message body**: If operators author messages containing names, account references, or contact details, the message body becomes a PII data asset governed by CCPA/GDPR with erasure obligations.
5. **Connection pool**: The `DirectorConfiguredDBCPdatasourceCreator` uses Apache Commons DBCP. No pool sizing, validation query, or connection timeout parameters are visible in the repository; production misconfiguration is possible.
