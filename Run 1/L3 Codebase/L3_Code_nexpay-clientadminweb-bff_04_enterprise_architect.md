# nexpay-clientadminweb-bff — Enterprise Architect View

## 1. Position in the NexPay Gen-3 Architecture

NexPay is Onbe's third-generation cloud-native payments platform, designed to replace the legacy eCount/Atlys stack with a microservices architecture on Azure Container Apps. `nexpay-clientadminweb-bff` is the northbound API aggregation layer for the client administration domain — one of three BFF services currently provisioned (the others being `nexpay-recipientweb-bff` and `nexpay-ivr-bff`).

The BFF pattern is a well-established Gen-3 practice: instead of a monolithic API gateway, each front-end channel has a dedicated BFF that owns the aggregation, transformation, and caching logic specific to that channel's UX requirements. This reduces coupling and allows independent deployment cadences.

## 2. Architectural Fit Assessment

### 2.1 Strengths (Gen-3 Aligned)

| Principle | Status | Evidence |
|---|---|---|
| Stateless service | Achieved | No database; Redis used only for caching |
| Container-native | Achieved | Azure Container Apps with Consumption profile |
| Config externalised | Achieved | Azure App Configuration + Key Vault references |
| Managed Identity auth | Achieved | `credential.managed-identity-enabled: true` |
| Virtual threads (Project Loom) | Achieved | `spring.threads.virtual.enabled: true`, Java 25 |
| OpenTelemetry observability | Achieved | OTLP traces/metrics/logs to Dynatrace |
| CI/CD reusable workflow | Achieved | Delegates to `nexpay-iac` shared workflow |
| API published to APIM | Achieved | `PUBLISH_TO_APIM: true`, OpenAPI spec auto-published |
| CodeQL SAST gate | Achieved | `CODEQL_QUALITY: true` |

### 2.2 Architecture Gaps

| Gap | Impact | Priority |
|---|---|---|
| No authorisation middleware (programId RBAC) | High — any authenticated admin can access any program | P1 |
| Management `env` endpoint exposed | High — may leak resolved secrets | P1 |
| No circuit breaker / retry on downstream calls | Medium — cascade failures to claim-code/config svc | P2 |
| Container runs as root | Medium — PCI DSS Requirement 2.2 non-compliance | P2 |
| No `-Xmx` JVM cap | Medium — OOMKill risk | P2 |
| Unstructured logging format | Low — log aggregation consistency | P3 |

## 3. Service Boundary and Domain Ownership

The BFF owns the **client administration experience domain** but does not own data. Data ownership is:

- **Program/country/modality config** → owned by `nexpay-config-svc`
- **Claim code lifecycle** → owned by `nexpay-claim-code-svc`
- **Authentication** → owned by `nexpay-auth-svc` (referenced in nexpay-ivr-bff; likely shared)
- **Caching** → Redis (Azure Cache for Redis, shared infrastructure)

This is correct domain separation. The risk is that the BFF becomes a "smart BFF" that leaks business logic — the current implementation keeps the BFF thin (client wrapper + caching), which is the right approach.

## 4. API Management Integration

The service is published to the **External APIM** (`INTERNAL_APIM: false`, `EXTERNAL_APIM: true`). This means:

- The APIM acts as the internet-facing TLS termination and throttling point.
- The BFF itself runs on an internal Azure Container Apps environment (`internal_load_balancer_enabled: true` in `container_apps_integration.tf` line 27). It is not directly internet-reachable; only APIM can reach it.
- This is the correct architecture for a FinTech service that must satisfy PCI DSS Requirement 1 (network segmentation).

However, because APIM forwards requests inbound to the BFF, the APIM's network rules must ensure that only APIM can call the BFF ingress. This is typically achieved via Container Apps Environment ingress restrictions. Verification of this restriction is recommended.

## 5. Authentication Architecture

The BFF relies on an upstream identity provider (likely Azure AD B2C or Azure Entra ID) to issue JWTs. The `AuditFilter` reads claims from the JWT principal (`AuditFilter.java` lines 182–222) but there is no explicit security configuration (`SecurityConfig` class) in the scanned file tree. This suggests that Spring Security JWT validation is configured either in the parent BOM or in a yet-to-be-committed security module. This must be confirmed before production deployment — an unauthenticated BFF would expose program configuration to anyone who can reach the APIM endpoint.

## 6. Resilience Architecture

Current state: zero resilience wrappers. `RestClient` calls in `ConfigSvcClient` and `ClaimCodeSvcClient` propagate `RestClientResponseException` directly as `ServiceClientException`. Under sustained downstream failure, all BFF threads will block on socket timeouts (10s read timeout), exhausting the virtual thread pool and causing BFF unresponsiveness.

Recommended pattern: Resilience4j `CircuitBreaker` + `Retry` with exponential backoff on each downstream client, with fallback responses where possible (e.g., stale cached config data during a transient config-svc outage).

## 7. Dependency Management

The `pom.xml` pins `nimbus-jose-jwt:10.9` — a modern, well-maintained JWT library. The `otel-grpc:1.0.0-SNAPSHOT` dependency is a snapshot, which is a risk in a production path — snapshot artifacts are mutable and can change without a version bump, breaking reproducible builds. This should be promoted to a release version before any production promotion.

## 8. Cross-Cutting Concerns Coverage

| Concern | Solution | Status |
|---|---|---|
| Distributed tracing | OpenTelemetry + Dynatrace | Implemented |
| Audit logging | AuditFilter → OTEL baggage | Implemented |
| Security scanning | CodeQL SAST + Dependabot | Implemented |
| Container scanning | `.github/containerscan/README.md` present | Partially — README only |
| Secret management | Azure Key Vault via App Config refs | Implemented |
| Config management | Azure App Configuration | Implemented |
| Service discovery | Azure Container Apps internal DNS | Implemented (static internal hostnames) |
| Rate limiting | APIM (external) | Assumed — not verified |
| mTLS between services | Not observed | Gap — internal service calls are plain HTTP |
