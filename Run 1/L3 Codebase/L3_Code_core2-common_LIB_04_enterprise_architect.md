# core2-common_LIB — Enterprise Architect View

## Platform Generation (Gen-1/Gen-2/Gen-3)

**This library is a Gen-2 artifact.**

Evidence:
- Package root is `com.ecount.Core2` — "Core2" explicitly denotes the second-generation Ecount/Onbe prepaid platform.
- The Maven group ID `com.ecount.service.Core2` and artifact ID `common` are consistent with the Gen-2 service naming convention visible elsewhere in the Onbe portfolio.
- The parent POM `com.parents:prepaid-parent:6.0.12` is the Gen-2 shared parent.
- The library uses XML-RPC as its primary integration pattern (all DTO packages are named `dto.xmlrpc.*`), which is characteristic of Gen-2's legacy RPC-based inter-service communication style.
- Java 21 source/target is set, which represents a platform modernization of the Java runtime within Gen-2, but does not change the underlying architectural pattern.
- No Spring Boot auto-configuration, REST controllers, or message-queue integration is present — consistent with Gen-2's non-cloud-native style.

---

## Business Domain

**Prepaid Payments — Core Platform Services**

This library defines the canonical contract for four business domains within the Core2 prepaid platform:

| Domain | Interface | Description |
|---|---|---|
| Member Management | `IMemberService` | Cardholder identity, registration, PII vaulting |
| Payment Device Management | `IDeviceService` | Prepaid card, ACH, DDA, eCheck, credit card lifecycle |
| Check/PreCheck Instruments | `IManageService` | Physical/virtual check issuance, authorization, stop payment |
| Fund Transfer | `ITransfer` | Multi-leg money movement across devices |

The business domains map to Onbe's core B2C disbursement, incentive, and prepaid card product lines.

---

## Role in Platform

`core2-common_LIB` plays the role of a **shared interface and domain-model contract library**. It is the single source of truth for:

1. **Service contracts**: The four service interfaces (`IMemberService`, `IDeviceService`, `IManageService`, `ITransfer`) are the API surface that all Core2 service implementations must satisfy.
2. **Canonical domain objects**: Value classes (`Member`, `Account`, `StoredValueCard`, `SecureUserProfile`, `BasicRegistration`, `ExtendedRegistration`, etc.) are the shared language of the Core2 platform — all services and consumers speak this vocabulary.
3. **DTO shapes**: All `dto.xmlrpc.*` Input/Output classes define the wire format for inter-service XML-RPC calls.
4. **Error codes**: `enums/Exceptions.java` (class ID 14) and `exceptions/ECSDebitServiceExceptions.java` (class ID 34) are the canonical error taxonomy for Core2.
5. **Shared utilities**: `SQLMapper`, `MetaDataCache`, `UUIDConverter`, `LibraryUtils` are reusable infrastructure utilities for all Core2 service implementations.

Without this library, no Core2 service can compile. It is a hard build-time dependency for the entire Gen-2 platform.

---

## Dependencies (What Services Depend on This Common Library?)

This library has **no runtime dependencies itself** beyond `commons-beanutils`. It is consumed by other services. Based on the service interfaces defined, the following service types are expected consumers (inferred from the interface names, Javadoc agent identifiers like "B2CTEST", and DTO package names):

| Likely Consumer Service | Consumes Interface / DTO |
|---|---|
| `emember` service | `IMemberService`, `dto.xmlrpc.emember.*` |
| `edevice` service | `IDeviceService`, `dto.xmlrpc.edevice.*` |
| `eManage` service | `IManageService`, `dto.xmlrpc.eManage.*` |
| `eTransfer` service | `ITransfer`, `dto.xmlrpc.eTransfer.*` |
| Any Core2 data-access layer | `SQLMapper`, `MetaDataCache`, `UUIDConverter` |
| Any Core2 business service | `enums/*`, `exceptions/*`, `value/*` |

The relationship is strictly one-directional: consumers depend on this library; this library depends on nothing at the Core2 level.

---

## Integration Patterns

| Pattern | Mechanism | Evidence |
|---|---|---|
| XML-RPC | All DTO packages under `dto.xmlrpc.*` | Package naming convention throughout all Input/Output classes |
| Request/Response | Every service method takes an Input DTO and returns an Output DTO extending `OutputBase` | `IOutput` interface, `OutputBase.result: Result{code, message}` |
| Agent-scoped calls | All service methods carry an `agent` String parameter; Input DTOs extend `AgentAware` | `AgentAware.java`, `IAgentAware.java`; Javadoc "RPC Agent, example: B2CTEST" |
| Result codes | Numeric `Result.code` (0 = success) + `String message` | `Result.java`, `OutputBase.java` |
| Addenda extensibility | `Map<String,Object>` addenda on member, account, transaction | `AccountDefinition.addenda`, `TransactionDefinition.addenda`, `MemberAddenda` |
| JDBC ResultSet mapping | `SQLMapper` maps `ResultSet` columns to bean fields by reflection | `SQLMapper.java` uses Apache Commons BeanUtils |
| JMS messaging | Error codes reference JMS communication and message-receive errors | `ECSDebitServiceExceptions.ECSJMSCommunicationError` (34001), `ECSJMSMesgReceiveError` (34002) |
| External PII vault | `SecureUserProfile.id` is a reference to an external vault ("strong box") | `IMemberService` Javadoc, `SecureUserProfile.id` field |
| External debit processor (MLI) | ECS MLI (Multi-Link Interface) error codes | `ECSDebitServiceExceptions.InvalidECSMLIRequest` (34011), `ECSMLIResponseError` (34012) |

---

## Strategic Status

| Dimension | Assessment |
|---|---|
| Lifecycle status | Active Gen-2 platform library; currently maintained (Java 21 target set) |
| Version | `2.0.0` — stable, no SNAPSHOT indication |
| Security scanning | GitHub CodeQL enabled (weekly) |
| Dependency updates | Dependabot enabled (weekly Maven updates) |
| Test coverage | Zero — no unit tests exist |
| Tech debt level | High — deprecated API usage (`clazz.newInstance()`), no tests, XML-RPC coupling |
| Migration priority | High — this library is the first dependency that must be re-platformed for any Gen-3 migration |

The library is the **central migration blocker** for Gen-3: until a Gen-3-compatible contract library replaces or extends this one, no Gen-2 service can be independently migrated.

---

## Migration Blockers

The following items in this library create friction for a Gen-3 migration:

1. **XML-RPC DTO naming and structure**: All ~100+ DTO classes are named and structured for XML-RPC (`dto.xmlrpc.*`). A REST/gRPC/event-driven Gen-3 platform would require new DTO shapes, breaking all consumers simultaneously.

2. **Agent-scoped service interface pattern**: Every service method takes a positional `String agent` parameter. Gen-3 typically externalizes multi-tenancy into request context / JWT claims, not method parameters.

3. **Monolithic service interfaces**: `IMemberService` has 20+ methods; `IManageService` has 20+ methods; `IDeviceService` has 9+ methods. Gen-3 microservices should decompose these into bounded contexts. Decomposition requires coordinated changes across all consumers.

4. **`SQLMapper` with static column metadata cache**: Direct `ResultSet` → bean mapping using reflection couples Gen-2 services to a relational database schema. Gen-3 migration to a different persistence model (e.g., NoSQL, event store) would require replacing this utility.

5. **`SecureUserProfile` carries full PII in DTOs**: In Gen-3, PII should not travel in service DTOs — only vault tokens should. Current structure passes SSN, DOB, driver's license, etc. across service boundaries in plain objects. Migrating to a tokenized model requires changing the `IMemberService` contract and all consumers.

6. **`int` monetary amounts**: Gen-3 multi-currency support would require `BigDecimal` or a proper `Money` value object. Changing `Funds.amount` and all derived classes is a breaking change.

7. **`CreditCard` holds full PAN and CVV**: PCI DSS-compliant Gen-3 architecture should never carry full PAN or CVV through application-layer DTOs. Replacing this with a tokenized reference requires reworking the entire `IDeviceService` and `IManageService` surface.

8. **Parent POM coupling**: `com.parents:prepaid-parent:6.0.12` governs all dependency versions. Migrating to a Gen-3 bill-of-materials (BOM) style would require changing the parent reference and auditing all transitive version changes.

9. **No Semantic Versioning enforcement**: The library is at version `2.0.0`. Any breaking interface change (adding a method to an interface without a default implementation) will silently break all consumers until they recompile. A Gen-3 migration plan needs a clear versioning and compatibility strategy.
