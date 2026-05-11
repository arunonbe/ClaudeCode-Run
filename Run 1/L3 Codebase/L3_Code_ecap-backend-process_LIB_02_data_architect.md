# ecap-backend-process_LIB — Data Architect Report

## Data Architecture Overview

`ecap-backend-process_LIB` operates entirely against **SQL Server** databases via JDBC. It does not have its own database schema — it is a consumer of the `ecountcore` and `cbaseapp` databases. Data access is implemented using:
- Spring JDBC `JdbcTemplate` (wrapped in custom DAO classes)
- SQL Server stored procedures called via Spring's `StoredProcedureItemReader` and custom `StoredProcedure` wrappers
- Apache Commons DBCP connection pooling

---

## Database Configuration

The library loads its data source configuration from a Spring XML context file (`applicationContext-ecap-datasource.xml`) and the main `applicationContext.xml`. The data source parameters are externalized to a properties file:
```
file:///d:/c-base/config/ecap-backend-process/card-creation.properties
```
(`applicationContext.xml`, line 11-14)

This properties file is not in the repository — it is a runtime configuration file. The data source appears to connect to SQL Server on a host managed by the `director-client` service (`director-client-1.0.9` dependency in `pom.xml`, line 111).

---

## DAO Layer — Tables and Stored Procedures

### `EcapRecipientDaoImpl.java` (Primary DAO — 9,641 bytes)
This is the core data access class for recipient management. Based on method names in `IEcapRecipientDao.java`:

| Method | Target DB Object | Purpose |
|---|---|---|
| `getRecipients()` | Stored proc / view | Fetches pending card creation requests |
| `updateRecipientStatusCode()` | Recipient table | Updates processing status |
| `updateRecipientProcessCounter()` | Recipient table | Increments retry counter |
| `getAffiliate()` | Affiliate/program table | Retrieves program/affiliate config |
| `getBinInfo()` | BIN table | BIN validation for card creation |

### `EcapUpdateProcessCounterAndStatusCodeStoreProc.java`
Calls a stored procedure to atomically update both the process counter and status code for a recipient record. This is a critical idempotency mechanism — it prevents double-processing of card requests.

### `InsertCommentDAOImpl.java` (3,218 bytes)
Inserts audit trail comments into the comment/workflow tracking tables.

### `GetCsaInquiryCategoryByInquiryType.java` (1,559 bytes)
Reads CSA (Customer Service Agent) inquiry category configuration. References `dbo.get_csa_inquiry_category_by_inquiry_type` or equivalent stored procedure.

---

## Key Data Entities

### `Recipient` — `Recipient.java`
Maps to a recipient/request queue table (likely `ecountcore.dbo.ecap_recipient` or `cbaseapp.dbo.ecap_recipient`). Fields:

| Field | Type | Sensitivity |
|---|---|---|
| `recipient_id` | int | Internal ID |
| `member_id` | String | Account identifier |
| `first_name`, `middle_name`, `last_name` | String | **PII — Name** |
| `address1`, `address2`, `city`, `zip_code`, `state_code`, `country_code` | String | **PII — Address** |
| `email_id` | String | **PII — Email** |
| `card_value` | Long (cents) | Financial |
| `plastic_fee`, `shipping_fee` | Long (cents) | Financial |
| `status_code` | String | Processing state |
| `process_counter` | int | Retry count |
| `affiliate_id` | String | Program ID |
| `program_id` | String | Program reference |
| `locale_id`, `locale` | String | Language setting |
| `confirmation_number` | String | Transaction reference |
| `embossMessage` | String | Card emboss text |
| `cardType` | String | Card product type |
| `shipTo` | String | Shipping destination |

No PAN, CVV, or PIN fields are present in `Recipient.java` — the card number is generated and managed entirely within the eCount core system.

### `CardRequest` — `CardRequest.java` (4,874 bytes)
Wraps `Recipient` with:
- `parent_member_id` — the purchaser's member ID
- `parent_email_lang` — language preference for failure notifications
- Processing state flags and fee details

### `GetCsaInquiryCategoryByInquiryTypeValue` — `GetCsaInquiryCategoryByInquiryTypeValue.java`
Lookup data value object for CSA inquiry category configuration.

---

## State Machine Data Flow

### State Transitions Write to Database
Each state class in the `state/` package interacts with the eCount core system through the `xPlatform` and `ecount-system` dependencies (the cbase business layer):

| State | Database Interactions |
|---|---|
| `CreateMemberState` | Creates member record in `cbaseapp.dbo.member` or equivalent |
| `CreateGiftCardState` | Creates card device in eCount core (`ecountcore.dbo.device`) |
| `CreateDDAState` | Creates DDA device in eCount core |
| `DDAToDDAFundTransferState` | Initiates fund transfer via ECountCore transfer API |
| `PurchaserRecipientLinkState` | Links purchaser member ID to recipient in association table |
| `EndState` | Final status update via `EcapUpdateProcessCounterAndStatusCodeStoreProc` |

---

## Notification Data Elements in Database

`EcapEmailNotificationImpl.java` calls `MemberManagerImpl.InquiryBasic()` (line 42) to retrieve:
- `basic.getRegistration().getFirstName()` — purchaser first name
- `basic.getRegistration().getLastName()` — purchaser last name
- `basic.getRegistration().getEmailAddress()` — purchaser email

These are read from the `cbaseapp.dbo.registration` or equivalent table and are used only to populate email notification parameters — they are not persisted by this library.

---

## Logging Configuration

`log4j.properties` (`src/main/resources/log4j.properties`):
- Log output to console and file
- Log level: INFO for production, DEBUG for development
- **Risk**: Exception messages are logged with `e.getMessage()` and `e.printStackTrace()` in `EcapEmailNotificationImpl.java` (lines 85–86). Stack traces may contain member IDs or other PII if exceptions occur during member inquiry. Log files should be treated as containing PII.

---

## Dependency Libraries and Data Access Patterns

| Dependency | Version | Purpose | Risk |
|---|---|---|---|
| `spring` | 2.0.8 | Core IoC/DI | EOL — unsupported |
| `log4j` | 1.2.15 | Logging | **CVE-2019-17571** (socket appender vulnerability) |
| `sqljdbc` | 1.1 | SQL Server JDBC | Very old; use `mssql-jdbc` 12.x |
| `mssql-jdbc` | 6.4.0.jre7 | SQL Server JDBC | Outdated; no TLS 1.3 support |
| `xPlatform` | 2.5.28 | eCount platform | Internal Gen-1 library |
| `ecount-system` | 2.0.0 | eCount core system | Internal Gen-1 library |
| `director-client` | 1.0.9 | Data source routing | Internal infrastructure |
| `comment` | 1.0.0 | Comment/audit library | Internal library |

The combination of `log4j:1.2.15` and `spring:2.0.8` indicates this library has **not been updated in approximately 12–15 years**.
