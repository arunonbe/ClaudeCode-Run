# core-clients_LIB — Business Analyst View


## Business Purpose

`core-clients_LIB` is a shared Java client library that enables consuming applications to communicate with Onbe's Gen-1/Gen-2 back-end services over XML-RPC. It does **not** contain business logic itself; instead it provides type-safe, agent-aware proxy objects that marshal Java POJOs into XML-RPC payloads and unmarshal responses back. Every downstream service that needs to interact with ECountCore, the Profile service, the Security service, the Order service, the Event service, or the StrongBox secret store depends on one or more JARs from this library.

The library is published as a multi-module Maven artifact (`groupId: com.citi.prepaid.service.core.client`, `artifactId: client`, current version `2.0.3-SNAPSHOT`) to Onbe's private GitHub Maven Packages registry.

## Business Capabilities

| Module | Business Capability |
|---|---|
| `director-client` | Runtime service-location lookup ("Director") — resolves agent-specific URLs for all other services |
| `ecount-core-client` | Member lifecycle (create, update, inquiry); device/card lifecycle (create, inquiry, update, control); value transfer (begin, commit, cancel, QuickLoad); fast payment; event rule creation |
| `profile-client` | Program/member configuration store — create, read, update, delete profile classes and scopes |
| `securityServiceClient` | User provisioning via bulk records; hierarchy node management for access control |
| `eventServiceClient` | Event publishing (EventDispatch) to the Event Service |
| `orderXMLRPCClient` | File-order management — create, post, force-status, cancel orders |
| `strongBoxClient` | Read secrets/credentials from the StrongBox repository by reference key |

## Business Entities

- **Member** (`com.ecount.core.value.Member`) — identified by a UUID (e.g. `{1846cd84-7f5c-11d8-9c7d-009027d30cbb}`). Central identity token carried on almost every service call.
- **Agent** (String, e.g. `B2CTEST`, `B2CSTAGE`, `PPTEST`) — programme environment discriminator used by Director to route settings and service URLs.
- **Affiliate / Program ID** (String, e.g. `10050001`, `04018324`) — identifies the client programme / brand.
- **Account / Device** (`com.ecount.core.value.Account`, `AccountDefinition`, `AccountDefinitionECard`) — represents a prepaid card, eCard, eCheck, or other stored-value device.
- **Transfer** (`com.ecount.core.value.Transfer`, `TransferDefinition`) — a monetary movement between accounts.
- **QuickLoadTransaction** (`com.ecount.core.value.QuickLoadTransaction`) — a direct card-load transaction with optional `TransactionStrategy`.
- **SecureUserProfile** (`com.ecount.core.value.SecureUserProfile`) — a cardholder's secure identity attributes (PII sub-object managed separately from the main member record).
- **ExtendedRegistration / ExtendedUniversalRegistration** — name, addresses, phone numbers, email for a member.
- **ProfileClass / ProfileScope** — key-value configuration nodes stored in the Profile service, scoped to a programme or member.
- **OrderRef / FileOrder** — a bulk-card fulfilment or plastics order, referencing `fileId`, `memberId`, `programId`, `facility`.
- **BulkUserRecord** (`com.ecount.client.security.xmlrpc.input.BulkUserRecord`) — a full user provisioning record carrying username, password, role group, registration info, locations, promotions.
- **EventRuleDefinition** (`com.ecount.core.value.EventRuleDefinition`) — trigger-action rule for card event notifications.

## Business Rules & Validations

1. **Agent resolution** — every client call resolves its effective agent via the pattern `(null != agent && !EMPTY_STR.equals(agent)) ? agent : this.agent` (e.g. `MemberXMLRPCClient` line 84, `TransferXMLRPCClient` line 66). The instance-level default agent is used only when the caller passes null or empty string.
2. **Director-based service location** — client modules must not hard-code service URLs. All endpoints are looked up at runtime from Director via `DirectorServiceLocator`, with an in-memory URI cache that respects a configurable timeout (`cacheTimeOutMs`). If Director is down and a cached URI exists, the cached value is used with a warning rather than failing the call (`DirectorServiceLocator` lines 97-101).
3. **Dependency-on-director** — all service clients (`ProfileXMLRPCClient`, `DeviceXMLRPCClient`, `MemberXMLRPCClient`, etc.) accept a `XMLRPCServiceLocator` at construction, making Director the single source of truth for service topology.
4. **Default-result convention** — every client initialises a failure output `new Result(-1, "Failure during initializaiton")` before the RPC call to ensure callers receive a typed (non-null) error object on failure.
5. **EventDispatch stub** — `EventXMLRPCClient.eventDispatch()` has the actual `invokeXMLRPCCall` commented out and only generates a UUID transaction ID (line 50-51). The event is silently dropped. This is an intentional placeholder or unfinished feature.
6. **No SNAPSHOT dependencies in release builds** — the `maven-enforcer-plugin` rule `requireReleaseDeps` is applied in every module, excluding only internal `com.citi.prepaid.service.core` and `com.citi.prepaid.service.core.client` artefacts.
7. **Password transmitted in clear text in `BulkUserRecord`** — `BulkUserRecord.password` is a plain-text String (`securityServiceClient/.../BulkUserRecord.java` line 16). No masking or hashing is applied within this library.

## Business Flows

### Member Registration
1. Caller constructs `ExtendedRegistration` + optional `SecureUserProfile` + `addenda` map.
2. `MemberXMLRPCClient.addBasic()` or `addExtended()` or `addUniversalRegistration()` is invoked, passing `agent` + `affiliate`.
3. Library serialises input to XML-RPC and posts it to the ECountCore.eMember endpoint resolved via Director.
4. `AddBasicInfoOutput` / `AddExtendedOutput` / `AddUniversalRegistrationOutput` is returned.

### Card Device Create and Inquiry (combined)
1. Caller populates `AccountDefinitionECard`, `AccountSetupOptionsECard`, `AccountDetailLevel`, `AccountInquiryOptions`.
2. `DeviceXMLRPCClient.createandInquiry()` posts to `ECountCore.eDevice` → `CreateandInquiry`.
3. `CreateInquiryOutput` returns card details including card number (`output.getDefinition().getCard().getNumber()`).

### Value Transfer
1. `TransferXMLRPCClient.Begin()` initiates, returns a `Transfer` handle.
2. `TransferXMLRPCClient.Commit()` finalises.
3. `TransferXMLRPCClient.Cancel()` reverses.
4. `QuickLoad()` provides a single-step load with optional `TransactionStrategy[]`.

### Order Fulfilment
1. `OrderXMLRPCClient.CreateFileOrder()` creates a file-based card order.
2. `PostFileOrder()` submits it for processing.
3. `PostCompletedFileOrder()` marks it complete.
4. `CancelOrder()` / `ForceOrderStatus()` for exception handling.

### User Provisioning
1. Caller builds a `BulkUserRecord` with username, password, role, registration, locations.
2. `SecurityServiceXMLRPCClient.setUserManagementRequest()` wraps it in `UserManagementRequestInput` and invokes `SecurityService.SecurityManager.SetUserManagementRequest`.

## Compliance & Regulatory Concerns

- **PII in transit** — `UserRegistrationInfo` carries full name, addresses, phone numbers, email. `ExtendedRegistration` / `SecureUserProfile` likewise carry cardholder PII. All transported over XML-RPC HTTP calls. No evidence of TLS enforcement within this library; transport security must be enforced at the infrastructure layer.
- **Password in plain text** — `BulkUserRecord.password` is a plain String. Under PCI DSS Requirement 8 (authentication data), passwords must not be transmitted or stored in plaintext. The library transmits this over XML-RPC without masking.
- **Account numbers** — `DeviceXMLRPCClient.main()` (line 304) logs `output.getDefinition().getCard().getNumber()` which is the card number (PAN). Logging PANs violates PCI DSS Requirement 3.3. This is in a `main()` test stub, but the pattern is risky.
- **GDPR / CCPA** — Names, addresses, emails, and phone numbers are included in request DTOs with no explicit data minimisation or redaction controls at the library level.
- **NACHA / Reg E** — `TransferXMLRPCClient` and `QuickLoadInput` operate on stored-value transfers; the underlying ECountCore service is expected to enforce Reg E error resolution, but the library provides no indication that dispute flags are surfaced.

## Business Risks

1. **EventDispatch is a dead stub** — `EventXMLRPCClient.eventDispatch()` silently suppresses events; consuming services that believe events are being published are not. Risk: broken notification workflows, potential compliance gap in audit trails.
2. **Director is a single point of failure** — all service URL resolution flows through a single Director call. If Director is unavailable and the in-memory cache is cold, all service calls fail.
3. **Module stability split** — README documents that `eventServiceClient`, `orderXMLRPCClient`, `securityServiceClient`, and `strongBoxClient` were excluded from the `2.0.0-beta` release. Their quality and compatibility with the 2.x XML-RPC transport has not been validated to the same degree as the beta modules.
4. **Snapshot version in production** — the parent POM declares `2.0.3-SNAPSHOT`; snapshot artefacts are mutable and their composition can change between builds, creating reproducibility risk.
5. **Hardcoded internal hostnames in test/example code** — `UsageExample.java` references `http://ecappdev/service/dispatch.asp`; `TestDirectorXMLRPCClient` references `http://ppamwdcddcor1/service/dispatch.asp`; `DeviceXMLRPCClient.main()` references `http://localhost:9001/service/dispatch.asp`. If these leak into deployable artefacts or CI pipelines, they expose internal hostnames.
