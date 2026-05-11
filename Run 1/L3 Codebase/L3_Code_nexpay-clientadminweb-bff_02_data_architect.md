# nexpay-clientadminweb-bff — Data Architect View

## 1. Data Architecture Overview

`nexpay-clientadminweb-bff` is a **stateless** BFF. It does not own a persistent data store of its own; it orchestrates data from downstream services and uses Redis as a session/cache layer. This is the correct pattern for a BFF in a cloud-native microservices architecture: it avoids duplicating canonical data and keeps the BFF deployable independently.

## 2. Data Stores

### 2.1 Redis (Azure Cache for Redis)

**Purpose**: Session caching, affiliate data caching, content caching.

**Configuration** (from `application.yaml` and `application-qa.yaml`):

| Property | Local Default | QA |
|---|---|---|
| Host | `localhost` | Injected via Azure App Configuration |
| Port | `6379` | `6380` (TLS) |
| SSL | `false` | `true` |
| Timeout | `5000ms` | `5000ms` |
| Pool max-active | `10` | `10` |

Key naming conventions (`application-qa.yaml` lines 62–64):
- `clientadminweb:affiliate` — affiliate-scoped data
- `clientadminweb:content` — content data

The Spring Lettuce pool is configured with `max-idle: 4`, `min-idle: 4`, `max-active: 10` (`application.yaml` lines 33–36). TLS is enforced in QA via `ssl.enabled: true` (`application-qa.yaml` line 39), which is correct for Azure Cache for Redis (port 6380).

**Data classification**: Redis keys store derived/cached representations of business objects. No PAN, CVV, or PII should be stored in Redis; however, there is no enforced serialisation filter in the codebase at the time of analysis to guarantee this. A Redis data classification review is recommended.

### 2.2 No Owned Relational Database

The BFF has no JPA/Hibernate configuration and no Flyway migrations, confirming it owns no relational schema. All relational data is delegated to downstream services (`nexpay-config-svc` for program/country data).

## 3. Data Models (API Contract)

### 3.1 Data Received from `nexpay-config-svc`

The BFF consumes three entities via generated OpenAPI client (`nexpay-clientadminweb-config-client-api`):

- **`ProgramModalityDetail`** (`ConfigSvcClient.java` line 45) — fields likely include modality type, currency, processor routing rules.
- **`ProgramRegistrationSettings`** (line 62) — self-registration toggles, OTP configuration, address validation strictness.
- **`ProgramCountryConfig`** (line 77) — list of countries enabled for a program, with address format configuration.

The actual JSON schema is generated from the `nexpay-config-svc` OpenAPI spec (`openapi.yml`) and compiled into the client module. The `pom.xml` references `nimbus-jose-jwt:10.9` for JWT handling — this is a security library dependency used for token validation.

### 3.2 Data Received from `nexpay-claim-code-svc`

Client module `nexpay-clientadminweb-claimcode-client-api` wraps the claim code service API. Exact model fields are in the generated stub (`ClaimCodeSvcClient.java` line 34). Claim codes are short-lived, program-scoped tokens — they are not payment card data and do not fall within PCI DSS CDE scope. However, claim codes may be linked to cardholder disbursement events, making them sensitive business data.

## 4. Data Flow Diagram

```
Browser SPA
  [HTTPS via APIM]
    nexpay-clientadminweb-bff
      |-- Redis (cache)           [Azure Cache for Redis - TLS]
      |-- nexpay-claim-code-svc   [HTTP internal ACA network]
      |-- nexpay-config-svc       [HTTP internal ACA network]
```

Outbound calls to downstream services use `RestClient` instances configured in `RestClientConfig.java`. Each service has its own pre-configured `ApiClient` bean with dedicated connect/read timeouts (5s/10s defaults, `ServiceProperties.java` lines 63–64). There is no circuit-breaker or retry wrapper in the current code, which is a resilience gap.

## 5. Sensitive Data Handling

### 5.1 Actor Identity in OTEL Baggage

The `AuditFilter` extracts `actor.id` from the JWT and propagates it as an OpenTelemetry baggage entry (`AuditFilter.java` lines 99–104). The baggage value travels through distributed trace spans to downstream services. This means that the admin user's email address (a PII field) is present in trace data that flows to Dynatrace.

**Recommendation**: Evaluate whether Dynatrace's data retention and access controls meet GDPR/CCPA requirements for the email address stored in trace telemetry. Consider hashing the actor.id before insertion into baggage if the trace data is stored long-term.

### 5.2 Log Sanitisation

`AuditFilter.sanitizeForLogging()` (lines 228–242) and `sanitizeForBaggage()` (lines 123–138) strip ISO control characters from string values before logging or baggage insertion, preventing log injection attacks. This is a positive security control.

### 5.3 Redis Key Design

Keys use prefixed namespaces (`clientadminweb:affiliate`, `clientadminweb:content`). Without encryption at rest on the Redis tier, cached objects are visible in plaintext to anyone with Redis access credentials. The `REDIS_PRIMARY_ACCESS_KEY` secret is managed in Azure Key Vault (`kv-secrets.json` line 29), which is appropriate.

## 6. Data Retention and Lifecycle

- **Redis**: TTL policies are not explicitly configured in this BFF's YAML files. The `idempotency` section is commented out (`application.yaml` lines 57–63), meaning idempotency key TTL defaults (24h) apply if the platform library is on the classpath.
- **Audit traces**: Stored in Dynatrace with `sampling.probability: 1.0` — all requests are traced (relevant for `nexpay-config-svc` but the pattern is shared). Retention is governed by Dynatrace contract.
- **No PII storage**: The BFF does not own a persistent store, so there is no GDPR data subject access request (DSAR) surface in this service.

## 7. Data Architecture Risks and Recommendations

| Risk | Severity | Recommendation |
|---|---|---|
| No circuit-breaker on downstream calls | Medium | Add Resilience4j or Spring Retry on `RestClient` calls |
| Actor email in Dynatrace traces | Medium | Hash or pseudonymise actor.id in OTEL baggage |
| Redis data classification undefined | Medium | Document and enforce what can/cannot be cached |
| Actuator `env` endpoint exposes config | High | Restrict management port to internal subnet only |
| No per-program authorisation enforced in BFF | High | Add programId-based RBAC check before delegating to config-svc |
