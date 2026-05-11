# cicd-testapp_SVC — Data Architect View

## Data Stores

| JNDI Name | Bean ID | Type | Purpose |
|---|---|---|---|
| `jdbc/ecountCoreDS` | `ecountCoreDS` | SQL Server (jTDS driver `net.sourceforge.jtds.jdbc.Driver`) | Primary operational database — members, devices, transactions, journals, ACH, IEFT, fulfillment, configuration |
| `jdbc/jobsvcDS` | `jobsvcDS` | SQL Server | Job service database — `job_account_get_map` procedures; used by `IMemberService.puidMemberSearch` |
| `jdbc/fdrODSDS` | `fdrODSDS` | FDR ODS (non-standard; commented config shows `sun.jdbc.odbc.JdbcOdbcDriver` / ODBC `CBASClntCATM`) | First Data Resources Operational Data Store — authoritative card record; accessed exclusively via IBM MQ JMS |
| `jdbc/strongboxDS` | `strongboxDS` | SQL Server | StrongBox encrypted repository — stores serialised encrypted blobs (SSN, DOB, secure profile) |
| **IBM MQ** (`jms/ECSQueueConnectionFactory`) | `ecsMQJMSImp` | IBM WebSphere MQ | ECS+ (EcountCore Service) request/response queues for prepaid authorisation messaging |
| **IBM MQ** (`jms/FDRQueueConnectionFactory`) | `fdrQueueConnectionFactory` | IBM WebSphere MQ | FDR ODS request/reply queues used by all `FDRDebitServices.xml` operation beans |
| **IBM MQ** (`jms/ActimizeQueueConnectionFactory`) | `actimizeMQJMSImp` | IBM WebSphere MQ | Actimize real-time sanctions screening request queue |
| **IBM MQ** (`jms/GPPAccStatusQ`) | `gppMQJMSImp` | IBM WebSphere MQ | GPP account status notification queue |
| **Northlane Config Server** | Spring Cloud Config Context | External HTTP service | Runtime property source; client class `com.northlane.configserver.client.bootstrapping.SpringCloudConfigContext` (configured in `web.xml`) |

## Schema & Tables

No DDL files exist in this repository. The data model is inferred from stored procedure wrapper classes. Key tables/entities implied:

- **Core device tables**: invoked by `CoreDeviceCreateECard`, `CoreDeviceCreateECheck`, `CoreDeviceCreateDDA`, `CoreDeviceCreateCreditCard`, `CoreDeviceCreateProtected`, `CoreDeviceCreateProtectedIEFT` — one create procedure per device type, suggesting a polymorphic device table or type-discriminated schema.
- **Member / registration tables**: `CoreRegistrationCreateExtended`, `CoreRegistrationUpdateExtended` — extended member registration. `CoreMemberGetAccount`, `CoreMemberGetDevices`, `CoreMemberGroupGetDevices`.
- **Activity journal**: `CoreActivityJournalInsert` + `CoreActivityJournalAddendaInsert` (in `ecountCoreDAO/src/main/java/com/ecount/core/dao/eAuditActivity/jdbc/StoredProcedure/`).
- **Emboss / fulfillment tables**: `CoreCardAccountEmbossHistoryInquiry`, `CoreCardAccountEmbossHistoryUpdate`, `CoreCardAccountEmbossRequest`, `CoreProcessEmbossQueueRequest`, `CoreCardPurgeRequest`, `CoreProfileCardDistributionInquiry`, `CoreProfileFulfillmentInquiry`.
- **Processor profile tables**: `CoreProfileProccessorInquiry`, `CoreProfileProgramAccessLevelInquiry`, `CoreAgentProcessorInquiry`.
- **ACH tables**: dedicated `ACHDeviceDAO` with procedures `AchAccountVerify`, `AchBankInquiry`, `AchBankValidate`, `AchTransactionCreate`, `AchTransactionInquiry`, `CanadaAchBankInquiry`, `CanadaAchTransactionCreate`.
- **IEFT tables**: `IEFTTransactionCreate`, `IEFTTransactionCommit`, `IEFTTransactionCancel`, `IEFTTransactionCancelOnDemand`, `IEFTTransactionInquiry`.
- **eManage / Check tables**: ~100 stored procedure wrappers in `ecountCoreDAO/src/main/java/com/ecount/core/dao/eManage/jdbc/` covering ACH lists, PreCheck catalog/books/activity, check orders, stop-payments, DDA auth.
- **FDR ODS** (via MQ, not JDBC): `newAccount`, `issuePlastic`, `rushIssuePlastic`, card balances, PIN management, address updates, authorization adjustments, EMV chip — ~30+ operations.
- **StrongBox tables**: `StrongBoxJDBCDAOImpl` using `strongboxDS`; schema not visible but stores encrypted blobs with version reference (`writeReference.version` property in `StrongBoxService.xml`).
- **CyberSource settings**: `CoreGetCyberSourceSettings` stored procedure — credit card fraud scoring integration.
- **ICS score rules**: `ICSScoreRulesInquiry` — ICS fraud scoring rules.
- **FDR DDA Authorization journal**: `FDRDDAAccountAuthorizationJournalStatusInquiry` (in `coreservices` package).

## Sensitive Data Handling

- **SSN / Date of Birth**: stored via `IStrongBoxService.repositoryServiceWriteMap()`. The `SecureUserProfile` object (parameter to `IMemberService.addExtended/addUniversalRegistration`) is serialised and encrypted before database persistence. Only an opaque reference string is stored in the core database.
- **Card numbers (PAN)**: not stored in `ecountCoreDS`; FDR ODS is the system of record for card data. PANs pass through JMS messages to/from FDR ODS. `MQJMSImp.executeGetReply()` logs the full request string at INFO level (line 72 of `MQJMSImp.java`), which may include card data depending on FDR ODS message format.
- **PIN data**: PIN management entirely delegated to FDR ODS via MQ (`GeneratePinChangeRefId`, `SetPinId`, `GenerateEMVPinChangeRefId`, `SetEMVPinId`). No PIN material is stored in `ecountCoreDS`.
- **Bank account / routing numbers**: stored in DDA and ACH device records in `ecountCoreDS`; protected by `CoreDeviceCreateProtected` and `CoreDeviceCreateProtectedIEFT` procedures suggesting a protected column or encryption at the stored procedure layer.
- **Member registration PII** (name, address, phone, email): stored in `ecountCoreDS` via `CoreRegistrationCreateExtended`; no column-level encryption observed in application code.

## Encryption & Protection

- **StrongBox**: `StrongBoxJDBCDAOImpl` + `StrongBoxXmlMarshallerImpl` (`StrongBoxService.xml`) provide application-level encryption for sensitive PII blobs. The `writeReferenceVersion` bean property suggests versioned key management.
- **FDR ODS security element** (`ODSSecurityElement`, `FDRDebitServices.xml` lines 714–725): `userId`, `passwordHash`, and `encryptCodePage` are runtime properties (not hardcoded); the `IBM037` encoding (EBCDIC) is used for the XStream message converter.
- **`CoreDeviceCreateProtected` / `CoreDeviceCreateProtectedCreditCard` / `CoreDeviceCreateProtectedIEFT`**: dedicated stored procedures for protected device types imply database-layer protection for sensitive account identifiers.
- **`CoreDeviceUpdateProtected` / `CoreDeviceUpdateProtectedIEFT`**: update paths also use dedicated protected procedures.
- No TLS configuration is present in this codebase; TLS is expected to be handled at the container (Tomcat) or network layer. The `aether.connector.https.securityMode=insecure` flag in the GitHub Actions workflow (`.github/workflows/codeql-java.yml` line 26) disables TLS certificate validation during Maven artifact resolution — this is a build-time risk, not a runtime risk.

## Data Flow

```
Client (XML-RPC or REST)
  |
  v
XmlRPCServlet / DispatcherServlet  [eCoreWar/web.xml]
  |
  +---> eDeviceProxy / eMemberProxy / eManageProxy / eTransferProxy  [XML-RPC]
  |       --> IDeviceService / IMemberService / IManageService / ITransferService
  |
  +---> DeviceController / MemberController / TransferController / AchController  [REST]
          --> IDeviceService / IMemberService / ITransferService / IManageService
                |
                +---> ecountCoreDS (SQL Server) via JDBC stored procedures
                |       EDeviceJDBCDAO, ACHDeviceDAO, IEFTDeviceDAO,
                |       CoreServiceJDBCDAO, EAuditActivityDAO, etc.
                |
                +---> fdrODSDS (FDR ODS) via IBM MQ JMS
                |       FDRDebitServices -> FDRODSDAO -> jms/FDRRequestQueue
                |                                    <- jms/FDRReplyQueue
                |
                +---> ECS+ via IBM MQ JMS
                |       MQJMSImp -> jms/ECSRequestQ <- jms/ECSResponseQ
                |
                +---> Actimize via IBM MQ JMS
                |       KYCLibrary -> jms/ActimizeRequestQ
                |
                +---> StrongBox via JDBC (strongboxDS)
                        StrongBoxJDBCDAOImpl -> encrypted blob storage
```

## Data Quality & Retention

- **Activity journal** is append-only (`CoreActivityJournalInsert` — no update or delete procedures observed), providing an immutable audit trail.
- **JMS message expiry**: configurable per template — long expiry = 172,800,000 ms (48 hours), short expiry = 120,000 ms (2 minutes), FDR ODS TTL is runtime property `${fdr.ttl}` (`MQConfig.properties`, `FDRDebitServices.xml`).
- **SQL timeout**: 40-second default for all stored procedures (`sqlTimeoutManager` in `DataSources.xml`), preventing connection-pool exhaustion from slow queries.
- No data retention, archival, or purge policies are visible in application code beyond `CoreCardPurgeRequest` (card-specific purge stored procedure).
- No schema migration tooling (Flyway, Liquibase) is present.

## Compliance Gaps

1. **PAN in logs**: `MQJMSImp.java` INFO log of full request string (line 72) may expose PAN in log files. PCI DSS Requirement 3.5 prohibits unmasked PAN in logs. Requires log scrubbing or request redaction before logging.
2. **No field-level masking in REST API responses**: `DeviceController`, `MemberController` return full domain objects (e.g., `Account`, `Member`, `CoreMemberExtendedFull`) — no `@JsonIgnore` or masking annotations visible for sensitive fields such as DDA number, bank account number, or SSN reference.
3. **StrongBox write reference versioning**: `writeReference.version` is a runtime property; if key rotation has not been implemented for older versions, data written with deprecated keys may become inaccessible or remain under weaker encryption.
4. **Database credentials in commented config** (`DataSources.xml` lines 22–41): hardcoded username `b2ctest` and password `b2ctest` appear in commented-out XML. While inactive, they represent a credential leak risk in source control history.
5. **FDR ODS password hash in runtime properties** (`fdr.passwordHash`): stored as a property — the security of this credential depends entirely on the config server or fallback properties file security. No HSM or vault integration is visible in this codebase for the FDR ODS password.
6. **No DLP on StrongBox blobs**: `StrongBoxXmlMarshallerImpl` serialises the entire `SecureUserProfile` object to XML before encrypting; field-level access control within the blob is not enforced by this application.
