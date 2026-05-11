# card-notification-restful_API — Solution Architect View

## Technical Architecture

### Module Structure
```
card-notification (pom, v3.0.1-SNAPSHOT)
├── card-notification-ws (JAR) — Business logic, models, JAX-RS resources
│   ├── com.ecount.model        — SMS_MO, SMS_MT, PARAMETERS, MobilResponses, OperatorInformationDetails, Operator_Code
│   └── com.ecount.services     — All service, DAO, interceptor, and utility classes
│       └── cardnotification.config — Ehcache/JCache configuration (Config.java)
├── card-notification-war (WAR) — Legacy Tomcat packaging
│   └── WEB-INF/web.xml, applicationContext.xml, dataSourcesContext.xml
└── card-notification-boot (Spring Boot fat JAR) — Modern K8S packaging
    └── com.citi.prepaid.cardnotification — Boot app, Java-config translations of legacy XML
        ├── config/              — DataSourcesConfig, ECountSystemConfiguration, JerseyConfiguration, LegacyXmlConfig, WebConfiguration
        ├── datasources/         — CbaseApp, EcountSvc, JobSvc DataSource auto-configurations
        └── health/              — HealthCheck @RestController
```

### Runtime Architecture
- **Spring Boot 3.5.7** embedding Jersey (JAX-RS 3.x) as a servlet on path `/Cardnotification/*`
- Jersey servlet registered programmatically via `JerseyConfiguration.jerseyServlet()` — `ServletRegistrationBean<ServletContainer>`
- Spring MVC `DispatcherServlet` handles remaining paths (health check, actuator)
- All legacy Spring XML beans reproduced as Java `@Configuration` in the Boot module (`LegacyXmlConfig`, `DataSourcesConfig`, `WebConfiguration`, `ECountSystemConfiguration`)
- `AppContextListener` sets `CardNotificationUtils.springctxt` on servlet init so that legacy code can access the Spring context statically
- Three `DataSource` beans, each wrapped in `TransactionAwareDataSourceProxy`: `CbaseappDataSource`, `EcountSvcDataSource`, `JobSvcDataSource`

---

## API Surface

### Inbound Endpoints

| Method | Path | Content-Type | Auth | Description |
|---|---|---|---|---|
| `GET` | `/Cardnotification/CardnotificationService` | — | None | Returns all messages (XML); `cardNotificationModelRequest.getAllMessages()` |
| `POST` | `/Cardnotification/CardnotificationService` | `application/x-www-form-urlencoded` | None | Production SMS MO handler; decodes `XmlMsg=<SMS_MO XML>`, processes, sends MT to Sinch |
| `POST` | `/Cardnotification/CardnotificationService/Internal` | `application/x-www-form-urlencoded` | None | Internal test path; echoes MT response as URL-encoded string instead of forwarding to Sinch |
| `GET` | `/hc` | — | None | Health check; returns `"OK"` |
| `GET` | `/actuator/health` | — | None | Spring Actuator health |
| `GET` | `/actuator/info` | — | None | Spring Actuator info |
| `GET` | `/myresource` | — | None | Stub resource; returns `"Got it!"` — leftover scaffold code in `MyResource.java` |

### Outbound Calls

| Target | Method | Auth | Path |
|---|---|---|---|
| ECount Director (xSearch XMLRPC) | HTTP POST | None visible | `{director.address}` |
| ECount Director (EDevice processInquiry) | HTTP POST | None visible | `{director.address}` |
| Sinch SMS MT | HTTPS POST | HTTP Basic (`sapMtusername`/`sapMtpassword`) | `{cardnotification.sapmturl}` |

### OpenAPI Contract
`openapi.json` is present at the repo root and describes only the main POST endpoint. It is manually authored, not generated from annotations. The schema shows the `SMS_MO` XML payload embedded in a URL-form-encoded field named `incomingEncoded`, though the actual request parameter is extracted as `XmlMsg=` in `JaxRsCardNotificationService.processMO()` — the `openapi.json` and the code use different field names.

---

## Security Posture

### Inbound API Authentication
**None.** The `POST /Cardnotification/CardnotificationService` endpoint has no authentication, no API key, no IP allowlist, and no token validation. Any HTTP client that can reach the endpoint can submit arbitrary SMS_MO payloads. The only protection is network-level (APIM routing, AKS ingress rules — not visible in this repo).

### Log Injection Vulnerability (Partially Mitigated)
- `JaxRsCardNotificationService.sanitizeForLog()` escapes newlines (`\n`, `\r`) and HTML special characters in the URL-decoded payload before logging it
- However, this method is applied only to `urlDecodedStringList` (the XML body log line), not to `moRequest.getMSISDN()`, `moRequest.getMESSAGE()`, or `moRequest.getORIGINATING_ADDRESS()` which are also logged directly at INFO level
- Partial mitigation: the sanitized method exists but is not applied uniformly

### Credentials Management
- Database and Sinch credentials stored in Azure Key Vault — good
- `sapMtusername` and `sapMtpassword` are **static fields** in `JaxRsCardNotificationService`; they are set once at bean creation and cannot be dynamically refreshed without restart

### TLS
- `trustServerCertificate=true` in all JDBC connection strings disables certificate validation for SQL Server connections — a PCI DSS violation for data in transit
- Outbound Sinch calls use HTTPS with proper certificate validation (no equivalent flag)
- Internal CA cert (`nam.wirecard.sys.crt`) is imported into JRE truststore during Docker build

### String Comparison Bug (Carrier Detection)
`CardNotificationServiceImpl` lines 262, 274, 333, 355: carrier comparison uses `==` instead of `.equals()`:
```java
if (carrier == "TMobileFTEU" || carrier == "ATTFTEU") {
```
In Java, `==` on `String` compares object references, not content. Since `carrier` is populated by `convertedResponse.setCarrier("TMobileFTEU")` in `CardNotificationUtils`, both strings are compile-time literals. Whether this works depends on string interning. However, this is fragile and a latent defect — any code path that sets carrier to a non-interned string (e.g., read from a database or external source) will fail. FTEU subscribers may receive incorrect regulatory messages.

### Input Validation
- `CardNotificationServiceImpl`: validates action type against a fixed set of constants; unknown commands return an error SMS
- No input length validation on mobile number, carrier, or action type fields
- Mobile number extraction: `mobileNum.substring(2, 12)` — will throw `StringIndexOutOfBoundsException` if MSISDN is shorter than 12 characters (e.g., non-US numbers or malformed input)
- Null checks for `moRequest.getMESSAGE()` and `moRequest.getMSISDN()` are present; missing `PARAMETERS` would throw NPE at `moRequest.getPARAMETERS().getOPERATORID()` (lines 114, 253)

---

## Technical Debt

### Critical

| Issue | Location | Description |
|---|---|---|
| **String equality bug on carrier** | `CardNotificationServiceImpl` lines 262, 274, 333, 355 | `==` instead of `.equals()` for FTEU carrier comparison; latent correctness defect |
| **Unmasked PII in logs** | `JaxRsCardNotificationService` lines 113–116, 251–254; `CardNotificationUtils` line 153 | Full MSISDN (mobile number) logged at INFO without masking |
| **`trustServerCertificate=true` on all DB connections** | All `appsettings.json` files | Disables TLS cert validation for SQL Server — PCI DSS Req. 4 violation |
| **No inbound authentication** | `JaxRsCardNotificationService` | Any caller can submit SMS payloads |
| **MSISDN substring with no length guard** | `CardNotificationUtils` line 155 | `mobileNum.substring(2, 12)` will throw if MSISDN < 12 chars |

### High

| Issue | Location | Description |
|---|---|---|
| **Static ApplicationContext** | `CardNotificationUtils.springctxt` | Anti-pattern; prevents testability and breaks in non-servlet environments |
| **Static SAP credentials** | `JaxRsCardNotificationService.sapMturl/sapMtusername/sapMtpassword` | Static fields; credential rotation requires restart |
| **Stale brand references** | `messages.properties` | "North Lane", "MyPaymentVault", and old SAP UAT URL in production messages |
| **Hardcoded UAT URL in Internal test endpoint** | `JaxRsCardNotificationService.processMO_InternalTesting()` lines 302, 308 | `http://sms-pp.sapmobileservices.com/cmn/citi_uat_487792/citi_uat_487792.sms` hardcoded |
| **Duplicate HealthCheck classes** | `card-notification-boot/health/HealthCheck.java` and `card-notification-war/health/HealthCheck.java` | Both at `GET /hc`; the war version logs at ERROR level on every health check call |
| **`allow-bean-definition-overriding: true`** | `application.yml` line 25 | Hides configuration conflicts; should be false in production |
| **`allow-circular-references: true`** | `application.yml` line 26 | Signals architectural debt; circular dependency somewhere in context |
| **Ehcache persistence to `java.io.tmpdir`** | `ehcache.xml` | Unnecessary disk persistence configured for a heap-only cache |
| **Dual deployment paths** | Both `card-notification-boot` and `card-notification-war` modules | Adds maintenance burden; WAR path is still fully wired and deployed to a VM |

### Medium

| Issue | Location | Description |
|---|---|---|
| **Minimal test coverage** | `CardNotificationServiceImplTest` | Only 3 tests covering cache operations; no tests for `cardNotificationInquiry`, `processMO`, or any DAO |
| **Scaffold/dead code** | `MyResource.java` | JAX-RS resource returning `"Got it!"` — leftover from project scaffolding |
| **`urlParameters` dead variable** | `JaxRsCardNotificationService` lines 109, 246 | `String urlParameters = "param1=data1&param2=data2&param3=data3"` — never used |
| **`TODO` comments with `printStackTrace()`** | Multiple locations in `JaxRsCardNotificationService` | Exception swallowing with stack trace only; no structured error propagation |
| **Legacy XML spring config retained** | `card-notification-ws/src/main/resources/applicationContext.xml` | Duplicate bean definitions alongside Boot Java config; `ecountMethodCache` bean is commented out in XML but referenced in XML config |
| **Comment-only cache wiring in XML** | `applicationContext.xml` lines 24–29 | The `ecountMethodCache` bean is commented out in XML; in Boot it is provided by `Config.java`, but the AOP pointcut in `CardNotificationLoggingInterceptor` references the wrong package path (`com.ecount.services.cardnotification.CardNotificationServiceImpl` — this class does not exist; the actual class is `com.ecount.services.CardNotificationServiceImpl`) |
| **OpenAPI / code mismatch** | `openapi.json` vs `JaxRsCardNotificationService` | OpenAPI says field name is `incomingEncoded`; code extracts `XmlMsg=` from form body |
| **`cardNotificationModelRequest.getAllMessages()`** | `JaxRsCardNotificationService.moResponse()` | GET endpoint returns all stored SMS_MO messages — unclear what data is in scope and whether this is a data exposure risk |

---

## Gen-3 Migration Requirements

To migrate this service to a Gen-3 architecture (REST JSON, event-driven, cloud-native), the following work is required:

1. **Member Lookup API** — Replace `XSearchClientFactory.getClient(XMLRPC_Client)` with a REST/gRPC member search API. The `FindMemberByMobilPhone` operation must be available via a modern API.

2. **Account Data API** — Replace `EDevice.processInquiry()` (ECount Director RPC) with a REST account inquiry API that returns balance, journal, and definition data.

3. **Program Configuration API** — Replace `AffiliateService.getAffiliateForValue("SMSPULLENABLEDPROGRAMS", "Y")` (Hibernate query against `cbaseapp`) with a program configuration API or event-driven config cache.

4. **SMS Profile API** — Replace `AppSmsMsgProfileClass.retrieve()` (xplatform library) with a configurable message template service.

5. **Async SMS Processing** — Decouple inbound MO processing from outbound MT delivery using a message queue (e.g., Azure Service Bus). This prevents the inbound SAP/Sinch HTTP call from blocking while waiting for account data retrieval and MT delivery.

6. **Inbound Authentication** — Add JWT/OAuth2 bearer token validation or shared secret verification for the inbound POST endpoint (SAP/Sinch supports HMAC or header-based auth).

7. **Observability** — Add structured logging (MDC with masked mobile number), Micrometer metrics (request counts, latency histograms), and distributed trace propagation.

8. **PII Handling** — Mask mobile number in all log statements to last 4 digits; implement data retention policies for `sms_cardnotification_log` and `sms_cardnotification_profile`.

9. **Remove Static ApplicationContext** — Replace `CardNotificationUtils.getSpringContext().getBean("...")` with proper Spring dependency injection.

10. **Enable TLS certificate validation** — Remove `trustServerCertificate=true` from JDBC URLs and configure proper cert chain validation.

---

## Code-Level Risks

### Risk 1: NPE in processMO on missing PARAMETERS
`JaxRsCardNotificationService.processMO()` lines 113–114:
```java
log.info(" ... " + moRequest.getPARAMETERS().getOPERATORID());
```
If `PARAMETERS` is absent from the inbound XML (it is optional per the schema), `getPARAMETERS()` returns null and this throws `NullPointerException`. The `null` checks at line 125 only check `getMESSAGE()` and `getMSISDN()`, not `getPARAMETERS()`.

### Risk 2: AOP Pointcut Targets Non-Existent Class
`CardNotificationLoggingInterceptor` line 37:
```java
@AfterReturning("execution(public * com.ecount.services.cardnotification.CardNotificationServiceImpl.cardNotificationInquiry(..))")
```
The actual class is `com.ecount.services.CardNotificationServiceImpl` (no `.cardnotification.` sub-package). This pointcut will never match, meaning **the SMS audit log (`sms_cardnotification_log`) is never written** when the Boot application is running. The XML config in `applicationContext.xml` has the correct expression, so the WAR deployment does log correctly. This is a silent regression in the Boot module.

### Risk 3: Ehcache NullPointerException in getEcountCache
`CardNotificationServiceImpl.getEcountCache()` line 655:
```java
Object element = getCache().get(key);
```
If `this.cache` is null (not wired — the Boot `LegacyXmlConfig` does not set the cache on `cardNotificationService` because the comment says "XML referenced a cache bean named ecountMethodCache; it was commented out"), `getCache()` returns null and this throws NPE. The `Config.java` class provides an `ecountMethodCache` bean, but `LegacyXmlConfig.cardNotificationService()` does not inject it. Depending on whether auto-wiring picks it up by type, this may or may not work at runtime.

### Risk 4: ConcurrentHashMap Mutation Risk in CardNotificationMessageFactory
`CardNotificationMessageFactory` line 13:
```java
static Map<String, CardNotificationMessage> map = new ConcurrentHashMap<...>();
```
The map is `static` and non-final. Although it is populated in a `static {}` block, it is publicly accessible via `getMessageProcessor`. No modification methods are exposed, but the static reference itself could be reassigned in tests.

### Risk 5: Race Condition in processMO — cardNotifService Assignment
`JaxRsCardNotificationService.processMO()` line 148:
```java
cardNotifService = (CardNotificationService) CardNotificationUtils.getSpringContext().getBean("cardNotificationService");
```
`cardNotifService` is an **instance field** but is reassigned on every request from the static Spring context. Under concurrent requests, different threads may overwrite each other's reference. This is harmless only because all threads ultimately get the same singleton bean, but it is an unnecessary and unsafe pattern.

### Risk 6: URL Construction in encodeData Prepends `+1`
`CardNotificationUtils.encodeData()` line 219:
```java
dataMap.put("List", "+1" + (data.getMSISDN()));
```
The `+1` US country code is unconditionally prepended. For FTEU or international numbers this produces a malformed MSISDN in the outbound MT message.

### Risk 7: Missing docker-compose-test.yaml
The `code_cov_build.yml` workflow references `docker-compose-test.yaml` in `card-notification-war/`, which does not exist in the repository. This means the integration test step will fail (though `continue-on-error: true` prevents pipeline failure), and JaCoCo code coverage data from integration tests will be missing/empty.
