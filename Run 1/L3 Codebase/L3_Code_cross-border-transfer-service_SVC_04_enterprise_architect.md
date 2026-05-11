# Enterprise Architect View — cross-border-transfer-service_SVC

## 1. Platform Generation and Heritage

| Dimension | Assessment |
|---|---|
| Generation | Generation 2 (Gen2): Spring Boot microservice, containerized, multi-module Maven, Java 21 compile target — but with significant Gen1 traits (in-process cache, config in YAML files, no secrets manager, no service mesh, no distributed tracing) |
| Lineage | Originally developed under Wirecard/Northlane branding (package `com.wirecard.crossbordertransferservice`, GitLab origin `northlane/development/...`, legacy DB hostname `wirecard.sys`) — acquired and operated by Onbe |
| Tech debt age | QA config still references Wirecard-era infrastructure; partner ID in `TokenServiceImpl.java` line 26 is still `"wirecard"` hardcoded (`private static final String PARTNER = "wirecard"`) |
| Deployment model | Containerized (Docker, Azul Zulu JDK 21 Alpine base), deployed via GitHub Actions to Onbe's container platform; legacy GitLab CI retained |

## 2. Domain Classification

- **Domain**: Payments — Cross-Border / FX Remittance
- **Subdomain**: External Payment Gateway Integration (Cambridge/Corpay)
- **Bounded Context**: Cross-Border Transfer — owns the complete lifecycle of FX spot rates, wire transfer instructions, remitter/beneficiary profiles, and reconciliation data within Onbe's disbursement platform
- **Context Map**: CBTS is a supplier of cross-border transfer capability to Onbe's orchestration layer (upstream callers are not in this repo; they call CBTS REST APIs directly). CBTS is a customer of Cambridge Global Payments (downstream).

## 3. Architectural Role Within Onbe Platform

```
[Onbe Disbursement Platform / Orchestration Layer]
              │
              │  REST (HTTP Basic Auth)
              ▼
   ┌─────────────────────────────┐
   │  cross-border-transfer-svc  │  ← This repository
   │  (Spring Boot, Java 21)     │
   └──────────┬──────────────────┘
              │ HTTPS (Feign + OkHttp)  │  SFTP (PGP-encrypted)
              ▼                          ▼
   Cambridge Global Payments      Cambridge / eCount SFTP
   (Corpay) REST API               (Recon / Reject files)
              │
              ▼
   SQL Server (CBTS DB)  ←→  Spring Batch jobs
```

CBTS is the sole integration point to Cambridge. No other Onbe service should be calling Cambridge directly for the transfer capabilities managed here. The service acts as an Anti-Corruption Layer (ACL) translating Onbe's internal transfer model to Cambridge's quote/book/instruct deal model.

## 4. Service Dependencies

### Outbound (CBTS depends on)
| Dependency | Protocol | Purpose | Resilience Pattern |
|---|---|---|---|
| Cambridge Global Payments REST API | HTTPS (Feign/OkHttp) | FX rates, transfer instruction, beneficiary/remitter CRUD, token issuance | Resilience4j circuit breaker (9 instances) |
| SQL Server `CBTS` database | JDBC (HikariCP) | Persistent state for all domain entities | Connection pool (max 50), 30s transaction timeout |
| Cambridge SFTP | SSH/SFTP | Inbound recon/reject files; outbound processed files | Spring Integration SFTP, CachingSessionFactory |
| eCount SFTP | SSH/SFTP | Outbound reject file delivery | Spring Integration SFTP |
| Spring Cloud Config Server | HTTP | Externalized runtime configuration | `optional:configserver:` prefix — falls back gracefully |
| Mailgun SMTP | SMTP/587 | Batch job completion/failure email notifications | No retry/fallback in code |

### Inbound (depends on CBTS)
- Onbe's disbursement orchestration layer (callers not in this repository) via `POST/GET /remitters`, `/beneficiaries`, `/rates`, `/transfers`
- Batch trigger scripts (shell scripts + cron or CI scheduler)

## 5. Integration Patterns

| Pattern | Implementation | Location |
|---|---|---|
| Anti-Corruption Layer | `CambridgeClient` Feign interface translates Cambridge's API model to CBTS domain objects | `cross-border-transfer-service-cambridge-client` |
| Circuit Breaker | Resilience4j on all Cambridge-facing operations | `TokenServiceImpl`, `SpotServiceImpl`, `CancelRateServiceImpl` etc. |
| Repository Pattern | Spring Data JPA repositories for all domain aggregates | `cross-border-transfer-service-persistence` |
| Factory Pattern | Request/response factories for Cambridge DTOs | `BeneficiaryRequestFactoryImpl`, `TransferRequestFactoryImpl`, `SpotRateRequestFactoryImpl` etc. |
| Handler Pattern | Request handlers layer between controller and service | `CreateTransferHandlerImpl`, `BookRateHandlerImpl` etc. in `rest-controller` |
| Marshaller Pattern | Entity↔DTO mapping layer | `BeneficiaryMarshallerImpl`, `TransferMarshallerImpl`, `RateMarshallerImpl` etc. |
| Batch ETL | Spring Batch for file-based data exchange (Reader/Processor/Writer) | `cross-border-transfer-service-batch` |
| File Encryption | BouncyCastle PGP encrypt/decrypt tasklets | `PGPEncryptionTasklet`, `PGPDecryptionTasklet` |
| JWT Token Authentication | HMAC-SHA256 JWT for Cambridge partner auth; client-level OAuth2 token exchange | `JwtTokenCreatorImpl`, `TokenServiceImpl` |
| Caching | EhCache 3 (JVM heap) for beneficiary rules per country/currency | `ehcache3.xml`, `GetBeneficiaryRulesServiceImpl` |

## 6. Multi-Tenancy / Brand Model

CBTS supports multiple Onbe client brands through a BIN-prefix → client-name → Cambridge client-config mapping:

1. A `brands` YAML block maps 40+ BIN prefixes to named clients (Disney, RCCL, OnbeSunrise, OnbeFITB, ChicagoParkDistrict, Brightspot, Onbe, RCCLNew, DisneyNew, DCL, OnbeSunriseBrightspot).
2. `BrandsConfig.forBrand(brand)` resolves the client name.
3. `CambridgeConfig.getClients()` provides Cambridge-specific `ClientConfig` (id, code, signature, settlementAccountId) per client and per `RequestType` (one-time vs. recurring).
4. `TokenServiceImpl.getClientTokenAndClientConfig()` assembles the correct token for each request based on brand + request type.

This design allows a single CBTS instance to serve multiple Onbe prepaid programs without code changes — only configuration changes.

## 7. API Surface

| Endpoint | Method | Handler | Description |
|---|---|---|---|
| `/remitters` | PUT | `CreateEditRemitterHandlerImpl` | Create or update remitter |
| `/remitters/{remitterId}` | GET | `GetRemitterHandlerImpl` | Retrieve remitter by ID |
| `/remitters/{remitterId}/deactivate` | POST | `DeactivateRemitterHandlerImpl` | Soft-deactivate remitter |
| `/beneficiaries` | PUT | `CreateEditBeneficiaryHandlerImpl` | Create or update beneficiary |
| `/beneficiaries/{beneficiaryId}` | GET | `GetBeneficiaryHandlerImpl` | Retrieve beneficiary by ID |
| `/beneficiaries/{beneficiaryId}/deactivate` | POST | `DeactivateBeneficiaryHandlerImpl` | Soft-deactivate beneficiary |
| `/beneficiaries/beneficiary-rules` | GET | `GetBeneficiaryRulesHandlerImpl` | Country/currency validation rules (cached) |
| `/beneficiaries/search-beneficiary-banks` | GET | `SearchBeneficiaryBanksHandlerImpl` | Bank directory search |
| `/rates` | POST | `CreateRateHandlerImpl` | Request FX spot rate |
| `/rates/{rateId}` | GET | `GetRateHandlerImpl` | Retrieve rate by ID |
| `/rates/{rateId}/book` | POST | `BookRateHandlerImpl` | Lock/book a rate |
| `/rates/{rateId}/cancel` | POST | `CancelRateHandlerImpl` | Cancel a rate |
| `/transfers` | POST | `CreateTransferHandlerImpl` | Execute a transfer |
| `/transfers/{transferId}` | GET | `GetTransferHandlerImpl` | Retrieve transfer by ID |

All secured endpoints use HTTP Basic Authentication (`SecurityConfiguration.java`). OpenAPI/Swagger UI available via springdoc-openapi v2.6.0 (`OpenApiConfiguration.java`).

## 8. Technology Stack

| Layer | Technology | Version |
|---|---|---|
| Language | Java | 21 |
| Framework | Spring Boot | via `prepaid-parent:6.0.12` |
| REST | Spring MVC | — |
| ORM | Spring Data JPA / Hibernate | — |
| HTTP Client | OpenFeign + OkHttp | — |
| Circuit Breaker | Resilience4j | — |
| Batch | Spring Batch | — |
| File Integration | Spring Integration SFTP | — |
| PGP | BouncyCastle | — |
| Cache | EhCache 3 / JSR-107 | — |
| API Docs | springdoc-openapi | 2.6.0 |
| JWT | auth0 java-jwt | — |
| DB | SQL Server | — |
| DB Migration | Liquibase | — |
| Build | Maven | 3.x (wrapper) |
| Container | Docker (Azul Zulu JDK 21 Alpine) | — |
| CI/CD | GitHub Actions + Onbe shared workflow | — |
| Utilities | Internal `sftp-common-utilities:2.0.0`, `utilities:2.0.0`, `correlation-web:2.0.1` | Internal |

## 9. Architectural Status

| Dimension | Status |
|---|---|
| Active development | Yes — version `3.2.0-SNAPSHOT`; multiple recent Liquibase changesets |
| Production readiness | Partially — containerized and CI/CD present; significant security gaps block full enterprise readiness |
| Secrets management | Not implemented — all secrets in YAML files in Git |
| Distributed tracing | Not implemented — correlation ID propagated but no trace exporter |
| Service mesh | Not implemented — no mTLS, no sidecar proxy other than inactive Dapr config |
| API versioning | Version 1 only; API media type `application/vnd.crossbordertransferservice.api.v1+json` |
| OpenAPI spec | Published via springdoc (Swagger UI at runtime) and pushed to APIM on deploy |
| Test coverage | Unit tests present for most classes; integration tests in `cross-border-transfer-service-qa`; **all skipped in CI** |

## 10. Blockers and Architectural Concerns

| Blocker | Priority | Recommendation |
|---|---|---|
| Cambridge credentials and PGP private key in Git | P0 | Rotate all credentials immediately; migrate to Vault or Azure Key Vault; remove from repository |
| No OFAC/sanctions screening | P0 | Implement pre-submission sanctions check against OFAC SDN and FinCEN lists; CBTS is the instructing entity |
| In-memory HTTP Basic Auth (`{noop}` password) | P1 | Migrate to OAuth2/OIDC with Onbe's identity platform; in-memory auth does not support rotation or MFA |
| PGP private key in Git | P0 | Revoke and replace; manage via secrets store |
| No distributed tracing | P2 | Add OpenTelemetry agent or Micrometer Tracing for end-to-end observability |
| Tests skipped in all CI pipelines | P1 | Re-enable test execution; add test coverage gate before deployment |
| Legacy `wirecard.sys` infrastructure references | P2 | Confirm whether QA still points at legacy Wirecard infrastructure; migrate to Onbe-owned infrastructure |
| `TokenServiceImpl` hardcodes partner name `"wirecard"` | P2 | Parameterize partner name; `TokenServiceImpl.java` line 26 |
| `show-sql: true` in QA config | P2 | Disable for any environment where logs are shipped externally; SQL output can contain sensitive data |
| Dapr sidecar present but unused | P3 | Remove or activate; dead infrastructure adds complexity and CVE exposure |
