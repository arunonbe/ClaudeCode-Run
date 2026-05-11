# core2-common_LIB — Solution Architect View

## Technical Architecture

### Library Structure

```
com.ecount.Core2
├── dto/xmlrpc/
│   ├── eManage/
│   │   ├── input/   (23 input DTOs)
│   │   └── output/  (23 output DTOs)
│   ├── eTransfer/
│   │   ├── input/   (5 input DTOs)
│   │   └── output/  (5 output DTOs)
│   ├── edevice/
│   │   └── output/  (10 output DTOs — no input package)
│   └── emember/
│       ├── input/   (17 input DTOs)
│       └── output/  (17 output DTOs)
├── enums/
│   (ActivationCodes, BlockCodes, CountryCodes, CreditCardTypes, DeviceTypes, Exceptions, InternalCards, PinSelectionCodes)
├── exceptions/
│   (BusinessObjectNotValidException, CoreException, ECSDebitServiceExceptions, ServiceEnums, ServiceException)
├── service/
│   (IDeviceService, IManageService, IMemberService, ITransfer)
├── utils/
│   (LibraryUtils, MetaDataCache, SQLMapper, UUIDConverter)
├── value/
│   (~70 domain value objects)
└── xmlrpc/common/
    (AgentAware, IAgentAware, IOutput, OutputBase, Result)
```

**Total Java files**: ~200 (counted from PowerShell directory listing)
**Packages**: 12 distinct packages
**External runtime dependencies**: 1 (`commons-beanutils`)
**Test classes**: 0

### Design Pattern: Interface-DTO-Value Separation

The library implements a clean three-layer contract:
1. **Service interfaces** (`service/` package) — define business operations.
2. **DTOs** (`dto/xmlrpc/` packages) — define the wire format for each operation.
3. **Value objects** (`value/` package) — define the shared domain model used by both DTOs and service interfaces.

Input DTOs extend `AgentAware` (carries `agent` String). Output DTOs extend `OutputBase` (carries `Result{code:int, message:String}`). This ensures every call is agent-scoped and every response is result-coded.

### Inheritance Hierarchy (Key Lines)

```
Account
└── AccountDefinition (adds block_code, device_type, addenda, is_default, is_protected)
    ├── AccountDefinitionECard (adds StoredValueCard, StoredValueAccount, BankAccount)
    │   └── FDRCardAccountDetail (adds billing ExtendedRegistration)
    ├── AccountDefinitionDDA (adds StoredValueAccount, BankAccount x2)
    ├── AccountDefinitionACH (adds BankAccount, verification_code/amount)
    ├── AccountDefinitionCreditCard (adds CreditCard, billing ExtendedRegistration, Session)
    ├── AccountDefinitionECheck (adds Member issuer/recipient, dates, amount)
    ├── AccountDefinitionOperator (no additional fields observed)
    └── CoreDeviceSummary (extends AccountDefinition, currently all fields commented out)
        └── CoreDeviceProtected (adds reference_id)

UserRegistration
└── BasicRegistration (adds name fields, email variants)
    └── ExtendedRegistration (adds address, phone variants)

PreCheck
└── PreCheckDefinition (adds all check lifecycle fields)

Transfer
└── TransferDefinition (adds state, converged, risk, activity)

Transaction
└── TransactionDefinition (adds account, funds, addenda, taxable)

CreditCard
└── StoredValueCard (adds activation/block/pin codes, emboss date, card_id, is_ciu)
```

---

## API Surface

### Service Interfaces (contract methods)

**`IMemberService`** (17 methods):
```
AddBasic(agent, affiliate, BasicRegistration, addenda) → AddBasicOutput
AddExtended(agent, affiliate, ExtendedRegistration, addenda, SecureUserProfile) → AddExtendedOutput
AddUniversalRegistration(agent, affiliate, ExtendedUniversalRegistration, addenda, SecureUserProfile) → AddUniversalRegistrationOutput
UpdateBasic(agent, Member, BasicRegistration) → UpdateBasicOutput
UpdateExtended(agent, Member, ExtendedRegistration) → UpdateExtendedOutput
UpdateAddenda(agent, Member, addenda) → UpdateAddendaOutput
UpdateUniversalRegistration(agent, Member, ExtendedUniversalRegistration) → UpdateUniversalRegistrationOutput
UpdateSecureProfile(agent, Member, SecureUserProfile) → UpdateSecureProfileOutput
InquiryBasic(agent, Member) → InquiryBasicOutput
InquiryExtended(agent, Member) → InquiryExtendedOutput
InquirySecureProfile(agent, Member) → InquirySecureProfileOutput
InquiryDefaultDevice(agent, Member, device_type) → InquiryDefaultDeviceOutput
EvaluateFeatureSet(agent, Member) → EvaluateFeatureSetOutput
GroupMemberAdd(agent, owner, group, role, member) → GroupMemberAddOutput
GroupMemberRoleUpdate(agent, owner, group, role, member) → GroupMemberRoleUpdateOutput
GroupMemberRemove(agent, owner, group, member) → GroupMemberRemoveOutput
GroupMemberInquiry(agent, owner, group) → GroupMemberInquiryOutput
GroupMemberSearch(agent, group, role, member) → GroupMemberSearchOutput
BasicMemberSearch(agent, BasicRegistration, addenda) → BasicMemberSearchOutput
PUIDMemberSearch(agent, partner_id, affiliate_id, program_id, lookup_partner_user_id, lookup_emember_id) → PUIDMemberSearchOutput
```

**`IDeviceService`** (9 methods):
```
Create(agent, Member, AccountDefinition, AccountSetupOptions, batch_process) → CreateOutput
Inquiry(agent, Account, AccountDetailLevel, AccountInquiryOptions) → InquiryOutput
Update(agent, AccountDefinition) → UpdateOutput
Control(agent, Account, method, Map<String,Object> options) → ControlOutput
CatalogInquiry(agent, Member, device_type, detail_level) → CatalogInquiryOutput
GroupCatalogInquiry(agent, Member, group, device_type, detail_level) → GroupCatalogInquiryOutput
ExtendedAddendaInquiry(agent, ExtendedAddendaReference) → ExtendedAddendaInquiryOutput
DDAInquiry(agent, id) → DDAInquiryOutput
getDefaultDevice(agent, Member, deviceType) → DefaultDeviceOutput
updateSecureProfile(agent, Member, SecureUserProfile) → UpdateSecureProfileOutput
```

**`IManageService`** (20 methods — check and PreCheck operations):
Key methods include `CheckOrderRequest`, `CheckStopPaymentRequest`, `CheckDDAAvailableAuthInquiry`, `CheckProgramAccountInquiry`, `PreCheckOrderRequest`, `PreCheckAssign`, `PreCheckAuthorize`, `PreCheckMerchantVerify`, `PreCheckCatalogInquiry`, `PreCheckActivityJournalInquiry`.

**`ITransfer`** (5 methods):
```
Begin(agentname, BeginInput) → BeginOutput
Commit(agentname, CommitInput) → CommitOutput
Cancel(agentname, CancelInput) → CancelOutput
SimpleFeeInquiry(agentname, SimpleFeeInquiryInput) → SimpleFeeInquiryOutput
Inquiry(agentname, InquiryInput) → InquiryOutput
```

### Utility API Surface

**`SQLMapper`** (public static methods):
- `mapObject(ResultSet, Class)` — maps ResultSet to new bean instance.
- `mapObject(ResultSet, Object)` — populates existing bean from ResultSet.
- `mapObject(ResultSet, List<String>, Class)` — field-list-filtered mapping.
- `mapObject(ResultSet, Map<String,String>, Class)` — custom column-to-field mapping.
- `mapObjectCachingMetaData(ResultSet, Class)` — cached column metadata version.
- `mapObjectCachingMetaData(ResultSet, Class, String cacheKey)` — explicit cache key version.
- `buildMetaDataList(ResultSet)` — extract column names from ResultSet metadata.
- `mapProperty(Object, String, Object, List<String>)` — set individual bean property.
- `createObject(Class)` — instantiate bean with all nested non-primitive fields initialized.

---

## Security Posture

### Strengths
- **CodeQL scanning** is active (weekly, GitHub Actions). SAST coverage mitigates common CWE patterns.
- **`banTransitiveDependencies`** enforcer rule reduces uncontrolled dependency surface.
- **Dependabot** is configured for weekly Maven updates, reducing known-CVE exposure window.
- **Minimal runtime dependency surface**: Only `commons-beanutils` is a runtime dependency.

### Weaknesses and Security Risks

1. **Full PAN in `CreditCard.number`** (`value/CreditCard.java` line 39): Stored as a plain `String`. Any serialization of a `CreditCard` object (to logs, to JMS messages, to XML-RPC payloads) will expose the full PAN. PCI DSS Requirement 3.4 requires PANs to be rendered unreadable wherever stored.

2. **CVV in `CreditCard.cv_code`** (`value/CreditCard.java` line 29): Stored as a plain `String`. PCI DSS Requirement 3.3 prohibits storing SAD (including security codes) after authorization. The library provides no mechanism to enforce deletion.

3. **SSN in `SecureUserProfile.federal_id`** (`value/SecureUserProfile.java` line 19): Plain `String` field. The `validate()` method strips formatting but does not mask or encrypt the value. GLBA and state privacy laws require SSNs to be protected.

4. **`String.intern()` as synchronization monitor** (`MetaDataCache.java` line 25): `synchronized(metaDataKey.intern())` uses the JVM intern pool as a lock. If cache keys are long or numerous, the intern pool grows indefinitely (permanent generation / metaspace leak). An attacker controlling cache key values could cause resource exhaustion.

5. **`clazz.newInstance()` deprecated** (`SQLMapper.java` line 405): Deprecated since Java 9. In Java 21, this method still works but suppresses checked exceptions and bypasses access control in a way that `getDeclaredConstructor().newInstance()` would not. It is a code quality and future compatibility risk.

6. **No input sanitization on `agent` parameter**: The `agent` string is passed to all service calls and used in error messages and log output (by implementing services). If it originates from untrusted input, it could contribute to log injection.

7. **`ServiceException.initializeMessageDictionary`** (`exceptions/ServiceException.java` lines 133–153): Static initializer references `sMessageDictionary` before it is initialized (the static block at the bottom of the file sets `sMessageDictionary = ServiceException.initializeMessageDictionary(...)`, but `initializeMessageDictionary` at line 138 calls `sMessageDictionary.put(...)` — this will throw a `NullPointerException` at class initialization if any message entries are passed). The current call passes an empty array, so no NPE occurs today; but adding entries to the array would silently break all `ServiceException` subclass initialization.

8. **`equals()` on `SecureUserProfile` has a bug** (`SecureUserProfile.java` line 98): `} else if (s2 != null && s2 != null) {` — the condition checks `s2 != null` twice instead of `s1 != null && s2 != null`. This means if `s1 == null` and `s2 != null`, the method returns `false` (correct by accident), but if `s1 != null` and `s2 == null`, it also proceeds to `s1.equals(s2)` which throws a `NullPointerException` (because the check is `s2 != null` not `s1 != null`). This is a logic bug that can cause NPE when comparing profiles where one has a non-null field and the other has null.

---

## Technical Debt

| Item | Location | Severity | Description |
|---|---|---|---|
| Zero test coverage | Entire repository | Critical | No unit tests. Zero confidence in correctness of validation logic, SQLMapper, or equals/hashCode implementations. |
| `clazz.newInstance()` deprecated | `SQLMapper.java` line 405 | High | Deprecated since Java 9; should use `getDeclaredConstructor().newInstance()` |
| `String.intern()` as lock | `MetaDataCache.java` line 25 | High | Potential memory leak and denial of service |
| `ServiceException` static initializer bug | `ServiceException.java` lines 133–153 | High | NPE if non-empty message array is ever passed; currently masked by empty array |
| `SecureUserProfile.equals()` NPE bug | `SecureUserProfile.java` line 98 | High | `s2 != null && s2 != null` should be `s1 != null && s2 != null`; causes NPE when one profile has non-null field and the other has null |
| Commented-out `validate()` methods | Multiple (`AccountDefinitionACH`, `AccountDefinitionDDA`, `AccountDefinitionECheck`, `AccountDefinitionCreditCard`, `BankAccount`, `CoreDeviceSummary`) | Medium | Validation code commented out across multiple classes, leaving silently un-validated inputs |
| Commented-out fields in `CoreDeviceSummary` | `CoreDeviceSummary.java` | Medium | `created`, `updated`, `owner_id` fields entirely commented out — may be needed |
| `int` for monetary amounts | `Funds`, `AccountBalance`, `CoreTransactionJournal`, all Amount fields | Medium | No overflow protection; max ~$21.4M. Multi-currency not representable |
| Public instance variables on `SecureUserProfile` | `SecureUserProfile.java` lines 17–27 | Medium | PII fields declared `public` — bypasses encapsulation; any code can set `federal_id` without triggering validate() |
| Hard-coded agent reference `"B2CTEST"` in Javadoc | `IMemberService.java` | Low | Test agent identifier leaked into production Javadoc |
| `LibraryUtils.breakUSPhone()` ignores `phone.indexOf('X')` result | `LibraryUtils.java` lines 118–122 | Low | `phone.indexOf('X')` result is discarded; uppercase 'X' extension separator not handled |
| `TODO` in `IMemberService` Javadoc | `IMemberService.java` line 197 | Low | `TODO are addenda values used in BasicMemberSearch ???` — unresolved design question in production code |

---

## Gen-3 Migration Requirements

To migrate this library's contracts to a Gen-3 platform, the following changes are required:

### Must Do (Breaking Changes)
1. **Replace XML-RPC DTOs with REST/gRPC/event contracts**: Rename and restructure all 100+ `dto.xmlrpc.*` classes. Define OpenAPI or Protobuf schemas as the new contract language.
2. **Remove PAN and CVV from DTOs**: Replace `CreditCard.number` and `cv_code` with a tokenized card reference. Integrate with a PCI-compliant tokenization vault.
3. **Remove SSN and PII from service method signatures**: `AddExtended`, `UpdateSecureProfile`, `InquirySecureProfile` must accept/return vault tokens, not `SecureUserProfile` objects with live PII.
4. **Replace `int` amounts with `BigDecimal` or a `Money` type**: Required for multi-currency support and overflow safety.
5. **Extract `agent` from method signatures**: Move to request context / JWT claims / Spring Security context.
6. **Decompose large service interfaces**: Split `IMemberService` (20 methods) and `IManageService` (20 methods) into bounded-context microservice contracts.

### Should Do (Quality / Maintainability)
7. **Add unit tests**: Minimum 80% branch coverage on validation logic (`CreditCard.validate()`, `SecureUserProfile.validate()`, `SQLMapper`, `LibraryUtils`).
8. **Fix `ServiceException.initializeMessageDictionary()`**: Rewrite static initializer to be null-safe.
9. **Fix `SecureUserProfile.equals()` NPE bug**: Change `s2 != null && s2 != null` to `s1 != null && s2 != null`.
10. **Replace `clazz.newInstance()`** with `clazz.getDeclaredConstructor().newInstance()`.
11. **Replace `String.intern()` lock** in `MetaDataCache` with a `ConcurrentHashMap`-based pattern.
12. **Make `SecureUserProfile` PII fields private**: Enforce encapsulation; validate in setters.

### Could Do (Gen-3 Alignment)
13. **Introduce `@Sensitive` or equivalent annotation** on PAN, CVV, SSN, DOB fields for framework-level redaction in logs and serialization.
14. **Replace `Map<String,Object>` addenda** with typed addenda classes or a schema-validated `JsonNode` / Protobuf `Any`.
15. **Move `SQLMapper`** to a separate data-access utility library — it is not a domain contract and should not be in the common contract library.
16. **Adopt semantic versioning with a compatibility policy**: Provide default methods on interfaces or use a separate `v2.*` package namespace for breaking changes.

---

## Code-Level Risks

| Risk | Class/Method | Line | Impact |
|---|---|---|---|
| NPE in `SecureUserProfile.equals()` | `SecureUserProfile.java` | 98 | Crashes during member deduplication if one profile has null field and other does not |
| NPE in `ServiceException` static init | `ServiceException.java` | 138 | Crashes JVM class initialization if any message entries are added |
| `clazz.newInstance()` suppresses checked exceptions | `SQLMapper.java` | 405 | Silent failures during bean instantiation; exception swallowed by broad catch |
| `String.intern()` memory leak | `MetaDataCache.java` | 25 | Unbounded growth of JVM intern pool under load with diverse class names |
| Full PAN traverses service boundary | `CreditCard.java`, `BeginInput.java` (via AccountDefinition) | — | PCI DSS scope expansion; any service touching these objects enters the CDE |
| Commented-out validation | `AccountDefinitionACH`, `AccountDefinitionDDA`, `BankAccount`, etc. | multiple | Routing numbers, account numbers, and verification codes not validated |
| `LibraryUtils.addUSPhoneToPhonesArray` does not copy arrays defensively | `LibraryUtils.java` | 52–79 | Original array reference not modified; caller must use returned array — documentation does not emphasize this |
| Monetary overflow | `CoreTransactionJournal.amount` (int), `Funds.amount` (int) | multiple | Integer overflow for amounts > $21.4M |
