# exemplar-cross-border-transfer-service_WAPP — Enterprise Architect Report

## 1. Platform Generation

| Attribute | Value |
|-----------|-------|
| Platform generation | Gen-3 reference implementation (Onbe "exemplar" series) |
| Technology stack | Spring Boot 2.5.2, Spring Batch, Spring Cloud OpenFeign, Resilience4j, Liquibase, SQL Server |
| Repository naming | `exemplar-` prefix — designated reference implementation |
| Group ID | `com.onbe.service` — Onbe namespace (not Wirecard) |
| Architecture style | Multi-module Spring Boot microservice + batch jobs |
| Deployment model | JAR-based (RPM scripts present; Kubernetes-ready) |
| Java version | 8 (POM); README states 11 — mismatch |
| Partner | Cambridge Payments (cross-border remittance) |

The `exemplar-` prefix in the repository name marks this as an **architectural reference implementation** — a template demonstrating Gen-3 patterns for Onbe's engineering teams. This is the cross-border transfer instantiation of the exemplar series (alongside `exemplar-customer-service_WAPP`, `exemplar-database_WAPP`, `exemplar-theater-service_WAPP`).

---

## 2. Business Domain

**Domain**: Payments — Cross-Border Money Remittance  
**Subdomain**: International fund transfers via Cambridge Payments FX platform

This service enables Onbe's prepaid card clients to send funds internationally. It is a **cross-border payment rail** that:
1. Quotes FX spot rates from Cambridge
2. Books FX deals
3. Instructs cross-border wire transfers
4. Reconciles completed and rejected transfers via SFTP file exchange with Cambridge
5. Cancels expired FX rate bookings automatically

The service is regulated under:
- OFAC (sanctions screening for international transfers)
- FinCEN/BSA (AML obligations for international wires above threshold)
- Reg E (consumer EFT protections)
- FATF Travel Rule (remitter/beneficiary identity for qualifying transfers)
- GLBA (PII of remitters/beneficiaries)

---

## 3. System Role in the Enterprise

| Role | Description |
|------|-------------|
| Cross-border payment orchestrator | Primary service for Cambridge-based international remittance |
| FX rate manager | Obtains, books, and cancels FX rate quotes |
| Reconciliation processor | Processes Cambridge recon and reject files via batch jobs |
| Exemplar / reference implementation | Demonstrates Gen-3 architectural patterns for other teams |
| Cambridge API integration point | Single point of integration with Cambridge Payments API |

As an **exemplar**, this repository has a dual role: it is both a production-capable service and a reference architecture for Gen-3 development practices at Onbe. Other teams are expected to use its patterns (Spring Boot multi-module, Liquibase, Feign clients, Resilience4j, PGP file exchange, 90% test coverage) as baselines for new service development.

---

## 4. Dependencies

### Upstream (callers of this service)
| System | Interface | Purpose |
|--------|----------|---------|
| REST controllers (missing module) | HTTP REST API | Client/cardholder-initiated transfer requests |
| Cambridge SFTP (inbound) | SFTP + PGP | Cambridge delivers recon and reject files |
| Batch job scheduler | Spring Batch / cron | Triggers `automatic-rate-cancellation` and file import/publish jobs |

### Downstream (called by this service)
| System | Interface | Purpose |
|--------|----------|---------|
| Cambridge Payments API | HTTPS + OAuth-style token | FX quotes, deal booking, transfer instruction, remitter/beneficiary management |
| Cambridge SFTP (outbound) | SFTP + PGP | Delivers Onbe recon and reject files to Cambridge |
| SQL Server database | JDBC (mssql-jdbc) | Persists all transfer records, recon data, rate cancellations |
| Spring Cloud Config Server | HTTP | Externalised application configuration |
| AWS S3 | SDK | File staging (inferred from POM dependency) |
| SMTP | Email | Job execution notifications |

### Configuration dependencies
| System | Interface | Purpose |
|--------|----------|---------|
| Spring Cloud Config | HTTP | All application properties including secrets (intended pattern) |
| Secrets vault (implied) | Spring Vault / Azure Key Vault | Cambridge API credentials, SFTP passwords, PGP passphrase |

---

## 5. Integration Patterns

| Pattern | Where Used | Gen-3 Compliance |
|---------|-----------|-----------------|
| Spring Cloud OpenFeign | `CambridgeClient` | Yes — standard Gen-3 HTTP client pattern |
| Resilience4j circuit breaker | All Cambridge API calls (11 instances) | Yes — circuit breaker per Cambridge operation |
| Spring Batch | 5 batch jobs | Yes — standard Gen-3 batch pattern |
| PGP file encryption | All SFTP file exchange | Yes — appropriate for financial file transfer |
| SFTP file exchange | Cambridge and Ecount SFTP channels | Yes — standard for B2B financial file exchange |
| Liquibase DB migrations | `cross-border-transfer-service-db-app` | Yes — Gen-3 schema management standard |
| Spring Cloud Config | `bootstrap.yml` in batch + web | Yes — but config server password is hardcoded |
| JaCoCo 90% coverage gate | `pom.xml` properties | Yes — exemplary coverage requirement |
| Multi-module Maven | 10 modules | Yes — standard Gen-3 modular structure |
| Token exchange (partner → client) | Cambridge auth flow | Appropriate two-tier OAuth-like pattern |
| RPM packaging + shell scripts | Batch module | Pre-Kubernetes deployment pattern; should migrate to container |

---

## 6. Strategic Status

**Current status**: Active exemplar — intended as a production-ready reference implementation.

**Assessment**: This service is architecturally the most mature in the analysed set. It demonstrates correct Gen-3 patterns: Spring Boot, Liquibase, Feign, Resilience4j, PGP encryption, high test coverage targets, and multi-module structure. However, it has significant **pre-production security gaps** that must be resolved before it can be treated as a production deployment:

1. Multiple credentials committed to `application.yml` and `bootstrap.yml`.
2. Cambridge URL pointing to `beta.cambridgelink.com` (not production).
3. Wirecard-era placeholder emails (`test@wirecard.com`).
4. Spring Boot 2.5.2 (EOL November 2022).
5. H2 console enabled.

The `application.yml` contains actual Cambridge API client IDs (`252648_API_User`, `252650_API_User`) and signatures — these appear to be real test/staging credentials for RCCL (Royal Caribbean Cruises) and Disney programmes. Immediate credential rotation is required.

---

## 7. Migration/Production-Readiness Blockers

| Blocker | Detail |
|---------|--------|
| Credentials in source control | Cambridge API signatures, SFTP password, PGP passphrase, app credentials must be rotated and removed from git |
| Cambridge URL is beta | `https://beta.cambridgelink.com` — must be replaced with production endpoint |
| Spring Boot 2.5.2 EOL | Upgrade to Spring Boot 3.x required; breaking changes exist (Jakarta EE namespace migration) |
| Java version mismatch (8 vs 11) | POM says Java 8; README says Java 11; must be resolved |
| Missing REST/service/persistence modules (partial clone) | Full security and data architecture review cannot be completed without these modules |
| OFAC sanctions screening | No OFAC check visible in available source — must be confirmed in missing REST/service module or documented as external dependency |
| Wirecard email addresses | `test@wirecard.com` in email config — operational alerts would not reach Onbe team |
| RPM deployment scripts | Pre-Kubernetes deployment model in batch module (`src/main/rpm/`) — must migrate to Docker/Kubernetes |
| H2 console enabled | Must be disabled for production profile |
| Liquibase `enabled: false` in db-app | Liquibase is disabled in db-app config — schema migrations will not run automatically |
