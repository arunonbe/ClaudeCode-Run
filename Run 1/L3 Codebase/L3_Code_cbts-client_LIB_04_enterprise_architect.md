# cbts-client_LIB — Enterprise Architect View

## Platform Generation (Gen-1/Gen-2/Gen-3)

**Assessment: Gen-1 / Legacy**

Evidence:
- The Javadoc comment in `CBTSClient.java` (lines 43–46) explicitly states: *"CBTSClient is intended for legacy Prepaid applications, such as OP and batch."* and *"Since OP and xPlatform can only support up to Java 1.7, it has to be developed as Java 1.7 only."* (Note: the code has since been updated to Java 21 per `pom.xml`, but the architectural intent remains legacy integration.)
- Originated as a Wirecard-era library (`com.wirecard.crossbordertransferservice` package namespace, `wirecard.sys` hostnames in test config).
- Designed to bridge legacy OP/batch systems to a third-party FX provider (Cambridge Global Payments via CBTS) — a Gen-1 pattern of wrapping external provider APIs for monolithic callers.
- No Spring, no reactive patterns, no service mesh integration, no event-driven messaging. Plain synchronous HTTP via `javalite-common`.
- The parent POM (`prepaid-parent:6.0.13`) places this squarely in the legacy prepaid platform lineage.

## Business Domain

**Global Payouts / International Disbursements**

This library sits at the intersection of:
- **Prepaid Card Programs** — funding source for the remitter (cardholder or program participant)
- **Cross-Border Payments** — FX rate acquisition and wire/EFT instruction to Cambridge Global Payments
- **Beneficiary Management** — recipient bank account and identity management

It supports Onbe's B2C disbursement use case for international recipients, covering: healthcare reimbursements, insurance claims, auto finance refunds, marketplace seller payouts, gig/creator payments, and consumer rebates that cross national borders.

## Role in Platform

`cbts-client_LIB` is a **shared infrastructure library** — a consumable JAR with no runtime server component. Its role in the Onbe platform:

```
┌─────────────────────────────────────────────────────────┐
│  Onbe Legacy Platform                                    │
│                                                         │
│  ┌─────────────┐    ┌──────────────────┐               │
│  │  OP Portal  │    │  Batch Processor │               │
│  │  (legacy)   │    │  (legacy)        │               │
│  └──────┬──────┘    └────────┬─────────┘               │
│         │  embeds JAR        │  embeds JAR              │
│         └─────────┬──────────┘                          │
│                   │                                     │
│          ┌────────▼────────┐                            │
│          │  cbts-client    │  ← this library            │
│          │  LIB (JAR)      │                            │
│          └────────┬────────┘                            │
└───────────────────┼─────────────────────────────────────┘
                    │ HTTPS REST (Basic Auth)
                    ▼
          ┌─────────────────────┐
          │  CBTS Service       │  (Onbe-managed middleware)
          └─────────┬───────────┘
                    │ SWIFT/banking rails
                    ▼
          ┌─────────────────────┐
          │  Cambridge Global   │  (third-party FX provider)
          │  Payments           │
          └─────────────────────┘
```

## Dependencies

### Upstream (consumed by this library)
| Dependency | Version | Type |
|---|---|---|
| `com.parents:prepaid-parent` | 6.0.13 | Maven parent POM / BOM |
| `org.javalite:javalite-common` | (BOM-managed) | HTTP client + JSpec test assertions |
| `com.google.code.gson:gson` | (BOM-managed) | JSON serialisation |
| `commons-lang:commons-lang` | (BOM-managed) | String utilities / ToStringBuilder |
| Lombok | (BOM-managed, `@Data`, `@Slf4j`) | Code generation |
| SLF4J | (BOM-managed, via Lombok) | Logging facade |

### Downstream (who consumes this library)
Based on the Javadoc, the known consumers are:
- **OP (Online Portal)** — legacy prepaid portal for cardholders and program managers
- **Batch processing systems** — back-office automated disbursement pipelines

The library is published to `maven.pkg.github.com/onbe/onbe_maven_releases`, meaning any Onbe Maven project can declare it as a dependency.

### External Service Dependencies
| Service | Protocol | Authentication |
|---|---|---|
| CBTS REST API (`cross-border-transfer-service`) | HTTPS (TLS 1.2, cert validation bypassed) | HTTP Basic Auth |
| Cambridge Global Payments | Internal to CBTS | Not visible to this library |

## Integration Patterns

| Pattern | Implementation | Assessment |
|---|---|---|
| **Synchronous HTTP REST client** | `javalite-common` `Http.get/post/put` with blocking I/O | Simple but blocking; no async/reactive support |
| **HTTP Basic Authentication** | `.basic(USERNAME, PASSWORD)` on every request | Credentials passed per-request; no token refresh |
| **Correlation ID propagation** | MDC → `CORRELATION-ID` header (lines 460–467) | Positive: enables distributed tracing through logs |
| **Custom versioned Accept/Content-Type** | `application/vnd.cross_border_transfer_service.v1+json` | Vendor-specific media type versioning; v1 only |
| **PUT-for-upsert pattern** | `createUpdateRemitter` and `createUpdateBeneficary` use HTTP PUT | Idempotent create-or-update; avoids separate create/update flows |
| **Location header ID extraction** | HTTP 201 response `Location` header parsed to extract new resource ID | Post-Azure-migration fix with `split("/")[5]` brittle path parsing (lines 191–197) |
| **Error response normalisation** | Hyphen stripping before JSON parse: `structuredError.replaceAll("-", "")` (line 450) | Fragile; could corrupt legitimate hyphenated values |
| **JSON serialisation** | Gson with `@SerializedName` annotation on `BeneficiaryRule.isRequired` | Minimal annotation usage; mostly relies on field name matching |

## Strategic Status

**Status: Active Legacy — Migration Candidate**

- The library remains in active use (SNAPSHOT version `2.1.5-SNAPSHOT` indicates ongoing development) and is a required component for international payout capabilities in legacy OP and batch systems.
- The Wirecard-origin package namespace (`com.wirecard.crossbordertransferservice`) and hostname references (`wirecard.sys`) indicate this was inherited during Onbe's acquisition/evolution from Wirecard and has not been fully rebranded.
- The package is not yet migrated to a Gen-2 or Gen-3 pattern (no Spring Boot, no OpenAPI client generation, no reactive/async, no Kubernetes-native config).
- A comment in the codebase notes the Azure migration has already occurred (line 186: "After azure migration, appGateway was not handling the port properly"), meaning the backing CBTS service has partially modernised but the client library has only received point fixes, not architectural upgrades.
- CodeQL scanning is in place (weekly), indicating security hygiene awareness. Dependabot is configured for weekly dependency updates.

## Migration Blockers

The following issues must be resolved before this library can be migrated to a Gen-3 pattern:

| Blocker | Detail | Effort |
|---|---|---|
| **Hardcoded credentials** | `USERNAME`/`PASSWORD` in `CBTSClient.java` lines 94–95; must be moved to a secrets vault (e.g., Azure Key Vault, HashiCorp Vault) | Medium |
| **TLS trust-all bypass** | `initSSLContext()` disables certificate validation JVM-wide; must use a proper trust store | Medium |
| **Wirecard package namespace** | `com.wirecard.crossbordertransferservice` throughout; needs namespace migration to `com.onbe.*` | Medium (pure refactor) |
| **Windows-1252 source encoding** | Must change to UTF-8 across `pom.xml` and source files; `IsoCurrencyCode.java` has corrupted characters | Low |
| **No integration test automation** | Integration tests require a live CBTS instance; no mock/stub server or contract tests exist, making CI validation difficult | High |
| **Synchronous blocking HTTP** | For high-throughput batch scenarios, a non-blocking HTTP client (e.g., Spring WebClient, OkHttp async) would be needed | High |
| **Brittle Location header parsing** | `split("/")[5]` in `createUpdateRemitter` (line 192) is fragile — any change in CBTS URL structure breaks ID extraction | Low |
| **Legacy `javalite-common` HTTP client** | Not a standard enterprise HTTP client; lacks retry, circuit-breaker, pooling, and connection management features | High |
| **No OpenAPI/Swagger contract** | No machine-readable API contract for CBTS; changes to the CBTS API surface can silently break this client | Medium |
| **PII in log output** | `Beneficiary.toString()` and IBAN logging must be redacted before adopting centralised log aggregation | Medium |
