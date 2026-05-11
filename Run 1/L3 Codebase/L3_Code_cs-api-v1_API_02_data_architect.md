# Data Architect View — cs-api-v1_API

## Data Stores
The service itself does not own data. It reads from three downstream data sources:

| Data Source | Spring Bean / JNDI | Purpose | Technology |
|---|---|---|---|
| CbaseappDataSource | `CbaseappDataSource` | Affiliate/program metadata; Hibernate entity mapping for affiliate service; PUID lookup support | SQL Server |
| JobSvcDataSource | `JobSvcDataSource` | PUID-to-member-ID resolution via stored procedure | SQL Server |
| C-Base xPlatform | Not a JDBC source — proprietary RPC | Card balance, journal, device definition, member registration data | Proprietary C-Base protocol via xPlatform library |

In the Spring Boot module (`card-management-boot`), the data sources are configured via Azure App Configuration:
- `spring.datasource.jobsvc.*` — URL, username, password injected from Azure App Config at runtime
- `spring.datasource.cbaseapp.*` — same pattern
- Credentials are NOT stored in source code; application.yml contains placeholder values (`url-from-app-config`)

## Schema — Returned Domain Objects

### CardDetail (card-management-ws)
```
card_number       String  (XXXXXXXX + last 8 — 16-char masked value)
puid              String
program_id        int
created_date      Calendar
last_plastic_date Calendar
expiration        String  ("MM/YYYY")
account_status    String  (active | closed | frozen | lost | "Contact Ecount for Status")
```
Note: `ship_date` field exists in the domain object but is only populated in V3. In V1 it is set but never returned to the caller through the V1 API.

### Balance
```
balance_available int   (cents)
balance_ledger    int   (cents)
balance_pending   int   (ledger - available, cents)
balance_date      Calendar
```

### TransactionDetail
```
transaction_date    Calendar
transaction_amount  int   (cents)
transaction_fee     int   (cents)
transaction_type    String (mapped from activity+phase via DescriptionLookup inner class)
transaction_details String ("XXXX" or PPID value)
```

### Registration
```
address_1, address_2   String
attention_line         String
company_name           String
city, state, zip       String
email                  String
first_name, last_name  String
home_phone, business_phone, mobile_phone  String
```

## Sensitive Data — Locations (Values NOT Reproduced)
| Data Type | Location | Notes |
|---|---|---|
| DB credentials | Azure App Config (not in source) | Injected at runtime via Azure Key Vault + Managed Identity |
| Application config values (agent, appId, classification) | `applicationContext-V1.yml` | Non-secret config values; agent = B2CSTAGE |
| Azure Managed Identity client ID | `bootstrap.yaml` via `${AZURE_MANAGED_IDENTITY_CLIENT_ID}` | Injected via environment variable; not in source |
| Azure App Config endpoint | `bootstrap.yaml` via `${AZURE_APP_CONFIG_ENDPOINT}` | Injected via environment variable |
| Azure App Config connection string (local dev only) | `bootstrap.yaml` via `${AZURE_APP_CONFIG_CONNECTION_STRING}` | Local profile only; not committed |

## Encryption
- **At rest**: Database credentials managed by Azure Key Vault; not present in source.
- **In transit**: HTTPS via server/load balancer. Azure Managed Identity used for Azure service authentication (no static credentials).
- **Card masking**: XXXXXXXX + last 8 in response. PCI-compliant display masking (though V3 adopts more conservative masking).
- **No field-level encryption** in responses — balance amounts are returned in plaintext integers.

## Data Flow
```
SOAP Client
    │ HTTPS SOAP 1.1
    ▼
Spring Boot Application (cardmanagementws)
  (Spring-WS / Apache Axis via card-management-war module)
    │
    ├── AffiliateService
    │     └── HibernateSessionFactory → CbaseappDataSource (SQL Server)
    │           (getAffiliateForValue("cs_api_v1_app_id", application_id))
    │           (getMetadata(6, affiliateId) — cs_api_enabled, cs_api_v1, cs_api_disp_merchant_name)
    │
    ├── GetPuid → JobSvcDataSource (stored procedure call)
    │     (PUID to member ID resolution)
    │
    ├── xPlatform (EMember, EDevice)
    │     └── C-Base proprietary RPC (configured via ecount-config.yml / bootAddress)
    │           EMember.puidMemberSearch() → JobAccountMapDetails
    │           EDevice.createDevice() → device ID
    │           EDevice.processInquiry() → balance, journal, definition, member
    │           EMember.processInquiryExtended() → registration data
    │
    └── ProgramIdAwareGlobalRequestIDGenerator
          └── Log4jMDCWriter → MDC context for correlation logging
    │
    ▼
SOAP Response (masked AccountInquiry)
```

## Data Quality
- **Date normalisation**: `add1DayToEndDate()` handles edge case of zero or malformed end dates.
- **Null safety for lastEmbossDate**: `if(ecard.getCreditCard().getLastEmbossDate() != null)` — null check correctly implemented in V1.
- **Integer math for balance**: Balances stored as integer cents — no floating point risk.
- **PPID addenda extraction**: Nested null checks for `TransactionAddenda` and its `Dictionary`.

## Compliance Gaps
1. **PCI DSS card masking**: XXXXXXXX + last 8 exposes 8 digits — technically exceeds PCI DSS's "no more than first 6/last 4" but the last-8 exposure is borderline. V3 corrects to first 4 + XXXXXXXX + last 4.
2. **No cardholder data in logs confirmed**: `log.debug("card_number: {}", card_number==null ? "": card_number.replaceAll("[^\\w]+", " "))` sanitises the card number before logging — this is good practice.
3. **Structured security audit logging absent**: Card lookups are INFO-logged with class name, method, and duration only. No separate PCI audit event channel.
4. **Azure App Config refresh interval**: Set to 15 minutes (`${AZURE_APP_CONFIG_REFRESH_INTERVAL:15m}`) — configuration changes take up to 15 minutes to propagate; acceptable for non-security config but could be a concern for rapid response to a compromised application_id.
