# cicd-testapp_SVC — Solution Architect View

## Technical Architecture

### Module Dependency Chain
```
common (interfaces, enums, value objects, exceptions)
  ^
  |-- ecountCoreDAO       (JDBC DAO impls, stored procedure wrappers)
  |-- MQLibrary           (IBM MQ JMS abstraction: MQJMS, MQJMSImp)
  |-- ecountCoreLibrary   (business library implementations)
  |-- ecountCoreService   (service layer implementations)
  |-- ProcessorServices/FDRDebitService  (FDR debit service)
  |-- ecountCoreRestApi   (REST request/response DTOs)
  |
  +--> eCoreWar (WAR: Spring XML config, XmlRPCServlet, DispatcherServlet)
  +--> ecountCoreRestController (Spring MVC @RestController classes)
```

### Technology Stack
- **Language**: Java 8
- **Framework**: Spring Framework 4.3.27.RELEASE (XML-driven; AOP for tracing and transactions)
- **Web**: Spring MVC (DispatcherServlet), custom XmlRPCServlet, Servlet API 3.1
- **Persistence**: Spring JDBC + custom `StoredProcedure` subclasses; jTDS 1.2.2 JDBC driver
- **Messaging**: Spring JMS + IBM MQ (`com.ibm.mq.jms.*`); Spring JMS templates
- **Serialisation**: XStream 1.4.12 (HTTP Invoker remoting and FDR ODS messages), Jackson 2.11.1 (REST JSON), GSON 2.8.6
- **Security/PII**: Custom StrongBox (`strongboxImpl 1.0.2`) for encrypted PII storage
- **XML-RPC**: Custom `com.ecount.core.xmlrpc.servlet.XmlRPCServlet`; `com.citi.prepaid.service.core:xmlrpc:2019.4.1`
- **API docs**: SpringFox Swagger 2.9.2 (`SwaggerConfiguration` in `ecountCoreRestController`)
- **Logging**: Log4j 1.2.15 + Log4jMDCWriter for correlation
- **Testing**: JUnit 4.13, JMock 2.12.0, Hamcrest 2.2, Spring Test
- **Utilities**: Lombok 1.18.12, Google Guava 29.0-jre, Apache Commons (Lang 2.4/3.10, BeanUtils 1.7.0, DBCP 1.2.2, Pool 1.4)
- **Build**: Maven 3 with JaCoCo (90% coverage targets), Cobertura reporting, AsciiDoc documentation generation

## API Surface

### XML-RPC API (primary legacy interface — `/dispatch.asp`)

All operations are mapped via Spring bean aliases in XML files under `eCoreWar/src/main/resources/`:

**eDevice** (`EDeviceXMLRPC.xml`):
- `ECountCore.eDevice.Create` — create device (eCard, eCheck, DDA, CreditCard, IEFT, Operator)
- `ECountCore.eDevice.Inquiry` — device inquiry
- `ECountCore.eDevice.Update` — device update
- `ECountCore.eDevice.Control` — device control (block/unblock operations)
- `ECountCore.eDevice.CatalogInquiry`, `GroupCatalogInquiry`
- `ECountCore.eDevice.ExtendedAddendaInquiry`, `UpdateAddenda`, `DDAInquiry`, `CreateandInquiry`

**eMember** (`EMemberXMLRPC.xml`):
- `ECountCore.eMember.AddBasic`, `AddExtended`, `AddUniversalRegistration`
- `ECountCore.eMember.UpdateBasic`, `UpdateExtended`, `UpdateUniversalRegistration`, `UpdateAddenda`, `UpdateSecureProfile`
- `ECountCore.eMember.InquiryBasic`, `InquiryExtended`, `InquirySecureProfile`, `InquiryDefaultDevice`
- `ECountCore.eMember.BasicMemberSearch`, `PUIDMemberSearch`
- `ECountCore.eMember.GroupMemberAdd/Remove/RoleUpdate/Inquiry/Search`
- `ECountCore.eMember.DoKYCCheck`, `DeAssociateMemberCorrelator`, `AssociateMemberCorrelator`

**eManage** (`EManageXMLRPC.xml`):
- Check: `CheckOrderRequest/Inquiry`, `CheckStopPaymentRequest/Inquiry`, `CheckDDAAvailableAuthInquiry`, `CheckProgramAccountInquiry`, `CheckVoid`
- PreCheck: `PreCheckOrderRequest/Inquiry`, `PreCheckBookInquiry`, `PreCheckStopPaymentRequest`, `PreCheckAddendaSet/Inquiry`, `PreCheckAssign`, `PreCheckAuthorize`, `PreCheckMerchantVerify`, `PreCheckDefinitionInquiry`, `PreCheckCatalogInquiry`, `PreCheckActivityJournalInquiry`, `PreCheckActivityDefinitionInquiry`, `PreCheckMemberInventoryInquiry`, `PreCheckActivityFeeInquiry`
- TxReviewQueue: `TxReviewQueueInquiry/Update`, `ACHTxReviewQueueInquiry/Update`
- ACH: `ACHListInquiry/Update`, `ACHVoid`

**eTransfer** (`ETransferXMLRPC.xml`):
- `ECountCore.eTransfer.Begin`, `Commit`, `Cancel`, `CancelOnDemand`, `Inquiry`, `QuickLoad`, `SimpleFeeInquiry`, `TransactionInquiry`

### REST API (newer overlay — Spring MVC)

Servlet mapping: `/*` (DispatcherServlet); Swagger UI available.

**`/device`** (`DeviceController`): POST `/ecard`, `/echeck`, `/dda`, `/creditcard`, `/ieft`; GET `/inquiry`, `/catalog`, `/group-catalog`, `/extended-addenda`, `/dda-inquiry`, `/by-member`, `/by-addenda`; PUT `/update`, `/control`, `/update-addenda`; POST `/create-and-inquiry`.

**`/member`** (`MemberController`): POST `/basic`, `/extended`, `/universal`; PUT `/basic`, `/extended`, `/universal`, `/addenda`, `/secure-profile`; GET `/basic`, `/extended`, `/secure-profile`, `/default-device`, `/search`, `/puid-search`, `/ecap`, `/dda-only`, `/by-addenda`, `/by-echeck`; POST `/kyc`.

**`/transfer`** (`TransferController`): POST `/begin`, `/begin/ecard`; PUT `/commit`, `/cancel`, `/cancel-on-demand`; GET `/inquiry`, `/fee-inquiry`; POST `/quick-load`.

**`/ach`** (`AchController`): ACH list inquiry/update, review queue inquiry/update, ACH void.

**`/check`** (`CheckController`): Check order/stop-payment/void, DDA auth inquiry, TX review queue.

**`/precheck`** (`PrecheckController`): All PreCheck operations.

### HTTP Invoker (internal service-to-service, `core-servlet.xml`)
Exposed via `RequestContextHttpInvokerServiceExporter` with XStream marshalling:
- `/eDevice` → `IDeviceService`
- `/eMember` → `IMemberService`
- `/eManage` → `IManageService`
- `/eTransfer` → `ITransferService`
- `/eDeviceProxy`, `/eMemberProxy`, `/eManageProxy`, `/eTransferProxy` (proxy variants)

## Security Posture

### Authentication & Authorisation
- **No application-level authentication** is implemented in this codebase. Neither the XML-RPC servlet, the HTTP Invoker endpoints, nor the REST controllers (`DeviceController`, `MemberController`, etc.) implement `@PreAuthorize`, Spring Security filters, or any token/credential validation.
- The `correlationIdFilter` (DelegatingFilterProxy in `web.xml`) handles request correlation only — not authentication.
- Access control is expected from the network/container layer (Tomcat connector, network firewall).
- This represents a **critical security gap** if any of the REST or HTTP Invoker endpoints are reachable outside a trusted internal network without a gateway enforcing authentication.

### Transport Security
- No HTTPS/TLS configuration in application code. Relies entirely on Tomcat connector configuration.
- GitHub Actions workflow uses `-Daether.connector.https.securityMode=insecure` for artifact resolution — build-time TLS bypass.

### Input Validation
- REST request objects (`ecountCoreRestApi` DTOs) use Lombok `@Data`/`@Builder` annotations but contain no JSR-303/Bean Validation (`@NotNull`, `@Size`, etc.) annotations visible in the reviewed files.
- XML-RPC inputs are mapped via `scope="prototype"` bean DTOs — no explicit validation layer.
- Stored procedure parameters provide implicit SQL injection protection (parameterised calls via Spring `StoredProcedure`).

### Sensitive Data in Logs
- `MQJMSImp.java` line 72: `log.info("MQJMSImp||executeGetReply: Request being sent is: ["+ requestStr +"]")` — full request string (may include card numbers, account data from FDR ODS messages) logged at INFO.
- `MQJMSImp.java` line 132: `log.info(" messageCreator.getTextMessage() = " + messageCreator.getTextMessage())` — JMS TextMessage logged.
- These are PCI DSS violations if the request contains PAN data.

### Dependency Vulnerabilities
- **Log4j 1.2.15**: CVE-2019-17571 (CVSS 9.8) — remote code execution via socket appender deserialization.
- **XStream 1.4.12**: CVE-2021-21344, CVE-2021-21345, CVE-2021-21346 — arbitrary code execution via deserialization; XStream 1.4.18+ required.
- **commons-beanutils 1.7.0**: CVE-2019-10086 — insecure deserialization.
- **Spring 4.3.27**: multiple CVEs post-EOL; Spring Framework 5.3.x+ required for current patches.
- **aspectj 1.5.2a**: very old (2006 era); replaced by AspectJ 1.9.x.
- **commons-dbcp 1.2.2**: EOL; replaced by commons-dbcp2 or HikariCP.
- CodeQL `security-extended` scan is configured and runs on GitHub Actions — some vulnerabilities should be detected.

## Technical Debt

1. **Spring XML-first architecture**: Hundreds of XML bean definitions across 40+ Spring context files (`web.xml` loads 20 context XML files at startup). Refactoring to annotation-based configuration and Spring Boot would reduce operational complexity significantly.
2. **XStream 1.4.12**: Used for HTTP Invoker marshalling and FDR ODS message conversion. Known deserialization vulnerabilities. `com.thoughtworks.xstream.XStream` without a security framework (type whitelist) is exploitable if attacker-controlled input reaches the deserializer.
3. **jTDS 1.2.2 JDBC driver**: Ancient jTDS driver for SQL Server; Microsoft JDBC Driver (`com.microsoft.sqlserver:mssql-jdbc`) is the current supported option.
4. **commons-dbcp 1.2.2 / commons-pool 1.4**: End-of-life connection pool; HikariCP is the modern replacement and offers better performance and monitoring.
5. **`Log4jConfigListener` in `web.xml`**: This Spring 4 API was removed in Spring 5, making Spring 5 migration impossible without addressing logging bootstrap.
6. **`REGISTRATION_REPLACE_EXISTING` JMX property** (`Configuration.xml` line 45): Spring 5 renamed this to `REPLACE_EXISTING`; commented in code but not yet resolved.
7. **Inline commented credentials** (`DataSources.xml` lines 22–41): Commented-out beans contain `username=b2ctest`, `password=b2ctest`. Present in git history.
8. **`CachingConnectionFactory` without XA** (`FDRDebitServices.xml` line 733): Session cache size 10, but no XA transaction manager despite XA connection factory being declared in `context.xml`. Potential message loss under crash scenarios.
9. **Abstract base class pattern for debit services**: `FDRDebitServices` extends `AbstractDebitServices` — the abstract base is not visible in the repo but is implied; tight coupling to FDR ODS protocol.
10. **`MQJMSImp` recursive retry with `Thread.sleep`**: lines 140–146 and 193–198 use `Thread.sleep(2000)` in a recursive call chain up to depth 3. Under high load this wastes thread pool resources. Should use scheduled retry or circuit breaker.

## Gen-3 Migration Requirements

To migrate this service toward a Gen-3 cloud-native, API-first, containerised architecture:

1. **Containerise**: Replace WAR + Tomcat with a Spring Boot fat-JAR or containerised deployment. This requires:
   - Externalise JNDI data sources to Spring Boot `DataSource` beans with connection pool (HikariCP)
   - Replace `SpringCloudConfigContext` with Spring Boot Config Server client
   - Replace `context.xml` JNDI resource links with Kubernetes Secrets / AWS SSM / Vault integration

2. **Replace Log4j 1.x**: Migrate to SLF4J + Logback or Log4j 2. Remove `Log4jConfigListener` from `web.xml`. Update all `LogFactory.getLog()` calls.

3. **Upgrade Spring to 5.3.x or migrate to Spring Boot 2.7.x / 3.x**: Resolve all documented blockers (KYCService.xml marshaller, MBeanExporter API, web.xml listener).

4. **Retire XML-RPC**: Ensure all consumers migrate to the REST API layer before decommissioning `XmlRPCServlet` and associated XML-RPC DTO/proxy classes (~40 aliases, 200+ DTO classes).

5. **Secure the REST API**: Implement OAuth 2.0 / JWT authentication on all REST endpoints. Add Spring Security configuration. Add JSR-303 Bean Validation to REST request DTOs.

6. **Fix PAN/sensitive data in logs**: Introduce a `MessageSanitizer` interceptor or redact sensitive fields before any log statement in `MQJMSImp`.

7. **Upgrade XStream to 1.4.20+**: Add type whitelist/security framework to prevent deserialization attacks.

8. **Replace jTDS with Microsoft JDBC Driver**: `com.microsoft.sqlserver:mssql-jdbc:12.x` for SQL Server.

9. **Migrate Nexus artifacts to Onbe-controlled repository**: `strongboxImpl`, `xmlrpc`, `DAO-Util`, `springutils` must be available outside the `wirecard.sys` domain.

10. **Introduce API gateway**: Place an API gateway (Kong, AWS API Gateway, or internal) in front of both XML-RPC and REST endpoints to provide authentication, rate limiting, and audit logging without changing application code.

## Code-Level Risks

| Risk | Location | Severity |
|---|---|---|
| Full request string logged at INFO (potential PAN exposure) | `MQJMSImp.java:72,132` | Critical (PCI DSS) |
| XStream deserialization without type whitelist | `ecountCoreRestController` / `core-servlet.xml` XStreamMarshaller | High |
| Log4j 1.2.15 socket appender RCE (CVE-2019-17571) | `pom.xml:365` | High |
| No authentication on REST endpoints | `DeviceController`, `MemberController`, `TransferController`, etc. | High |
| `Thread.sleep` in JMS retry loop (thread pool starvation under load) | `MQJMSImp.java:140-146, 193-198` | Medium |
| Hardcoded credentials in commented XML (git history exposure) | `DataSources.xml:22-41` | Medium |
| `aether.connector.https.securityMode=insecure` in CI | `.github/workflows/codeql-java.yml:26` | Medium (build-time MITM) |
| commons-beanutils 1.7.0 deserialization (CVE-2019-10086) | `pom.xml:313` | Medium |
| Tests skipped in all CI/CD pipelines | `Jenkinsfile:19`, `.gitlab-ci.yml:15-17` | Medium (quality gate absent) |
| `SNAPSHOT` versions deployed to non-dev environments | `pom.xml:13` | Medium (reproducibility) |
| No JSR-303 validation on REST request DTOs | `ecountCoreRestApi/**Request.java` | Medium |
| `StrongBoxXmlMarshallerImpl` entire SecureUserProfile serialised — no field-level access control | `StrongBoxService.xml` | Low-Medium |
| Spring 4.3.27 EOL — multiple unpatched CVEs | `pom.xml:77` | Medium |
