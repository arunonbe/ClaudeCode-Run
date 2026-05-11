# card-notification_API — Solution Architect View

## Technical Architecture

The service is a Java 8 WAR deployed to Apache Tomcat, exposing a single SOAP endpoint via Apache Axis 1.4 (JAX-RPC). Spring Framework 2.5.4 provides dependency injection, AOP advice, and JDBC support. There is no REST, no message queue, and no reactive/async processing.

### Layered Structure

```
Axis AxisServlet (web.xml: url-pattern /*)
  └─ JaxRpcCardNotificationService      extends ServletEndpointSupport
       └─ CardNotificationServiceImpl   implements CardNotificationService
            ├─ CardNotificationMemberValidator
            ├─ CardNotificationMessageFactory  (static ConcurrentHashMap)
            │    ├─ CardNotificationMessageBalance
            │    ├─ CardNotificationMessagePayment   extends AbstractCardNotificationMessage
            │    ├─ CardNotificationMessageTransaction  extends AbstractCardNotificationMessage
            │    └─ CardNotificationMessageHelp
            ├─ AccountJournalPaymentTxPredicate  (Apache Commons Collections Predicate)
            ├─ CardNotificationUtils             (static Spring context holder, formatters)
            └─ EHCache (cardnotification_cache)

AOP (Spring AOP + AspectJ @AfterReturning)
  └─ CardNotificationLoggingInterceptor
       └─ CardNotificationLogInsertDAO    extends StoredProcedure
            └─ dbo.sms_cardnotification_log_insert  (SQL Server stored proc)
```

### Servlet Container Configuration
- `web.xml` uses Servlet 2.3 DTD
- `AxisServlet` maps to `/*` — all requests handled by Axis
- Spring context loaded by `ContextLoaderListener` at startup
- `AppContextListener` stores `WebApplicationContext` in the static `CardNotificationUtils.springctxt` field — a static mutable singleton that creates thread-safety risk during concurrent context reload

## API Surface

### SOAP Operation
- **WSDL**: `src/main/resources/CardNotificationService.wsdl`
- **Namespace**: `http://ecount.com/cardnotification`
- **Service name**: `JaxRpcCardNotificationServiceService`
- **Port name**: `CardNotificationService`
- **Binding style**: RPC
- **Encoding**: SOAP encoding (`use="encoded"`) — deprecated per WS-I Basic Profile 1.1
- **Local address** (from WSDL): `http://localhost:9070/cardnotification/CardNotificationService`
- **CI health check address**: `http://{host}:9324/cardnotification/Cardnotification/CardnotificationService`

### Single Exposed Method
```
cardNotificationInquiry(CardNotificationRequest) -> CardNotificationResponse
```

**CardNotificationRequest** (`CardNotificationRequest.java`):
| Field | Type | Notes |
|---|---|---|
| `actionType` | String | BALANCE, PAYMENT, TRANSACTION, HELP (case-insensitive; uppercased in service impl line 129) |
| `mobileNumber` | String | Cardholder's registered mobile phone number — no format validation |
| `carrier` | String | SMS carrier identifier — passed through to response; not used in business logic |

**CardNotificationResponse** (`CardNotificationResponse.java`):
| Field | Type | Notes |
|---|---|---|
| `mobileResponses` | `MobileResponse[]` | One entry per valid matching member |

**MobileResponse** (`MobileResponse.java`):
| Field | Type | Notes |
|---|---|---|
| `programId` | String | Derived from member EBN; `"-"` on error |
| `mobileNumber` | String | Echo of request mobile number |
| `actionType` | String | Echo of request action type |
| `carrier` | String | Echo of request carrier |
| `smsData` | String | Formatted SMS text; null if message processor not found |
| `timestamp` | Date | Timestamp at response object construction |

### WSDD Registration (`server-config.wsdd`)
- Service `CardNotificationService`, provider `java:RPC`, style `rpc`
- Class: `com.ecount.services.cardnotification.JaxRpcCardNotificationService`
- `allowedMethods`: `*` (all public methods exposed)
- Axis `AdminService` has `enableRemoteAdmin=false`
- **No authentication handler in the service request flow chain** — the `Authenticate` and `Authorize` handlers are declared globally but not wired into any `requestFlow` for the `CardNotificationService` service definition

## Security Posture

### Authentication & Authorization
- **None configured**: The `CardNotificationService` in `server-config.wsdd` has no `requestFlow` element with authentication or authorization handlers. Any client that can reach the network endpoint can call the service.
- Axis `AdminService` correctly disables remote admin (`enableRemoteAdmin=false`)
- Session timeout is 5 minutes (`web.xml` line 63) but sessions are not used for the stateless SOAP service

### Transport Security
- No HTTPS/TLS configuration present anywhere in the repository
- WSDL endpoint uses plain `http://`
- Protocol variable in CI is `http` (`.gitlab-ci.yml` line 9)
- PII (mobile phone numbers) and the SOAP envelope containing member-correlated data traverse the network unencrypted

### Input Validation
- `mobileNumber`: No validation in `CardNotificationRequest.java` or in `CardNotificationServiceImpl`. Any string is accepted, used as a cache key (`CACHE_KEY_MOBILE + mobileNumber`), and forwarded to xSearch. A sufficiently long or specially crafted string could poison the cache or cause issues at the downstream XML-RPC layer.
- `actionType`: `EcountUtils.toUpperCase()` is applied (line 129), but unrecognised action types simply result in `messageProcessor = null` (line 248–252 in `CardNotificationServiceImpl`) and `smsData = null` — no error is returned, which is a silent failure mode.
- `carrier`: No validation; passed through to response unchanged.

### PAN Handling
- Full card number retrieved from `MemberInquiryValue` and held in memory/disk EHCache for up to 14 days
- Masked to last-4 via `EcountUtils.getLastFourDigitsCC()` before SMS text construction
- Full PAN never written to `sms_cardnotification_log` or SMS text — **correctly masked at the output boundary**
- **Risk**: Full PAN lives in the serialised Java object graph on EHCache disk (`java.io.tmpdir`) without encryption

### PII Logging
- Mobile number logged at INFO level on every inbound request (`JaxRpcCardNotificationService.java` line 42)
- No log masking or truncation of mobile numbers

### Known Hardcoded Secret
- `server-config.wsdd` line 5: `<parameter name="adminPassword" value="admin" />` — default Axis admin password left in place. Although `enableRemoteAdmin=false` limits exposure, the password is hardcoded and trivially known.

## Technical Debt

| Item | Location | Severity | Notes |
|---|---|---|---|
| Apache Axis 1.4 EOL (2006) | `pom.xml` line 96 | Critical | SOAP runtime with no security patches for ~20 years |
| log4j 1.2.17 EOL with CVE-2019-17571 | `pom.xml` line 147 | Critical | SocketServer deserialization RCE if socket appender enabled |
| Spring 2.5.4 EOL (2013) | `pom.xml` line 39 | High | 15+ years behind; Spring Security ecosystem absent |
| SOAP RPC-encoded style | `CardNotificationService.wsdl` line 88 | High | `use="encoded"` is deprecated and non-WS-I compliant |
| Static Spring context singleton | `CardNotificationUtils.java` lines 32–39 | High | `static ApplicationContext springctxt` — not thread-safe during context reload; anti-pattern |
| Service locator anti-pattern | `CardNotificationServiceImpl.java` line 270; `CardNotificationMessageHelp.java` line 32 | Medium | `getSpringContext().getBean(...)` bypasses DI; hard to test and swap |
| Hard-coded affiliate app ID = 6 | `CardNotificationMessageHelp.java` line 34 | Medium | TODO comment left in place; incorrect CS phone for non-standard affiliate IDs |
| Hard-coded Citi Prepaid branding | `messages.properties` lines 1–4 | Medium | Wrong error messages for non-Citi programs |
| SNAPSHOT production dependency | `pom.xml` line 121 (`xSearch-client:2013.2.1-SNAPSHOT`) | Medium | Non-reproducible builds |
| JUnit 3.8.1 test framework | `pom.xml` line 58 | Medium | No assertions library, no mocking; test class uses `assertEquals` from JUnit 3 |
| All tests skipped in CI | `.gitlab-ci.yml` lines 15–17 | Medium | Zero automated test coverage enforced |
| EHCache 1.3.0 (2007) | `pom.xml` line 140 | Medium | Pre-JSR-107; no standard cache API; disk serialization without encryption |
| `allowedMethods=*` on SOAP endpoint | `server-config.wsdd` line 32 | Medium | All public methods of `JaxRpcCardNotificationService` are exposed |
| Default Axis admin password `admin` | `server-config.wsdd` line 5 | Low-Medium | Known default credential |
| Windows-hardcoded log4j path | `web.xml` line 19 | Low | `d:/c-base/config/...` |
| Servlet 2.3 DTD in web.xml | `web.xml` line 3 | Low | ~25-year-old deployment descriptor DTD |
| `AbstractDependencyInjectionSpringContextTests` base class | `CardNotificationServiceImplTest.java` line 9 | Low | Removed in Spring 4.0 |
| Balance format edge case (>$9999.99 loses cents) | `CardNotificationUtils.java` line 92 | Low | `setMaximumFractionDigits(0)` for large amounts |
| `bracket()` method wraps deviceId in `{...}` | `CardNotificationServiceImpl.java` line 422 | Low | Undocumented; reason for wrapping is not explained |

## Gen-3 Migration Requirements

To migrate this service to a Gen-3 platform (modern Spring Boot REST/JSON microservice), the following work is required:

### Protocol Replacement
- Replace Apache Axis / SOAP JAX-RPC with a REST/JSON endpoint (Spring Boot + Spring Web)
- Define OpenAPI 3.x specification replacing the hand-authored WSDL
- Update the SMS gateway (SAP or carrier aggregator) to call the new REST endpoint — **this is the primary external coordination dependency**

### Framework Upgrade
- Migrate from Spring 2.5.4 XML configuration to Spring Boot 3.x with annotation-based configuration
- Replace `AbstractDependencyInjectionSpringContextTests` with `@SpringBootTest`
- Replace `spring-mock:2.0.4` with Mockito + Spring Test
- Replace JUnit 3 with JUnit 5

### Platform Library Decoupling
- Audit and extract all usages of `com.cbase.*` classes (`EDevice`, `EMember`, `AccountJournal`, `AccountBalance`, `RequestContext`, `ReturnStatus`, etc.)
- Define clean domain model interfaces independent of cbase library
- Implement adapters to call Gen-3 equivalents of the account inquiry and member lookup services

### Caching Redesign
- Replace EHCache 1.3.0 with Spring Cache abstraction + Redis or Caffeine
- **Critical**: Never cache raw `MemberInquiryValue` objects containing full PANs — cache member identity tokens or masked references only
- Apply proper TTL aligned with business rules (e.g., 15-minute TTL for member status to prevent suspended-account access window)

### Security Hardening
- Add API authentication (mutual TLS or OAuth2 client credentials) at gateway or service level
- Enable HTTPS on all endpoints
- Remove mobile number from application logs, or apply masking (e.g., log only last 4 digits)
- Remove `adminPassword=admin` from any Axis remnants

### Message Template Externalisation
- Remove hard-coded Citi Prepaid branding from `messages.properties`
- Drive all error message text from the `app_sms_msg_profile` table (already used for success messages)

### Logging
- Replace log4j 1.x with SLF4J + Logback or log4j2
- Apply structured JSON logging compatible with current ELK pipeline (jsonevent-layout pattern preserved)

### Observability
- Add Spring Actuator health/liveness/readiness endpoints
- Add Micrometer metrics for request count, latency, cache hit/miss ratios

## Code-Level Risks

### Race Condition — Static Spring Context
`CardNotificationUtils.springctxt` is a `static` non-volatile field set by `AppContextListener.contextInitialized()`. If the context is reloaded concurrently (e.g., Tomcat hot-deploy), the static field could be observed as null or stale by other threads with no synchronization. (`CardNotificationUtils.java` lines 32–39)

### Silent Null Return on Unknown actionType
`CardNotificationMessageFactory.getMessageProcessor(actionType)` returns `null` for any unrecognised action type. In `CardNotificationServiceImpl.java` lines 248–252, the null check guards the `msg` assignment but `mobileResponse` is still added to the response with a null `smsData` field. The SMS gateway receives a well-formed response with no SMS text — a silent failure from the cardholder's perspective.

### NullPointerException Risk on `getEcountCache`
`CardNotificationServiceImpl.getEcountCache()` (line 426) calls `getCache().get(key)` without null-checking `this.getCache()`. If the `cache` bean fails to initialize (EHCache startup error), every call will throw a `NullPointerException` before reaching any business logic.

### Integer Overflow Risk in Balance Formatting
`CardNotificationUtils.getFormattedCurrencyAmount()` (line 80) accepts an `int` for the amount. eCount core stores balances as integer cents. If a program supports balances exceeding `Integer.MAX_VALUE` cents (~$21.4 million), silent integer overflow would produce incorrect balance values.

### `AccountJournalPaymentTxPredicate` — PAYMENT condition on sign only
`evaluate()` line 55 returns `true` for any journal entry with `amount > 0`. This could match non-payment credits (e.g., fee reversals, adjustments) as the "last payment" depending on journal entry typing in eCount core.

### `CardNotificationMessageHelp` — Integer parsing of affiliate ID
`getWebAppAffiliateId()` (line 47): `Integer.parseInt("1" + affiliateId)` — prepends "1" to the programId string. If `affiliateId` is null (possible if `EcountUtils.getProgramFromDDA()` returns null for an edge-case EBN), this throws a `NullPointerException`. If the resulting string exceeds `Integer.MAX_VALUE`, it throws `NumberFormatException`. No exception handling wraps this call in the public `getMessageByActionType()` method.

### EHCache `putEcountCache` — Unchecked Exception Swallowing
`CardNotificationLogInsertDAO.execute()` wraps the stored procedure call in a `try/catch(Throwable)` (line 61) that only logs the error and continues. A failed audit log insert is not surfaced to the caller — audit trail gaps will occur silently on DB failures.
