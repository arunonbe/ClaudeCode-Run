# Data Architect — wirecard_corporate-client-module_LIB

## Data Stores
| Store | Technology | Purpose |
|---|---|---|
| Primary database | Oracle (production), H2 in-memory (dev/test) | Corporate client data, cards, contacts, audit log |
| EventHub | ActiveMQ | Inbound `AccountStateEvent` consumption |
| EhCache 3 (JCache) | In-process heap cache | Application-level caching |

## Schema / Tables (from Liquibase changelogs v1.0 through v1.2 + history tables)

### `CORP_CLIENT` — Core corporate client record
Key columns: `ID` (PK, VARCHAR2(32)), `CORP_CLIENT_KEY` (BIGINT, unique), `SHORT_NAME` (unique), `ORGANIZATION_UNIT_ID`, `NOTIFICATION_EMAIL_ADDRESS`, `STATUS`, `CRM_NUMBER`, `COMMENTS`, audit cols.

### `CORP_ADDRESS` — Mailing/billing addresses
Street, house number, line two, ZIP code, city, state, country (2-char), address type.

### `CORP_CONTACT` — Contact persons (PII-heavy)
| Column | Notes |
|---|---|
| FIRST_NAME, LAST_NAME | **PII** |
| EMAIL_ADDRESS | **PII** |
| PHONE_NUMBER | **PII** |
| DATE_OF_BIRTH | **PII (sensitive)** |
| T_PIN | **Potentially SAD/PII — critical compliance finding** |
| INDEX_KEY | Unique per client |

### `CORP_WIRECARD_CONTACT` — Internal Wirecard contacts
Name, type, FK to `CORP_CLIENT`.

### `LEGAL_ENTITY` — Legal entity for corporate client
Name, email, address FK, FAX, URL, business purpose, commercial register, VAT_ID, phone numbers.

### `CORP_CLIENT_BRAND` — Corporate client to brand mapping
`CORP_CLIENT_ID` FK, `BRAND_NAME` (unique index).

### `CORP_CLIENT_CUSTOM_FIELD` — Flexible key-value attributes
`FIELD_TYPE`, `FIELD_VALUE` (unique constraint on type+value), FK to `CORP_CLIENT`.

### `CORP_CLIENT_LOG` — Audit history
`ACTION_TYPE` (CREATE/UPDATE/TERMINATE), `RESULT_TYPE` (SUCCESS/FAIL), `DETAILS` (VARCHAR2(2048)), FK to `CORP_CLIENT`.

### `CRM_COMMENTS_CORPORATE` — CRM comment linking table
Links comments to `CORP_CLIENT_LOG` entries.

### `CARD` — Issued card records
`VCA` (BIGINT), `ACCOUNT_REF_ID`, `CARD_REF_ID` (unique).

### Additional tables (from history changelog)
`CORP_CLIENT_CONTACT_HISTORY`, `CORP_CLIENT_ADDRESS_HISTORY`, etc. (from `db.changelog-history-tables-1.0.xml` — not fully read).

### `PRODUCT` and `PRODUCT_HISTORY` (from v1.2 — not fully read)
Product management tables.

## Sensitive Data Assessment

| Data Element | Table / Column | Classification | Compliance Requirement |
|---|---|---|---|
| Contact first/last name | `CORP_CONTACT` | PII | GDPR Art 4, CCPA, GLBA |
| Email address | `CORP_CONTACT` | PII | GDPR, CCPA |
| Phone number | `CORP_CONTACT` | PII | GDPR, CCPA |
| Date of birth | `CORP_CONTACT.DATE_OF_BIRTH` | Sensitive PII | GDPR Art 9 (special category), CCPA |
| T_PIN | `CORP_CONTACT.T_PIN` | **Potentially SAD** | **PCI DSS Req 3.2.1 — must not be stored** |
| VAT ID | `LEGAL_ENTITY.VAT_ID` | Business identifier | Varies by jurisdiction |
| Commercial register | `LEGAL_ENTITY.COMMERCIAL_REGISTER` | Business PII | GDPR (B2B context) |
| Notification email | `CORP_CLIENT.NOTIFICATION_EMAIL_ADDRESS` | Business PII | |
| Account ref ID | `CARD.ACCOUNT_REF_ID` | Payment reference | PCI DSS adjacent |
| Card ref ID | `CARD.CARD_REF_ID` | Payment reference | PCI DSS adjacent |

## Encryption
- **JDBC TLS**: `DataSourceTruststoreProperties` + `DataSourceConfiguration` pattern (same as `check-agent`); TLS enabled when `tlsEnabled: true`. Truststore Base64-decoded from config at startup.
- **At-rest**: No application-layer column encryption visible. Oracle TDE is not configured at application level — must be addressed at infrastructure level.
- **`T_PIN` column**: If this is a PIN value, it **must** be encrypted with a strong algorithm (Triple-DES or AES at minimum) per PCI DSS Req 3.5. Storage of cleartext PINs is prohibited.
- **EventHub**: ActiveMQ `tcp://` in dev config — production must use SSL transport.

## Data Flow
```
REST API (POST /callcenter-api/corporate-clients)
  --> CorporateClientController
  --> CorporateClientLogHandler
  --> CorporateClientService
  --> JPA Repositories (Oracle): CORP_CLIENT, CORP_ADDRESS, CORP_CONTACT, LEGAL_ENTITY, CORP_CLIENT_BRAND
  --> CORP_CLIENT_LOG (audit entry)
  --> ISS Auth Server (technical user creation, optional)

REST API (POST /callcenter-api/corporate-clients/{key}/cards)
  --> CardHandler
  --> CCP Client (HTTP) - fund reservation
  --> CMM Client (HTTP) - card creation
  --> CARD table (Oracle)

EventHub Consumer (AccountStateEvent)
  --> EventConsumerContext
  --> AccountStateEventHandler (inferred)
  --> VirtualClientAccount state update (via CCP or local DB)
```

## Data Quality / Retention
- All tables include `INSERTED_AT/BY`, `UPDATED_AT/BY` audit columns with Oracle `SYSDATE` defaults.
- `CORP_CLIENT_LOG` provides an append-only audit trail.
- No data retention or purge policy defined in the codebase.
- `LEGAL_ENTITY.COMMERCIAL_REGISTER` and `VAT_ID` data quality is not validated beyond VARCHAR length constraints.

## Compliance Gaps
1. **CRITICAL — `T_PIN` storage**: `CORP_CONTACT.T_PIN VARCHAR2(16)` — if this is a PIN, storing it violates PCI DSS Req 3.2.1 (prohibits storage of SAD after authorisation). Requires immediate clarification of what `T_PIN` represents. If it is a card PIN or security PIN, it must not be stored.
2. **PII without column encryption**: Contact names, DOB, email, phone in `CORP_CONTACT` are stored in plaintext. Under GDPR Article 32, appropriate technical measures for PII protection are required.
3. **DATE_OF_BIRTH retention**: With no defined retention policy, DOB data may be retained beyond its legitimate purpose — GDPR violation risk.
4. **No data masking for logs**: Application logs may contain PII from request/response logging (Logstash encoder enabled in `check-agent-rest-controller` pattern — confirmed present via `build.gradle` dependency).
