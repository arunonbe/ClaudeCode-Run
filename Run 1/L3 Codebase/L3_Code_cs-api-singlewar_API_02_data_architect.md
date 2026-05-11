# Data Architect View — cs-api-singlewar_API

## Data Stores
This service does not own any data stores. It acts as a facade over the C-Base / ecount platform backend.

| Data Source | JNDI Name | Purpose | Technology |
|---|---|---|---|
| CbaseappDataSource | jdbc/CbaseappDataSource | Affiliate program/metadata lookups; PUID lookups | SQL Server (via Hibernate for affiliate service) |
| JobSvcDataSource | jdbc/JobSvcDataSource | PUID resolution (`GetPuid` stored procedure) | SQL Server |
| EcountCoreDataSource | jdbc/EcountCoreDataSource | (Referenced in web.xml; used by downstream platform libraries) | SQL Server |

All DataSource beans are configured via JNDI — the actual connection strings, usernames, and passwords are held in the application server's JNDI context (Tomcat/JBoss context.xml), not in source code.

The `context.xml` at `csapi-ws/src/main/webapp/META-INF/context.xml` would define JNDI resources but was not individually read; its JNDI structure is implied by the web.xml resource-ref declarations.

## Schema — Key Domain Objects

### CardDetail
```
card_number       String  (masked: XXXXXXXX + last 8)
puid              String  (Partner User ID)
program_id        int
created_date      Calendar
last_plastic_date Calendar
expiration        String  (MM/YYYY)
account_status    String  (active | closed | frozen | lost | Contact Ecount for Status)
ship_date         Calendar (V3 addition)
```

### Balance
```
balance_available int    (cents)
balance_ledger    int    (cents)
balance_pending   int    (ledger - available)
balance_date      Calendar
```

### TransactionDetail
```
transaction_date    Calendar
transaction_amount  int    (cents)
transaction_fee     int    (cents)
transaction_type    String (derived from activity + phase lookup)
transaction_details String (XXXX masked unless merchant display enabled)
payment_details     PaymentDetail[] (PPD promotion details, V3 only)
```

### Registration
```
first_name, last_name, company_name, attention_line  String
address_1, address_2                                 String
city, state, zip                                     String
home_phone, business_phone, mobile_phone             String
email                                                String
```

### CommentHistory (V3 only)
```
inquiryIdNumber    int
origDateReceived   Calendar
closedDate         Calendar
problemDescription String
inquiryTypeDesc    String
secondaryTypeDesc  String
employeeId         String
status             String
emailOrPhone       String
```

## Sensitive Data — Locations (Values NOT Reproduced)
| Data Type | Location | Risk |
|---|---|---|
| Application ID to Program ID mapping | accountManagementContext.xml (hardcoded in configMap) | API key table in source; should be in secrets store |
| configPath (Windows filesystem path) | accountManagementContext.xml | Reveals server directory structure |
| Syslog endpoint IP | csapi-ws/src/main/resources/log4j.properties | Internal infrastructure IP address in source |
| Platform config file path | accountManagementContext.xml | `d:\\c-base\\config\\ecount-config.xml` hardcoded |
| Card numbers in responses | Runtime only | Masked per code, not stored |

## Encryption
- **At rest**: No encryption implemented within this service layer. The C-Base platform handles any storage-level encryption.
- **In transit**: HTTPS assumed at the load balancer/web server level. No evidence of message-level (WS-Security) encryption in this codebase.
- **Card masking at display layer**: First 8 digits masked as `XXXXXXXX` in `AccountManagementImpl`. This is weaker than PCI DSS first-6/last-4 requirement; the V3 production repo (`cs-api-v3_API`) corrects this to first 4 + XXXXXXXX + last 4.

## Data Flow
```
SOAP Client
    │  (HTTPS, SOAP 1.1)
    ▼
Apache Axis Servlet (csapi-ws WAR)
    │
    ▼
AccountManagementImpl (V1 or V3 path, Spring bean)
    │
    ├── AffiliateService → CbaseappDataSource (SQL Server)
    │     (lookup app_id → affiliate_id; check cs_api_enabled flag)
    │
    ├── GetPuid → JobSvcDataSource (SQL Server)
    │     (PUID resolution)
    │
    ├── ecount xPlatform (DeviceManager, EMember)
    │     (C-Base RPC/proprietary protocol → Core platform)
    │
    └── CommentService (V3 only)
          (fetch comment history from comment store)
    │
    ▼
SOAP Response (AccountInquiry with masked card data)
```

## Data Quality
- **End-date normalization**: `add1DayToEndDate()` corrects for inclusive vs. exclusive date semantics.
- **Null-safety**: Most fields have empty-string defaults; `NullPointerException` risk exists on `ecard.getCreditCard().getLastEmbossDate()` (null check present in V3, absent in V1 path).
- **SQL injection mitigation**: `SQLInjectionScrubber.evenOutSingleQuotes()` and `stripWildChars()` applied in V3 for PPD and mobile phone inputs.
- **No input length enforcement** at the SOAP level — length validation is only in V3 `updateAccountProfile` path.

## Compliance Gaps
1. **Card masking weaker than PCI DSS**: XXXXXXXX+last-8 masks only 8 of 16 digits; PCI DSS requires at most first-6/last-4 (10 digits visible maximum). The singlewar version exposes 8 digits — borderline.
2. **Application IDs in XML config**: These function as shared secrets. PCI DSS Requirement 8.3 requires unique IDs per user; a shared `application_id` per affiliate program violates this if multiple applications share the key.
3. **Log4j 1.x**: The `log4j.properties` configures Log4j 1.x, which reached end-of-life in 2015 and has known CVEs.
4. **Syslog log destination in source**: The log4j config hardcodes an internal syslog server IP and facility setting — this is an infrastructure leak.
5. **No audit logging of sensitive operations**: Card lookups and account updates do not appear to generate audit events beyond application-level INFO logs.
