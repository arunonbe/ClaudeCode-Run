# nexpay-config-svc — Enterprise Architect View

## 1. Role in NexPay Architecture

`nexpay-config-svc` is the **configuration domain service** — a first-class microservice that owns the data model for payment program configuration. It is a structural dependency of the entire NexPay platform: without it, no other service can determine which countries, currencies, modalities, or registration flows apply to a given program.

This is an architectural **shared kernel** — a service that multiple bounded contexts depend on. This creates a dependency risk: if config-svc is unavailable or returns incorrect data, it will affect order processing, card issuance, recipient registration, and the admin portal simultaneously. The service must therefore be treated as a critical, high-availability component despite its non-transactional appearance.

## 2. Gen-3 Architecture Compliance Assessment

| Principle | Status | Evidence |
|---|---|---|
| Database-per-service | Achieved | Dedicated `config` database in PostgreSQL |
| API-first (OpenAPI) | Achieved | `nexpay-config-api` module with OpenAPI spec |
| No shared database | Achieved | No cross-service JPA relationships |
| Managed Identity DB auth | Achieved | `passwordless-enabled: true`, Azure AD plugin |
| Audit trail | Achieved | Hibernate Envers with source/reason tracking |
| Flyway schema management | Achieved | `db/migration/V1–V10__*.sql` |
| Testcontainers for integration tests | Achieved | `TestContainerConfig.java` in test modules |
| OTEL observability | Achieved | Dynatrace OTLP HTTP traces/metrics/logs |
| Idempotency at API level | Achieved | Redis-based distributed lock (platform library) |
| Feature flags | Partially | `AZURE_APP_CONFIG_FEATURE_FLAGS_ENABLED` var present, disabled by default |

## 3. Service Classification

From an enterprise classification perspective, config-svc sits in the **Platform Services** tier (not the Business Services tier):

```
Presentation Layer:    nexpay-clientadminweb-bff, nexpay-ivr-bff, nexpay-recipientweb-bff
Business Layer:        nexpay-order-orchestrator, nexpay-cardprocessor-svc, nexpay-recipient-profile-svc
Platform Layer:        nexpay-config-svc  ← HERE
                       nexpay-auth-svc
Infrastructure Layer:  nexpay-iac
```

Platform services change infrequently (program configurations are set during client onboarding, then updated occasionally). They should have high read throughput and be write-protected (command/query separation is appropriate here — CQRS with a read replica could be evaluated for high-scale production).

## 4. Cross-Service Dependencies and Fan-Out Risk

Config-svc is consumed by at minimum 4 other NexPay services. A config-svc outage or performance degradation creates a cascading failure across the entire NexPay platform. Mitigation strategies:

1. **Client-side caching**: BFF layer should cache config data in Redis with appropriate TTLs. The `clientadminweb:content` Redis prefix suggests this is planned.
2. **Read replicas**: For production, a PostgreSQL read replica should serve GET endpoints while mutations go to the primary.
3. **Circuit breakers in consumers**: Each consuming service should wrap config-svc calls with a circuit breaker that returns a stale cached value on open-circuit.
4. **SLA definition**: Config-svc must have a defined SLA (e.g., 99.9% availability, <100ms p99 read latency) that is monitored via Dynatrace SLO dashboards.

## 5. Data Governance

The config service is the authoritative source for:
- Which countries are PCI/compliance-approved for Onbe disbursements
- Which payment modalities are active per program (relevant for OFAC/sanctions screening — disabled modalities should not be offered)
- Program registration settings (relevant for identity verification/KYC requirements)

Changes to this data have regulatory implications. The Hibernate Envers audit trail with `source` and `reason` fields (V10 migration) is the right control, but it must be monitored: a SonarQube or Splunk rule should alert on program configuration changes outside of approved change windows.

## 6. Security Architecture

### 6.1 Network Position

Config-svc is `external_enabled: false` — it is not reachable from the internet or through APIM. It is accessible only to services within the same Container Apps Environment. This is the correct position for a service that manages program configuration.

### 6.2 Authentication Gap

Despite the internal-network isolation, there is no service-to-service authentication on the config-svc API. Any service inside the ACA environment can make arbitrary API calls to config-svc without presenting credentials. In a PCI DSS CDE, Requirement 6.4 (protect public-facing web applications) and the principle of defence in depth suggest that internal services should still validate caller identity.

**Recommendation**: Implement Spring Security with JWT bearer token validation on config-svc, where the JWT is a service account token issued by the platform's auth service. The BFF's managed identity can obtain a token via Managed Identity credential flow.

### 6.3 Key Vault RBAC Scope

The ACA user-assigned managed identity (`msi-nexpay-qa`) has `Key Vault Secrets User` role on the entire vault (`container-apps/main.tf` lines 38–42). This grants access to FIS, Thredd, Redis, JWT, and SQL secrets — far more than config-svc requires. Config-svc likely only needs the Redis password and database connection parameters.

**Recommendation**: Assign individual Container App managed identities per service with scoped Key Vault secret access. This is the least-privilege principle required by PCI DSS Requirement 7.

## 7. Roadmap and Maturity

The migration history (V1–V10) and the `pig.template` file (possibly a "pretty-print integration guide" template) suggest the service is actively developed and maturing. The presence of `INTEGRATION_TESTING.md` at the root indicates the team is investing in integration testing documentation — a positive indicator of engineering maturity.

The feature flag support (`app_config_feature_flags_enabled`) is not yet activated (`default: false`). When enabled, this will allow progressive feature rollout for new config capabilities without code deployments — a Gen-3 best practice that should be enabled for production use cases such as enabling new payment modalities.
