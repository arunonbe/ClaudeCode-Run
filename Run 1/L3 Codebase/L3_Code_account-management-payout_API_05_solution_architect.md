# account-management-payout_API — Solution Architect View

## Technical Architecture

### Module Structure
```
accountmanagementapi-payout (pom, v3.0.1-SNAPSHOT)
├── accountmanagementapi-payout-impl (JAR)
│   ├── constants/        AccountManagementConstant
│   ├── domain/           Input/Output domain objects (ServiceInput, RegistrationInput, WithdrawInput, etc.)
│   ├── exception/        Exception hierarchy (BusinessValidationException, InputValidationException,
│   │                     KYCProcessException, SystemFailureException)
│   ├── helper/           AccountHelper, AMPayoutHelper, JWEHelper, AssignPackageHelper, ProfileHelper, etc.
│   ├── service/          AccountManagementApiService<IN,OUT>, AccountManagementApiServiceImpl<IN,OUT>,
│   │                     ActivationStatusInquiryService, ActivateCardService, SetPinService,
│   │                     UpdateRegistrationService (+ ~12 disabled services)
│   ├── type/             Enums: ResponseStatusType, WithdrawType, BankAccountType, AddendaType
│   └── validator/        IValidator, Validator, ParameterValidator, StringValidator, EmailValidator,
│                         PhoneValidator, DateValidator, IntegerValidator, LongValidator, etc.
├── accountmanagementapi-payout-ws (JAR)
│   ├── domain/           SOAP domain objects: Card, Registration, Address, Addenda, VoidACH, WithdrawACH, etc.
│   ├── handler/          AccountManagementHandler interface + AccountManagementHandlerImpl
│   ├── helper/           DomainHelper (XStream XML, request/response mapping), JweDDAHelper, RequestAwareGlobalRequestIDGenerator
│   ├── request/          SOAP request objects (ActivateCardRequest, SetPinRequest, etc.)
│   ├── response/         SOAP response objects
│   └── ws/               AccountManagementApiWebService (interface extends java.rmi.Remote)
│                         AccountManagementApiWebServiceImpl (extends ServletEndpointSupport)
│                         ProvisionServiceApiWebService / Impl (all methods commented out)
└── accountmanagementapi-payout-war (WAR → accountmanagementpayoutapiws.war)
    ├── health/           HealthCheck (@RestController GET /hc)
    └── WEB-INF/          web.xml, accountmanagementapi-servlet.xml, wsdl.xml
```

### Request Path
```
HTTP POST /services/AccountManagementApiWebServices
  → AuthenticationCheckFilter (com.citi.prepaid.security.api.filter)
  → AxisServlet (org.apache.axis.transport.http.AxisServlet)
  → AccountManagementApiWebServiceImpl.{setPin|activationStatusInquiry|activateCard}()
      (manual bean lookup: getWebApplicationContext().getBean("accountManagementHandler"))
  → AOP Proxy: GlobalRequestIDInterceptor → AuditMethodInterceptor
  → AccountManagementHandlerImpl.{setPin|activationStatusInquiry|activateCard}()
      → JweDDAHelper.decryptDDA()  (Nimbus JWE)
      → IValidator.validate()       (Spring XML-configured validator chain)
      → {ActivationStatusInquiryService|ActivateCardService|SetPinService}.execute()
          → AccountHelper / FDRCardAccountDetailInquiryDAO / KYC / OrderService
  → JweDDAHelper.encryptDDA()  (response DDA encryption)
```

---

## API Surface

### Active WSDL Operations (published to external APIM)
**Namespace**: `http://ws.accountmanagementapi.prepaid.citi.com`
**Binding**: `AccountManagementApiWebServicesSoapBinding` (SOAP 1.1, document-literal)
**Service endpoint**: `/services/AccountManagementApiWebServices`

| Operation | Input Type | Output Type | Key Fields |
|---|---|---|---|
| `activationStatusInquiry` | `activationStatusInquiryRequest` | `activationStatusInquiryResponse` | IN: card_number, cvv, postal_code, validate_postal. OUT: activationStatus, accountNumber (JWE-encrypted), binBankName, code, sub_code, description |
| `activateCard` | `ActivateCardRequest` | `ActivationCardResponse` | IN: card_number, cvv, postal_code, accountNumber (JWE or empty). OUT: activationStatus, code, sub_code |
| `setPin` | `SetPinRequest` (extends `ServiceRequestAccountNumber`) | `UpdateAccountStatusResponse` | IN: accountNumber (JWE), new_pin, partner_user_id, program_id, transaction_id. OUT: code, sub_code, existingTransaction |

**Response codes**:
- `code = 0`: Success (`PROCESSED_SUCCESSFULLY`, `ACCOUNT_CREATED`, etc.)
- `code = 1`: Failure (`PROCESSING_FAILED`, `OVER_PIN_SET_LIMI`, etc.)
- `code = 2`: Async processing in progress (`PROCESSING`)

### Health endpoint
`GET /hc` → `200 OK` with body `"OK"` (Spring MVC REST)

### Monitor page
Path not explicitly defined in read code; follows eCount springutils monitor controller convention.

---

## Security Posture

### Authentication
- `AuthenticationCheckFilter` (`com.citi.prepaid.security.api.filter.AuthenticationCheckFilter`) is the only authentication mechanism (`web.xml` lines 33–39). It is applied to `/*`.
- The internals of this filter are in `api-security-lib:3.0.1` — an internal library not present in this repository. The mechanism (certificate, shared secret, or token-based) cannot be confirmed from code in this repo.

### Authorization
- API-level security (`validateAPISecurity()` — `AccountManagementApiServiceImpl.java` lines 78–87) is fully commented out for all three active operations. The code path that would call `SecurityValidator.authorize(candidate, domain)` is disabled via "JIRA 476" comment (`AccountManagementApiServiceImpl.java` line 151, `SetPinService.java` line 43).
- This means: after passing `AuthenticationCheckFilter`, no program-level or method-level authorization is enforced.

### Transport Security
- Tomcat `server.xml` configures only port 80 (HTTP). No TLS at the service level. TLS must be enforced by the upstream ingress or load balancer.
- The WSDL hardcodes `https://` in the service endpoint address (`wsdl.xml` line 252), indicating TLS is expected to be available at the published endpoint.

### DDA Encryption
- `JweDDAHelper` (Nimbus JOSE): `DIR` + `A256GCM`. Key sourced from `${jwe.secretKey}` property.
- Token includes timestamp; replay window controlled by `${jwe.expirationTime}`.
- When `encryptDDA != Y`, account numbers traverse in clear text.
- Decrypted DDA number is logged at INFO level (`AccountManagementHandlerImpl.java` line 100) — sensitive data in log stream.

### Input Validation
- Two-tier: (1) `IValidator`/`ParameterValidator` chain run via `validate(Map<>)` — Spring XML-configured, checks presence and format of each field; (2) Business rule checks in `AccountManagementApiServiceImpl` (program-account binding, mutual exclusion checks).
- Validators are data-type validators (String, Integer, Long, Date, Email, Phone, Choice) but there is no evidence of SQL injection protection at the service layer (all DB access is via stored procedures, which is inherently parameterised — this is a mitigating control).

### Session
- Session timeout: 5 minutes (`web.xml`). Service is effectively stateless (no server-side session state per request).

### Known CVE Suppressions
`.trivyignore` and `allowedlist.yaml` suppress the following; each should be reviewed against actual impact:
- `CVE-2024-22262`: Spring Web redirect vulnerability (service does not appear to perform redirects)
- `CVE-2024-38816`, `CVE-2024-38819`: Spring Framework path traversal
- `CVE-2024-47072`: XStream (used heavily via `DomainHelper.printObjectToXML()`)
- `CVE-2024-50379`: Tomcat partial PUT (service does not use PUT)
- `CVE-2024-52316`: Tomcat HTTP/2 (service only uses HTTP/1.1)
- `CVE-2024-56337`: Tomcat servlet context
- `CVE-2018-1000632`, `CVE-2020-10683`: DOM4J/xml-apis

**Note**: `CVE-2024-47072` (XStream deserialization) is a concern because `DomainHelper` uses XStream to serialize request/response objects to XML for logging. If log messages are ever deserialized, this vulnerability is relevant.

---

## Technical Debt

### Critical / High
1. **`ServletEndpointSupport` manual bean lookup** (`AccountManagementApiWebServiceImpl.java` line 20): `getWebApplicationContext().getBean("accountManagementHandler")` — bypasses Spring dependency injection. This class is effectively dead code in Spring 6+. Removed from the framework without deprecation notice.

2. **JIRA 476 dead code block**: ~700 lines in `AccountManagementHandlerImpl.java` and matching service/validator beans are inside a block comment with no deletion date or migration ticket. Includes complete implementations of createAccount, withdraw (ACH+Check+void), addFunds, linkCard, assignPackage, createPackage, createBulkOrder, updateAccountStatus, updateProvisionStatus — a full B2C disbursement feature set that is silently disabled.

3. **Logging of sensitive data**: Encrypted DDA (with clear 8-digit prefix) and decrypted DDA number logged at INFO (`AccountManagementHandlerImpl.java` lines 98, 100). This is a PCI DSS finding.

4. **`ProvisionServiceApiWebServiceImpl`** — entire class body is a comment. The class and interface exist solely as empty skeletons. No active functionality.

5. **WSDL hardcoded dev endpoint**: `wsdl.xml` line 252 references `https://d-app02.nam.wirecard.sys:9326/...` — a legacy host that no longer exists. The WSDL is published to APIM, so consumers may be receiving incorrect endpoint information.

6. **`SHA1PRNG` in `JWEHelper.java`** (lines 363, 382): The old Visa JWE implementation uses `SecureRandom.getInstance("SHA1PRNG")`. In OpenJDK 17+, this defaults to the underlying platform PRNG; the explicit name is misleading and not the strongest available.

7. **BouncyCastle `AESFastEngine`** (`JWEHelper.java` line 275): This class was deprecated in BouncyCastle 1.58. The `bcprov-jdk15on` artifact is also the legacy BouncyCastle JAR; `bcprov-jdk18on` is the current recommended artifact.

### Medium
8. **`jakarta.servlet.http.HttpUtils.java`** in `accountmanagementapi-payout-ws/src/main/java/jakarta/servlet/http/HttpUtils.java`: A source file placed directly in the `jakarta.servlet.http` package in application source. This is either a patched copy of a Jakarta EE class or an empty shim — placing code in the `jakarta.*` namespace in application source is a packaging anti-pattern and may cause ClassLoader conflicts.

9. **`AESFastEngine` + `GCMBlockCipher`**: `JWEHelper.java` uses `new GCMBlockCipher(new AESFastEngine())`. `AESFastEngine` is the old name; current BouncyCastle uses `AESEngine.newInstance()`.

10. **`DomainHelper.printObjectToXML()`** uses XStream for object serialization to XML for logging. XStream with `AnyTypePermission` (line 3 import visible in `DomainHelper.java`) is the most permissive XStream configuration and disables deserialization protection — relevant for `CVE-2024-47072`.

11. **Spring XML configuration**: Approximately 600+ lines across `accountmanagementapi-implContext.xml`, `accountmanagementapi-wsContext.xml`, `validation.xml`, `validator.xml`, `appCtx-core.xml`, `monitor.xml`. No `@Configuration` classes. Upgrade to Spring Boot would require full rewrite of this wiring.

12. **`Thread.sleep` in test mode** (`AccountManagementApiServiceImpl.java` lines 116–120): `testAPI` feature allows injecting sleep delays — this is a debug/QA mechanism with no access control gate. If enabled accidentally in production, it could cause widespread request timeouts.

13. **Typo in log message**: `AccountManagementApiServiceImpl.java` line 445: `"mssage_id="` — missing `e`. Minor, but indicates low code review thoroughness.

### Low
14. **`kycStatusInsertUpdateSP` static field** in `AMPayoutHelper.java` (line 33): `private static KYCStatusInsertUpdateSP kycStatusInsertUpdateSP` — static mutable state injected via a non-static setter. This creates a singleton-scope data race risk if multiple bean instances were created.

15. **Empty catch blocks**: `ActivateCardService.execute()` line 76 catches `Exception` but only logs at `debug` level (`log.debug("Error while updating card Status")`). Error detail may be lost.

---

## Gen-3 Migration Requirements

To modernize this service to a Gen-3 REST/cloud-native architecture, the following must be addressed:

### Must Have
1. **Replace Apache Axis 1.4 SOAP with REST (HTTP/JSON)**: Define OpenAPI 3.x spec for the three active operations. Maintain backward compatibility via a SOAP-to-REST adapter if mobile clients cannot be updated simultaneously.
2. **Replace `ServletEndpointSupport` with Spring Boot `@RestController`**: Eliminate manual bean lookup pattern.
3. **Spring Boot migration**: Replace all XML `ApplicationContext` wiring with `@Configuration` and `@SpringBootApplication`. Migrate `PropertyPlaceholderConfigurer` to Spring Boot `application.properties` / externalized ConfigMaps.
4. **Secret management**: Move `jwe.secretKey`, `kyc.ms.client.secret`, DB credentials from flat properties files to Azure Key Vault or Kubernetes Secrets. Remove plain-text config file dependency.
5. **Re-enable authorization**: Implement program-level authorization (currently commented out) using a Gen-3 auth mechanism (e.g., JWT bearer token with program claim validation).
6. **Log data masking**: Mask DDA numbers and card numbers in all log statements before shipping to log aggregation.

### Should Have
7. **Replace eCore RPC with modern API**: PIN set and card activation use `ECount.System.RPC` — this must have a REST or gRPC equivalent. May require a Gen-3 eCore adapter layer.
8. **Externalize KYC integration**: Extract KYC portal call into a dedicated KYC microservice or client library with its own SLA and circuit breaker.
9. **Circuit breaker / retry**: Wrap eCore RPC calls, Order Service JMS, and KYC portal calls with Resilience4j circuit breakers and exponential backoff.
10. **Resolve JIRA-476 dead code**: Formally decommission or migrate the 12 disabled operations. Each requires a product decision: permanently remove, migrate to Gen-3, or re-enable in Gen-2 with a migration path.
11. **Replace XStream with Jackson**: `DomainHelper` uses XStream for XML serialization; replace with Jackson or a structured logging approach to eliminate the deserialization risk.

### Nice to Have
12. **OpenTelemetry tracing**: Replace the custom `GlobalRequestIDInterceptor` + MDC pattern with OpenTelemetry distributed tracing (trace ID propagated from mobile app through all downstream calls).
13. **Contract testing**: The Pact client is already wired (`PACT_PACTICIPANT: account-management-payout-api`). Extend to cover all three active operations and enable provider verification.
14. **Update WSDL endpoint address**: Until SOAP is removed, the WSDL service address should be templated/filtered to reflect the actual deployment URL, not the hardcoded `wirecard.sys` dev host.

---

## Code-Level Risks

| Risk | Severity | Location | Description |
|---|---|---|---|
| Decrypted account number in INFO log | High | `AccountManagementHandlerImpl.java:100` | `log.info("Decrypted DDA : "+decryptedDDA)` — PCI DSS data leak in log stream |
| API authorization bypassed | High | `AccountManagementApiServiceImpl.java:148`, `SetPinService.java:43` | `validateAPISecurity()` commented out; no program-level authz on active operations |
| Plain-text CVV in SOAP | High | WSDL `activationStatusInquiryRequest`, `ActivateCardRequest` | `cvv` transmitted as `xsd:string` with no in-message encryption |
| Plain-text PIN in SOAP | High | WSDL `SetPinRequest` | `new_pin` transmitted as `xsd:string` |
| `XStream AnyTypePermission` | Medium | `DomainHelper.java:3` (import visible) | Deserialization with no type restrictions — CVE-2024-47072 vector if untrusted XML is deserialized |
| `SHA1PRNG` in crypto | Medium | `JWEHelper.java:363,382` | Legacy PRNG name; behavior platform-dependent on JDK 21 |
| `AESFastEngine` deprecated | Medium | `JWEHelper.java:275,504` | Deprecated BouncyCastle class; `bcprov-jdk15on` is legacy artifact |
| `ServletEndpointSupport` removal | High | `AccountManagementApiWebServiceImpl.java:17` | Removed in Spring 6; will break on framework upgrade |
| Static mutable singleton in `AMPayoutHelper` | Medium | `AMPayoutHelper.java:33` | `private static KYCStatusInsertUpdateSP` — race condition if re-instantiated |
| Tomcat downloaded at build time | Medium | `Dockerfile:8` | External URL dependency during Docker build; breaks in network-restricted CI environments |
| QA cert in production image | Medium | `Dockerfile:20-21` | `certfile_qa.crt` imported during build — if same image is used in production, trust store is widened |
| KYC `def = null` silent path | Medium | `ActivationStatusInquiryService.java:193-200` | On `KYCProcessException`, `def` set to null; response body populated from `finally` block but may also return partial data from the outer success path if not carefully controlled |
| Test mode no access control | Low | `AccountManagementApiServiceImpl.java:91-138` | `testAPI.isTestMode()` has no authentication gate — if misconfigured, artificial delays/failures injected in production |
| Empty debug catch | Low | `ActivateCardService.java:76-83` | `catch(Exception e)` logs at debug level only; production errors silently masked |
| Typo in log format | Low | `AccountManagementApiServiceImpl.java:445` | `"mssage_id="` should be `"message_id="` |
