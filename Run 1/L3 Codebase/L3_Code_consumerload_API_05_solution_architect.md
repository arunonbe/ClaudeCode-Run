# consumerload_API — Solution Architect View

## Technical Architecture

The service is a two-module Maven project packaged as a WAR deployed to a Java Servlet 2.3 container (Tomcat).

```
consumerload (parent POM, version 1.0.0)
├── consumerload-ws  (WAR — web layer)
│   ├── com.citi.prepaid.consumerload.ws
│   │   ├── ConsumerLoadWebService         (java.rmi.Remote interface — SOAP contract)
│   │   └── ConsumerLoadWebServiceImpl     (extends ServletEndpointSupport — Axis entry point)
│   ├── com.citi.prepaid.consumerload.request   (WSDL2Java-generated request POJOs)
│   ├── com.citi.prepaid.consumerload.response  (WSDL2Java-generated response POJOs)
│   ├── com.citi.prepaid.consumerload.domain    (WSDL2Java-generated domain POJOs)
│   ├── com.citi.prepaid.consumerload.helper    (ValidationHelper, InputHelper, OutputHelper, ExceptionHelper)
│   ├── com.citi.prepaid.consumerload.validator (Validator, StringValidator, LongValidator, ArrayValidator)
│   ├── com.citi.prepaid.consumerload.type      (InputValidationType, ParameterValidatorType, ResponseStatusType)
│   └── com.citi.prepaid.consumerload.exception (ConsumerLoadException, InputValidationException, SystemFailureException)
│
└── consumerload-impl  (JAR — business logic)
    ├── com.citi.prepaid.consumerload.service
    │   ├── ConsumerLoadService<IN,OUT>    (abstract base with KYC gate and member resolution)
    │   ├── LoadFundsUsingCCService        (CC load with fee calc, velocity, transfer)
    │   ├── GetCCLoadFeeService
    │   ├── GetACHInfoService
    │   ├── UpdateKYCInfoService
    │   ├── CheckKYCStatusService
    │   └── GetDefaultCreditCardService
    ├── com.citi.prepaid.consumerload.helper
    │   ├── AccountHelper                  (PUID lookup, device mgmt, credit card ops, KYC)
    │   ├── ProfileHelper                  (program profile, strategy, KYC feature flag)
    │   └── CommentHelper                  (audit comment writing)
    ├── com.citi.prepaid.consumerload.type (CLConstants, type objects)
    └── com.citi.prepaid.consumerload.exception (ConsumerLoadImplException, ServiceFailureException)
```

**Request processing flow** (per operation):
1. Axis `AxisServlet` deserializes SOAP XML → `ConsumerLoadWebServiceImpl` method
2. `ValidationHelper.populateParameters()` → `HashMap` of field values
3. `IValidator` bean(s) from Spring context validate each field via regex
4. `InputHelper.populate*Input()` maps domain objects to `ServiceInput` subclass
5. Service bean (e.g., `LoadFundsUsingCCService.execute()`) performs business logic
6. `OutputHelper.populate*Response()` maps service output to response POJO
7. Axis serializes response → SOAP XML

## API Surface

**Protocol**: SOAP 1.1 / JAX-RPC over HTTP  
**Endpoint base**: `/services/ConsumerLoadService` (Axis mapping via `web.xml`)  
**WSDL namespace**: `http://ws.consumerload.prepaid.citi.com`

| Operation | Request Class | Response Class | Key Request Fields | Key Response Fields |
|---|---|---|---|---|
| `loadFundsUsingCC` | `LoadFundsUsingCCRequest` | `LoadFundsUsingCCResponse` | partner_user_id, program_id, amount (long, cents), cvv, creditCard (optional), transactionId | code, message, description |
| `getCCLoadFee` | `GetCCLoadFeeRequest` | `GetCCLoadFeeResponse` | partner_user_id, program_id, loadAmount | code, message, fee (int) |
| `getACHInfo` | `GetACHInfoRequest` | `GetACHInfoResponse` | partner_user_id, program_id | code, accountNum, routingNum, maxLoadLimit, minLoadLimit |
| `updateKYCInfo` | `UpdateKYCInfoRequest` | `UpdateKYCInfoResponse` | partner_user_id, program_id, kycInfo (BasicKYCInfo + SecureKYCInfo), checkKYC (boolean) | code, message |
| `checkKYCStatus` | `CheckKYCStatusRequest` | `CheckKYCStatusResponse` | partner_user_id, program_id | code, kycStatus (string) |
| `getDefaultCreditCard` | `GetDefaultCreditCardRequest` | `GetDefaultCreditCardResponse` | partner_user_id, program_id | code, cardNumber (masked), cardType, expYear |

**Common base request**: `CLServiceRequest` — `partner_user_id` (String), `program_id` (String), `keyValues` (KeyValue[]).  
**Common base response**: `CLServiceResponse` — `code` (int: 0=success, 2=failed, 999=system failure), `message` (String), `description` (String), `keyValues` (KeyValue[]).

**Axis type descriptors** are registered via static initializers in each WSDL2Java class (e.g., `LoadFundsUsingCCRequest.typeDesc` — line 198). Custom serializers/deserializers use `BeanSerializer` / `BeanDeserializer`.

## Security Posture

### Authentication & Authorization
- **None implemented at the application layer.** `ConsumerLoadWebService` has no authentication filter, no Spring Security configuration, and no token validation. Any client that can reach the HTTP endpoint can call any operation with any `partner_user_id` / `program_id` combination.
- The only access control is network-level (firewall / reverse proxy — outside this repository).

### Input Validation
- Regex-based Spring bean validators (`StringValidator`, `LongValidator`) configured in `validator.xml`.
- `PARTNER_USER_ID`: `[A-Za-z0-9-]{1,40}`
- `PROGRAM_ID`: `[0-9]{8}`
- `CARD_NUMBER`: `[0-9]{1,16}` — note upper bound of 16 digits is correct for most cards but accepts 1-digit numbers.
- `CVV`: `[0-9][0-9][0-9]` — exactly 3 digits (does not accept 4-digit Amex CVV).
- `EXP_YEAR`: `[2][0][1-9][1-9]` — regex bug: matches 2011–2019 and 2021–2029 etc., but **rejects 2020** (the `[1-9]` in position 3 excludes `0`). Also excludes 2030–2099 (position 4 `[1-9]` excludes `0`).
- Luhn validation: `CreditCardValidator` from `com.cbase.business.validation` — correct.
- DOB validation: `BirthDateValidator` from `com.cbase.business.validation` — called in `ValidationHelper.validateDOB()`.
- SSN format check: `ssnValidator` regex `[0-9]{9}` present in `validator.xml`, but the `validateSSN()` method with structural SSN validation is commented out.

### Sensitive Data Exposure
- **CVV in SOAP request**: `LoadFundsUsingCCRequest.cvv` is a top-level field in the SOAP message body, transmitted in plaintext.
- **PAN in SOAP request**: `CreditCard.cardNumber` is in the SOAP body.
- **SSN and DOB in SOAP request**: `SecureKYCInfo.dob` and `SecureKYCInfo.ssn` in `UpdateKYCInfoRequest`.
- **Full bank account + routing in SOAP response**: `GetACHInfoResponse.accountNum` and `routingNum` returned unmasked.
- **XStream debug logging of full objects**: `print(Object)` method in `ConsumerLoadWebServiceImpl` (line 237) and `ConsumerLoadService` (line 51) serializes entire request/response objects to XML for logging. At DEBUG level this writes PAN, CVV, SSN, DOB to log files.
- **Session IP hardcoded**: `AccountHelper.updateCreditCard()` line 196 and `createCreditCard()` line 210 set `coreSession.setIpAddress("127.0.0.1")` — the actual client IP is never captured.

### Transport Security
- No TLS/SSL configuration in `web.xml` or any Spring config. No `<security-constraint>` elements requiring HTTPS. Entirely dependent on server-level SSL termination.

## Technical Debt

| Issue | Location | Severity | Description |
|---|---|---|---|
| EOL Java 6 | `pom.xml` line 49–50 | Critical | Java 6 EOL 2013; no security patches; incompatible with modern TLS |
| EOL Apache Axis 1.4 | `pom.xml` dependency | Critical | Multiple CVEs; SOAP/JAX-RPC deprecated since Java EE 6 (2009) |
| EOL Spring 2.0.8 | `pom.xml` `spring.version=2.0.8` | Critical | Spring 2.x EOL; no security patches; Spring Security not present |
| EOL Log4j 1.2.15 | `consumerload-ws/pom.xml` line 59 | High | Log4j 1.x EOL with known CVEs |
| EOL XStream 1.3.1 | `pom.xml` `xstream.version=1.3.1` | High | Deserialization CVEs in early XStream versions |
| SSN validation commented out | `ValidationHelper.java` line 159 | High | `//throw new InputValidationException(...)` after `validateSSN()` call removed |
| EXP_YEAR regex bug | `validator.xml` line 111 | High | `[2][0][1-9][1-9]` rejects year 2020 and years ending in 0 (2030, 2040…) |
| PAN/CVV in debug logs | `ConsumerLoadWebServiceImpl` lines 30, 59, 87, 120, 167 | High | XStream serialization of full request objects to logger |
| Service Locator anti-pattern | `ConsumerLoadWebServiceImpl` lines 33, 41, 69, 98, 126–136, etc. | Medium | `getWebApplicationContext().getBean("...")` throughout; not injectable, untestable |
| Hardcoded Windows file paths | `consumerload-wsContext.xml` line 8; `web.xml` line 24 | Medium | Prevents containerization; environment-specific; not portable |
| Hardcoded IP address `127.0.0.1` | `AccountHelper` lines 196, 210 | Medium | `coreSession.setIpAddress("127.0.0.1")` — actual client IP not forwarded to eCore |
| Hardcoded IP constant unused | `CLConstants.java` line 4 | Low | `IP_ADDRESS = "123.123.123.123"` defined but never used |
| No authentication | `web.xml`, `ConsumerLoadWebServiceImpl` | Critical | No SOAP WS-Security, no HTTP Basic, no token auth |
| No test coverage | Entire repo | High | Zero unit or integration tests |
| Commented-out service bean registrations | `consumerload-wsContext.xml` lines 26–31 | Medium | Dead XML code; maintenance confusion |
| `address2` mapped twice in `InputHelper` | `InputHelper.java` line 118 | Low | `kycType.setAddress2()` called twice; second call overwrites first |
| Maven compiler plugin version 2.0.2 | `pom.xml` line 46 | Medium | Extremely outdated; should be at least 3.x |
| Dual VCS (.svn + .git) | Repository root | Medium | Operational confusion about authoritative version control system |

## Gen-3 Migration Requirements

To migrate this service to a Gen-3 architecture (Spring Boot, REST/JSON, containerized, cloud-native):

### Must-Have (blockers)
1. **Replace Apache Axis SOAP with Spring MVC REST controllers** (or Spring Boot `@RestController`). The six SOAP operations become six REST endpoints (e.g., `POST /consumer-load/funds`, `GET /consumer-load/cc-fee`, etc.).
2. **Replace WSDL2Java-generated domain classes** with clean POJOs using Jackson annotations. All 15 domain/request/response classes need rewriting.
3. **Replace Spring XML configuration with Spring Boot auto-configuration**. All seven Spring XML context files become a single `application.yml` + `@Configuration` classes.
4. **Externalize configuration**: Replace `D:/c-base/config/ConsumerLoad/ConsumerLoad.properties` with Spring Boot `application.yml` + environment variables + a secrets manager (e.g., HashiCorp Vault, AWS Secrets Manager).
5. **Replace cbase SDK calls**: Map each `AccountHelper`, `ProfileHelper`, and `CommentHelper` method to the equivalent Gen-3 platform API (REST or gRPC). This is the largest effort and requires platform API documentation.
6. **Implement authentication**: Add OAuth 2.0 / JWT bearer token validation (or mTLS) at the API gateway or service level.
7. **Fix CVE-laden dependencies**: Upgrade Java (17 LTS minimum), Spring Boot (3.x), replace Axis, replace XStream, replace Log4j 1.x.

### Should-Have
8. **Containerize**: Add `Dockerfile` and Kubernetes manifests. Remove all absolute file path assumptions.
9. **Add structured logging**: Replace Log4j 1.x with Logback / SLF4J; add JSON log format; sanitize sensitive fields before logging (mask PAN to last 4, remove CVV, mask SSN).
10. **Add unit and integration tests**: Minimum 80% coverage; mock eCore SDK calls via interfaces.
11. **Fix EXP_YEAR validator bug**: Replace regex with proper date comparison logic.
12. **Re-enable SSN validation**: Restore `SsnValidator.isValid()` call in the update-KYC path.
13. **Mask bank account number in response**: Return only last 4 digits of `accountNum`.
14. **Capture real client IP**: Pass actual remote IP to eCore sessions, replacing hardcoded `127.0.0.1`.

### Nice-to-Have
15. **Add idempotency**: Use `transactionId` as an idempotency key with a short-lived cache to prevent duplicate CC loads.
16. **Add observability**: Micrometer metrics, Spring Boot Actuator health endpoints, distributed tracing (OpenTelemetry).
17. **Add circuit breaker**: Resilience4j around eCore SDK calls to prevent cascade failures.

## Code-Level Risks

### Critical
- **`ConsumerLoadWebServiceImpl.print()` logs full SOAP objects at DEBUG** (line 237). If the log4j config enables DEBUG for this class in production, PAN, CVV, SSN, and DOB are written to disk. Log4j config is external; there is no application-side protection.
- **No authentication**: Anyone who can reach port 80/443 of the server can call `loadFundsUsingCC` and execute a CC-to-eCard transfer for any `partner_user_id` / `program_id` combination (subject to the card validation checks).

### High
- **`catch(Throwable e)` in `ConsumerLoadWebServiceImpl`** (lines 48, 78, 107, 157, 220): Catches `Throwable` (including `Error`), calls `ExceptionHelper.handleException()`. If `handleException` itself throws (e.g., due to a null response), the exception propagates to Axis which will generate a generic SOAP fault. No structured error codes.
- **`isKYCEnabled()` silently returns `false` on exception** (`ProfileHelper.java` line 111): The catch block sets `KYCEnabled = false` and swallows the exception. If the profile service is down, KYC checking is silently bypassed for all calls, allowing loads without identity verification.
- **`ServiceFailureException` constructor bug** (line 72–74): The three-arg constructor assigns `serviceFailureExceptionType = serviceFailureExceptionType` (self-assignment on the local parameter, not `this.serviceFailureExceptionType`). The exception type is lost for the `FAILED_TO_LOAD_FUNDS` exception variant.

### Medium
- **`GetCCLoadFeeService.execute()` swallows exceptions silently** (lines 29–33): If `getCreditCardLoadFee()` throws, the exception is caught, `e.printStackTrace()` is called, and the response is returned with the default fee value of 0. The caller receives a success response with a fee of 0, which could allow loads to proceed with incorrect fee calculations.
- **`GetACHInfoService.execute()` sets `FAILED` status and returns without throwing** (lines 38–42): On any exception in the ACH info retrieval, the method returns a `FAILED` response but does not propagate the error in a way that includes the failure reason.
- **`maskThefirst12NumbersCC()` off-by-one** (`GetDefaultCreditCardService` line 64): The loop runs `for (int i = 0; i < ccToMask.trim().length() - 3; i++)` — masks `length-3` characters, leaving 3 unmasked. But `unMaskedEnd` takes the last 4 characters (line 62). This means a 16-digit PAN returns 13 X's + last 4 = 17 characters (one extra X). The last character of the actual number before the last-4 is double-counted. For a 16-digit PAN: masks 13 chars, returns `XXXXXXXXXXXXX` + last 4 = 17 chars instead of the correct 12 X's + last 4 = 16 chars.
- **`expYearValidator` regex** `[2][0][1-9][1-9]` in `validator.xml` line 111: Year 2020 does not match `[1-9][1-9]` (the zero in '20' is not in `[1-9]`). Cards expiring 2020 were rejected. Years 2030, 2040, 2050, 2060, 2070, 2080, 2090 are also rejected. This is a live functional defect if cards with those expiry years are in use.
