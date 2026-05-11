# clientapi_API — Solution Architect View

## Technical Architecture

**Runtime model**: Spring Boot 3.5.7 fat JAR (`clientapiws.jar`) hosting an Apache Axis 1.4 SOAP engine inside an embedded servlet container, deployed as a Docker container on AKS.

**Module structure**:
```
clientapi (root POM, 3.0.6-SNAPSHOT)
├── clientapi-ws        — SOAP interface layer: interfaces, request/response types, validators, handlers
│   ├── ws/             — V1 service interface + handler
│   ├── ws/v2/          — V2 service interface + handler
│   ├── ws/v3/          — V3 service interface + handler (no getRequestStatusAndDFI)
│   └── ws/v4/          — V4 service interface + handler (adds region_id, international routing)
├── clientapi-impl      — Business logic: 5 service classes + domain types + exception hierarchy
├── clientapi-war       — WAR packaging for legacy VM deployment
├── clientapi-boot      — Spring Boot bootstrap + all @Configuration classes + Dockerfile
└── clientapi-https     — Separate HTTPS REST controller layer (not in root module list; legacy)
```

**Request processing chain**:
```
HTTP POST /services/ClientApiWebServices
    |
    v
AuthenticationCheckFilter (IP/cert check → cbaseapp DB)
    |
    v
AxisServlet (/services/*)
    |
    v
ClientApiWebServiceImpl extends ServletEndpointSupport
  (fetches handler bean from ApplicationContext by name)
    |
    v
ProxyFactoryBean (clientApiWebServiceHandler)
  → GlobalRequestIDInterceptor (MDC, request ID)
  → AuditMethodInterceptor (statistics)
  → ClientApiWebServiceHandlerImpl (or V2/V3/V4 variant)
        |
        |-- Input validation (Validator.validate(parameterMap))
        |-- Service-specific checks (status=CLOSED, address_3/4 block)
        v
{AddFunds|UpdateRegistration|UpdateAccountStatus|GetRequestStatus[AndDFI]}Service
        |
        |-- validateAPISecurity (CacheEntityManager → cbaseapp, per-program)
        |-- testAPI (if TEST MODE enabled)
        v
SynchronousOrderProcessor (HTTP Invoker → OrderService)
        |
        v
Response mapping → PROCESSED/PROCESSING/FAILED
```

**API versioning model**: Four co-deployed versions (V1/V2/V3/V4) sharing the same service implementations (`AddFundsService`, etc.) but with different SOAP interfaces, request/response types, and validator configurations:
- V1: Base — 5 operations, no region_id
- V2: Same interface as V1 with V2-specific response wrapper (`ws/response/v2/`)
- V3: No `getRequestStatusAndDFI` operation; V3 request types with `PhoneWithExtension` support
- V4: Adds `region_id` field to all requests; international routing; mobile phone support; separate V4 validators (`validatorNA_v4`, `validatorEMEA_v4`, `internationalValidator`)

## API Surface

**SOAP Endpoints (Axis 1.4):**

| Version | Path | Operations |
|---|---|---|
| V1 | `/services/ClientApiWebServices` | updateRegistration, addFunds, updateAccountStatus, getRequestStatus, getRequestStatusAndDFI |
| V2 | `/services/ClientApiWebServices/v2` | Same as V1 |
| V3 | `/services/ClientApiWebServices/v3` | updateRegistration, addFunds, updateAccountStatus, getRequestStatus (no getRequestStatusAndDFI) |
| V4 | `/services/ClientApiWebServices/v4` | updateRegistration, addFunds, updateAccountStatus, getRequestStatus (adds region_id to all) |

**REST Endpoints:**
- `GET /hc` — Health check, returns `"OK"` (`HealthCheck.java`)
- `GET /actuator/health`, `GET /actuator/info` — Spring Actuator

**Common request parameters (V1/V2/V3):**
- `package_id` (String, required): Card package identifier
- `program_id` (String, required): 8-digit program/affiliate ID
- `promotion_id` (String, required): 1-4 digit promotion
- `transaction_id` (String, required): Client-generated idempotency key (1-40 chars)

**V4 additional parameter:**
- `region_id` (String, required): `NA` or `EMEA`

**Operations additional parameters:**
- `addFunds`: `amount` (long, cents), `comment`, `reference_1` through `reference_4`
- `updateRegistration`: Full PII (Name, Address, home/business/mobile phone, SSN, DOB, email), `reference_1` through `reference_3`
- `updateAccountStatus`: `status` (must be `CLOSED`), `reference_1`
- `getRequestStatus`/`getRequestStatusAndDFI`: No extra params beyond common set

**SOAP fault types:**
- `InputValidationException` → AxisFault with `INPUT_VALIDATION_EXCEPTION` fault code
- `BusinessValidationException` → AxisFault with `BUSINESS_VALIDATION_EXCEPTION` fault code
- `SystemFailureException` → Inline PROCESSING_FAILED (code=1) in response (no fault)

**Note on `wsdl.xml`**: The committed `wsdl.xml` is a placeholder stub (`GenericOperation`) used for APIM publication, pointing to `api-qa.onbe.io`. It does not match the actual Axis-generated WSDL. Axis generates real WSDLs dynamically from `server-config.wsdd`, but service listing is disabled (`axis.disableServiceList=1`).

## Security Posture

**Authentication/Authorization:**
- `AuthenticationCheckFilter` (`com.citi.prepaid.security.api.filter.AuthenticationCheckFilter`) is registered globally for all URLs (`WebConfiguration.java` line 30). This filter checks incoming requests against the entity model (IP address, IP range, or client certificate).
- `CacheEntityManager` loads the complete access entity model from cbaseapp at startup. The model includes whitelist and registrar entries.
- Per-operation authorization: `ClientApiServiceImpl.validateAPISecurity()` calls `SecurityValidator.authorize(candidate, domain)` where domain is constructed from API name (`InstantIssue`), method name, and `program_id`. This enforces per-program, per-operation access control.
- `EntityCandidate` is retrieved from `CandidateStore.getCandiate()` — note: this appears to be a thread-local or request-scoped store populated by the authentication filter.

**Transport security:**
- HTTPS enforced at infrastructure level (APIM terminates TLS externally)
- Custom CA certificate (`nam.wirecard.sys.crt`) installed at Docker build time for backend service TLS
- Database connections use `trustServerCertificate=true` (server cert validation disabled — weakness)

**Access control model:**
- Three identification mechanisms supported: IP address (`JdbcAccessEntityIPAddressDao`), IP range (`JdbcAccessEntityIPRangeDao`), X.509 certificate (`JdbcAccessEntityCertificateDao`)
- Entity model is cached in memory; refresh requires service restart (no live reload mechanism found)

**Security audit:**
- `LoggingSecurityAudit.getInstance()` logs all security validation events
- `AuditMethodInterceptor` wraps service calls for statistics collection

**Gaps:**
- No OAuth2/JWT authentication — authentication relies on IP/certificate allow-list, which is an older pattern
- `trustServerCertificate=true` on all JDBC connections bypasses database server identity verification
- No API rate limiting visible at the application layer
- `ex.printStackTrace()` calls in `ClientApiWebServiceHandlerImpl.getRequestStatusAndDFI()` line 230 and multiple service implementations write stack traces to stdout, which may include sensitive request context

## Technical Debt

### High severity:
1. **Apache Axis 1.4** (released 2006, EOL): Multiple CVEs suppressed in `allowedlist.yaml` (`CVE-2018-1000632`, `CVE-2020-10683`). No upgrade path within Axis framework; requires full SOAP stack replacement.

2. **`ex.printStackTrace()` in production code**: Found in `ClientApiWebServiceHandlerImpl.getRequestStatusAndDFI()` (line 230), `AddFundsService.java` (line 147), `UpdateRegistrationService.java` (line 278), `GetRequestStatusService.java` (line 87), `GetRequestStatusAndDFIService.java` (line 83). These should be replaced with structured `log.error(message, ex)` calls. Stack traces may leak internal infrastructure details (hostnames, class paths) in SOAP fault responses or logs.

3. **`allow-circular-references: true` and `allow-bean-definition-overriding: true`**: These flags in `application.yml` mask underlying architectural issues and will break silently if Spring Boot removes support for them.

4. **XStream HTTP Invoker**: `XStreamMarshaller` for inter-service communication is a proprietary, Java-only, serialization-based protocol vulnerable to deserialization attacks if input is not fully trusted.

5. **`jakarta.servlet.http.HttpUtils` shim**: `clientapi-ws/src/main/java/jakarta/servlet/http/HttpUtils.java` is a manually copied compatibility class that was removed from the Jakarta Servlet API. This is a sign that Axis dependencies have been patched by hand.

### Medium severity:
6. **WSDL2Java auto-generated code patterns**: All domain classes (`AddFundsInput`, `UpdateRegistrationInput`, etc.) contain Axis-generated `__equalsCalc` / `__hashCodeCalc` patterns — thread-unsafe under high concurrency (synchronized methods but mutable state). These classes implement `Serializable` without defining serialVersionUID consistently.

7. **`getRequestStatusAndDFI` performance logging bug**: In `ClientApiWebServiceHandlerImpl.java` lines 218 and 234, the log message calls the method `"updateRegistration"` instead of `"getRequestStatusAndDFI"` — a copy-paste error making performance tracing misleading.

8. **Hardcoded ACH values in config**: `dfiNA=553`, `routingNA=011001234`, `typeNA=C` in `clientapi.yml`. These are financial routing numbers that should be environment-specific and stored in App Config, not source-controlled YAML.

9. **`TestAPI` test mode in production code**: `TestAPI` bean is wired in the main Spring context (`ClientApiImplConfiguration.java` line 80). If any configuration activates test mode in production, real payment operations would be delayed or return simulated failures without any gate to prevent it.

10. **`clientapi-https` module orphaned**: The `clientapi-https` module (with `AddFundsController`, `UpdateAccountStatusController`, `UpdateRegistrationController`, `CheckServiceAvailabilityController`) is not included in the root POM modules list and appears to be a legacy/abandoned REST facade. Its presence creates confusion about the service's actual API surface.

11. **`mobilePhoneValidatorNA` uses `INVALID_BUSINESS_PHONE` error type**: In `validationNA.xml` line 440-442, `mobilePhoneValidatorNA` references `INVALID_BUSINESS_PHONE` as the invalid error type instead of `INVALID_MOBILE_PHONE`. This means mobile phone validation errors report the wrong error code to callers.

12. **Two separate Maven modules with `HealthCheck` class**: Both `clientapi-boot` (`com.citi.prepaid.clientapi.health.HealthCheck`) and `clientapi-war` (`com.ecount.clientapi.health.HealthCheck`) define a health check endpoint — code duplication with divergent package names.

### Low severity:
13. **`countyValidatorNA` regex malformed**: In `validationNA.xml` line 284, the regex `[A-Za-z]{0,15}]` has a trailing unmatched `]`. This will cause a `PatternSyntaxException` at runtime if county validation is triggered for NA requests.

14. **`spring-cloud-dependencies:2025.0.0` BOM**: This is a very recent release; combined with `spring-boot:3.5.7`, these are cutting-edge versions that may introduce instability. No evidence of version compatibility validation beyond the Maven enforcer SNAPSHOT check.

15. **Commented-out `UpdateInventoryAction` code**: In `AddFundsService.java` (lines 80-89) and `UpdateAccountStatusService.java` (lines 64-72), inventory update actions are commented out. This suggests intentional feature rollback but leaves dead code that may confuse future maintainers about intended behaviour.

## Gen-3 Migration Requirements

To migrate this service to a Gen-3 REST/JSON/cloud-native architecture:

1. **Replace Axis with Spring MVC REST controllers**: Implement `@RestController` classes for each operation; define OpenAPI 3.0 specification. The existing service implementations (`AddFundsService`, etc.) can be largely preserved as the business layer.

2. **Replace `ClientApiWebService` SOAP interface with REST DTOs**: Create separate request/response DTO classes with Jackson serialization, Bean Validation (`@NotNull`, `@Pattern`, `@Size`) annotations replacing the XML validator configuration.

3. **Replace Spring HTTP Invoker with REST/gRPC client to OrderService**: The `SynchronousOrderProcessor` call must be replaced with a modern client once OrderService exposes a REST or gRPC endpoint.

4. **Replace `AuthenticationCheckFilter` + IP-based auth with OAuth2/mTLS**: Implement standard OAuth2 client credentials flow or mutual TLS for client authentication, removing dependency on `api-security-lib` and `cbaseapp` entity model.

5. **Migrate validator XML to Bean Validation**: `validationNA.xml` / `validationEMEA.xml` contain ~80 beans each. These should be replaced with `@Validated` annotations and custom constraint validators per region.

6. **Remove ECount ServiceConfig**: `ECountSystemConfiguration` bootstraps a proprietary service bus. This can be eliminated if OrderService is accessed via REST.

7. **Resolve circular dependencies**: Remove `allow-circular-references: true` by restructuring the configuration classes — the `@Lazy` annotations on many beans in `ClientApiImplConfiguration` and `ClientApiWSConfiguration` hint at the cycle locations.

8. **Consolidate to single deployment artifact**: Eliminate `clientapi-war` module and `clientapi-https` orphaned module; deliver only `clientapi-boot` as the single deployable.

9. **Add structured logging with PII redaction**: Implement Log4j2/Logback JSON encoder; add masking patterns for SSN (redact middle digits), DOB, and email in log output.

10. **Remove `TestAPI` from production context**: Move test mode support to a separate test-only Spring profile or remove entirely.

## Code-Level Risks

| Risk | Location | Severity |
|---|---|---|
| `ex.printStackTrace()` in payment service handlers | `AddFundsService:147`, `UpdateRegistrationService:278`, `GetRequestStatusService:87`, `GetRequestStatusAndDFIService:83`, `ClientApiWebServiceHandlerImpl:230` | High |
| `trustServerCertificate=true` disables JDBC TLS validation | `CbaseAppDataSourceAutoConfiguration:24`, `appsettings.json` all environments | High |
| Synchronized `equals()`/`hashCode()` with mutable `__equalsCalc` state in domain classes | `AddFundsInput:160`, `UpdateRegistrationInput:281`, `ServiceInput:115` | Medium |
| `countyValidatorNA` regex `[A-Za-z]{0,15}]` has trailing unmatched bracket → `PatternSyntaxException` | `validationNA.xml:283` | Medium |
| Performance log method name `"updateRegistration"` used in `getRequestStatusAndDFI` | `ClientApiWebServiceHandlerImpl:218,234` | Low |
| `mobilePhoneValidatorNA` emits `INVALID_BUSINESS_PHONE` error instead of `INVALID_MOBILE_PHONE` | `validationNA.xml:440` | Low |
| `allow-circular-references: true` + `allow-bean-definition-overriding: true` | `application.yml:25-26` | Medium |
| Email stored in both `email` and `email2` fields of `Registration` | `UpdateRegistrationService:137` | Low |
| Dead commented-out `UpdateInventoryAction` blocks | `AddFundsService:80-89`, `UpdateAccountStatusService:64-72` | Low |
| `axis.disableServiceList=1` but stub `wsdl.xml` committed — actual service descriptor mismatch | `WebConfiguration:82`, `wsdl.xml` | Medium |
| `InternationalFlagService` Redis calls with no authentication | `InternationalFlagService:24-42` | Medium |
| `TestAPI` bean live in all environments | `ClientApiImplConfiguration:80` | Medium |
| 9 CVEs suppressed in container scan allowlist without resolution timeline | `.github/containerscan/allowedlist.yaml` | High |
