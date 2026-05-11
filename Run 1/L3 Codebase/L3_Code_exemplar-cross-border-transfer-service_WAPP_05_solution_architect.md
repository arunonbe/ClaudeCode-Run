# exemplar-cross-border-transfer-service_WAPP — Solution Architect Report

## Important Note: Partial Clone

Due to Windows MAX_PATH limitations, several modules are not fully available locally: `cross-border-transfer-service-rest-controller`, `-service`, `-data`, `-persistence`, `-db-scripts`, `-qa`. Solution architecture analysis relies on the available batch module, Cambridge client module, root POM, `application.yml`, `bootstrap.yml`, and CodeQL/Dependabot configuration. Full analysis requires the complete repository.

---

## 1. Technical Architecture

| Attribute | Value |
|-----------|-------|
| Language | Java 8 (POM `java.version=1.8`; README states Java 11 — mismatch) |
| Framework | Spring Boot 2.5.2 (EOL Nov 2022) |
| Spring Cloud | `2020.0.2` (Ilford) |
| Build | Maven multi-module (10 modules) |
| Batch | Spring Batch |
| HTTP client | Spring Cloud OpenFeign |
| Resilience | Resilience4j (circuit breakers for all Cambridge API calls) |
| DB | SQL Server — mssql-jdbc 9.2.1.jre11 |
| Schema management | Liquibase (`db/changelog/db.changelog-master.xml`) |
| File encryption | PGP (BouncyCastle inferred from `PGPUtils`, `PGPDecryptionTasklet`, `PGPEncryptionTasklet`) |
| File transfer | SFTP (Spring Integration SFTP — `CambridgeSftpCommonChannelConfig`, `EcountSftpCommonChannelConfig`) |
| Caching | JCache/Ehcache 3 (`ehcache3.xml`) |
| Testing | JUnit 5, Spring Boot Test, JaCoCo (90% threshold), WireMock (for Cambridge API mocking) |
| Container | H2 in-memory for tests |
| Coverage gate | 90% instruction/class/line/branch/method |
| Code style | Checkstyle (`checkstyle.xml`) |

---

## 2. API Surface

### 2.1 REST API (partially available — `rest-controller` module partially cloned)

Based on available source, the REST application exposes:
- **Base URL**: `http://localhost:9000/cross-border-transfer-service`
- **Swagger UI**: `http://localhost:9000/cross-border-transfer-service/swagger-ui.html` (SpringDoc OpenAPI)
- **Actuator**: `http://localhost:9000/cross-border-transfer-service/monitoring/*`

Spring Security is configured (DEBUG logging for `org.springframework.security.web`). Credentials for HTTP Basic auth are defined in `application.yml`:
```yaml
credentials:
  username: "[REDACTED — rotate immediately]"
  password: "[REDACTED — rotate immediately]"
  role: "USER"
```
**These credentials are in source control — must be rotated and externalised.**

### 2.2 Batch REST API (`BatchJobController`, `RestJobController`)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/jobs` | GET | List all batch jobs and last execution status |
| `/jobs` | POST | Trigger a batch job by name |

`BatchJobController` uses `@Hidden` (hidden from Swagger) — internal operational endpoint.

### 2.3 Outbound API: Cambridge Payments (`CambridgeClient.java`)

All calls include `CMG-AccessToken` header:

| Method | URL Template | Purpose |
|--------|-------------|---------|
| `getPartnerToken` | `/api/partner/oauth2/token` | Obtain partner-level token |
| `getClientToken` | `/api/partner/oauth2/userToken` | Obtain client-level token |
| `getSpotRate` | `/api/{clientCode}/0/quotes/spot` | Get FX spot rate |
| `bookDeal` | `/api/{clientCode}/0/quotes/{quoteId}/book` | Lock FX rate |
| `requestCancellation` | `/api/{clientCode}/0/orders/{orderNumber}/request-cancellation` | Request cancellation |
| `bookCancellation` | `/api/{clientCode}/0/cancel-quotes/{cancelationID}/book` | Book cancellation |
| `createEditRemitter` | `/api/{clientCode}/0/remitters/{uniqueRemitterID}` | Create/edit remitter |
| `createEditBeneficiary` | `/api/{clientCode}/0/templates/{beneId}` | Create/edit beneficiary |
| `instructDeal` | `/api/{clientCode}/0/order-book` | Execute transfer |
| `getBeneficiaryRules` | `/api/{clientCode}/0/template-guide?...` | Get beneficiary validation rules |
| `viewBeneficiary` | `/api/{clientCode}/0/benes/{beneID}` | View beneficiary |
| `viewRemitter` | `/api/{clientCode}/0/remitters/{uniqueRemitterID}` | View remitter |
| `getRateResource` | `/api/{clientCode}/0/quotes/{quoteId}` | Get rate details |

### 2.4 Batch Jobs

| Job Name | Direction | Trigger |
|----------|----------|---------|
| `import-cambridge-recon-file` | Inbound (Cambridge SFTP → DB) | Manual / scheduled |
| `import-cambridge-reject-file` | Inbound (Cambridge SFTP → DB) | Manual / scheduled |
| `publish-cambridge-recon-file` | Outbound (DB → Ecount SFTP) | Manual / scheduled |
| `publish-cambridge-reject-file` | Outbound (DB → Ecount SFTP) | Manual / scheduled |
| `automatic-rate-cancellation` | Internal | Manual / scheduled |

---

## 3. Security Posture

### 3.1 Authentication

| Interface | Auth Mechanism | Assessment |
|-----------|---------------|------------|
| REST API inbound | HTTP Basic auth (username/password in `application.yml`) | **Credentials in source — CRITICAL** |
| Cambridge API outbound | Two-level token exchange (partner → client) via `CMG-AccessToken` | Token-based; credentials in source |
| SFTP | Username/password (`wirecard`/`FxDMahi4TU` in `application.yml`) | **Credentials in source — CRITICAL** |
| SQL Server | Spring datasource config (credentials in Cloud Config — but bootstrap password hardcoded) | Partially externalised |
| Config server | HTTP Basic (`application`/`s3cr3t`) | **Credentials in source — CRITICAL** |

### 3.2 Secrets in Source Control — CRITICAL

All of the following are committed to `application.yml` or `bootstrap.yml`:

| Secret | File | Location |
|--------|------|---------|
| Config server password `s3cr3t` | `bootstrap.yml` (batch + web) | Line 6 |
| App HTTP credential (long string) | `application.yml` | Lines 7–8 |
| Cambridge partner signature | `application.yml` | Line 191 |
| Cambridge RCCL one-time signature | `application.yml` | Line 196 |
| Cambridge RCCL recurring signature | `application.yml` | Line 201 |
| Cambridge Disney/NoRecurring signature | `application.yml` | Lines 208, 213 |
| SFTP password `FxDMahi4TU` | `application.yml` | Lines 320, 324 |
| PGP passphrase `wirecard` | `application.yml` | Line 329 |

**All must be rotated immediately and removed from all git branches and history.**

### 3.3 Encryption

- **File transfer**: PGP encryption via `PGPUtils`, `PGPDecryptionTasklet`, `PGPEncryptionTasklet` — appropriate for financial file exchange.
- **PGP key files**: `/pgp/0x6392B27D-pub.asc` and `/pgp/0x6392B27D-sec.asc` — paths in config; private key file must be secured on server (not in source control; not visible in repo).
- **DB transport**: `tlsEnabled: true` in datasource config — SQL Server TLS enforced.
- **HTTPS to Cambridge**: `https://beta.cambridgelink.com` — TLS in transit.
- **No data-at-rest encryption** defined in visible config; relies on DB-level TDE.

### 3.4 Actuator Exposure

`application.yml`:
```yaml
management:
  endpoints:
    web:
      exposure:
        include: '*'
  endpoint:
    health:
      show-details: 'ALWAYS'
```

**All actuator endpoints exposed with full health detail to any caller.** In production, this must be restricted to:
```yaml
management:
  endpoints:
    web:
      exposure:
        include: health, info, metrics
  endpoint:
    health:
      show-details: when-authorized
```

---

## 4. Technical Debt

| Issue | Severity | Detail |
|-------|---------|--------|
| Credentials in source control (8 instances) | CRITICAL | Cambridge API signatures, SFTP, PGP passphrase, app auth, config server password |
| Spring Boot 2.5.2 EOL (Nov 2022) | HIGH | Known CVEs in transitive dependencies; upgrade to 3.x required |
| Java 8/11 mismatch | HIGH | POM targets Java 8; README states Java 11; must resolve before production |
| Cambridge URL is `beta` environment | HIGH | `https://beta.cambridgelink.com` — not production |
| H2 console enabled | HIGH | Must be disabled in non-local profiles |
| Actuator fully exposed without auth | HIGH | All endpoints exposed to unauthenticated callers |
| Wirecard placeholder emails | HIGH | `test@wirecard.com` and `wirecard` SFTP credentials — operational alerts go nowhere |
| Liquibase disabled in db-app | MEDIUM | `liquibase.enabled: false` in `db-app/application.yml` — schema migrations must be enabled |
| RPM deployment scripts | MEDIUM | Pre-container deployment model; not Kubernetes-native |
| Wirecard Nexus dependency | MEDIUM | `d-na-stk01.nam.wirecard.sys:8080/nexus` in Maven distribution management |
| `com.wirecard` in logging config | LOW | `com.wirecard.crossbordertransferservice.cambridgeclient` in logger config — Wirecard package name; suggests refactoring incomplete |
| No CI/CD build pipeline | HIGH | CodeQL only; no build, test, deploy automation |
| Partial clone — MAX_PATH issue | MEDIUM | REST/service/persistence/qa modules cannot be fully analysed locally |

---

## 5. Gen-3 Migration Assessment

This IS a Gen-3 service — it represents the current Onbe Gen-3 architectural target. The gaps are pre-production readiness issues, not architectural migration issues.

**Pre-production checklist**:
1. Rotate all credentials in `application.yml`/`bootstrap.yml` and move to Spring Cloud Config + Vault.
2. Replace `beta.cambridgelink.com` with production Cambridge URL.
3. Upgrade Spring Boot from 2.5.2 to 3.x (breaking change: Jakarta EE namespace migration from `javax.*` to `jakarta.*`).
4. Resolve Java 8 vs 11 version mismatch.
5. Disable H2 console in non-local Spring profiles.
6. Restrict Actuator endpoints.
7. Replace Wirecard email placeholders with Onbe-managed DLs.
8. Enable Liquibase in db-app.
9. Implement CI/CD pipeline (Maven build + JaCoCo + deploy).
10. Containerise batch module (replace RPM scripts with Docker image).

---

## 6. Code-Level Risks

| Risk | File | Detail |
|------|------|--------|
| Config server password | `bootstrap.yml:6` | `password: s3cr3t` — if config server is compromised, all downstream secrets are exposed |
| App auth credentials | `application.yml:7-9` | Long string credentials committed; must be rotated |
| Cambridge partner signature | `application.yml:191` | `BwiVUg-UoXZfWoNSkwBFrjeoU4QZiCS-AOowiqpN78w` — API signing credential |
| SFTP password | `application.yml:320,324` | `FxDMahi4TU` for both Cambridge and Ecount SFTP |
| PGP passphrase | `application.yml:329` | `wirecard` — PGP private key passphrase; enables decryption of all Cambridge files |
| `automatic-rate-cancellation` reliability | `AutomaticRateCancellationConfig.java` | FX rate cancellation must be reliable; failure = financial loss (expired deals charged at market); no dead-letter queue or compensation mechanism visible |
| Circuit breaker misconfiguration | `application.yml:95-97` | `failure-rate-threshold: 40` — circuit opens at 40% failure rate over 100 calls. For Cambridge (single external dependency), this may be too permissive in production |
| Cambridge client RCCL/Disney BINs in config | `application.yml:147-165` | Specific BIN numbers (`04014519`, `04019591`, etc.) mapped to Cambridge clients; config change required when BINs are added/retired |
