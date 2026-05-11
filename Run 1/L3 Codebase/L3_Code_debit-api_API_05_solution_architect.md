# Solution Architect Report — debit-api_API

## 1. Architecture Overview

debit-api_API is a **Spring Boot 3 / Java 21 SOAP web service** that wraps the legacy ECount Core2 prepaid card ledger. It is composed of four Maven modules:

| Module | Role |
|---|---|
| `debitapi-boot` | Spring Boot entry point; all configuration, datasource auto-config, Dockerfile |
| `debitapi-common` | Request/response DTOs, validators, exception hierarchy, type enums |
| `debitapi-impl` | Business logic — service classes, account helper, DAO layer |
| `debitapi-ws` | SOAP endpoint, handler wiring, controller classes (referenced in boot config) |

The runtime is containerized (Docker / Kubernetes), configured via Azure App Configuration + Key Vault, and deployed through a GitHub Actions pipeline delegating to the shared `Onbe/om-ci-setup` workflow library.

---

## 2. API Surface

**Protocol**: SOAP 1.1 over HTTP/HTTPS  
**Endpoint**: `POST /services/DebitService` (SOAP action header required)  
**WSDL**: Published to Azure External APIM on every main-branch deployment

### Operations

| SOAP Action | Request Class | Response Class | Key Fields |
|---|---|---|---|
| `beginDebit` | `BeginDebitRequest` | `BeginDebitResponse` | `program_id`, `account_id`, `transaction_id`, `amount` (cents), `comment` |
| `commitDebit` | `CommitDebitRequest` | `CommitDebitResponse` | `program_id`, `account_id`, `transaction_id`, `transfer_id` |
| `cancelDebit` | `CancelDebitRequest` | `CancelDebitResponse` | `program_id`, `account_id`, `transaction_id`, `transfer_id` |
| `getStatusDebit` | `GetStatusDebitRequest` | `GetStatusDebitResponse` | `transfer_id` |
| `inquiry` | `InquiryRequest` | `InquiryResponse` | `program_id`, `account_id`, `additional_info[]` |

`additional_info` accepts `BALANCE`, `REFILL`, `TRANSACTION_ID` to enrich responses.

---

## 3. Security Architecture

| Control | Implementation | Gap |
|---|---|---|
| Transport encryption | HTTPS enforced at load balancer / APIM layer | Not enforced at service level in code |
| Credential storage | Azure Key Vault (all DB passwords) | `memberId` GUID still in app-config JSON |
| Authentication / Authorization | Not observed in SOAP handler or filters | **Gap**: No inbound authentication on SOAP endpoint |
| CA certificate pinning | `nam.wirecard.sys.crt` imported into JVM trust store (Dockerfile lines 24–27) | Only for outbound Director/Core calls |
| DB TLS | `trustServerCertificate=true` | **Gap**: Certificate validation disabled |
| Log sanitization | Not observed | **Gap**: Account IDs logged at INFO |
| SAST | CodeQL workflow active | No DAST observed |
| Container scanning | Trivy allowlist (`.github/containerscan/allowedlist.yaml`) | Allowlist may suppress real findings |

---

## 4. Technical Debt

| Item | File / Class | Severity |
|---|---|---|
| Null pointer bug in `populateInput` | `BeginDebitRequest.java` line 127: `if(getComment() != null \|\| getComment().length() > 0)` — OR should be AND; null comment causes NPE on second condition | High |
| `allow-circular-references: true` | `application.yml` line 33 | Medium |
| `allow-bean-definition-overriding: true` | `application.yml` line 32 — hides bean conflicts | Medium |
| `debitapi-war` module still present | Root `pom.xml` | Low — dead code confusion |
| Java compiler target mismatch in test repo | `debit-api_TESTING_AUTO/pom.xml` targets Java 1.7 | Low |
| Thread pool queue unbounded | `DebitApiWsConfig` line 395 `new LinkedBlockingQueue<>()` | Medium |
| `TestDirectorXMLRPCClient.testValues()` not annotated `@Test` | `director-client_LIB` test line 45 | Low |
| Commons HTTPClient 3.x used in `director-client_LIB` | Deprecated; use Apache HttpClient 5 | Low |

---

## 5. Gen-3 Migration Considerations

### 5.1 SOAP → REST Migration Path
1. Define OpenAPI 3.0 spec for `beginDebit`, `commitDebit`, `cancelDebit`, `getStatus`, `inquiry`
2. Implement REST adapter layer; keep existing service/controller classes unchanged initially
3. Deploy both SOAP and REST endpoints side-by-side; migrate consumers with traffic shadowing
4. Deprecate SOAP after all consumers cut over; remove `debitapi-ws` module and `server-config.wsdd`

### 5.2 Core2 Decoupling
- Introduce `ITransferGateway` interface over `ECoreTransfer` / `TransferManagerImpl`
- Implement a Gen-3 gateway backed by the new Core3 ledger API
- Feature-flag at the `AccountHelper` layer

### 5.3 Configuration
- Replace Director XML-RPC lookups with Azure App Configuration labels — already partially done; remove `director-client.yaml` dependency once all consumers migrated

### 5.4 Observability
- Add OpenTelemetry tracing to replace MDC-based `GlobalRequestIDInterceptor`
- Standardize structured JSON logging via Log4j2 JSON layout

---

## 6. Code Quality Risks

| Risk | Location | Notes |
|---|---|---|
| NPE on null comment | `BeginDebitRequest.java:127` | Production impact: any begin-debit call with null comment will throw NPE |
| Synchronous Core2 call on servlet thread | `BeginDebitService.doExecute` — `TransferManagerImpl.begin()` is blocking | Latency spikes from Core2 propagate to all SOAP clients |
| No retry logic on Director calls | `DirectorXMLRPCClient` — exceptions are swallowed (lines 117–124, returns null) | Silent config failure possible at startup |
| `DebitApiConfig` hardcoded program IDs | `DebitApiConfig.java:16` | Requires code change per new client program onboarding |
| Mixed package namespaces | `com.citi.prepaid`, `com.citiprepaid`, `com.onbe` — three different package roots | Indicates multiple rounds of ownership/renaming; complicates refactoring |
