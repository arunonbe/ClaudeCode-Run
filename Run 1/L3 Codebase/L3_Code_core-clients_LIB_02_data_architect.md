# core-clients_LIB — Data Architect View

## Data Stores

This library is a **client-side stub only**. It does not own or directly access any database, file system, or message queue. All data stores it interacts with are remote XML-RPC services:

| Logical Store | Director Key (observed) | Java Interface |
|---|---|---|
| ECountCore Member DB | `Services\ECountCore.eMember` (inferred) | `MemberXMLRPCClient` → `ECountCore.eMember` |
| ECountCore Device/Card DB | `Services\ECountCore.eDevice` | `DeviceXMLRPCClient` → `ECountCore.eDevice` |
| ECountCore Transfer DB | `Services\ECountCore.eTransfer` (inferred) | `TransferXMLRPCClient` → `ECountCore.eTransfer` |
| ECountCore Event Rules | `Services\ECountCore.Event` (inferred) | `EcountcoreEventXMLRPCClient` → `ECountCore.Event` |
| CoreLite (fast payment) | `Services\ECountCore.coreLite` (inferred) | `CoreLiteXMLRPCClient` → `ECountCore.coreLite` |
| Profile Service | `ECountCore.Profile` interface | `ProfileXMLRPCClient` → `ECountCore.Profile` |
| Security Service | `SecurityService.SecurityManager` | `SecurityServiceXMLRPCClient` |
| Security Hierarchy | `SecurityService.HierarchyManager` | `SecurityHierarchyServiceXMLRPCClient` |
| Event Service | `EventService.Publish` | `EventXMLRPCClient` |
| Order Service | `OrderService.OrderManager` | `OrderXMLRPCClient` |
| StrongBox Repository | `StrongBox.RepositoryService` | `StrongBoxXMLRPCClient` |
| Director Config Store | `Http://ecappdev/service/dispatch.asp` (dev) | `DirectorXMLRPCClient` |

Director itself acts as a remote configuration registry, storing key-value trees under paths such as `System\DataCredentials\{agent}`, `System\Servers`, `System\DataEnvironment`, `System\DataSettings`, and `Services\{service-name}`.

## Schema & Tables

No DDL or ORM mapping exists within this repository. The data models that this library serialises over XML-RPC are represented as plain Java POJOs. Key data structures and their fields:

### Member / Registration
- `ExtendedRegistration` (from `ecountcore-common`) — name, email, addresses, phones
- `ExtendedUniversalRegistration` — superset of ExtendedRegistration with universal fields
- `SecureUserProfile` — sensitive profile attributes for a cardholder
- `InquiryBasic` / `InquiryDefault` / `InquiryExtended` input types — all keyed on `Member` UUID + `agent`

### Account / Device
- `AccountDefinition` / `AccountDefinitionECard` — `create_flag`, `default_flag`, `device_type`, `name`, `addenda`, `card` (StoredValueCard), `dda` (StoredValueAccount)
- `StoredValueCard` — `access_level` (e.g. `"virtual"`), `number` (PAN)
- `AccountSetupOptionsECard` — `is_rssr`, `batch_process`, `create_flag`, `default_flag`, `plastic_only`, `is_smots`, `delivery_location_code`, `xref_member`
- `AccountDetailLevel` — `definition` (integer)
- `AccountInquiryOptions` — nested definition with `detail_level`

### Transfer
- `TransferDefinition` — transfer specification
- `Transfer` — transfer handle (used in Commit/Cancel/Inquiry)
- `QuickLoadTransaction` — direct load, `TransactionStrategy[]`
- `BeginInput` fields: `agent`, `affiliate`, `member` (UUID), `transfer` (TransferDefinition), `transaction` (Vector), `batch_process`, `program`

### Profile
- `ProfileClassKey` — class name + optional qualifiers
- `ProfileClassTopic` — scope descriptor (`"global"` or `"member"`)
- `ClassPut` input: `agent`, `member`, `memo`, `topic`, `key`, `operation` (one of `"create"`, `"update"`, `"create-update"`), `values` (Map<String,Object>)

### Security / User Provisioning
- `BulkUserRecord` fields: `record_action`, `program_id`, `user_name`, `account_status`, `role_group` (Integer), `password_status`, `password` (String plaintext), `notification_code`, `registration` (UserRegistrationInfo), `locations` (List<Location>), `promotions` (List<Promotion>)
- `UserRegistrationInfo` fields: `first_name`, `middle_name`, `last_name`, `suffix_name`, `home_email`, `address1`, `address2`, `city`, `state`, `postal`, `country`, `home_phone`, `business_phone`, `mobile_phone`

### Order
- `CreateFileOrderInput` fields: `agent`, `facility`, `memberId`, `programId`, `fileId`, `fileName`
- `ForceOrderStatusInput`, `PostFileOrderInput`, `PostCompletedFileOrderInput`, `CancelOrderInput` — similar agent/order-reference patterns

### StrongBox
- `RepositoryServiceReadInput` fields: `reference` (lookup key), `agent`
- `RepositoryServiceReadOutput` — wraps a generic `data` Object

### Director
- `GetInput.key` (String, e.g. `"System\DataCredentials\B2CTEST"`)
- `GetOutput.value` (Map<String,Object>) — recursive key-value tree

## Sensitive Data Handling

| Sensitive Field | Location | Current Handling |
|---|---|---|
| Card PAN (`number`) | `StoredValueCard.number` via `AccountDefinition` | Passed as plain String in XML-RPC payload; logged in `DeviceXMLRPCClient.main()` line 304 |
| Password | `BulkUserRecord.password` (`securityServiceClient/.../BulkUserRecord.java` line 16) | Plain String, no masking |
| Password (Director credentials) | `System\DataCredentials\{agent}` Director tree | Retrieved as plain Map value; test asserts `assertEquals("b2ctest", datacredentials.get("Password"))` (`TestDirectorXMLRPCClient` line 64) |
| Full name, address, phones, email | `UserRegistrationInfo`, `ExtendedRegistration` | Passed as plain Strings in XML-RPC |
| `SecureUserProfile` | `UpdateSecureProfileInput` | Treated as opaque object; no field-level encryption at library layer |
| StrongBox secret reference | `RepositoryServiceReadInput.reference` | Reference key only; actual secret returned as `data Object` in output |
| Member UUID | All inputs with `Member` parameter | GUIDs used as PII identifiers; transmitted in all requests |

## Encryption & Protection

- **No TLS enforcement in library code** — `DirectorXMLRPCClient` uses Apache Commons HttpClient 3.x with plain `new HttpClient()`. No `SSLSocketFactory`, no certificate pinning, no `https://` validation is applied within this library. The test endpoint is `http://ecappdev/...` (plaintext HTTP).
- **No field-level encryption** — none of the DTO classes apply encryption, masking, or hashing to any field before serialisation.
- **No signing of payloads** — XML-RPC requests are sent as raw `StringRequestEntity` without HMAC or signature.
- **GitHub token via environment variable** — `.mvn/wrapper/settings.xml` uses `${env.GITHUB_TOKEN}` for the package registry password, which is the correct approach for CI secret injection.
- **Allowed CVEs** — `allowedlist.yaml` explicitly skips `CVE-2018-1000632` (dom4j) and `CVE-2020-10683` (dom4j/XML external entity) from container scan. Both relate to XML processing, which is the library's core concern.

## Data Flow

```
Caller (upstream service)
    |
    | constructs typed Input DTO (e.g. BeginInput, CreateDeviceInput)
    v
XMLRPCClient.invokeXMLRPCCall()
    |
    | uses XmlRPCFromObjectMapper.fromObject() to serialize DTO → XML-RPC XML string
    v
DirectorServiceLocator.getServiceAddress(agent)
    |
    | queries DirectorXMLRPCClient.getSerivceLocationURI() if cache is stale
    |   DirectorXMLRPCClient uses Apache Commons HttpClient POST to Director
    |   Director returns key-value map with InterfaceServer alias
    |   Second Director call resolves alias → URI under System\Servers
    v
XMLRPCClient (base): HTTP POST to resolved service URI
    |
    | XmlRPCToObjectMapper.toObject() deserializes XML-RPC response → Output DTO
    v
Caller receives typed Output DTO (e.g. BeginOutput, CreateDeviceOutput)
```

## Data Quality & Retention

- **No validation** — input DTOs have no `@NotNull`, `@Size`, or similar constraint annotations. There is no validate() method in any client class. Field validation is entirely delegated to the server-side services.
- **No retry logic** — `DirectorXMLRPCClient.get()` catches all exceptions and returns `null` silently (line 120-123); callers receive null Maps without knowing the root cause.
- **No data retention policy** — this is a client library; it holds no persistent state. In-flight data exists only in JVM memory for the duration of a call.
- **URI cache** — `DirectorServiceLocator.uriCache` is a `HashMap<String, URICacheEntry>` kept in JVM heap. It is not persisted across restarts. Cache entries are never evicted; they are only refreshed after `cacheTimeOutMs` elapses.
- **Raw type use** — `BeginInput.transaction` is a `Vector` (raw type, line 15 of `BeginInput.java`); `EventDispatchInput.topic` is a `Dictionary` (raw, line 10). These lose compile-time type safety.

## Compliance Gaps

| Gap | Regulation | Evidence |
|---|---|---|
| PAN logged in plain text | PCI DSS Req 3.3, 10.3 | `DeviceXMLRPCClient.main()` line 304 logs `card.getNumber()` |
| Password transmitted as plain String | PCI DSS Req 8.3, 8.6 | `BulkUserRecord.password` is a plain `String` |
| HTTP (not HTTPS) used in test/example configs | PCI DSS Req 4.2 (data in transit) | `DirectorXMLRPCClient`, `UsageExample`, `TestDirectorXMLRPCClient` all reference `http://` endpoints |
| Allowed XML CVEs (dom4j) skipped | PCI DSS Req 6.3.3 | `allowedlist.yaml` waives CVE-2018-1000632 and CVE-2020-10683 |
| No field-level encryption of PII | GDPR Art. 32, CCPA | `UserRegistrationInfo`, `ExtendedRegistration` carry PII as plain Strings |
| No input validation | OWASP, PCI DSS Req 6.2 | No constraints on any DTO field |
| Director credentials stored as plain text in config tree | PCI DSS Req 8 | `TestDirectorXMLRPCClient` demonstrates plaintext credential retrieval |
