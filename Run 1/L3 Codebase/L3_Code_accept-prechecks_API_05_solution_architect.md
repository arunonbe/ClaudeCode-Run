# accept-prechecks_API — Solution Architect View

## Technical Architecture

The service is a **three-module Maven project** built on Java 21 / Spring Boot 3.5.7. The three modules have distinct roles:

```
accept-prechecks (parent POM, v3.0.1-SNAPSHOT)
├── accept-prechecks-ws  (JAR)  — all business logic, service interface, validators, SOAP types
├── accept-prechecks-war (WAR)  — legacy Tomcat packaging; depends on ws JAR
└── accept-prechecks-boot (Fat JAR) — Spring Boot entry point; depends on ws JAR; active delivery
```

The **boot module** is the production deployment artifact. It wraps the ws JAR inside a Spring Boot fat JAR and embeds Tomcat with the Apache Axis servlet registered programmatically (`WebConfiguration.java`).

The **ws module** implements the actual SOAP service using:
- Apache Axis 1.x (forked to `jakarta-axis` by the internal Maven registry) as the SOAP engine
- `JaxRpcAcceptPrecheckService` as the JAX-RPC servlet endpoint (extends deprecated Spring `ServletEndpointSupport`)
- `AcceptPrecheckServiceImpl` as the business logic class (Spring-managed bean, injected by name `"acceptPrecheckService"`)
- `IEManageManager` (from `xplatform`) as the upstream ecount Core client

## API Surface

### SOAP Endpoint
- **URL pattern**: `/*` (AxisServlet catches all), service accessible at `/AcceptPrecheckService`
- **WSDL**: `AcceptPrecheckService.wsdl` — namespace `http://ecount.com/acceptprechecks`
- **Operation**: `acceptPrecheck(AcceptPrecheckRequest) → AcceptPrecheckResponse`
- **Binding**: `rpc` style, SOAP encoded (`use="encoded"`)
- **Transport**: SOAP 1.1 over HTTP/HTTPS

#### Request Schema (from WSDL)
| Field | Type | Constraints |
|---|---|---|
| `checkNumber` | xsd:string | Pattern: `[0-9]{8}\|[0-9]{14}`, minOccurs=1 |
| `serialNumber` | xsd:string | Pattern: `[0-9]{3}\|[0-9]{10}`, minOccurs=1 |
| `amount` | xsd:decimal | fractionDigits=2, minExclusive=0, minOccurs=1 |
| `lastName` | xsd:string | minOccurs=1 |
| `vendorId` | xsd:string | minOccurs=1 |
| `testMode` | xsd:boolean | Optional |

#### Response Codes
| Code | Constant | Meaning |
|---|---|---|
| 0 | `NO_PROBLEMS` | Accepted |
| 10 | `ALREADY_PROCESSED` | Check not in authorised state |
| 20 | `ALREADY_VOIDED` | Check stopped |
| 30 | `CHECK_VERIFIED` | Already verified |
| 40 | `INVALID_CHECK_NUMBER` | Format error, not found, or serial mismatch |
| 50 | `INVALID_CREDENTIALS` | Empty or wrong last name |
| 60 | `INVALID_AMOUNT` | Amount mismatch |
| 70 | `INVALID_SERIAL_NUMBER` | Format error |
| 90 | `SYSTEM_DOWN` | Unhandled exception |

### REST Endpoints
- `GET /hc` — Health check, returns `"OK"` (`HealthCheck.java` in both boot and war modules)
- `GET /actuator/health`, `GET /actuator/info` — Spring Boot Actuator (boot module only)

### Axis Admin Service
`server-config.wsdd` registers `AdminService` with `enableRemoteAdmin=false`. Remote administration is disabled but the service definition is present.

## Security Posture

### Transport
- No TLS termination configured within the application; relies on ingress/load balancer.
- SOAP over plain HTTP is supported (no enforcement of HTTPS at the application level).

### Authentication & Authorisation
- **No authentication on the SOAP endpoint**: The `server-config.wsdd` registers `Authenticate` (SimpleAuthenticationHandler) and `Authorize` (SimpleAuthorizationHandler) handlers but they are not applied to the `AcceptPrecheckService` service definition. The `AcceptPrecheckService` block has no `requestFlow` referencing these handlers. Any caller with network access can invoke the service.
- `axis.disableServiceList=1` prevents enumeration of available services.
- Azure Managed Identity secures the App Configuration and Key Vault access in non-local environments.

### Secrets Management
- **Production**: Azure Key Vault via Managed Identity (correct practice).
- **Local / UAT**: `.env_bkp` file in-repository contains real UAT credentials and Azure connection string with secret — **critical finding**.
  - File: `E:\OnbeEast363\repos\accept-prechecks_API\.env_bkp`
  - Lines 4, 14–19: Azure App Config secret, three database passwords in plaintext.

### Input Validation
- WSDL schema defines regex patterns for `checkNumber` and `serialNumber`, but schema validation is not enforced by Axis at runtime (SOAP encoded style does not enforce W3C Schema validation). Runtime validation is entirely in `AcceptPrecheckServiceImpl.process()`.
- Null-before-regex ordering bug: `checkNumber` and `serialNumber` are passed to `Pattern.matcher()` before the null check (`AcceptPrecheckServiceImpl.java` lines 88–90 and 95–97), causing NPE on null input.
- `amount` is cast via `floatValue()` which can produce floating-point precision errors.

### Logging of Sensitive Data
- `log.info("processing request " + request.toString())` at `AcceptPrecheckServiceImpl.java` line 58 logs the full request including `checkNumber`, `serialNumber`, `lastName`, and `amount` in every invocation.
- `log.info("for request: " + request.toString() + "returning response: " + response.toString())` at line 70 repeats the same.

### Dependency Vulnerabilities (Trivy / Container Scan Suppressions)
The `.trivyignore` file suppresses 15 CVEs. Notable suppressions include:
- `CVE-2024-22262` — Spring Framework (also in `allowedlist.yaml`)
- `CVE-2024-38816`, `CVE-2024-38819` — Spring Framework path traversal vulnerabilities
- `CVE-2024-47072` — XStream (used indirectly)
- `CVE-2024-50379`, `CVE-2024-52316`, `CVE-2024-56337` — Apache Tomcat
- `CVE-2016-1000338` through `CVE-2016-1000352`, `CVE-2018-1000180` — BouncyCastle (`bcprov-jdk15on`)
- `CVE-2025-59250` — 2025-dated CVE suppressed

Suppressing Spring path traversal CVEs and multiple Tomcat CVEs without documented justification is a compliance risk.

## Technical Debt

### High Priority
1. **Credentials committed to SCM** (`/.env_bkp`): Real UAT database passwords, Azure connection string secret. Must be rotated and the file removed from git history.
2. **SOAP RPC/Encoded**: `use="encoded"` is a 20-year-old antipattern, non-WS-I compliant. No modern SOAP toolkit generates this style. This constrains consumers to Axis or equivalently old stacks.
3. **Null-before-regex NPE** (`AcceptPrecheckServiceImpl.java` lines 88, 95): `Pattern.matcher(checkNumber)` called before null guard.
4. **`JaxRpcAcceptPrecheckService`** (line 3): `import javax.xml.rpc.ServiceException` — uses `javax` namespace despite the codebase having migrated to `jakarta`. The Axis JAX-RPC library is internally forked and unstandardised.
5. **Unsuppressed CVEs in BouncyCastle**: Multiple 2016-era BouncyCastle CVEs suppressed. `bcprov-jdk15on` is the deprecated pre-modular BouncyCastle artefact; should be replaced with `bcprov-jdk18on`.
6. **Root `wsdl.xml` mismatch**: The file published to APIM (`wsdl.xml` at repo root) is a generic placeholder (`GenericOperation`, `http://example.com/soap`) — does not match the actual `AcceptPrecheckService.wsdl`. APIM subscribers receive an incorrect contract.

### Medium Priority
7. **Floating-point amount comparison** (`AcceptPrecheckServiceImpl.java` line 167): `(int)(request.getAmount().floatValue() * 100)` — should use `amount.multiply(BigDecimal.valueOf(100)).intValueExact()`.
8. **Hardcoded routing number `38791282`** in three locations: lines 82, 114, 150 of `AcceptPrecheckServiceImpl.java`. Should be externalised to configuration.
9. **Hardcoded `facility = "certegy"`** in `application.yml`. Not parameterised.
10. **`PerformanceFilter` is a no-op**: Registered and mapped but performs no timing or logging (`PerformanceFilter.java` lines 29–37 — `chain.doFilter()` only).
11. **`LastNameValidatorECountCore` and `LastNameValidatorXSearch` unused**: Both classes implement `LastNameValidator` but are not wired into `AcceptPrecheckServiceImpl`. The interface exists but the implementation is only used via `definition.addenda.get("cz-lastname")` inline logic. The beans `eMember` and `searchService` wiring in config is unreferenced by the actual service logic.
12. **`allow-circular-references: true` and `allow-bean-definition-overriding: true`** in `application.yml`: These Spring Boot antipatterns mask configuration problems.
13. **`HttpUtils.java` in `jakarta.servlet.http` package**: A copy of the removed `jakarta.servlet.http.HttpUtils` class placed into the source tree under `accept-prechecks-ws/src/main/java/jakarta/servlet/http/HttpUtils.java` — pollutes the `jakarta` package namespace with an application class. This is a workaround for a removed API.
14. **Version snapshot**: Root POM declares `3.0.1-SNAPSHOT`. Maven enforcer `requireReleaseDeps` rule has `failWhenParentIsSnapshot=false`, meaning the build is always a SNAPSHOT.
15. **WAR module never decommissioned**: `accept-prechecks-war` and `.gitlab-ci.yml` are dead artefacts consuming build time and creating maintenance confusion.

### Low Priority
16. **Apache Commons Lang 2 still used** (`commons-lang:commons-lang`) alongside Commons Lang 3 (`commons-lang3`). Lang 2 is end-of-life.
17. **`Hashtable` and `Dictionary`** used throughout (`AcceptPrecheckServiceImpl.java` lines 111, 112) — legacy Java 1.0 collections, should be `HashMap`/`Map`.
18. **`StopWatch` from Commons Lang 2** (`AcceptPrecheckServiceImpl.java` line 55): `sw.getTime()` is called twice (lines 72, 73) — once discarded, once logged.
19. **Test files with `.java1` extension**: `AcceptPrecheckCoreIntegrationTest.java1`, `AcceptPrecheckServiceImplTest.java1`, `LastNameValidatorECountCoreTest.java1`, `LastNameValidatorXSearchTest.java1` — test files renamed to `.java1`, excluding them from compilation. This is a deliberate bypass of test execution.

## Gen-3 Migration Requirements

To migrate this service to a Gen-3 cloud-native REST/JSON API on Azure:

1. **Replace SOAP with REST**: Redesign the single `acceptPrecheck` operation as `POST /prechecks/accept` with JSON request/response. Eliminate Axis, JAX-RPC, `server-config.wsdd`, and WSDL entirely.
2. **Replace xplatform client**: `IEManageManager` (via `ECoreEManage`) must be replaced with a direct API call to the Gen-3 ecount Core service or migrated platform equivalent. This is the critical dependency.
3. **Resolve `javax.xml.rpc` import**: Remove JAX-RPC dependency entirely (`JaxRpcAcceptPrecheckService` becomes unnecessary in a REST architecture).
4. **Externalise all hardcodes**: `38791282` routing number, `certegy` facility into Azure App Config keys.
5. **Fix amount precision**: Replace `floatValue()` with `BigDecimal` arithmetic.
6. **Fix null-before-regex NPE**: Add null guards before `Pattern.matcher()` calls.
7. **Add authentication**: Implement OAuth 2.0 / mTLS on the endpoint (currently unauthenticated).
8. **Mask sensitive data in logs**: Implement a log sanitiser or use structured logging with field-level masking for `checkNumber`, `serialNumber`, `lastName`.
9. **Rotate and remove `.env_bkp`**: Purge credentials from git history; rotate all affected secrets.
10. **Remove WAR module and GitLab CI**: Decommission `accept-prechecks-war` and `.gitlab-ci.yml` once Tomcat hosts are confirmed decommissioned.
11. **Replace BouncyCastle**: Upgrade from `bcprov-jdk15on` to `bcprov-jdk18on` to clear BouncyCastle CVEs.
12. **Fix APIM `wsdl.xml`**: Replace root `wsdl.xml` with the actual `AcceptPrecheckService.wsdl` content, or remove WSDL publishing and replace with OpenAPI spec for the new REST API.
13. **Restore and fix tests**: Rename `.java1` test files back to `.java`, fix compilation errors, and remove `-Dmaven.test.skip` from pipeline definitions.

## Code-Level Risks

| File | Line(s) | Risk | Severity |
|---|---|---|---|
| `AcceptPrecheckServiceImpl.java` | 58, 70 | Logs full request (checkNumber, serialNumber, lastName, amount) at INFO | Critical |
| `.env_bkp` | 4, 14–19 | Azure secret and DB passwords committed to repository | Critical |
| `AcceptPrecheckServiceImpl.java` | 88–90, 95–97 | NPE: `matcher()` called before null check on `checkNumber`/`serialNumber` | High |
| `AcceptPrecheckServiceImpl.java` | 167 | Float-to-int amount conversion precision loss | High |
| `AcceptPrecheckServiceImpl.java` | 195–202 | Last-name validation returns `true` when `cz-lastname` absent from addenda — any name passes | High |
| `server-config.wsdd` | 6 | `adminPassword=admin` in WSDD configuration | Medium |
| `AcceptPrecheckServiceImpl.java` | 82, 114, 150 | Hardcoded Citibank routing number `38791282` | Medium |
| `JaxRpcAcceptPrecheckService.java` | 3, 17–23 | `javax.xml.rpc` import; `getWebApplicationContext()` called twice per request (lines 21–22) — redundant lookup | Medium |
| `datasourceTestContext.xml` | 20–27 | Hardcoded QA database hostname and credentials in test config | Medium |
| `QA.postman_environment.json` | 204 | Committed JWT Bearer token | Medium |
| `.trivyignore` | 8–14 | Multiple 2016-era BouncyCastle CVEs suppressed without documented justification | Medium |
| `jakarta/servlet/http/HttpUtils.java` | entire file | Application class placed in `jakarta.servlet.http` package — namespace pollution | Low |
| `AcceptPrecheckServiceImpl.java` | 72–73 | `sw.getTime()` called twice; first call result discarded | Low |
| `wsdl.xml` (root) | entire file | Generic placeholder published as the service WSDL to external APIM | Low |
