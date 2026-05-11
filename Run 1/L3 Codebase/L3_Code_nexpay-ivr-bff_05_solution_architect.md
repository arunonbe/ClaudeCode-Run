# nexpay-ivr-bff — Solution Architect View

## Technical Architecture

- **Language**: Java 25 (early-access)
- **Framework**: Spring Boot (from `nexpay-parent:0.2.8-SNAPSHOT`)
- **Web layer**: Spring MVC; virtual threads enabled (`spring.threads.virtual.enabled: true`)
- **Cache**: Jedis (Redis client) with `JedisPool`; SSL in QA/production
- **Auth downstream**: `RestClientConfig` configures HTTP client for `nexpay-auth-svc`; `AsyncConfig` configures async task executor
- **JWT**: `nimbus-jose-jwt:10.9` declared — JWT parsing capability (usage in controllers not yet implemented)
- **OTel**: `com.onbe.otel:otel-grpc:1.0.0-SNAPSHOT` — internal gRPC-based OTel exporter
- **Config**: Azure App Configuration + Key Vault via Spring Cloud Azure
- **API validation**: Jakarta Bean Validation (`@NotBlank`, `@NotNull`, `@Valid`)

## Module Layout

```
nexpay-ivr-bff/
├── nexpay-ivr-api/
│   └── model/
│       ├── IvrCustomerInquiryRequest.java   # Request model with validation
│       └── IvrCustomerInquiryResponse.java  # Response model with SelectedFields map
├── nexpay-ivr-boot/
│   ├── Dockerfile
│   ├── NexpayIvrBffApplication.java
│   └── exception/ErrorExceptionHandlers.java
├── nexpay-ivr-client/                        # Client library (content not fully scanned)
└── nexpay-ivr-impl/
    ├── config/
    │   ├── AsyncConfig.java
    │   ├── ImplementationConfig.java         # Registers AuditFilter
    │   ├── RedisConfig.java                  # JedisPool bean
    │   ├── RestClientConfig.java             # HTTP client for auth service
    │   └── ServiceProperties.java            # nexpay.services.endpoints config
    ├── controller/
    │   └── FsCustomerInquiryController.java  # STUB — hardcoded responses
    ├── dummy/
    │   └── DummyController.java              # In production main source
    ├── filter/
    │   └── AuditFilter.java                  # OTel baggage actor propagation
    └── health/
        └── ApplicationHealthIndicator.java
```

## API Surface

### REST Endpoints (port 8080)

| Method | Path | Auth | Status |
|---|---|---|---|
| `POST` | `/fs/customer/v4/inquiry` | `x-api-key` + `x-api-secret` headers | **STUB** — hardcoded response |
| `GET` | `/dummy/*` (presumed) | Unknown | Present in `DummyController` |

### Management Endpoints (port 8081)
`health`, `info`, `metrics`, `prometheus`, `startup`, `env`

### External APIM Publication
- Service publishes its OpenAPI spec to external Azure APIM (`PUBLISH_TO_APIM: true`, `EXTERNAL_APIM: true`)
- This means the stub API is visible to external consumers through APIM

## Security Posture

### Authentication / Authorization
- **`x-api-key` + `x-api-secret` headers** required on `POST /fs/customer/v4/inquiry` — validated structurally (missing = HTTP 401) but **not validated against any secret store** in the current stub implementation. The values are extracted as `String apiKey, String apiSecret` but not checked.
- **No JWT validation implemented** despite `nimbus-jose-jwt:10.9` being a declared dependency.
- **No Spring Security configuration** visible in scanned source.
- The `AuditFilter` extracts actor ID from JWT claims if available, but does not validate the JWT.

### Cryptography
- **Redis**: SSL supported (`redis.ssl: true`); `JedisPool` constructor uses SSL flag correctly when `password != null && !password.isBlank()`. However, when no password is provided (non-SSL path), the SSL flag is ignored — local/dev Redis is unencrypted.
- **JWT library present but unused**: `nimbus-jose-jwt` is a dependency but no JWT validation code is in the scanned controllers.

### Secrets
- Redis password from Azure Key Vault via App Configuration — correct pattern.
- `AUTH_SERVICE_URL` from environment variable.
- API keys (`x-api-key`, `x-api-secret`) are received as request headers but not validated against a stored secret — this is the most critical security gap.

### Hardcoded Sensitive Data (Critical)
In `FsCustomerInquiryController.java` lines 49–62, the following values are hardcoded in the production controller:
```java
selectedFields.put("SOCL_SCRT_ID", "987654321");        // 9-digit SSN-format value
selectedFields.put("ACCT_ID", "5424092085370868   ");   // 16-digit card-number-format value
selectedFields.put("BRTH_DT", "2001-01-01");            // Date of birth
selectedFields.put("HOME_PHON_ID", "6101234567         ");
selectedFields.put("DDA_ID", "0401942000002454 ");      // DDA account number
```
These are stub values but their format mirrors real PCI/PII data. A PAN format value in production source code triggers PCI DSS scan findings.

### CVE Assessment
- **nimbus-jose-jwt 10.9**: Recent version; low CVE risk but unused — should be either activated or removed.
- **Java 25 (EA)**: No official LTS security patch schedule.
- **`nexpay-parent:0.2.8-SNAPSHOT`** and **`otel-grpc:1.0.0-SNAPSHOT`**: Non-deterministic transitive dependencies.
- **Jedis**: Current major version; check for Redis deserialization CVEs in specific version.

## Technical Debt

| Item | File | Severity |
|---|---|---|
| Hardcoded PAN-format value `5424092085370868` | `nexpay-ivr-impl/.../FsCustomerInquiryController.java` | **Critical** — PCI DSS scan will flag |
| Hardcoded SSN-format value `987654321` | `nexpay-ivr-impl/.../FsCustomerInquiryController.java` | **Critical** — GLBA/PII risk |
| Hardcoded DDA `0401942000002454` | `nexpay-ivr-impl/.../FsCustomerInquiryController.java` | **Critical** — financial ID in source |
| API key not validated against secret store | `FsCustomerInquiryController.java` lines 27–29 | **Critical** — auth bypass in stub |
| `DummyController` in main source | `nexpay-ivr-impl/.../dummy/DummyController.java` | High — unexplained endpoint exposed |
| JWT present as dependency but not used | `pom.xml` | High — either validate or remove |
| Java 25 (non-LTS EA) | Root `pom.xml` | High |
| `nexpay-parent:0.2.8-SNAPSHOT` | Root `pom.xml` | High |
| `otel-grpc:1.0.0-SNAPSHOT` | Root `pom.xml` | High |
| External APIM exposure of stub | `deployment.yml` | High — external callers get fake data |
| SSL not applied when no Redis password | `RedisConfig.java` lines 44–47 | Medium — SSL ignored on non-password path |
| No Redis TTL on cached entries | Not visible | Medium — data staleness |
| `spring.threads.virtual.enabled` + Jedis blocking | `application.yaml` | Medium — Jedis blocking calls on virtual threads |
| No ECS structured logging format | `application.yaml` | Low — differs from claim-code-svc pattern |

## Gen-3 Hardening Requirements

1. **Remove hardcoded PAN/SSN/DDA values** from `FsCustomerInquiryController.java` immediately
2. **Implement API key validation** against Azure Key Vault or a secrets store
3. **Implement JWT validation** using `nimbus-jose-jwt` and Azure Entra ID JWKS
4. **Complete the stub**: Wire to `nexpay-auth-svc` and cardholder profile service
5. **Remove `DummyController`** from production source
6. **Implement PAN masking**: Return first 6/last 4 only for `ACCT_ID`; never return full SSN
7. **Upgrade to Java 21 LTS**
8. **Stabilise SNAPSHOT dependencies**
9. **Migrate Redis client to Lettuce** for Project Loom compatibility
10. **Add Spring Security** with mTLS or OAuth2 for external caller authentication

## Code-Level Risks (File:Line References)

| Risk | File | Line |
|---|---|---|
| Hardcoded PAN-format card number | `nexpay-ivr-impl/src/main/java/com/onbe/nexpay/ivrbff/impl/controller/FsCustomerInquiryController.java` | 55 |
| Hardcoded SSN-format value | `nexpay-ivr-impl/src/main/java/com/onbe/nexpay/ivrbff/impl/controller/FsCustomerInquiryController.java` | 53 |
| Hardcoded DDA value | `nexpay-ivr-impl/src/main/java/com/onbe/nexpay/ivrbff/impl/controller/FsCustomerInquiryController.java` | 62 |
| Hardcoded date of birth | `nexpay-ivr-impl/src/main/java/com/onbe/nexpay/ivrbff/impl/controller/FsCustomerInquiryController.java` | 50 |
| API key received but not validated | `nexpay-ivr-impl/src/main/java/com/onbe/nexpay/ivrbff/impl/controller/FsCustomerInquiryController.java` | 27–29 |
| SSL flag ignored without password | `nexpay-ivr-impl/src/main/java/com/onbe/nexpay/ivrbff/impl/config/RedisConfig.java` | 44–47 |
| `DummyController` in production src | `nexpay-ivr-impl/src/main/java/com/onbe/nexpay/ivrbff/impl/dummy/DummyController.java` | All |
| Java 25 in Dockerfile | `nexpay-ivr-boot/Dockerfile` | 1 |
| `--enable-native-access=ALL-UNNAMED` | `nexpay-ivr-boot/Dockerfile` | 16 |
