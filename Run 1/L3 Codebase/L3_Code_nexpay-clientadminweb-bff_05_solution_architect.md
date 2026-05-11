# nexpay-clientadminweb-bff — Solution Architect View

## 1. Technical Stack Summary

| Layer | Technology | Version |
|---|---|---|
| Language | Java | 25 |
| Framework | Spring Boot | (inherited from nexpay-parent 0.2.8-SNAPSHOT) |
| Reactive model | Virtual threads (Project Loom) | JEP-444 |
| HTTP client | Spring RestClient | 6.x |
| Security | Spring Security + Nimbus JOSE JWT | 10.9 |
| Caching | Redis via Spring Data Redis (Lettuce) | TLS on Azure Cache for Redis |
| Observability | OpenTelemetry + Dynatrace (OTLP gRPC) | otel-grpc 1.0.0-SNAPSHOT |
| Config | Azure App Configuration + Key Vault refs | Spring Cloud Azure |
| Container runtime | Azure Container Apps (Consumption) | ACA |
| CI/CD | GitHub Actions (reusable workflow in nexpay-iac) | |
| API gateway | Azure API Management (External) | |
| Base image | bellsoft/liberica-openjre-alpine:25 | |

## 2. Module Architecture

```
nexpay-clientadminweb (parent POM)
│
├── nexpay-clientadminweb-api
│     └── Generated Spring MVC server stubs from OpenAPI spec
│         Exposes: /api/nexpay-clientadminweb/* (published to APIM)
│
├── nexpay-clientadminweb-boot
│     ├── NexpayClientadminwebApplication.java  — Spring Boot entry point
│     ├── ErrorExceptionHandlers.java           — RFC 7807 problem detail responses
│     ├── Dockerfile                            — Container build definition
│     └── application*.yaml                    — Profile-specific Spring config
│
├── nexpay-clientadminweb-client
│     ├── nexpay-clientadminweb-claimcode-client-api  — Generated OpenAPI client for claim-code-svc
│     └── nexpay-clientadminweb-config-client-api     — Generated OpenAPI client for config-svc
│
└── nexpay-clientadminweb-impl
      ├── client/
      │     ├── claimcode/ClaimCodeSvcClient.java  — Wraps generated claim code client
      │     └── config/ConfigSvcClient.java         — Wraps generated config client
      ├── config/
      │     ├── AsyncConfig.java               — Virtual thread executor config
      │     ├── ImplementationConfig.java      — Component scan + AuditFilter registration
      │     ├── RestClientConfig.java          — ServiceProperties → RestClient beans
      │     └── ServiceProperties.java         — @ConfigurationProperties for service URLs/timeouts
      ├── filter/AuditFilter.java             — OTEL baggage: actor.id, source, reason, idempotency-key
      └── health/ApplicationHealthIndicator.java — Custom health contributor
```

## 3. Configuration Resolution Chain

At runtime in the `qa` profile, configuration is resolved in this precedence order (Spring Boot default):

1. Environment variables (injected by Azure Container Apps at container start)
2. Azure App Configuration (keys: `nexpay-clientadminweb-bff/*`, label: `qa`)
3. `application-qa.yaml` (static QA profile config)
4. `application.yaml` (static defaults)

Key values injected via Azure App Configuration:
- Redis `host`, `port`, `password` (via Key Vault reference to `redis-primary-access-key`)
- `AZURE_APP_CONFIG_ENDPOINT` (the App Configuration endpoint itself)
- `OTEL_EXPORTER_OTLP_ENDPOINT` (Dynatrace OTLP URL)
- Downstream service base URLs (unless already hardcoded in `application-qa.yaml`)

The `fail-fast: true` on the App Configuration store (`application-qa.yaml` line 19) means that if App Configuration is unreachable at startup, the service will not start. This is a correct fail-safe for a payments service — a misconfigured instance is worse than a non-starting one.

## 4. Security Solution Design

### 4.1 Inbound Authentication

The service expects pre-authenticated requests from APIM. APIM should validate the JWT (Azure AD token) and forward `Authorization: Bearer <token>` plus the extracted `X-Actor-Id` header. Spring Security validates the JWT signature against the Azure AD JWKS endpoint. The Nimbus JOSE JWT library (`nimbus-jose-jwt:10.9`) handles token parsing.

The `AuditFilter` fires after Spring Security authentication, extracting the actor identity from:
1. `X-Actor-Id` header (highest priority — allows APIM to inject the identity explicitly)
2. JWT claims: `email` → `userId` → `preferred_username` → `sub`
3. Spring Security `Authentication.getName()` fallback
4. `"undefined"` if all else fails

### 4.2 Outbound Service Authentication

Calls to `nexpay-claim-code-svc` and `nexpay-config-svc` use plain HTTP on the internal Container Apps network (e.g., `http://ca-nexpay-claim-code-svc-qa`). There is no service-to-service JWT or mTLS. The security assumption is that the ACA internal network is trusted (network perimeter security). For a PCI DSS Level 1 environment, this should be reviewed: if the CDE boundary includes these internal calls, mTLS or service tokens are required by PCI DSS Requirement 4.2.1.

### 4.3 Secret Zero Pattern

`AZURE_CLIENT_ID` is the only secret required at container startup. All other secrets flow through the Managed Identity chain (ACA managed identity → Key Vault → App Configuration). There are no static passwords in any YAML file.

## 5. Key Technical Decisions and Rationale

### 5.1 Virtual Threads over Reactive

The team chose Project Loom virtual threads (`spring.threads.virtual.enabled: true`) rather than Spring WebFlux. This provides the scalability benefits of non-blocking I/O without the complexity of reactive programming. With Java 25, virtual threads are stable and production-ready. The trade-off is that any blocking call (e.g., Redis, downstream HTTP) will park the virtual thread rather than blocking an OS thread, which is acceptable.

### 5.2 RestClient over WebClient

`RestClient` (synchronous, virtual-thread-compatible) is used rather than `WebClient` (reactive). This aligns with the virtual threads choice and keeps the code imperative and easier to debug.

### 5.3 Generated OpenAPI Clients

Both downstream client modules use OpenAPI generator to produce type-safe client stubs from the server's `openapi.yml`. This ensures that API contract changes in `nexpay-config-svc` or `nexpay-claim-code-svc` are detected at compile time rather than at runtime.

## 6. Known Technical Debt and Recommendations

| Item | File | Recommendation |
|---|---|---|
| `otel-grpc:1.0.0-SNAPSHOT` dependency | `pom.xml` line 44 | Promote to a release artifact before prod |
| No `-Xmx` JVM cap | `Dockerfile` ENV JAVA_TOOL_OPTIONS | Add `-XX:MaxRAMPercentage=75` |
| Container runs as root | `Dockerfile` | Add `RUN adduser -S nexpay && USER nexpay` |
| `env` actuator endpoint exposed | `application.yaml` line 43 | Remove `env` from `exposure.include` |
| No circuit breaker | `RestClientConfig.java` | Wrap RestClient with Resilience4j |
| Internal calls plain HTTP | `application-qa.yaml` line 57-58 | Evaluate mTLS or JWT service tokens for CDE paths |
| Snapshot dependency | `pom.xml` | Pin `otel-grpc` to a release version |
| No structured logging format | `application.yaml` | Add `logging.structured.format.file: logstash` |
