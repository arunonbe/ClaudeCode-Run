# Solution Architect View — cross-border-transfer-service_SVC

## 1. Architecture Overview

CBTS is a Spring Boot microservice in a multi-module Maven layout. It provides an internal REST API for managing cross-border wire transfers through Cambridge Global Payments (Corpay). The service is logically split into:

- **REST runtime** (`cross-border-transfer-service-rest-controller`) — serves the API, handles auth, validation, exception handling
- **Batch runtime** (`cross-border-transfer-service-batch`) — runs scheduled and triggered Spring Batch jobs for file exchange with Cambridge and eCount
- **Cambridge client** (`cross-border-transfer-service-cambridge-client`) — OpenFeign client for all Cambridge API calls
- **Service layer** (`cross-border-transfer-service-service`) — business logic and email notifications
- **Persistence** (`cross-border-transfer-service-persistence`) — JPA entities and Spring Data repositories
- **Data/DTOs** (`cross-border-transfer-service-data`) — shared domain objects, enums, API request/response models
- **Config** (`cross-border-transfer-service-config`) — Spring context wiring for all modules
- **DB scripts** (`cross-border-transfer-service-db-scripts`) — Liquibase changelogs
- **DB app** (`cross-border-transfer-service-db-app`) — standalone Liquibase runner
- **QA** (`cross-border-transfer-service-qa`) — integration and functional tests

## 2. REST API Design

### Versioning
- Custom media type: `application/vnd.crossbordertransferservice.api.v1+json` and `application/vnd.crossbordertransferservice.api.v1+xml` (`ApiVersion.java`).
- All controller mappings produce and consume these versioned types.
- Only `v1` exists; no versioning migration path is defined.

### Authentication
- HTTP Basic Authentication (`SecurityConfiguration.java` lines 18–76).
- Credentials injected from config: `credentials.username`, `credentials.password`, `credentials.role`.
- In-memory `UserDetailsService` with `{noop}` password prefix (line 40) — password is stored and compared in plaintext.
- CSRF disabled (`csrf.disable()` line 57).
- Stateless sessions (`SessionCreationPolicy.STATELESS` line 62).
- Secured paths: `/beneficiaries/**`, `/rates/**`, `/remitters/**`, `/transfers/**`.
- Health check (`/hc`) and OpenAPI docs are effectively unsecured (not listed in `SECURED_PATHS`).

### Exception Handling
- `DataExceptionControllerAdvice.java` handles domain `DataException` subtypes (`DataCreationException`, `DataDeletionException`, `DataExistsException`, `DataUpdateException`, `InvalidDataException`, `NoSuchDataException`, `UnauthorizedException`).
- `GeneralExceptionControllerAdvice.java` handles generic exceptions.
- Custom `CbtsErrorController.java` overrides Spring Boot error controller.
- Error response model: `ErrorResponse.java` in `data.restapi.v1.error` with `ErrorType` enum.
- `ErrorResponseFactory` / `ErrorResponseFactoryImpl` constructs standardized error payloads.

### Validation
- Bean Validation (`javax.validation`) on DTOs: `@NotBlank`, `@Size(max=36)` on IDs in `Transfer.java` (lines 16–20).
- Custom `BeneficiaryValidatorImpl`: province required for US/CA, routing code ≤ 50, SWIFT ≤ 12 (`BeneficiaryValidatorImpl.java` lines 21–46).
- `BeneficiaryRulesValidatorImpl` validates beneficiary rules against Cambridge's template guide requirements.
- `RateValidatorImpl` validates rate request structure.
- Note: `@Valid` annotation on `TransferController.createTransfer()` uses `javax.validation` (lines 1–74) — this is Jakarta EE renamed in Spring Boot 3; the import at line 8 still uses old `javax.validation` namespace, which may indicate incomplete Jakarta EE migration.

## 3. Cambridge API Integration Design

### Token Flow
1. `JwtTokenCreatorImpl.createJwtToken()` generates a 5-minute HMAC-SHA256 JWT signed with the Cambridge partner signature (`JwtTokenCreatorImpl.java` lines 18–28).
2. `TokenServiceImpl.getPartnerToken()` calls Cambridge `/api/partner/oauth2/token` with this JWT to get a partner-level access token.
3. `TokenServiceImpl.getClientToken()` calls Cambridge `/api/partner/oauth2/userToken` with the partner token to get a client-level token.
4. All subsequent Cambridge API calls pass the client token as `CMG-AccessToken` header.

### Key Cambridge Operations
| CBTS Operation | Cambridge Endpoint | Cambridge Client Method |
|---|---|---|
| Get spot rate | `POST /api/{clientCode}/0/quotes/spot` | `CambridgeClient.getSpotRate()` |
| Book deal | `POST /api/{clientCode}/0/quotes/{quoteId}/book` | `CambridgeClient.bookDeal()` |
| Request cancellation | `POST /api/{clientCode}/0/orders/{orderNumber}/request-cancellation` | `CambridgeClient.requestCancellation()` |
| Book cancellation | `POST /api/{clientCode}/0/cancel-quotes/{cancelationID}/book` | `CambridgeClient.bookCancellation()` |
| Instruct deal (wire) | `POST /api/{clientCode}/0/order-book` | `CambridgeClient.instructDeal()` |
| Create/edit remitter | `PUT /api/{clientCode}/0/remitters/{uniqueRemitterID}` | `CambridgeClient.createEditRemitter()` |
| Create/edit beneficiary | `PUT /api/{clientCode}/0/templates/{beneId}` | `CambridgeClient.createEditBeneficiary()` |
| Get beneficiary rules | `GET /api/{clientCode}/0/template-guide?...` | `CambridgeClient.getBeneficiaryRules()` |
| View beneficiary | `GET /api/{clientCode}/0/benes/{beneID}` | `CambridgeClient.viewBeneficiary()` |
| View remitter | `GET /api/{clientCode}/0/remitters/{uniqueRemitterID}` | `CambridgeClient.viewRemitter()` |
| Rate resource (status check) | `GET /api/{clientCode}/0/new-quotes/{quoteId}` | `CambridgeClient.rateResource()` |
| Bank search | `GET /api/banks?country=...` | `CambridgeClient.getBanks()` |

Note: `CambridgeClient.bookDeal()` has a code comment (line 46–48) explaining that Cambridge requires a non-empty body even though it is unused — the `quoteId` is passed as body as a workaround.

### Error Handling for Cambridge
- `ErrorHandler.java` in the cambridge-client module handles Cambridge error responses.
- `CambridgeGatewayCommunicationException` wraps all Cambridge communication failures and is the recorded exception for circuit breaker failure rate calculation.
- Feign exception mapping handled in service-layer catch blocks (`AutomaticRateCancellationProcessor.java` line 74).

## 4. Batch Architecture

Five Spring Batch jobs using the standard Reader → Processor → Writer pattern with partitioned file processing:

### Import Jobs (Inbound from Cambridge SFTP)
```
CambridgeSftpCommonChannelConfig
    └─ ImportSftpDownloadTasklet (download from Cambridge SFTP)
    └─ PGPDecryptionTasklet (BouncyCastle decrypt)
    └─ FilesInDirectoryPartitioner (one partition per file)
    └─ ImportCambridgeReconFileReader (CSV → ReconFile DTO)
    └─ ImportCambridgeReconFileWriter (upsert → RECON_FILE table)
    └─ MoveFileStepExecutionListener (move to processed/failed dir)
    └─ ImportCambridgeReconFileEmailListener (email notification)
```

### Publish Jobs (Outbound to Cambridge/eCount SFTP)
```
PublishCambridgeReconFileReader (SQL Server RECON_FILE → CambridgeReconRecord)
    └─ CambridgeReconRecordsRowMapper (JdbcCursorItemReader row mapping)
    └─ PublishCambridgeReconFileBodyWriter (write to local file)
    └─ PGPEncryptionTasklet (BouncyCastle encrypt)
    └─ PublishSftpUploadTasklet (upload to SFTP)
    └─ PublishCambridgeReconFileListener (email + move)
```

### Auto Rate Cancellation Job
```
AutomaticRateCancellationReader (read NEW/BOOKED rates from DB)
    └─ AutomaticRateCancellationProcessor
          ├─ CancelRateService.cancelRate() → Cambridge request/book cancellation
          └─ RateService.updateRateStatus() → CANCELLED in DB
    └─ NoOpItemWriter
```

### Batch State Management
- Spring Batch meta-tables (`BATCH_JOB_INSTANCE`, `BATCH_JOB_EXECUTION`, `BATCH_STEP_EXECUTION`, etc.) managed by Liquibase (`db.changelog-spring-batch.xml`).
- `BatchJobContextListener` stores job context in `ThreadLocalBatchJobContext` for use by `BaseEntity.onPrePersist()` to populate `INSERTED_BY`.
- `BatchJobContextConfig` bootstraps the job context.

## 5. Security Design

### Current Implementation

| Control | Mechanism | Strength |
|---|---|---|
| API Authentication | HTTP Basic (`SecurityConfiguration.java`) | Weak — single static credential, no MFA, no rotation via code |
| Password storage | `{noop}` prefix (plaintext) | Critical weakness |
| Transport (API) | HTTPS (caller responsibility) | No TLS enforcement in service itself; QA SSL commented out |
| Transport (Cambridge) | HTTPS via OkHttp | Strong |
| Transport (SFTP) | SSH/SFTP | Strong |
| File confidentiality | PGP encryption (BouncyCastle) | Strong in mechanism; weak in key management (keys in Git) |
| CSRF | Disabled | Appropriate for stateless REST API |
| Token auth to Cambridge | JWT HMAC-SHA256 + OAuth2 client token | Strong mechanism; weak key management (signatures in YAML/Git) |
| DB connection TLS | Optional (`tlsEnabled` flag) | Disabled in QA config |

### Security Gaps

1. **In-memory `{noop}` password**: `SecurityConfiguration.java` line 40 — the `{noop}` prefix means Spring Security skips password hashing entirely. Credentials are compared as raw strings.

2. **Credentials in source-controlled YAML** (`application-qa.yml`):
   - DB password: line 41 (`[REDACTED — rotate immediately]`)
   - API user: line 26–27 (`credentials.username`, `credentials.password`)
   - SMTP password / API key: line 71 (`[REDACTED — rotate immediately]`)
   - Cambridge client signatures for all 10+ clients: lines 281–384
   These must be treated as compromised. Immediate rotation and migration to a secrets manager is required.

3. **PGP private key in Git**: `0x6392B27D-sec.asc` is committed. If the key passphrase is also stored nearby, files protected with this key are exposed.

4. **No OFAC screening**: Remitter and beneficiary names, addresses, and countries are not screened against OFAC SDN lists before submission to Cambridge. This is a regulatory compliance gap, not a technical one, but it must be remediated.

5. **HTTP Basic over HTTP possible**: QA SSL is commented out (`application-qa.yml` lines 3–8). If the service is accessed without a TLS-terminating proxy, credentials travel in Base64 encoding only.

6. **No rate limiting or throttling**: REST endpoints have no protection against brute-force or enumeration attacks on IDs.

## 6. Technical Debt

| Item | Class/File | Line(s) | Impact |
|---|---|---|---|
| `javax.validation` import (old namespace) | `TransferController.java`, `BeneficiaryController.java`, `RemitterController.java`, `RateController.java` | Line 8 (`import javax.validation.Valid`) | Jakarta EE migration incomplete; may fail with strict Spring Boot 3 validation configurations |
| `MonitoringConfiguration.java` entirely commented out | `MonitoringConfiguration.java` | 1–47 | Health aggregator and custom Jackson serializer lost; health endpoint may return degraded information |
| Partner name `"wirecard"` hardcoded | `TokenServiceImpl.java` | 26 | Breaks brand-neutrality; incorrect after Onbe rebrand |
| `show-sql: true` in QA config | `application-qa.yml` | 58 | May leak SQL structure in logs; must be disabled in production |
| Beneficiary payment-method validation commented out | `BeneficiaryValidatorImpl.java` | 24–26 | Reduces input integrity; original reason was UI-driven dropdown but API consumers are not so constrained |
| `JdbcCursorItemReader` for publish jobs | Batch module | `PublishCambridgeReconFileReader.java` | Cursor may hold DB connections open during slow SFTP uploads |
| `CambridgeSftpConfig` uses password auth | `CambridgeSftpConfig.java` | 12 | SSH key-based auth is preferable for SFTP in production |
| `README.md` states Java 1.8 | `README.md` | 6 | Misleading; actual target is Java 21 |
| `MAVEN_TEST_SKIP` in all CI stages | `.gitlab-ci.yml`, `deployment.yml` | — | No regression test gate; high deployment risk |
| Large HikariCP pool (max 50) with small JVM | `application-qa.yml` | 45 | May exhaust DB connections if multiple instances deployed without pool sizing review |

## 7. Gen3 / Modernization Recommendations

The following items represent the path from the current Gen2 state toward Onbe's Gen3 platform standards:

| Priority | Recommendation | Detail |
|---|---|---|
| P0 | **Rotate all secrets** | Immediately revoke and re-issue: DB credentials, Cambridge API signatures, SMTP API key, JKS keystores, PGP key pair |
| P0 | **Migrate secrets to Vault / Azure Key Vault** | Replace all YAML-embedded credentials with dynamic injection at runtime |
| P0 | **OFAC screening integration** | Add pre-submission screening of remitter/beneficiary name and country against OFAC SDN list |
| P1 | **OAuth2/OIDC authentication** | Replace HTTP Basic with OAuth2 client credentials flow using Onbe's identity platform |
| P1 | **Re-enable CI tests** | Remove `MAVEN_TEST_SKIP` from all CI configs; add JaCoCo coverage gate |
| P1 | **Jakarta EE migration** | Replace all `javax.validation`, `javax.persistence` imports with `jakarta.*` equivalents (Spring Boot 3 requires this) |
| P1 | **At-rest encryption for PII** | Apply Transparent Data Encryption (TDE) on SQL Server, or column-level encryption for `ACCOUNT_NUMBER`, `ROUTING_CODE`, names |
| P2 | **OpenTelemetry distributed tracing** | Add OTel Java agent for trace propagation to Onbe observability platform |
| P2 | **Parameterize partner name** | Remove hardcoded `"wirecard"` from `TokenServiceImpl.java` line 26 |
| P2 | **Structured logging** | Add Logback JSON encoder for log shipping to SIEM |
| P2 | **SSH key-based SFTP** | Replace password-based SFTP authentication with RSA key pairs stored in secrets manager |
| P3 | **Activate or remove Dapr** | Decide on event-driven messaging adoption; remove sidecar if unused |
| P3 | **Rate limiting** | Add API gateway or Spring Security rate limiting to prevent enumeration |
| P3 | **Data retention policy** | Implement time-based purge or archival of REMITTER/BENEFICIARY PII per GDPR/CCPA obligations |

## 8. Code Risk Summary

| Risk Category | Severity | Specific Finding |
|---|---|---|
| Secret exposure | Critical | Cambridge API signatures in `application-qa.yml` lines 281–384; PGP secret key in `pgp/0x6392B27D-sec.asc`; JKS keystore `config/server.jks` in Git |
| Authentication weakness | Critical | HTTP Basic with `{noop}` plaintext password (`SecurityConfiguration.java` line 40) |
| Missing compliance control | Critical | No OFAC/sanctions screening before wire transfer submission |
| Jakarta migration incomplete | High | `javax.validation` imports in controller layer (e.g., `TransferController.java` line 8) |
| Test gate absent | High | All CI pipelines skip tests; no quality gate |
| PII at rest unencrypted | High | Account numbers, names, routing codes in plaintext SQL Server columns |
| Monitoring disabled | Medium | `MonitoringConfiguration.java` entirely commented out |
| SQL logging in QA | Medium | `show-sql: true` (`application-qa.yml` line 58) |
| Legacy infrastructure | Medium | DB host `wirecard.sys`, partner name `"wirecard"` in code |
| Unused Dapr sidecar | Low | `docker-compose.yml` includes Dapr dependency without active use |
