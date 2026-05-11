# core2-common_LIB — Data Architect View

## Data Stores

This library contains **no direct database access code and no SQL statements**. It is a pure contract library. However, the following data store relationships are inferred from class names, Javadoc comments, and field names:

| Inferred Data Store | Evidence |
|---|---|
| Core2 relational database (likely SQL Server or similar) | `SQLMapper.java` maps `java.sql.ResultSet` to value objects; `MetaDataCache` caches column metadata by class name |
| `fdr_profile_transaction_field_type` table | Javadoc in `IMemberService.java` line 44: "Valid keys are defined in DB table fdr_profile_transaction_field_type" |
| `core_symbols` table | Javadoc in `IMemberService.java` line 143: device types "defined under core_symbols DB table" |
| "Strong box" / PII vault | `IMemberService.AddExtended` Javadoc lines 58-62: "a new secure profile will be stored in strong box" |
| "Director" service | `IMemberService.AddExtended` Javadoc line 62: "attempt to look for a secure profile with the given ID in director" |
| GitHub Packages Maven registry | `settings.xml`: `https://maven.pkg.github.com/onbe/onbe_maven_releases` |

---

## Schema & Tables

No DDL is present in the repository. The following logical schema is inferred from Java value-object fields, which directly map to DB columns via `SQLMapper` (column names must match field names):

### Member / Enrollment
| Object | Field | Java Type | Notes |
|---|---|---|---|
| `UserEnrollment` | `program` | String | Program code |
| `UserEnrollment` | `affiliate` | Integer | 4-digit numeric |
| `UserEnrollment` | `agent` | String | e.g. "B2CTEST" |
| `UserEnrollment` | `promotion` | String | |
| `UserEnrollment` | `date` | Timestamp | Enrollment date |
| `UserEnrollment` | `updated` | Timestamp | Last updated |

### Registration
| Object | Field | Java Type | Notes |
|---|---|---|---|
| `BasicRegistration` | `first_name`, `last_name`, `middle_name`, `suffix_name` | String | |
| `BasicRegistration` | `email_address`, `home_email`, `business_email`, `mobile_email` | String | |
| `ExtendedRegistration` | `address1`, `address2`, `attention_line`, `company_name` | String | |
| `ExtendedRegistration` | `city`, `state`, `postal`, `country` | String | ISO country code |
| `ExtendedRegistration` | `phone`, `home_phone`, `business_phone`, `mobile_phone` | String | |

### Secure Profile (PII vault)
| Object | Field | Java Type | Notes |
|---|---|---|---|
| `SecureUserProfile` | `federal_id` | String | SSN — up to 10 digits after normalization |
| `SecureUserProfile` | `date_of_birth` | String | |
| `SecureUserProfile` | `driver_license_number`, `driver_license_state` | String | |
| `SecureUserProfile` | `passport_number`, `passport_country` | String | |
| `SecureUserProfile` | `military_number` | String | |
| `SecureUserProfile` | `alien_number`, `alien_country` | String | |

### Account / Device
| Object | Field | Java Type | Notes |
|---|---|---|---|
| `Account` | `id` | UUID | Primary key (GUID) |
| `AccountDefinition` | `device_type` | String | eCard / eCheck / CreditCard / ACH / DDA / Operator |
| `AccountDefinition` | `block_code` | String | active / closed / suspended / batch-initialized / batch-queued |
| `AccountDefinition` | `is_protected`, `is_default` | boolean | |
| `StoredValueCard` | `number` | String | 16-digit PAN |
| `StoredValueCard` | `activation_code`, `block_code`, `pin_selection_code`, `statement_code` | String | |
| `StoredValueCard` | `last_emboss_date`, `created` | Timestamp | |
| `StoredValueCard` | `is_ciu`, `universal_address`, `card_id` | int | |
| `StoredValueCard` | `access_level` | String | |
| `CreditCard` | `cv_code` | String | CVV/CVC |
| `CreditCard` | `exp_month`, `exp_year` | int | |
| `CreditCard` | `type` | String | CreditCardTypes constants |
| `StoredValueAccount` | `number` | String | DDA account number |
| `BankAccount` | `routing_number`, `account_number` | String | |
| `BankAccount` | `account_type`, `account_holder_name`, `country` | String | |
| `CardProfile` | `card_type`, `processor_type` | int | |
| `CardProfile` | `sys_prin_agent`, `auth_strategy` | String | |
| `CardProfile` | `atm_enabled`, `intl_enabled`, `activation_required` | boolean | |
| `CardProfile` | `universal_address`, `is_ciu`, `pin_delay_days` | int | |

### Account Balance
| Object | Field | Java Type | Notes |
|---|---|---|---|
| `AccountBalance` | `ledger`, `pending`, `available` | int | Cents |
| `AccountBalance` | `date` | Date | Balance date |

### Transaction Journal
| Object | Field | Java Type | Notes |
|---|---|---|---|
| `CoreTransactionJournal` | `id`, `device_id`, `transaction_group` | UUID | |
| `CoreTransactionJournal` | `amount`, `fee`, `adjusted_amount` | int | Cents |
| `CoreTransactionJournal` | `transaction_state`, `transaction_ordinal` | int | |
| `CoreTransactionJournal` | `device_type`, `created` | String / Timestamp | |

### PreCheck
| Object | Field | Java Type | Notes |
|---|---|---|---|
| `PreCheckDefinition` | `check_account_number`, `serial_number` | String | |
| `PreCheckDefinition` | `authorized_amount`, `authorize_fee`, `stop_fee` | Integer | Cents |
| `PreCheckDefinition` | `authorization_code`, `admin_override_code` | Integer / String | Sensitive |
| `PreCheckDefinition` | `merchant_verified_code`, `disposition`, `disposition_reason`, `memo` | String | |
| `PreCheckDefinition` | `assigned_date`, `authorized_date`, `settled_date`, `check_stop_date` | Timestamp | |

### Transfer
| Object | Field | Java Type | Notes |
|---|---|---|---|
| `TransferDefinition` | `id` | UUID | |
| `TransferDefinition` | `state`, `converged`, `risk` | int | |
| `TransferDefinition` | `activity`, `name` | String | |
| `Funds` | `amount` | int | Cents |
| `Funds` | `currency` | String | ISO currency code |

---

## Sensitive Data Handling

The library defines the **data shapes** for sensitive data. Actual storage and access control are delegated to implementing services. Key observations:

1. **PAN (card number)**: `CreditCard.number` and `StoredValueCard` (via inheritance) carry the full 16-digit PAN as a plain `String`. No masking, encryption, or tokenization is applied at the library level. The Luhn validation in `CreditCard.validate()` operates on the full PAN.
2. **CVV/CVC**: `CreditCard.cv_code` stores the security code as a plain `String`. PCI DSS prohibits storing SAD post-authorization; this library does not enforce that constraint.
3. **SSN (`federal_id`)**: `SecureUserProfile.federal_id` is a plain `String`. The `validate()` method strips non-digits and truncates to last 10 digits, which provides minimal normalization but no masking.
4. **Date of Birth**: `SecureUserProfile.date_of_birth` is a plain `String` with no format enforcement.
5. **Bank account / routing numbers**: `BankAccount.account_number` and `routing_number` are plain `String` fields with no masking.
6. **Addenda**: The `Map<String,Object>` addenda can carry arbitrary sensitive data. No schema enforcement or field-level classification is present.
7. **`SecureUserProfile.id`**: References the ID of the record in the external "strong box" vault — not the PII itself. This is the correct pattern for referencing externally vaulted data.

---

## Encryption & Protection

- **No encryption libraries** are imported or referenced in this library.
- `commons-beanutils` is the only runtime dependency (`pom.xml`).
- Protection of PAN, CVV, SSN, and bank account data is entirely the responsibility of consuming services.
- The design intent (per Javadoc in `IMemberService`) is that `SecureUserProfile` data is stored in an external "strong box" vault; only the vault ID is carried in the member record. However, the DTO objects allow full PII to be populated and passed across service boundaries in clear text.

---

## Data Flow

```
Client Request
    │
    ▼
Input DTO (e.g., AddBasicXMLRPCInput)
    │  extends AgentAware (carries agent string)
    ▼
Service Interface (IMemberService / IDeviceService / IManageService / ITransfer)
    │  passed as decomposed value objects
    ▼
[Implementing Service — not in this library]
    │  uses SQLMapper to map ResultSet → value objects
    ▼
Output DTO (e.g., AddBasicOutput extends OutputBase)
    │  carries Result{code, message} + entity (Member/Account/Transfer)
    ▼
Client Response
```

**SQLMapper flow** (`utils/SQLMapper.java`):
- `mapObject(ResultSet, Class)` — reflects column names to bean field names using Apache Commons BeanUtils.
- `mapObjectCachingMetaData(ResultSet, Class, cacheKey)` — uses `MetaDataCache` (a `HashMap<String, List<String>>`) to cache column name lists per class name, avoiding repeated `getMetaData()` calls.
- Custom `UUIDConverter` registered for `UUID.class` — converts String columns to `java.util.UUID` automatically.
- Map-type fields on beans are handled specially: column names matching a Map field are converted to `beanUtils` map reference notation (`field(key)`).

---

## Data Quality & Retention

- **No retention policies** are defined in this library.
- **No data quality annotations** (e.g., `@NotNull`, `@Size`) are present. Validation is ad-hoc via `validate()` methods.
- **Null handling**: Many `validate()` methods normalize nulls to empty strings and back — this pattern can mask data quality issues (e.g., `BasicRegistration.validate()` will silently drop a null first_name without error).
- `BusinessObjectNotValidException` is thrown for hard structural violations (null UUID on Account, null ecount_id on `JobAccountMapDetails`), but most field-level nulls are silently coerced.
- **Amount precision**: All monetary values are Java `int` (cents). No `BigDecimal` is used, which is acceptable for US-cent amounts but limits multi-currency precision.

---

## Compliance Gaps

1. **PAN and CVV in the same object**: `CreditCard.java` holds both `number` (PAN) and `cv_code` (CVV) in the same class with no lifecycle separation. PCI DSS 3.3/4.0 requires CVV to be deleted post-authorization; no mechanism enforces this in the library.
2. **No field-level encryption markers**: There are no annotations or interfaces marking PAN, CVV, SSN, or DOB fields as requiring encryption. Consuming services must know to apply encryption via convention, not enforcement.
3. **`SecureUserProfile` fields are public instance variables** (not private with accessors in some cases — e.g., `federal_id`, `date_of_birth` are `public String` at declaration): This allows direct field access bypassing any potential future setter-level validation.
4. **No audit trail in the library**: No `@Audited` or event-sourcing mechanism is present. Audit must be implemented by consuming services.
5. **MetaDataCache is a shared mutable static**: `SQLMapper.metaDataCache` is a static `MetaDataCache` instance (`private static MetaDataCache metaDataCache` initialized in a static block). In multi-threaded servers this is accessed concurrently. `MetaDataCache.getMetaData()` uses `synchronized(metaDataKey.intern())` — interning arbitrary user-controlled strings is a potential memory leak and denial-of-service vector.
