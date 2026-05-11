# secure-data_LIB — Solution Architect View

## Technical Architecture
Spring Boot application (`@SpringBootApplication`) with a single REST controller (`SecureController`) that wraps a `StrongBoxClient`. Communication with StrongBox uses Apache Commons HttpClient 3.x (`org.apache.commons.httpclient`) sending XML-RPC formatted POST requests with `Content-Type: application/x-mapxml`. Service discovery of the StrongBox endpoint is performed via a Director XML-RPC client.

Springfox Swagger 2 (`@EnableSwagger2`) provides API documentation. Spring XML context file (`securedata.xml`) wires beans via `PropertyPlaceholderConfigurer` reading from a local properties file.

## API Surface
| Endpoint | Method | Description |
|---|---|---|
| `GET /getData/{refId}` | GET | Returns `Map<String,Object>` from StrongBox for the given reference |

- Produces: `application/json`, `application/xml`
- No request authentication or authorisation.
- Swagger UI available at `/swagger-ui.html` (default Springfox path).

## Security Posture

### Authentication / Authorisation
**None implemented.** The REST endpoint `GET /getData/{refId}` has no `@PreAuthorize`, no Spring Security configuration, and no API key mechanism. Any caller with network access can retrieve any secret by reference ID.

### Cryptography
No local cryptographic operations. All cryptographic material is delegated to StrongBox.

### Secrets Management — CRITICAL FINDINGS
1. **Hardcoded agent `B2CTEST`** in `securedata.xml:23` — test agent identifier in production Spring context file. This may restrict or incorrectly scope StrongBox access.
2. **External config at Windows absolute path** `d:/c-base/config/director-client.properties` (securedata.xml:15) — not portable, not container-ready.
3. No secret rotation mechanism.

### Transport Security
Apache Commons HttpClient 3.x (EOL since 2011) used for all outbound HTTP. Version 3.x does not enforce SNI or modern TLS by default. No `SSLSocketFactory` customisation observed in `StrongBoxClient.java` — TLS configuration is entirely default.

### CVE Exposure
- **Apache Commons HttpClient 3.x** — this library has been EOL since 2011. Multiple known CVEs exist. Should be replaced with Apache HttpClient 5.x or Spring WebClient.
- **Springfox Swagger 2** — has known CVEs (e.g., Spring Boot 2.6 compatibility issues, path traversal in older versions). Version not determinable from available source.

## Technical Debt

### Critical (Security)
- `SecureController.java:47-58` — constructor calls `directorClient.getSerivceLocationURI()` before Spring injects `directorLocation` and `directorAgent` fields. At runtime, `directorLocation` is null, causing `URISyntaxException` or NullPointerException. The service cannot function as coded unless this is overridden by the XML bean wiring in `securedata.xml`.
- `SecureController.java:53,57` — `e.printStackTrace()` in catch blocks (no structured logging).
- `SecureController.java:76-82` — `catch (Exception e)` silently swallows exceptions; `readOutput` could be null causing NullPointerException at line 84 (`readOutput.getData()`).

### Architecture
- `StrongBoxClient.java` uses a static `HttpClient` singleton — thread-safety depends on `MultiThreadedHttpConnectionManager` (present) but connection pool parameters are not configured.
- Duplicate import of `org.apache.commons.logging.Log` and `LogFactory` in `StrongBoxClient.java` (lines 14-15 and 34-35).
- `SwaggerConfiguration.java:24` has a typo in the controller package name (`securedatan` instead of `securedata`) — Swagger will find no controllers and produce an empty API spec.

## Gen-3 Migration Requirements
1. Replace XML-RPC StrongBox access with a modern secrets manager API (Vault KV, AWS SSM Parameter Store, Azure Key Vault).
2. Add authentication: OAuth2/JWT bearer token or mTLS on the REST endpoint.
3. Replace Apache Commons HttpClient 3.x with Apache HttpClient 5.x or Spring WebClient.
4. Remove Springfox; use SpringDoc OpenAPI 3 instead.
5. Fix constructor injection order defect.
6. Containerise (Docker + Kubernetes); remove Windows path dependencies.
7. Add Spring Actuator health endpoints.

## Code-Level Risks
| File | Line | Risk | Severity |
|---|---|---|---|
| `SecureController.java` | 47–62 | Constructor uses uninjected Spring fields — NPE/URISyntaxException at startup | CRITICAL |
| `SecureController.java` | 76–84 | Swallowed exception + potential NPE on null `readOutput` | HIGH |
| `SecureController.java` | 53,57 | `e.printStackTrace()` — unstructured error exposure | MEDIUM |
| `SwaggerConfiguration.java` | 24 | Typo in controller package `securedatan` — Swagger lists no endpoints | MEDIUM |
| `StrongBoxClient.java` | 34–35 | Duplicate import statements | LOW |
| `securedata.xml` | 23 | Hardcoded agent `B2CTEST` | HIGH |
| `securedata.xml` | 15 | Windows absolute config path `d:/c-base/config/...` | HIGH |
