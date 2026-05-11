# Data Architect View — exemplar-theater-service_WAPP

## Database

- **Engine**: Microsoft SQL Server (Docker: `exemplar-sqlserver`, Azure: `exemplar-sqlserver.database.windows.net`)
- **Database name**: `Theater` (provisioned by `exemplar-database_WAPP`)
- **Schema migration tool**: Liquibase 4.3.5
- **ORM**: Spring Data JPA / Hibernate (dialect: `SQLServer2012Dialect`, `application.yml` line 63)
- **Connection pool**: HikariCP (configured via Spring Boot defaults; `minimum-idle: 10`, `maximum-pool-size: 50`, per `application.yml` lines 58–60)

## Entity Model

### CUSTOM_SITE Table
Defined in `db.changelog-1.0.xml` lines 14–32.

| Column | Type | Constraints |
|--------|------|-------------|
| `ID` | varchar2(36) | PK, NOT NULL |
| `VERSION` | bigint | Optimistic locking |
| `CUSTOM_SITE_ID` | varchar2(36) | NOT NULL, UNIQUE (`UDX_CUSTOM_SITE`) |
| `CUSTOM_SITE_CODE` | varchar2(16) | NOT NULL |
| `INSERTED_AT` | timestamp(6) | Audit |
| `INSERTED_BY` | varchar2(255) | Audit |
| `UPDATED_AT` | timestamp(6) | Audit |
| `UPDATED_BY` | varchar2(255) | Audit |

**JPA Entity**: `CustomSite.java` (package `com.onbe.service.theaterservice.persistence.entity`)

### THEATER Table
Defined in `db.changelog-1.0.xml` lines 34–71.

| Column | Type | Constraints |
|--------|------|-------------|
| `ID` | varchar2(36) | PK, NOT NULL |
| `VERSION` | bigint | Optimistic locking |
| `THEATER_ID` | varchar2(36) | NOT NULL, UNIQUE (`UDX_THEATER`) |
| `CUSTOM_SITE_ID` | varchar2(36) | NOT NULL, FK → CUSTOM_SITE(ID) |
| `CREATOR_SUBJECT_ID` | varchar2(255) | NOT NULL (OAuth subject) |
| `CREATOR_ISSUER_ID` | varchar2(255) | NOT NULL (OAuth issuer) |
| `STATUS` | varchar2(32) | NOT NULL, indexed (`IDX_THEATER_STATUS`) |
| `INSERTED_AT` | timestamp(6) | Audit |
| `INSERTED_BY` | varchar2(255) | Audit |
| `UPDATED_AT` | timestamp(6) | Audit |
| `UPDATED_BY` | varchar2(255) | Audit |

**JPA Entity**: `Theater.java` — one-to-one relationship with `CustomSite` via `@JoinColumn(name = "CUSTOM_SITE_ID")`.

### THEATER_HISTORY Table
Defined in `db.changelog-1.0.xml` lines 73–96.

| Column | Type | Constraints |
|--------|------|-------------|
| `ID` | varchar2(36) | PK, NOT NULL |
| `VERSION` | bigint | Optimistic locking |
| `THEATER_ID` | varchar2(36) | NOT NULL, FK → THEATER(ID) |
| `STATUS` | varchar2(32) | NOT NULL |
| `INSERTED_AT` | timestamp(6) | Audit |
| `INSERTED_BY` | varchar2(255) | Audit |
| `UPDATED_AT` | timestamp(6) | Audit |
| `UPDATED_BY` | varchar2(255) | Audit |

**JPA Entity**: `TheaterHistory.java` — many-to-one relationship to `Theater`.

### TEST Table
A minimal scaffold table (ID + audit columns) created in `db.changelog-1.0.xml` lines 98–114, used for verifying the migration toolchain. No application data.

## Entity Relationships

```
CUSTOM_SITE (1) -----(1) THEATER (1) -----(N) THEATER_HISTORY
                    [FK: CUSTOM_SITE_ID]     [FK: THEATER_ID]
```

## Domain Transfer Object

`TheaterInfo.java` (package `com.onbe.service.theaterservice.data`) is the API-layer DTO:
- `theaterId` (max 36 chars) — UUID
- `customSiteId` (max 36 chars) — UUID
- `customSiteCode` (required, max 16 chars)
- `creatorSubjectId` (required, max 255 chars) — OAuth subject claim
- `creatorIssuerId` (required, max 255 chars) — OAuth issuer claim
- `status` (max 32 chars) — one of: `PENDING`, `CREATED` (per `TheaterStatus.java`)

## Event Model

`TheaterCreatedEvent.java` (package `com.onbe.service.theaterservice.data.event`) is the Dapr CloudEvent payload:
- `theaterId` (String) — UUID of the theater to transition to CREATED status.

This event is consumed from the Dapr pub/sub topic `dii.integration.customerservice.theaterv1`.

## Sensitive Data Assessment

**This exemplar service contains no payment card data, PAN, CVV, account numbers, or personally identifiable financial information.**

However, the following observations apply when this pattern is adapted for payment services:
- `CREATOR_SUBJECT_ID` and `CREATOR_ISSUER_ID` represent OAuth identity claims that could constitute PII (user identifiers). These should be treated as sensitive if they resolve to real user identities.
- The `show-sql: true` JPA setting (`application.yml` line 66) would expose all SQL queries (including any column values in parameterized queries at DEBUG level) to the application log. For production payment services, this must be disabled.
- Connection strings in `application.yml` (lines 40–53) contain the database password in plaintext. This must be replaced with a secrets reference.

## Liquibase Migration Management

The `theater-service-db-scripts` module contains:
- `db.changelog-master.xml`: Master changelog that includes version-specific changelog files.
- `db.changelog-1.0.xml`: Contains the four changeSets described above.

All changeSets use `<preConditions onFail="MARK_RAN">` guards with `<tableExists>` checks, making them idempotent and safe for repeated runs.

The `theater-service-db-app` module is a standalone Spring Boot application used exclusively to run Liquibase migrations, keeping schema evolution separate from the main application deployment. This is an Onbe Gen-3 best practice.

## Data Retention and Archival

No data retention or archival policies are configured in this exemplar. For production payment services using this pattern, THEATER_HISTORY is the appropriate model for transaction audit logs, and a retention policy (e.g., 7 years for financial records) must be defined and implemented.
