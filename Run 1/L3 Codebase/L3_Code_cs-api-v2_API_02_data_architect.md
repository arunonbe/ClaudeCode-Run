# Data Architect View — cs-api-v2_API

## Data Stores
| Store | JNDI Name | Purpose | Technology |
|---|---|---|---|
| JobSvcDataSource | `jdbc/JobSvcDataSource` | PUID lookup | SQL Server (jTDS driver) |
| EcountCoreDataSource | `jdbc/EcountCoreDataSource` | Status list lookup; transaction data via platform | SQL Server |
| C-Base xPlatform | (proprietary RPC via EMember/EDevice) | Member registration, card device inquiry, member update | Proprietary |

Note: V2 does **not** use CbaseappDataSource for affiliate lookup — there is no affiliate service. Application IDs are resolved via a static HashMap in the Spring XML configuration.

## Schema
### accountManagementContext.xml configMap (static application_id → program_id mapping)
The configMap in `accountManagementContext.xml` contains approximately 20 entries mapping MD5-style application_id strings to 8-digit program IDs (format `04XXXXXX`). This is the V2 authentication/routing mechanism. No dynamic affiliate service is used.

### AccountProfile (input to updateAccountProfile)
```
puid            String (required, max 50)
program_id      String (translates to affiliate via configMap; max 8 for direct, or application_id)
address_1       String (max 26)
address_2       String (max 26, optional)
city            String (max 18)
state           String (max 2)
postal          String (max 10)
country         String (max 2, US or CA)
home_email      String (max 50)
home_phone      String (max 16)
mobile_phone    String (max 16, optional)
business_phone  String (max 16, optional)
first_name      String (max 25)
last_name       String (max 25)
middle_name     String (max 25, optional)
suffix_name     String (max 25, optional)
```

### ResultCode (response from updateAccountProfile)
```
code        String ("0" = success, "1"–"7" = various error conditions)
description String
```

### Returned AccountInquiry (same as V1)
```
Balance:          balance_available, balance_ledger, balance_pending, balance_date
CardDetail:       card_number (masked), puid, program_id, created_date, last_plastic_date, expiration, account_status
TransactionDetail[]: transaction_date, amount, fee, type, details (always "XXXX" in V2)
Registration:     address, name, phone, email fields
Response:         completion_code, completion_message
```

## Sensitive Data — Locations (Values NOT Reproduced)
| Data Type | Location | Risk |
|---|---|---|
| Application ID → program_id mapping | accountManagementContext.xml (production config references `applicationContext-xCSAPI.properties` via `file:` path) | API key table; should be in secrets store |
| Hardcoded developer credentials (commented out) | accountManagementContext.xml (commented `<bean id="EcountCoreDataSource">`) | Developer database credentials (`andrewc`/`andrewc`) visible in XML comment — should be purged |
| Hardcoded database server name | accountManagementContext.xml comments | Internal SQL Server hostname `ecsqldev1` visible in comments |
| `configPath` | accountManagementContext.xml | `d:\\c-base\\config\\ecount-config.xml` — Windows path |
| Agent value | accountManagementContext.xml/ecountContext bean | `B2CSTAGE` — environment identifier |

## Encryption
- **At rest**: No encryption in this layer; JNDI DataSource credentials managed by application server configuration.
- **In transit**: HTTPS assumed at server level; no message-level security.
- **Card masking**: XXXXXXXX + last 8 — same as V1.
- **No secrets management**: Application ID-to-program-ID mapping and platform config paths are in plain XML.

## Data Flow
```
SOAP Client
    │ HTTPS SOAP (axis)
    ▼
Apache Axis Servlet (/CardManagementV2/services/AccountManagement)
    │
    ├── AccountManagementImpl.accountInquiry()
    │   └── getProperties() → new ClassPathXmlApplicationContext("accountManagementContext.xml") [EVERY CALL]
    │         → requestContextLookup.lookup(application_id) → program_id
    │         → EMember / EDevice (xPlatform RPC)
    │         → PuidLookup / BalanceLookup (JobSvc/EcountCore SQL Server)
    │
    └── AccountManagementImpl.updateAccountProfile()
          → getProperties() → same per-call context load
          → validateRequest() / prepareInputData()
          → EMember.puidMemberSearch() → memberId
          → EMember.processInquiryExtended() → current registration
          → checkAgainstExistingProfile() → validate postal/state
          → updateRegistrationInfo() → EMember.processUpdate()
    │
    ▼
SOAP Response (AccountInquiry or ResultCode)
```

## Critical Performance Issue
`AccountManagementImpl.getProperties()` creates a **new `ClassPathXmlApplicationContext`** on every single request call. This loads and initialises the entire Spring application context (bean definitions, JNDI lookups, property placeholder resolution) on every SOAP invocation. This is severely inefficient:
- Spring context creation takes hundreds of milliseconds
- Under any load, this will be a dominant latency contributor
- JNDI lookups are repeated per request
This pattern was corrected in V1 and V3 which use singleton/application-level Spring contexts.

## Data Quality
- **No transaction date range defaults**: If `start_date = 0`, no minimum date is set (V3 defaults to `new Date(0)` — epoch). V2 passes 0 directly to `jourInquiry.setStartDate()`.
- **`ecard.getCreditCard().getLastEmbossDate()`** called without null check in V2 — potential NPE if card has no last emboss date.
- **Postal validation**: US: 5-digit or 9-digit ZIP-plus-4; Canadian: `A#A #A#` format. Implemented in `checkAgainstExistingProfile`.

## Compliance Gaps
1. **Developer credentials in XML comments**: The commented-out `DriverManagerDataSource` bean contains a hardcoded SQL Server username and password. Although commented, this is a PCI DSS Requirement 2.2.3 violation (do not embed authentication credentials in code). Must be removed.
2. **No affiliate-level permission check**: Any application_id in the configMap has unrestricted V2 access; there is no `cs_api_enabled` flag.
3. **No audit trail for updateAccountProfile**: PII changes (address, email, phone) have no structured audit log entry.
4. **jTDS JDBC driver (1.2)**: Very old SQL Server JDBC driver — does not support TLS 1.2 connections in all configurations. Potential transport encryption risk for database connections.
