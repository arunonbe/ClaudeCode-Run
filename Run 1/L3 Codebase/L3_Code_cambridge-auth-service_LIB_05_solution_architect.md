# cambridge-auth-service_LIB — Solution Architect View

## Technical Architecture

The library is a Maven-packaged JAR implementing a single-operation SOAP client for Cambridge FX Online SSO. It uses a Spring 4 XML application context for dependency injection and Apache Axis 1.4 for SOAP serialisation and transport.

**Class hierarchy:**

```
ICambridgeAuthService (interface)
  └── CambridgeAuthServiceImpl
        ├── AuthServiceContext           (config POJO)
        ├── CambridgeAuthServiceHelper   (static utility — digital signature)
        └── IServiceLocator (interface, extends javax.xml.rpc.Service)
              └── ServiceLocator (extends org.apache.axis.client.Service)
                    └── BasicHttpBinding_ISSOServiceStub
                          (extends org.apache.axis.client.Stub, implements ISSOService)

ISSOService (interface, extends java.rmi.Remote)
  └── BasicHttpBinding_ISSOServiceStub  [main package]
  └── org.tempuri.BasicHttpBinding_ISSOServiceStub  [test/generated package — duplicate]

DTOs:
  SSOGenerateLoginTokenRequest  (implements java.io.Serializable, Apache Axis TypeDesc)
  SSOGenerateLoginTokenResponse (implements java.io.Serializable, Apache Axis TypeDesc)
  SSOValidationResult           (implements — Apache Axis TypeDesc)
```

There are **two complete parallel sets** of stub classes:
1. **Production set** in `com.citi.prepaid.authservice.*` — hand-crafted, Spring-managed.
2. **Test/generated set** in `org.tempuri.*` and `org.datacontract.schemas._2004._07.*` — raw Axis WSDL2Java output, only used in `AppTest.java`.

This duplication means any contract change at Cambridge requires updating both sets independently.

**Spring wiring (`appContext-CambridgeAuthService.xml`):**
```xml
cambridgeAuthService (CambridgeAuthServiceImpl)
  -> authServiceContext (AuthServiceContext) — all values from .properties
  -> serviceLocator (ServiceLocator) — WSDL address and service name from .properties
```

## API Surface

This is a library, not a service. Its **public API** is:

| Interface | Method | Description |
|---|---|---|
| `ICambridgeAuthService` | `String getLoginToken() throws Exception` | Sole public operation; returns raw SSO token string |
| `ISSOService` | `SSOGenerateLoginTokenResponse generateLoginToken(SSOGenerateLoginTokenRequest)` | Internal SOAP call interface |
| `IServiceLocator` | `ISSOService getISSOService()` | Retrieve SOAP stub by configured address |
| `IServiceLocator` | `ISSOService getISSOService(URL portAddress)` | Retrieve SOAP stub for explicit URL |

All other classes are implementation details. The consumer is expected to:
1. Import `appContext-CambridgeAuthService.xml` into their Spring context.
2. Inject `ICambridgeAuthService` bean (`cambridgeAuthService`).
3. Call `getLoginToken()` and use the returned string as an SSO redirect token.

There is **no REST endpoint, no HTTP server, no gRPC service, and no message-consumer** in this library.

## Security Posture

| Control | Status | Evidence |
|---|---|---|
| Transport encryption | Partial | HTTPS used to Cambridge endpoint; no explicit certificate validation or trust-store pinning |
| Authentication to external service | Shared secret (HMAC-like hash) | `CambridgeAuthServiceHelper.getDigitalSignature()` — secret + returnURL + username + timestamp hashed |
| Hash algorithm strength | Weak risk | Algorithm is configurable; `AppTest.java` line 91 hard-codes `"MD5"`. No minimum algorithm enforcement in code |
| Secret storage | Plaintext | `sharedSecretKey` read from `.properties` file as plain string; stored as `String` in JVM heap |
| Token exposure in logs | Present | `App.java` line 24: `System.out.println("Token is "+token)` |
| Exception detail exposure | Present | `CambridgeAuthServiceImpl.java` line 76: `System.out.println("Exception : "+e)` — full stack trace to stdout |
| Input sanitisation | Absent | No validation of any input before use in signature computation or SOAP call |
| Response validation | Absent | `CambridgeAuthServiceImpl.java` line 71 extracts token without checking `response.getValidationResult().getIsValid()` |
| Proxy credential security | Not implemented | Proxy host/port set but no proxy authentication handled |
| JVM system property side-effect | Present | `System.getProperties().put("http.proxyHost",...)` — mutates global JVM state; could affect unrelated HTTP calls in the same JVM |
| Dependency CVEs | High risk | Apache Axis 1.4 (multiple known CVEs including deserialization, SSRF); Spring 4.3.9 (EOL) |

**CVSS assessment note**: Apache Axis 1.4 has known deserialization vulnerabilities (e.g., CVE-2019-0227) that can allow server-side request forgery. This library is a client, but its use of Axis's client `Call.invoke()` with a `java.lang.Object[]` response may be affected by deserialization of crafted SOAP responses.

## Technical Debt

| Item | Severity | Detail |
|---|---|---|
| Apache Axis 1.4 (EOL 2006) | Critical | No security patches; known CVEs; removed from Maven Central security support |
| JAX-RPC 1.1 API | Critical | Removed from Java EE 6+; incompatible with Jakarta EE / Java 17+ |
| Spring 4.3.9 (EOL Dec 2020) | High | No security patches from Pivotal/VMware |
| JUnit 3.8.1 | High | Severely outdated; `TestCase` subclass pattern |
| `1.0-SNAPSHOT` never released | High | Mutable artifact; no version stability |
| Duplicated stub classes | Medium | `com.citi.prepaid.authservice.stub.BasicHttpBinding_ISSOServiceStub` vs `org.tempuri.BasicHttpBinding_ISSOServiceStub` |
| Hard-coded `d:/c-base/` Windows path | High | Breaks all non-Windows (Linux/container) deployments |
| JVM-global proxy mutation | Medium | Thread-safety risk; affects unrelated HTTP calls |
| Raw `Vector` usage | Low | `BasicHttpBinding_ISSOServiceStub` uses `java.util.Vector` (synchronized, legacy) instead of `ArrayList` |
| `new Long(timestamp)` deprecated constructor | Low | `CambridgeAuthServiceImpl.java` line 63, `AppTest.java` line 58 — `Long(long)` deprecated since Java 9 |
| No null-guard on SOAP response | Medium | `CambridgeAuthServiceImpl.java` line 71 — `response.getToken()` will NPE if `response` is null |
| Exception swallowing in `ContextHelper` | Medium | `ContextHelper.java` line 16 — catches all exceptions and returns null context silently |
| `System.out` as logging | Medium | Not log-level controllable; no correlation IDs; goes to container stdout unformatted |
| Commented-out Spring Boot migration | Low | pom.xml lines 58–81 — abandoned migration artefact adds confusion |
| No test for production code path | Medium | `AppTest.java` uses the raw `org.tempuri.*` stubs directly, not `CambridgeAuthServiceImpl` |

## Gen-3 Migration Requirements

To modernise this library for a Gen-3 platform (Spring Boot 3.x, Jakarta EE 10, Java 17+, containerised):

| Requirement | Action |
|---|---|
| **Replace Apache Axis 1.4** | Migrate to Apache CXF 4.x or Spring-WS 4.x for WSDL/SOAP client generation; regenerate stubs from Cambridge WSDL using `cxf-codegen-plugin` |
| **Remove JAX-RPC dependency** | Replace `IServiceLocator extends javax.xml.rpc.Service` with JAX-WS `javax.xml.ws.Service` or remove in favour of Spring `WebServiceTemplate` |
| **Upgrade to Spring Boot 3.x** | Replace Spring XML context with `@Configuration` classes; use `application.yml` for configuration |
| **Externalise configuration** | Remove hard-coded `d:/c-base/...` path; use Spring Boot `@ConfigurationProperties` bound to env vars or Kubernetes `ConfigMap`/`Secret` |
| **Enforce SHA-256 minimum** | Hard-code `"SHA-256"` in `CambridgeAuthServiceHelper` or add algorithmic validation; remove external configurability of the hash algorithm |
| **Protect shared secret** | Use Spring Cloud Vault, AWS Secrets Manager, or Kubernetes `Secret` mounted as env var; never store as heap `String` (use `char[]` or `SecretKeySpec`) |
| **Add response validation** | Check `SSOValidationResult.getIsValid()` in `CambridgeAuthServiceImpl.getLoginToken()` before returning token |
| **Replace `System.out` logging** | Use SLF4J + Logback/Log4j2; structured JSON logging; never log tokens |
| **Add resilience** | Wrap SOAP call with Resilience4j `@CircuitBreaker` and `@Retry`; configure explicit connection/read timeouts |
| **Add unit tests** | Mock `ISSOService` with Mockito; test: valid response, null token, isValid=false, RemoteException, and null SOAP response |
| **Upgrade test framework** | Replace JUnit 3 `TestCase` with JUnit 5 (`@Test`, `@ExtendWith`) |
| **Eliminate code duplication** | Remove `org.tempuri.*` and `org.datacontract.*` test stubs; use single canonical production set or generate once to a shared module |
| **Fix proxy handling** | Replace JVM global `System.setProperty()` with per-request proxy configuration using an `HttpClient` passed to CXF or configured via `ClientHttpRequestFactory` |
| **Add CI build workflow** | Add `.github/workflows/build.yml` with compile, test, and artifact-publish stages |
| **Pin to a release version** | Publish as `1.0.0` (or appropriate semantic version) after stabilisation; remove `-SNAPSHOT` from production references |

## Code-Level Risks

| Risk | Location | Detail |
|---|---|---|
| **NPE on null SOAP response** | `CambridgeAuthServiceImpl.java:71` | `response.getToken()` — if `ssoService.generateLoginToken()` returns null, NPE thrown and swallowed as `Exception` |
| **NPE on AxisFault suppression** | `ServiceLocator.java:63` | `getISSOService(URL)` returns `null` on `AxisFault` — caller will NPE on the returned null |
| **Unguarded `isValid` not checked** | `CambridgeAuthServiceImpl.java:71` | Library silently accepts tokens even when `validationResult.isValid == false` |
| **MD5 collision risk** | `AppTest.java:91` | Default algorithm in test is MD5; if same value is used in production config, digital signatures can be forged |
| **Global JVM state mutation** | `CambridgeAuthServiceImpl.java:49-50` | `System.getProperties().put("http.proxyHost",...)` — not thread-safe; overwrites proxy for entire JVM |
| **Token in stdout** | `App.java:24` | `System.out.println("Token is "+token)` — tokens visible in all log aggregators |
| **Exception detail in stdout** | `CambridgeAuthServiceImpl.java:76` | `System.out.println("Exception : "+e)` — stack traces to stdout, potentially revealing internal paths and config |
| **Silent null return from ContextHelper** | `ContextHelper.java:16` | On any Spring context initialisation failure (e.g., missing properties file), returns null — callers will NPE |
| **Deserialization via Axis** | `BasicHttpBinding_ISSOServiceStub.java:125` | `_call.invoke(new Object[] {request})` — Axis deserializes response via BeanDeserializer; crafted SOAP response from a MITM could exploit Axis CVE-2019-0227 |
| **Deprecated `new Long(long)` constructor** | `CambridgeAuthServiceImpl.java:63`, `AppTest.java:58` | Removed in Java 17 — `Long.valueOf(timestamp)` should be used |
