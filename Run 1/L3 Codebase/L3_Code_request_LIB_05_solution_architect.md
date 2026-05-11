# Solution Architect Analysis: request_LIB

## Technical Architecture
- **Language**: Java 21
- **Frameworks**: Spring (XML config, JMS), JDBC (stored procedures via Spring JdbcTemplate or similar)
- **Serialisation**: XStream (XML)
- **Messaging**: JMS via `springutils-jms:3.1.0`
- **HTTP**: Direct HTTP client for CRCP and SMS services
- **Testing**: JUnit; 80+ test classes covering DAO and handler layers

### Module Structure
```
request-common/
  - Domain: Request, Action (15 subtypes), ActionResult (15 subtypes), RequestActivity (12 subtypes),
            RequestProcessorConfig, RequestProcessorControl, Registration, Address, SecureProfile,
            FundsValue, NotificationValue, ClaimablePaymentAddenda
  - Enums: RequestStatus, ActionStatus, ActionType, RequestActivityType/Status/Facility,
           InventoryCardStatus, InventoryJournalAccountType, InventoryJournalActivityType
  - Serialisation: Symbol, SymbolFactory, XStreamFactory, SymbolEditor, SymbolEditorRegistrar
  - Manager interface: RequestManager
  - Config interface: RequestServiceConfigManager + client

request-manager/
  - Implementation: RequestManagerImpl
  - DAO interfaces: RequestDao, ActionDao, ActionResultDao, RequestActivityDao,
                    RequestProcessorConfigDao, RequestProcessorControlDao, SymbolDao
  - JDBC DAO implementations: JdbcRequestDao, JdbcActionDao, JdbcActionResultDao,
                               JdbcRequestActivityDao, JdbcRequestProcessorConfigDao,
                               JdbcRequestProcessorControlDao
  - Per-action JDBC operations (15 classes in action/ + 15 in actionresult/)
  - Activity handlers (10 classes for each activity type)
  - Config: TypeRoutingRequestActivityHandler

request-processor/
  - Core: RequestProcessorImpl, ActionProcessorImpl, RequestSynchronizerImpl, ActionSynchronizerImpl
  - Per-action handlers (15 classes): IssueCardActionHandler, AddFundsActionHandler, etc.
  - Supporting: PaymentServiceDelegateImpl, TypeRoutingActionHandler, XmlRpcRequestContextWrapperActionHandler
  - SMS: SmsNotificationService, SmsQueueService, SmsQueueDao, SmsConfigDao, SharedServiceConnector
  - CRCP: CrcpNotificationService, CrcpServiceConnector
  - Claimable: CreateClaimablePaymentSP, ACHTransferDetailCreateAPISP, InsertClaimCodeIssuanceInfo,
               GetPaymentExpiryDate, JdbcClaimablePaymentAddendaDao
  - SASI: SasiRequestProcessorThreadLocal
  - Config: RequestServiceConfigManagerImpl
  - Application context: ApplicationInstance
```

## API Surface
Library-only (no REST/SOAP surface):

**RequestManager interface**:
- `submitRequest(RequestActivity)` — submit a request for processing
- Various activity management methods per activity type

**Action handling** (internal to processor):
- Routed via `TypeRoutingActionHandler` based on `ActionType` enum

## Security Posture

### Authentication & Authorisation
- No authentication within the library.
- Trust model: callers are assumed to be authorised components within the same application.

### Sensitive Data Handling
- `SecureProfile.java:9` — `private String ssn` — SSN stored as plain String in memory and written to database without application-level encryption.
- `SecureProfile.java:11` — `private Date dob` — Date of birth stored as plain Date.
- `SecureProfile(SecureUserProfile sup)` constructor at line 33 maps from `SecureUserProfile.getFederal_id()` — SSN flows from the cbase user profile.
- `ActionSecureMemo` — security memo attached to actions; may contain sensitive data.

### Cryptography
- No cryptographic operations within this library.
- Relies on consuming application and database infrastructure for data protection.

### XStream Deserialization Risk
- `XStreamFactory.java` and `SymbolFactory.java` use XStream for XML serialisation/deserialisation.
- XStream has a long history of critical arbitrary code execution CVEs (CVE-2013-7285, CVE-2020-26217, CVE-2021-29505, and many others).
- If any XStream deserialization occurs on data from external/untrusted sources, RCE is possible.

### Known CVEs / Vulnerable Dependencies
| Library | Version | Risk |
|---|---|---|
| XStream (transitive via `xplatform:6.5.8`) | Likely old | Multiple critical RCE CVEs if deserialising untrusted XML |
| `xplatform:6.5.8` | Internal | Contains many legacy dependencies; full CVE analysis requires source |
| `springutils-jms:3.1.0` | Internal | JMS-based; Spring JMS CVEs if old Spring version |

## Technical Debt
1. **SSN without encryption** (`SecureProfile.java:9`): Plain-text SSN in domain object and database — GLBA compliance gap.
2. **XStream serialisation** (`XStreamFactory.java`): Critical CVE-prone library; must be replaced with Jackson or other safe serialiser.
3. **Thread-local SASI state** (`SasiRequestProcessorThreadLocal.java`): Thread-local state is incompatible with reactive/async processing and leaks across requests in thread pools without explicit clear.
4. **In-process synchronisation** (`RequestSynchronizerImpl`, `ActionSynchronizerImpl`): Does not work across JVM instances; incompatible with horizontal scaling.
5. **Config caching** (`ConfigCachingRequestServiceConfigManagerClient`): No TTL or invalidation visible; stale config risk.
6. **15 distinct action JDBC operation classes**: Each action type has a separate DAO class; high coupling to database schema.
7. **JMS broker dependency** (`springutils-jms`): Traditional broker-based messaging; must migrate to cloud messaging for Gen-3.
8. **cbase `SecureUserProfile`** in `SecureProfile.java:33`: Public constructor takes cbase type; ties library to cbase platform.
9. **SNAPSHOT root version** (`4.2.16-SNAPSHOT`): Not a released artifact.

## Gen-3 Migration Requirements
1. **Encrypt SSN and DOB at application layer** before any migration (immediate security requirement).
2. Replace XStream with Jackson or JAXB with strict type constraints.
3. Replace `SecureProfile` cbase dependency with a self-owned domain type.
4. Replace in-process synchronisation with distributed locking (Redis, DB optimistic locking).
5. Extract each action type into a dedicated microservice command handler (CQRS/event sourcing pattern).
6. Replace JMS broker with cloud message bus (Azure Service Bus, Kafka).
7. Replace JDBC stored procedures with JPA repositories or Spring Data JDBC.
8. Remove thread-local SASI state; redesign for stateless processing.
9. Replace config caching with Spring Cloud Config or Azure App Configuration with event-driven invalidation.

## Code-Level Risks (File:Line References)
- `SecureProfile.java:9` — `private String ssn` — plain-text SSN in domain model and persistence.
- `SecureProfile.java:33-37` — `SecureProfile(SecureUserProfile sup)` maps SSN from cbase type; SSN flows from `sup.getFederal_id()`.
- `XStreamFactory.java` — entire class: XStream instantiation; critical CVE risk if deserialising untrusted XML.
- `SasiRequestProcessorThreadLocal.java` — thread-local; potential state leakage across requests.
- `UpdateUserSecureProfileJdbcDaoOperations.java` — writes SSN/DOB to database; verify column encryption.
- `RequestManagerImpl.java` — core orchestrator; any bug here affects all 15 action types.
