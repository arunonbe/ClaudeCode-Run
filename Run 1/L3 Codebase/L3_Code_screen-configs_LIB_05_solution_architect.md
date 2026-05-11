# 05 Solution Architect — screen-configs_LIB

## Technical Architecture
Spring 2.0.4 library JAR (`screenconfigs:2016.2.1`). Pure service layer with no HTTP surface. Exposes a single manager interface (`InstIssueCZSetupScreenCfgManager`) backed by a DAO (`InstIssueCZScreenCfgDao`) that executes named SQL Server stored procedures. All wiring is via Spring XML (`applicationContext-instIssueCZScreenCfg.xml`). Consumed by caller applications as a compile-time dependency.

Key classes:
- `InstIssueCZSetupScreenCfgManager` (interface) / `InstIssueCZSetupScreenCfgManagerImpl` — business logic: reads screen driver flags, reversal/payment reasons, display defaults, O-account details; writes settings
- `InstIssueCZScreenCfgDao` / `InstIssueCZScreenCfgDaoImpl` — JDBC stored-procedure wrappers using xPlatform infrastructure
- Stored-procedure wrappers in `dao/jdbc/`: `CallInquiryDisplayDefaultData`, `CallInquiryOAccountDetails`, `CallInquiryPaymentReasons`, `CallInquiryReversalReasons`, `CallInquiryScreenDriverFlags`, `CallSaveInstIssueDisplayDefaultData`, `CallSaveInstIssueDisplaySettings`, `CallSaveInstIssuePmtOrRevReasons`, `CallSaveOAccountDetails`
- `InstIssueCZScreenCfgRecord` (domain) — generic column-indexed row result
- `InstIssueCZScreenCfgOptions` (DTO) — programId-keyed option bag for stored-proc calls
- `InstIssueCZScreenCfgDaoResult` (DTO) — list of `InstIssueCZScreenCfgRecord`

## API Surface
No HTTP or RPC API. Programmatic Java library API only:

```java
// Manager interface — key methods
List<String>                   inquireReversalReasonSettings(String programid)
Map<String,String>             inquirePaymentReasonSettings(String programid)
Map<String,Map<String,String>> inquireScreenDriverFlags(String programid)
Map<String,String>             inquireDisplayDefaultsData(String programid)
List<Map<String,String>>       inquireCCAdminLayout(String programid)
Map<String,Map<String,String>> inquireSectionsLayout(String programid)
Map<String,String>             inquireAccountSuspensionParams(String programid)
void savePaymentReasonSettings(InstIssueCZScreenCfgOptions cfgOpts)
void saveInstIssueDisplayDefaultData(InstIssueCZScreenCfgOptions cfgOpts)
void saveInstIssueDisplaySettings(InstIssueCZScreenCfgOptions cfgOpts)
void saveOAccountDetails(InstIssueCZScreenCfgOptions cfgOpts)
int  create(InstIssueCZScreenCfgRecord settingsRecord)  // stub — not implemented
```

## Security Posture
- No authentication or authorisation at the library level; all callers assumed to be trusted internal services
- No PAN, CVV, or cardholder financial data flows through this library; the data model is programme configuration only
- `dspHidePIIFld` flag visible in `inquireCCAdminLayout()` — the library controls whether PII is displayed in call-centre screens; misconfiguration of this flag is a PII exposure risk
- String-equality comparisons use `0 == "literal".compareTo(key.trim())` idiom — correct but unconventional; no injection risk as `programid` is passed directly to stored procedures (injection risk is in the DAO/xPlatform layer, not visible here)
- xPlatform version `2.5.28` is old; stored-procedure parameter binding through xPlatform must be verified as using parameterised queries (not string concatenation)

## Technical Debt
| Item | Severity |
|---|---|
| Spring 2.0.4 (EOL > 15 years) | Critical |
| Java compile target inferred from parent (likely 1.5/1.6) | High |
| Raw type usage: `new TreeMap()`, `new ArrayList()` (unchecked) | Medium |
| `create()` method stubbed — returns 0 and is unimplemented | Medium |
| Generic column-indexed result model (`column2`, `column3`, `column4`) — no type safety | Medium |
| xPlatform `2.5.28` dependency (internal, opaque, old) | Medium |
| No `@Override` annotations in impl | Low |
| `//TODO: Also obtain payment reasons....` in `inquireSectionsLayout()` | Low |
| JUnit 3.8.1 for tests | Low |

## Gen-3 Migration
- Replace the library with a Spring Boot 3.x `@Service` and JPA/JDBC repository, retaining the same logical API surface
- Replace generic column-indexed `InstIssueCZScreenCfgRecord` with typed entities per screen-config category
- Expose screen config reads as a REST API (`GET /programme/{id}/screen-config/...`) for consumption by the new UI layer
- Move stored-procedure logic to JPA named queries or Spring Data JDBC methods with named parameters
- Replace xPlatform JDBC wrappers with standard `JdbcTemplate` / `SimpleJdbcCall`

## Code-Level Risks
- `inquireCCAdminLayout()` calls `inquireReversalReasonSettings()` internally; if that returns an empty list, `revReasonsList.size()` loop is harmless, but a `null` return from `inquireReversalReasonSettings()` would throw a `NullPointerException` — the method returns `null` if `results` is null
- `inquireSectionsLayout()` makes three separate DB calls (screen flags, display defaults, payment reasons) with no transaction boundary; a concurrent programme-settings update could produce an inconsistent composite result
- `inquireScreenDriverFlags()` initialises `outerMap` with `new TreeMap()` outside the null check but processes results inside it; if `results` is null, an empty map is returned (benign, but callers receive no indication of a DB failure)
- All `saveXxx()` methods delegate directly to the DAO with no pre-validation; invalid `InstIssueCZScreenCfgOptions` inputs are passed straight to the stored procedure
