# cambridge-service_LIB — Solution Architect View

## Technical Architecture

### Overview
`cambridge-service_LIB` is a single-module Maven JAR library (`com.citi.prepaid:CambridgeService:1.0-SNAPSHOT`). It provides a Java client over Cambridge FX Online's WCF/SOAP web services. The architecture follows a three-tier pattern within the library:

```
Layer 1 — Context / Configuration
  CambridgeServiceContext       (POJO config holder: credentials, proxy, algorithm)
  CambridgeServiceConstants     (interface: Axis2 repository path constant)
  appContext-CambridgeService.xml (Spring 2 XML IoC; PropertyPlaceholderConfigurer)

Layer 2 — Service Implementations (Facades)
  CambridgeServiceImpl          (aggregate facade: holds all four sub-services)
  SSOServiceImpl                (authentication: generate HMAC token)
  TradeServiceImpl              (FX rate, book deal, cancel, instruct payment)
  BeneficiaryServiceImpl        (beneficiary CRUD and validation rules)
  BankServiceImpl               (bank directory search and lookup)

Layer 3 — SOAP Stubs (auto-generated from WSDL, Axis2 1.7.5, May 2017)
  SSOServiceStub                → https://isbeta.cambridgefxonline.com/Service.svc/sso
  TradeServiceAPIStub           → https://isbeta.cambridgefxonline.com/API/ServiceAPI.svc/apiTrade
  BeneficiaryServiceAPIStub     → https://isbeta.cambridgefxonline.com/API/ServiceAPI.svc/apiBene
  BankServiceAPIStub            → https://isbeta.cambridgefxonline.com/API/ServiceAPI.svc/apiBank
  RegEDisclosureServiceAPIStub  → https://isbeta.cambridgefxonline.com/API/ServiceAPI.svc/apiRegEDisclosure

Layer 4 — Data Transfer Objects (auto-generated from WSDL)
  org.datacontract.schemas._2004._07.*  (Cambridge-specific JAXB/ADB beans)
  com.microsoft.schemas._2003._10.serialization.*  (WCF DataContract primitives)
  org.tempuri.*  (SOAP operation wrappers: GenerateLoginToken, BookDeal, etc.)
```

### Helper
`CambridgeServiceHelper` provides one static utility method: `getDigitalSignature()`, which concatenates credentials and timestamp then hashes with `java.security.MessageDigest`.

---

## API Surface

This library exposes no HTTP API. Its surface is a set of Java method calls:

### SSOServiceImpl
| Method | Signature | Returns |
|---|---|---|
| `generateSecurityToken` | `() throws NoSuchAlgorithmException, RemoteException` | `String` (bearer token) |

### TradeServiceImpl
| Method | Key Parameters | Returns |
|---|---|---|
| `getRate` | `String token, BigDecimal amount, LockSide lockSide, String paymentCurrency, String settlementCurrency` | `String` quoteId |
| `bookDeal` | `String token, String quoteID` | `String` orderNumber |
| `bookDeal` (overload) | `String token, String quoteID, String correlationId` | `String` orderNumber |
| `cancelDeal` | `String token, String quoteID` | `String` cancelDealNumber |
| `cancelDeal` (overload) | `String token, String quoteID, String correlationID` | `String` cancelDealNumber |
| `getCancelRate` | `String token, String dealNumber` | `String` quoteId |
| `instructPayment` | `String token, String beneficiaryID, String dealNumber, String paymentAmount, String paymentMethod` | `String` paymentInstructionId |
| `instructPaymentSettlement` | `String token, String beneficiaryID, String dealNumber, BigDecimal paymentAmount` | `String` paymentInstructionId or error string |

Note: `instructPayment` accepts `paymentAmount` as `String` but converts to `BigDecimal` internally; `instructPaymentSettlement` accepts it directly as `BigDecimal`. This inconsistency is a code-level defect.

### BeneficiaryServiceImpl
| Method | Key Parameters | Returns |
|---|---|---|
| `getDynamicValidationRules` | `String token, String countryISOCode, String currency` | `ValidationRuleSpec[]` |
| `createOrUpdateBeneficiary` | `String securityToken` | `String` beneficiaryId |
| `getBeneficiaryDetails` | `String token, String beneficiaryID` | `BeneficiaryCompleteResponse` |

Note: `createOrUpdateBeneficiary` hard-codes all beneficiary data inline (test data). This method is not production-ready.

### BankServiceImpl
| Method | Key Parameters | Returns |
|---|---|---|
| `searchBanks` | `String token, String searchStr, MatchCS criteria, String countryISOCode` | `Bank[]` |

### Stubs (not exposed via Impl layer)
The following operations are registered in stubs but have **no corresponding Impl method**:
- `TradeServiceAPIStub`: `bookTrade`, `getForwardQuote`, `getOrderDetails`, `getQuote`, `instructSettlement`, `searchOrders`, `sendPayment`
- `BeneficiaryServiceAPIStub`: `updateBeneficiary`, and several others beyond the three wired in `BeneficiaryServiceImpl`
- `RegEDisclosureServiceAPIStub`: `getRegEDisclosure`

These represent Cambridge capabilities that have been stubbed out but not exposed through the facade layer.

---

## Security Posture

### Strengths
1. **TLS enforced by WS-Policy**: Every SOAP operation in every stub has a WS-Policy `TransportBinding` with `HttpsToken` and `Basic256` algorithm suite attached. Cambridge will reject non-HTTPS connections.
2. **HMAC authentication**: Token generation uses `MessageDigest` with a configurable algorithm over a composite string including the shared secret and timestamp, preventing replay attacks (timestamp-bound).
3. **Externalized credentials**: `sharedSecretKey`, `cambridgeUserName`, and `returnURL` are injected via Spring properties, not hardcoded in source code.

### Weaknesses / Vulnerabilities

| Issue | Location | Severity | Detail |
|---|---|---|---|
| Algorithm not validated | `CambridgeServiceHelper.getDigitalSignature()` | HIGH | `algorithm` is passed through to `MessageDigest.getInstance(algorithm)` without any whitelist check. A misconfigured properties file with `algorithm=MD5` would silently use a broken hash. |
| Beta endpoint in default constructors | All five `*Stub` constructors | HIGH | Default `new SSOServiceStub()`, `new TradeServiceAPIStub()`, etc. all target `isbeta.cambridgefxonline.com`. Any service that instantiates stubs without explicit endpoint override is connected to a sandbox. |
| Hardcoded beneficiary ID in production source tree | `App.java` line 157, `BeneficiaryServiceImpl.createOrUpdateBeneficiary()` line 109, 122 | MEDIUM | UUID `873f8ed7339e4178a3c0983f656cd38d` present as a string literal. Even as test/demo data, this is a real identifier that should not be in the source tree. |
| No token expiry management | `SSOServiceImpl` | MEDIUM | Token is generated once per application startup in `App.java`. No refresh logic or expiry check. If the token expires during a session, all subsequent calls will fail without context. |
| Raw account/routing numbers transmitted | `BankAccountInformation` | MEDIUM | Full bank account and routing numbers passed unmasked in SOAP XML. No tokenisation. |
| Proxy credentials via JVM system property | `App.java` lines 68–69 | LOW-MEDIUM | `System.getProperties().put("http.proxyHost", ...)` sets JVM-wide properties, potentially affecting other threads or library code. |
| No input sanitisation | All Impl classes | LOW | Inputs (country code, currency, beneficiary name) passed directly to SOAP with no sanitisation or length validation. Malformed inputs will produce SOAP faults rather than clean validation errors. |
| `java.util.HashMap` (raw type) in stubs | All stub classes | LOW | Raw `HashMap` usage without generics in fault mapping. Not a security issue but indicates Java 1.4 era code style. |
| No mutual TLS | WS-Policy `RequireClientCertificate="false"` in all stubs | LOW | Server certificate is validated but client does not present a certificate. One-way TLS only. |

### No Authentication on Library Consumer Side
The library itself performs no authentication of callers — it is a library, not a service. The consuming application must implement its own access controls to govern which callers may trigger payment operations.

---

## Technical Debt

### Critical Debt
| Item | Evidence | Impact |
|---|---|---|
| EOL Spring 2.0.3 | `pom.xml` line 22 | Known CVEs; incompatible with modern Spring ecosystem; prevents Spring Boot adoption |
| EOL Apache Axis2 1.7.5 | `pom.xml` lines 27–58 | Known XXE and deserialization CVEs; replaced by CXF, Spring WS, or REST clients in modern stacks |
| EOL JUnit 3.8.1 | `pom.xml` line 14 | Pre-annotation test harness; incompatible with JUnit 5 runners; virtually no test tooling |
| Windows-only filesystem paths | `CambridgeServiceConstants.java` line 5, `appContext-CambridgeService.xml` line 9 | Prevents Linux/Docker deployment entirely |
| Version permanently SNAPSHOT | `pom.xml` line 7 | No release history; non-deterministic dependency resolution |

### Significant Debt
| Item | Evidence | Impact |
|---|---|---|
| No interfaces on service classes | All `*ServiceImpl` classes | Cannot mock without bytecode manipulation; prevents unit testing |
| `createOrUpdateBeneficiary` not parameterised | `BeneficiaryServiceImpl.java` lines 72–132 | Method hard-codes all beneficiary fields inline; completely unusable for production |
| `instructPayment` amount as String | `TradeServiceImpl.java` line 215 | `String paymentAmount` converted to `BigDecimal` internally; risk of `NumberFormatException` on invalid input; inconsistent with `instructPaymentSettlement` which takes `BigDecimal` |
| Raw types in stub fault maps | All stubs, e.g. `BankServiceAPIStub.java` line 15 | `HashMap` without generics; Java 1.4 style; compiler warnings suppressed with `@SuppressWarnings` |
| Commented-out production Spring bean config | `appContext-CambridgeService.xml` lines 30–34 | ConfigContext factory bean is commented out; the in-use default stub constructors will fail if `AXIS_REPOSITORY` path does not exist |
| No null checks on `App.java` service results | `App.java` lines 86–162 | `getRate` returns `null` on exception; `bookDeal` receives `null` as `quoteId` without check |

### Minor Debt
| Item | Evidence | Impact |
|---|---|---|
| `printStackTrace()` instead of logging | `App.java` throughout | No structured error logging |
| Demo/test code in main source tree | `App.java` | Pollutes JAR; could be accidentally executed |
| Stub comment header copyright | All stubs: "auto-generated from WSDL by Apache Axis2 version: 1.7.5 Built on: May 06, 2017" | Confirms 8+ year old generated code; no refresh |
| Axis2 repository hard path in interface | `CambridgeServiceConstants.java` | Constants defined in an interface (anti-pattern); single constant; should be enum or properties |

---

## Gen-3 Migration Requirements

To migrate this library's capabilities to a Gen-3 platform architecture, the following requirements must be met:

### 1. Replace SOAP with REST/JSON
Cambridge/Corpay Cross-Border currently offers a REST API. All five service domains (SSO, Trade, Beneficiary, Bank, RegE) should be re-implemented using a modern HTTP client (Spring WebClient, OpenFeign, or Apache HttpClient 5) consuming JSON. All SOAP stubs (`*Stub` classes) and WCF data contract types (`org.datacontract.*`, `com.microsoft.*`, `org.tempuri.*`) would be replaced by POJO DTOs and an OpenAPI-generated client.

### 2. Upgrade Spring Framework
Migrate from Spring 2.0.3 XML IoC to Spring Boot 3.x with:
- `@Configuration` / `@Bean` Java config replacing `appContext-CambridgeService.xml`
- `@ConfigurationProperties` replacing `PropertyPlaceholderConfigurer`
- Spring profiles (`@Profile`) for environment targeting (dev/staging/prod)

### 3. Externalise All Configuration
- Endpoint URLs: move to application properties with per-environment override (Spring profiles or environment variables)
- Shared secret: move to HashiCorp Vault or AWS Secrets Manager, injected at runtime
- Remove all hardcoded filesystem paths

### 4. Add Service Interfaces
Extract interfaces from all four `*ServiceImpl` classes to enable:
- Unit testing with Mockito
- Multiple implementations (e.g., mock, live, retry-wrapper)

### 5. Implement Reg E Disclosure
Create `RegEDisclosureServiceImpl` to wrap `RegEDisclosureServiceAPIStub` (or its REST replacement), fulfilling the Reg E disclosure requirement for US international remittance transfers.

### 6. Parameterise `createOrUpdateBeneficiary`
The method must accept a `BeneficiaryComplete` (or equivalent DTO) parameter rather than hard-coding data inline. This is a prerequisite for any production use.

### 7. Add Observability
- Structured logging (SLF4J + Logback/Log4j2) with request/response logging, correlation IDs, masked sensitive fields
- Metrics (Micrometer → Prometheus) for call counts, latencies, error rates per operation
- Distributed tracing (OpenTelemetry) correlating Cambridge API calls with upstream request context

### 8. Add Resilience
- Configurable HTTP timeouts (connect, read, write)
- Retry policy with exponential backoff for transient errors
- Circuit breaker (Resilience4j) to prevent cascading failure on Cambridge API unavailability
- Token refresh: detect token expiry and re-authenticate transparently

### 9. Add Unit and Integration Tests
- Unit tests for `*ServiceImpl` classes using mocked stubs (minimum 80% coverage)
- Integration/contract tests against Cambridge sandbox endpoint
- GitHub Actions CI workflow running tests on every PR

### 10. Fix Type Inconsistency
- `instructPayment` should accept `BigDecimal` for `paymentAmount` (not `String`)
- Remove hard-coded correlation between `paymentMethod` and `PaymentMethod.WIRE`; accept as a parameter to support EFT and other methods

---

## Code-Level Risks

### Risk 1: Silent Payment to Wrong Environment
`TradeServiceAPIStub()` default constructor (line 342): `this(ConfigurationContextFactory.createConfigurationContextFromFileSystem(CambridgeServiceConstants.AXIS_REPOSITORY), "https://isbeta.cambridgefxonline.com/API/ServiceAPI.svc/apiTrade")`. A consuming service that omits explicit endpoint configuration sends all transactions to the Cambridge beta environment. There is no runtime warning or assertion.

### Risk 2: Axis2 Addressing Module Failure Masks Errors
Every service call calls `stub._getServiceClient().engageModule("addressing")`. If the Axis2 repository is absent or the MAR file is missing, this throws `AxisFault`. In `App.java`, this is caught by the top-level `catch (Exception e)` and printed then swallowed. Payment instructions will silently fail.

### Risk 3: `instructPaymentSettlement` Error Handling Returns Error String as Success
`TradeServiceImpl.java` lines 263–264:
```java
if(!response.getInstructPaymentSettlementResult().getOperationStatus().getSuccess()){
    return response.getInstructPaymentSettlementResult().getOperationStatus().getErrors().getString().toString();
}
```
This returns an error string from a `String`-returning method rather than throwing an exception. Callers receiving a non-null return value cannot distinguish success from failure without parsing the string, risking silent payment failures.

### Risk 4: Null Propagation in App.java Demo Flow
`getRate()` returns `null` on `RemoteException` (line 130). `bookDeal(tokenStr, quoteId, ctx)` then passes `null` as `quoteId`. `instructPayment` then passes `null` as `dealNumber`. These would trigger a `NullPointerException` or a SOAP fault. This flow defect is in the main source tree, not in a test.

### Risk 5: `MessageDigest.digest(string.getBytes())` Without Charset
`CambridgeServiceHelper.java` line 49: `md.digest(string.getBytes())` uses the platform default charset. On Windows (ISO-8859-1) vs. Linux (UTF-8), the same input string could produce different digests, causing authentication failures when the library is deployed cross-platform.

### Risk 6: Static Mutable Counter in Stubs
All stubs contain a `private static int counter = 0` with `synchronized` increment for unique service names. Under concurrent use in a multi-threaded application server, this could be a bottleneck. More critically, the reset logic (`if (counter > 99999) counter = 0`) wraps around, potentially generating duplicate service instance names during high concurrency.

### Risk 7: `HashMap` Fault Maps Never Populated
`populateFaults()` in all stubs is empty (e.g., `BankServiceAPIStub.java` lines 72–77). SOAP faults from Cambridge will not be mapped to typed Java exceptions and will propagate as generic `AxisFault`, losing fault type information.

### Risk 8: Uncommitted `RegEDisclosureServiceAPIStub` Index Bug
`RegEDisclosureServiceAPIStub.getRegEDisclosure()` line 134: `_operationClient = _serviceClient.createClient(_operations[1].getName())`. The `populateAxisService()` method only registers one operation at `_operations[0]`. Accessing `_operations[1]` will throw `ArrayIndexOutOfBoundsException` at runtime. The RegE operation cannot be called without fixing this index.
