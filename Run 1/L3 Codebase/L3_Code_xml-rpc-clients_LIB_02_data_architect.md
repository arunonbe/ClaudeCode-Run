# Data Architect View — xml-rpc-clients_LIB

## Data Models

xml-rpc-clients_LIB has no persistent data store. Its data models are XML-RPC request/response DTOs (input/output classes) and value objects shared across all sub-modules.

**Director DTO**:
- `GetInput` — wraps a Director key string for lookup
- `GetOutput` — map of key-value pairs returned by Director

**Member DTOs** (`com.ecount.client.member.xmlrpc.input/output`):
- `AddBasicInfoInput` — new member basic registration (name, email, affiliate)
- `AddExtendedInput` — extended registration (`ExtendedRegistration`, `SecureUserProfile`, addenda map)
- `AddUniversalRegistrationInput` — universal registration combining extended + secure profile + addenda
- `UpdateExtendedInput`, `UpdateUniversalRegistrationInput`, `UpdateAddendaInput` — member record update operations
- `InquiryBasic`, `InquiryDefault`, `InquiryExtended`, `InquirySecureProfileInput` — member inquiry variants; all keyed by `Member` value object (contains member identifier fields)
- `PuidMemberSearchInput` — lookup by `program_id`, `affiliate_id`, `partner_id`, `lookup_partner_user_id`
- `UpdateSecureProfileInput` — updates `SecureUserProfile` (authentication credentials)
- Output classes: `AddBasicInfoOutput`, `AddExtendedOutput`, `EMemberOutput`, `InquiryDefaultOutput`, `InquiryExtendedOutput`, `InquirySecureProfileOutput`, `PuidMemberSearchOutput`, `UpdateSecureProfileOutput` — each extends a `Result` base with success/failure code

**Transfer DTOs** (`com.ecount.client.transfer.xmlrpc.input/output`):
- `BeginInput` — transfer initiation: `agent`, `affiliate`, `Member`, `TransferDefinition`, `Vector` of `TransactionDefinition`, `batch_process` flag, `program`
- `CommitInput` — completes a transfer: `agent`, `Transfer` (contains transfer reference)
- `CancelInput` — cancels a transfer: `agent`, `Transfer`
- `QuickLoadInput` — single-step load: `agent`, `QuickLoadTransaction`, optional `TransactionStrategy[]`
- `InquiryInput` — transfer status lookup: `agent`, `Transfer`, `detail_level`

**Device DTOs**: `CreateDeviceInput`, `DeviceInquiryInput`, `GroupCatalogInquiryInput`, `DeviceUpdateInput`, `ControlInput` — card device lifecycle

**Event DTOs**: `RuleCreateInput`/`RuleCreateOutput` (eCountCore), `EventDispatchInput`/`EventDispatchOutput` with `EventAction` enum (Event Service)

**Order DTOs**: `CreateFileOrderInput`, `PostFileOrderInput`, `PostCompletedFileOrderInput`, `CancelOrderInput`, `ForceOrderStatusInput` — order lifecycle; outputs are status wrappers

**Profile DTOs**: `ClassCreate`, `ClassGet`, `ClassPut`, `ClassUpdate`, `ClassDelete`, `ClassDrop`, `ClassRetrieve`, `ClassSelect` (attribute-level); `ScopeCreate`, `ScopeRetrieve`, `ScopeUpdate`, `ScopeDelete` (scope-level); `ProfileOutput`, `ProfileMapOutput`, `ProfileScopeOutput`

**Core value objects** (from `ecountcore:common`):
- `Member` — cardholder identity object (member ID, PUID, or lookup keys)
- `SecureUserProfile` — authentication credentials (PIN, password hash, security questions)
- `ExtendedRegistration`, `ExtendedUniversalRegistration` — name, address, email, phone number aggregates
- `Transfer`, `TransferDefinition`, `TransactionDefinition`, `TransactionStrategy` — financial transfer value objects
- `QuickLoadTransaction` — single-step load value object

## Sensitive Data Handled

| Data Category | Presence | Risk |
|---|---|---|
| `SecureUserProfile` (PIN, password hashes) | `UpdateSecureProfileInput`, `AddExtendedInput` | Authentication credentials; must never be logged |
| Member name, email, phone, address | `ExtendedRegistration` in AddExtended/UpdateExtended | Cardholder PII subject to GLBA, CCPA, GDPR |
| `lookup_partner_user_id` | `PuidMemberSearchInput`, logged in MemberXMLRPCClient | May be PII depending on implementation |
| Program/affiliate IDs | All inputs | Business identifiers; low sensitivity |
| Transfer amounts | `TransferDefinition`, `QuickLoadTransaction` | Financial data; sensitive |
| Device (card) identifiers | Device DTOs | May include partial card identifiers |

**Critical PII logging finding**: `MemberXMLRPCClient.puidMemberSearch()` logs `lookupPartnerUserID` at INFO level in a concatenated string. If `lookupPartnerUserID` maps to a cardholder's email address, SSN fragment, or other PII field (implementation-dependent), this constitutes a PII-in-logs violation under GLBA, CCPA, and PCI DSS Requirement 3.3 (masking of PAN display). This log statement must be reviewed and sanitized.

## Encryption and Protection Status

- **Transport encryption**: XML-RPC messages are transmitted over HTTP using Apache Commons HttpClient 3.x. Whether TLS (HTTPS) is enforced depends entirely on the Director-resolved service endpoint URLs. If Director returns HTTP (not HTTPS) endpoint URLs, all cardholder data and security credentials traverse the network unencrypted. This must be verified against the Director configuration for all environments
- **No application-level payload encryption**: Request and response bodies are plain XML; no field-level encryption is applied by this library to sensitive fields within the XML payload
- **`SecureUserProfile` in transit**: PIN hashes and authentication credentials travel in XML-RPC request bodies; HTTPS is the only protection. If HTTP is used, this is a direct PCI DSS Requirement 4.2.1 violation

## Database Schemas

None — this library has no database. It is a pure client stub library that serializes Java objects to XML-RPC format and deserializes responses.

## Data Flows

```
Consumer application (OnePlatform, CSA, BatchJob)
  → DirectorXMLRPCClient.getAgentSetting(serviceKey, agent)
    → Director service (HTTP/HTTPS) → returns service endpoint URL
  → [Member|Transfer|Device|Profile|Event|Order]XMLRPCClient
    → XML-RPC serialization (XmlRPCFromObjectMapper)
      → Apache Commons HttpClient (HTTP POST to eCountCore)
        → eCountCore service (XML-RPC server)
          → SQL Server (ecountcore database)
        ← XML-RPC response (XmlRPCToObjectMapper)
      ← Deserialized output DTO
    ← Business result to consumer
```

**Sensitive data flow risk**: `SecureUserProfile` (PIN/password data) flows from consumer application → XML-RPC serialization → HTTP POST → eCountCore. If the endpoint URL returned by Director is HTTP rather than HTTPS, credentials travel in cleartext over the network — a critical PCI DSS violation.

## Retention Concerns

- No data is stored by this library; all data is transient in the call stack
- The `Testing.java` and `ClientTest1.java` files in `orderXMLRPCClient` appear to be test harness code checked into `src/main/java` (not test scope) — these must be reviewed to ensure they do not contain hardcoded test credentials, real endpoint URLs, or cardholder test data committed to source control

## PCI DSS Data Storage Compliance

- Library stores no data; PCI DSS storage requirements do not apply directly
- **PCI DSS Requirement 4.2.1** (strong cryptography for data in transit): Compliance depends on Director resolving HTTPS endpoint URLs; must be verified per environment (dev, QA, prod)
- **PCI DSS Requirement 3.3** (mask PAN on display): The PII logging in `puidMemberSearch()` must be audited; no PAN or sensitive authentication data should appear in logs
- **PCI DSS Requirement 6.2.4** (prevent common vulnerabilities): Apache Commons HttpClient 3.x is EOL with known CVEs; upgrading to a supported HTTP client library is required
