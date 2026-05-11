# DevOps & Operations View — cs-api-v3_API

## Build System
- **Build tool**: Maven (mvnw wrapper)
- **Maven parent**: `com.parents:prepaid-parent:6.0.13`
- **Artifact**: `CardManagementAPIV3` (WAR via `csapi-v3-war` module + Spring Boot executable via `csapi-v3-boot`)
- **Java version**: Source/target 21
- **Version**: `3.1.13` (release tag — no SNAPSHOT)
- **Packaging**: Multi-module Maven project with 7 modules:
  - `csapi-v3-rest-client` — HTTP client wrappers for ecount-core-rest-api
  - `csapi-v3-api` — Core business logic actions (SearchAccount, UpdateAccount, ReissueCard, HandleEscalation)
  - `csapi-v3-ws` — SOAP endpoint (Axis JAX-RPC), legacy XML context files
  - `csapi-v3-war` — WAR packaging module (includes Dockerfile)
  - `csapi-v3-payout-ws` — Payout SOAP sub-service
  - `csapi-v3-payout-war` — Payout WAR packaging
  - `csapi-v3-boot` — Spring Boot 3 entry point; all `@Configuration` classes; replaces XML context loading

## Key Dependencies
| Dependency | Version | Notes |
|---|---|---|
| Spring Boot | 3.5.7 | Current; autoconfiguration, embedded container |
| Spring Cloud Azure | 5.23.0 | App Config + Key Vault managed identity |
| Spring Cloud | 2025.0.0 | Bootstrap context for App Config |
| xplatform | 6.5.8 | C-Base xPlatform RPC library |
| ecount-core-rest-api | 3.1.8 | HTTP REST client for MemberService/DeviceService |
| xaffiliate-service | 4.0.1 | AffiliateService for dynamic app_id lookup |
| comment | 3.0.1 | ICommentService for audit trail + comment history |
| xsecurity-common/impl | 4.0.3 | JWE / JWT security utilities |
| jjwt | 0.11.5 | JWT / JWE token handling |
| WireMock | 3.9.1 | Integration test HTTP mocking |
| JaCoCo | 0.8.12 | Code coverage |
| msal4j | 1.22.0 | Microsoft MSAL for Azure AD token acquisition |
| Resilience4j | (via Spring Boot) | Circuit breaker for ecount-core HTTP calls |
| Xerces | 2.12.2 | XML parser (Axis dependency) |

## CI/CD
| Workflow | Trigger | Action |
|---|---|---|
| `.github/workflows/deployment-csapi.yml` | Push to main, PR | Calls `Onbe/om-ci-setup/.github/workflows/java-workflow.yml@main` |
| CodeQL | `CODEQL_QUALITY: true` | Static analysis enabled |
| Pact | `PACT_PACTICIPANT: card-management-api-v3` | Consumer-driven contract testing (VERIFY_PROVIDER_PACT: false — consumer only) |
| Dependabot | Scheduled | Dependency update PRs |

**Deployment pipeline**: Full CI/CD via om-ci-setup reusable workflow. Unlike V1 and V2, V3 has `USE_ROLLOUT_CONFIG: true` (canary/blue-green rollout), `EXCLUDE_STAGE: true` (no stage environment in the pipeline), and `UPDATE_DEPENDENCIES: true` / `UPDATE_PARENT_VERSION: true` (automated dependency management).

**APIM Publishing**: `PUBLISH_TO_APIM: true`, `EXTERNAL_APIM: true` — WSDL is published to Azure API Management external gateway. Backend suffix: `/services/AccountManagement`.

## Deployment
- Target: Container (Dockerfile in `csapi-v3-war/Dockerfile`)
- Rollout: Canary/blue-green via `USE_ROLLOUT_CONFIG: true`
- Context path: `${SERVER_CONTEXT_PATH:/}` (configurable via env var)
- Port: `${SERVER_PORT:80}` (configurable via env var)
- Health endpoint: `/actuator/health` and `/actuator/info` exposed
- Azure App Config: refreshes every 15 minutes (configurable via `AZURE_APP_CONFIG_REFRESH_INTERVAL`)
- Managed Identity: used for both App Config and Key Vault access in non-local profiles
- Session timeout: 5 minutes (matching V1)

## Configuration
| Source | Mechanism | Contents |
|---|---|---|
| Azure App Config | Managed Identity (non-local), connection string (local) | All runtime config: JDBC URLs/credentials, xPlatform bootAddress, CMS URLs, Redis URL, ecount-core base URL, JWE keys (should move to Key Vault) |
| Azure Key Vault | Managed Identity references from App Config | Secrets (JDBC passwords, ideally JWE keys) |
| `application.yml` | Classpath | Structural defaults; datasource stubs; logging levels |
| `bootstrap.yaml` | Spring Cloud bootstrap | Azure App Config endpoint, refresh interval, profile-based config selection |
| `applicationContext-CSWS.properties` | Committed file (QA artifact) | QA/staging values including JWE keys — should not be committed |
| Environment variables | Container runtime | `SERVER_PORT`, `SERVER_CONTEXT_PATH`, `AZURE_APP_CONFIG_ENDPOINT`, `AZURE_MANAGED_IDENTITY_CLIENT_ID`, `AZURE_APP_CONFIG_REFRESH_INTERVAL` |

**Spring profiles**: `local` uses App Config connection string; all other profiles use Managed Identity. `allow-bean-definition-overriding: true` and `allow-circular-references: true` set to accommodate legacy Spring XML + Boot co-existence.

## Observability
- **Logging**: SLF4J + Logback (Spring Boot default). Root: ERROR; `com.citi` and `com.onbe`: DEBUG in application.yml (likely overridden in production via App Config).
- **Request correlation**: `ProgramIdAwareGlobalRequestIDGenerator` with `appName="csapi.v3"` — MDC-based request ID includes program ID for log traceability.
- **Timing**: `startTime` / `duration` logged at debug per operation.
- **Health check**: `/actuator/health` and `/actuator/info` — basic liveness and info endpoints.
- **Metrics**: No Micrometer/Prometheus metrics configured; actuator limited to health and info.
- **Distributed tracing**: `correlation-web` library (version 2.0.1) — Onbe internal correlation header propagation.
- **Circuit breaker**: Resilience4j circuit breaker on ecount-core REST client calls with configurable failure rate threshold (5%), wait duration (30s), slow call threshold (30s).

## Local Development
- Profile `local` uses `AZURE_APP_CONFIG_CONNECTION_STRING` environment variable for App Config access (no Managed Identity required).
- WireMock used in integration tests to mock ecount-core HTTP responses.
- Managed Identity disabled for `local` profile — developers can use connection strings.

## Test Execution
- **Unit tests**: Standard Maven test phase with JUnit 5.
- **Integration tests**: WireMock-based integration tests in `csapi-v3-qa` and `csapi-v3-payout-qa` modules.
- **Code coverage**: JaCoCo configured (v0.8.12); report per module in `target/jacoco-reports/`.
- **Contract tests**: Pact consumer-driven contract testing (`card-management-api-v3` pacticipant). `VERIFY_PROVIDER_PACT: false` — this service acts as a consumer (of ecount-core), not a provider.

## Risks
1. **JWE keys committed to repository**: `applicationContext-CSWS.properties` at repo root contains encryption keys — must be removed, rotated, and stored in Azure Key Vault.
2. **Legacy Axis dependency with Java 21**: Apache Axis 1.x predates Java module system; `allow-bean-definition-overriding` and `allow-circular-references` workarounds suggest friction between legacy Axis and Spring Boot 3.
3. **`applicationContext-CSWS.properties` is a QA file in repo root**: This pattern risks environment bleed — QA config values (CMS QA URL, UAT ecount-core URL, staging credentials) could affect CI runs or be mistaken for production config.
4. **Redis HTTP without fallback**: International program lookup calls Redis HTTP endpoint; no circuit breaker or fallback documented for this path.
5. **`allow-circular-references: true`**: Spring Boot 3 disabled circular references by default — this override suggests architectural debt in the bean wiring that should be resolved.
