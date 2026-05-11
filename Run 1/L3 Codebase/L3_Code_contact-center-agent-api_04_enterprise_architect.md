# contact-center-agent-api — Enterprise Architect View

## Platform Generation (Gen-1/Gen-2/Gen-3)

**Gen-2 / transitional toward Gen-3.**

Evidence for Gen-2 characteristics:
- Directly connects to legacy SQL Server databases (`cbaseapp`, `ecountCore`) with JDBC; these are the classic Onbe/ECount backend databases.
- Backend REST dependency on `ECount Core` (internal service at `nam.wirecard.sys:8084`), which itself is a legacy/Gen-2 orchestration layer for the ECount card processing platform.
- Uses `msal4j` (Microsoft Authentication Library for Java) suggesting integration with Azure AD/Entra identity — a Gen-2/Gen-3 pattern.
- OTP service is consumed via Dapr sidecar (`http://localhost:3500`), which is a Gen-3 microservices pattern.

Evidence for Gen-3 progression:
- Spring Boot 3.5.7 (Jakarta EE 10, Java 21 LTS).
- OpenAPI-first contract (`openapi-generator-maven-plugin`) with delegate pattern — clean API contract boundary.
- Azure App Configuration + Key Vault for secrets and config externalisation.
- Deployed to AKS with Dynatrace APM.
- GitHub Actions CI/CD with Pact broker registration.
- No XML Spring configuration; annotation-only, modern Spring idioms.

**Assessment**: This service is a greenfield Gen-3 service that wraps Gen-2 backend systems. It provides a modern, contract-driven API facade over `ECount Core` and `cbaseapp`, enabling AI/chatbot integration without exposing legacy internals. The residual Gen-2 dependency is the direct JDBC connection to legacy DBs and the synchronous ECount Core REST dependency.

---

## Business Domain

**Cardholder Servicing / Contact Centre Operations**

Sub-domain: AI-assisted contact-centre automation (Decagon integration). Specifically covers:
- Identity verification (OTP-based cardholder authentication).
- Account servicing (inquiry, card reissue, registration update, PIN reset, fund withdrawal).
- Audit & case management (comment submission and retrieval via cbaseapp `service_records`).

This service sits at the boundary between **external AI chat** (Decagon platform, `decagonapi.onbe.com`) and **internal payment processing** (ECount Core, cbaseapp).

---

## Role in Platform

| Dimension | Description |
|---|---|
| **Consumer** | Decagon AI chat widget / contact-centre agents (external via APIM) |
| **Provider** | Public REST API over APIM (`contact-center-agent-east`) |
| **Upstream dependencies** | ECount Core REST API, cbaseapp SQL Server, ecountCore SQL Server, OTP shared service (`OmOtpSvc`), Azure Key Vault, Azure App Configuration |
| **Downstream dependents** | None detected within this repo; single consumer is Decagon/APIM |
| **Data ownership** | This service **writes** to `cbaseapp.service_records` and `cbaseapp.api_request_audit_log`; it **reads** from `b2c_csa_detailscreen_general`, `partnerdetail`, and ecountCore tables |
| **Identity/Auth gateway** | This service IS the authentication gateway for the Decagon integration — it issues JWTs after OTP verification |

---

## Dependencies

### Upstream Runtime Dependencies

| Service | Interface Type | Coupling Strength |
|---|---|---|
| **ECount Core REST API** (`https://prod.nam.wirecard.sys:8084/service`) | OpenAPI-generated client (`ecountcore.yaml`) | **High** — all account, card, member, transfer operations route through this |
| **cbaseapp SQL Server** | JPA / JDBC (direct schema coupling) | **High** — writes service records, reads program metadata |
| **ecountCore SQL Server** | JPA / JDBC (direct schema coupling) | **Medium** — reads emboss history, profile labels |
| **OTP Shared Service** (`OmOtpSvc` via Dapr) | OpenAPI-generated client (`otpapi.yaml`) | **Medium** — required for cardholder authentication flow only |
| **Azure App Configuration** | Spring Cloud Azure | **Medium** — service will not start correctly without it (non-local) |
| **Azure Key Vault** | Spring Cloud Azure | **High** — secrets cannot be resolved without it |

### Shared Credential Risk
- DB credential names (`managepaymentapi-cbaseappdb-*`, `managepaymentapi-ecountcoredb-*`) are shared with at minimum `manage-payment-api` service. This represents a cross-service credential coupling that creates blast-radius risk during rotation.

### Pact Contract Dependencies
- Registered as `contact-center-agent-api` in the Pact broker.
- Consumer contract testing is not enforced server-side (`VERIFY_PROVIDER_PACT: false`).

---

## Integration Patterns

| Pattern | Implementation |
|---|---|
| **API Gateway / APIM** | External Azure APIM fronts the service (`EXTERNAL_APIM: true`). OpenAPI spec is published to APIM on every merge to main. |
| **OpenAPI-First Contract** | Three OpenAPI YAML specs drive code generation: public API, ECount Core client, OTP client. The `delegatePattern: true` config cleanly separates generated interfaces from business logic. |
| **Tri-mode Authentication** | Priority-ordered filter (`AuthenticationFilter`) supports JWT token, AES-encrypted DDA (CHAT channel), and plain DDA. Allows gradual migration from direct DDA access to token-based. |
| **Request Audit Log** | Filter-level capture to `api_request_audit_log` table. Decoupled from business logic via `RequestAuditLoggingFilter`. |
| **Dapr Service Invocation** | OTP service consumed via Dapr sidecar at `localhost:3500`. This abstracts the actual OTP service address and enables service discovery within AKS. |
| **Dual DataSource / Dual JPA Context** | Two independent JPA configurations (`CbaseJpaConfig`, `ECountJpaConfig`) with separate `EntityManagerFactory` and `TransactionManager` beans. This cleanly separates CDE from operational data. |
| **ThreadLocal Request Context** | `RequestContextHolder` (ThreadLocal pattern) propagates authenticated account/member context from filter to service layer without passing parameters. |
| **In-Process Cache** | Spring Cache (`ConcurrentMapCacheManager`) for `appProfileLabelTypes`. Scoped to single pod — not distributed. |
| **Begin/Commit Transfer** | Fund withdrawal uses a two-phase begin+commit pattern against ECount Core `TransferService`, providing transactional semantics for fund movement. |

---

## Strategic Status

**Active / New Development** — recently built (tags: `20260416`, `20260422`, `20260426` in `.git/refs/tags`).

Strategic assessment:
- This is a purposeful new capability enabling AI-driven contact-centre automation. It is strategically aligned with Gen-3 objectives.
- It is not a migration/rewrite of an existing service — it is a net-new integration layer.
- Its continued relevance depends on the Decagon AI platform contract. If Decagon is replaced or retired, the API surface needs re-evaluation.
- The service currently has no inbound dependencies other than Decagon/APIM, making it safe to evolve independently.

**Risks to strategic viability**:
- Direct JDBC coupling to `cbaseapp` and `ecountCore` databases (bypasses ECount Core API for some reads). This is a technical debt item that complicates future Gen-3 data domain ownership.
- `manage-payment-api` credential sharing suggests these services may need to be re-assessed as a cohesive domain boundary.

---

## Migration Blockers

| Blocker | Description | Effort |
|---|---|---|
| **Direct cbaseapp JDBC** | Service writes `service_records` and reads `b2c_csa_detailscreen_general`, `partnerdetail` directly via JPA/JDBC. Migrating away requires those domains to expose APIs or events. | High |
| **Direct ecountCore JDBC** | Reads `core_card_account_emboss_history`, `app_profile_promotion_label` directly. ECount Core REST API does not expose these endpoints yet. | Medium |
| **Static AES-GCM IV** | The `encryptedDDA` scheme (used in CHAT channel) uses a fixed IV from Key Vault. Migrating to per-message IVs requires coordination with the Decagon MPV Chat Widget that generates the ciphertext. | Medium |
| **trustServerCertificate=true** | Disabling this requires valid TLS certificates on the MSSQL servers (nam.wirecard.sys) that are trusted by the JVM. This is an infrastructure dependency outside this service's control. | Medium |
| **Shared DB credentials** | Moving to service-specific credentials (`managepaymentapi-*` → `contactcenteragent-*`) requires coordination with manage-payment-api and Key Vault teams. | Low |
| **In-process cache** | Moving to a distributed cache (e.g., Redis) for `appProfileLabelTypes` requires infrastructure provisioning and cache configuration changes. | Low |
| **No distributed tracing** | Adding Micrometer Tracing / OpenTelemetry requires adding dependencies, configuring an OTLP exporter, and potentially coordinating with Dynatrace configuration. | Low |
