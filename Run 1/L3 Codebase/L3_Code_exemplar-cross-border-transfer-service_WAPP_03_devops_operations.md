# exemplar-cross-border-transfer-service_WAPP — DevOps and Operations Report

## Important Note: Partial Clone

This repository was cloned with a Windows MAX_PATH limitation. The `cross-border-transfer-service-rest-controller`, `-service`, `-data`, `-persistence`, `-db-scripts`, and `-qa` modules are partially or fully missing from the local clone. DevOps analysis is based on available artefacts: root `pom.xml`, `bootstrap.yml` files, `application.yml`, `BatchJobController.java`, batch module source, Cambridge client module, `checkstyle.xml`, CodeQL workflow, and Dependabot config.

---

## 1. Build System

| Attribute | Value |
|-----------|-------|
| Build tool | Apache Maven (multi-module, Maven Wrapper) |
| Parent | `spring-boot-starter-parent:2.5.2` |
| Java version | 1.8 (POM `java.version`); README states Java 11 — mismatch |
| Modules | 10 Maven modules |
| Packaging | POM (parent); JAR per module; `exec.jar` for runnable modules |
| Nexus | `d-na-stk01.nam.wirecard.sys:8080/nexus` (Wirecard-era internal repository) |
| CI/CD | GitHub Actions CodeQL scan only (`.github/workflows/codeql.yml`) |
| Code quality | Checkstyle (`checkstyle.xml`) |
| Code coverage | JaCoCo — 90% threshold on instruction/class/line/branch/method |
| Dependency updates | Dependabot weekly (`.github/dependabot.yml`) |

---

## 2. CI/CD Pipeline

### Existing pipeline
**CodeQL security scan** (`.github/workflows/codeql.yml`):
```yaml
schedule:
  - cron: 44 9 * * 4    # Every Thursday at 09:44 UTC
uses: Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main
with:
  java-runner: "['self-hosted', 'X64', 'Linux', 'ubuntu-docker']"
```

**Dependabot** (`.github/dependabot.yml`): Weekly dependency version update PRs.

**No build, test, or deployment pipeline is present.** Only security scanning is automated.

### Missing pipeline stages
- Maven build (`mvn clean install`) with JaCoCo 90% coverage enforcement
- Static analysis (Checkstyle is defined but not wired into CI)
- Artifact publishing to Nexus
- Docker image build
- Kubernetes deployment / Helm chart apply
- Liquibase migration execution
- Integration test suite (`cross-border-transfer-service-qa` module)

---

## 3. Configuration Management

| Configuration Item | File | Value | Assessment |
|---|---|---|---|
| Config server URI | `bootstrap.yml` (batch + web) | `http://localhost:9990/config-server` | **Localhost placeholder** — must be overridden per environment |
| Config server password | `bootstrap.yml` line 6 | `s3cr3t` | **Hardcoded secret** in source control |
| Config server username | `bootstrap.yml` line 5 | `application` | In source control |
| App credentials | `application.yml` lines 7–9 | `[REDACTED — rotate immediately]` / `6k50WLp...` | **API credentials hardcoded** |
| Cambridge partner signature | `application.yml:191` | `BwiVUg-UoXZfWoNSkwBFrjeoU4QZiCS-AOowiqpN78w` | **Cambridge API credential in source** |
| Cambridge client signatures | `application.yml:196,201,208,213` | `4fe39fc5...` / `0fd32305...` | **Cambridge API credentials in source** |
| Cambridge client IDs | `application.yml:193,200` | `252648_API_User`, `252650_API_User` | API user identifiers in source |
| SFTP credentials | `application.yml:319-324` | `username: wirecard / password: [REDACTED — rotate immediately]` | **SFTP credentials in source** |
| PGP passphrase | `application.yml:329` | `passphrase: wirecard` | **PGP key passphrase in source** |
| PGP key files | `application.yml:330-331` | `/pgp/0x6392B27D-pub.asc` / `-sec.asc` | PGP key file paths in config |
| H2 console | `application.yml:13-16` | `enabled: true` | **H2 console enabled — must be disabled in production** |
| Cambridge base URL | `application.yml:172` | `https://beta.cambridgelink.com` | **Beta environment URL in config** — not production |
| Liquibase DB migration | `db-app/application.yml` | `enabled: false` | Liquibase disabled in db-app config |
| Email addresses | `application.yml:295-310` | `test@wirecard.com` x 4 | Wirecard placeholder emails |

**CRITICAL FINDING**: Multiple credentials and secrets are hardcoded in `application.yml` and `bootstrap.yml`:
1. Config server password (`s3cr3t`)
2. Application credential (`[REDACTED — rotate immediately]` / `6k50WLp...`)
3. Cambridge API signatures (partner + 2 client signatures)
4. SFTP credentials (`wirecard`/`[REDACTED — rotate immediately]`)
5. PGP passphrase (`wirecard`)

All must be rotated and externalised to Spring Cloud Config + Vault before production deployment. The `bootstrap.yml` config server password would normally be the entry point for all other secrets — but it is hardcoded here.

---

## 4. Observability

- **Spring Boot Actuator**: Configured in `application.yml` with `management.endpoints.web.exposure.include: '*'` — all actuator endpoints exposed. Includes health, metrics, circuit breakers.
- **Health detail**: `show-details: ALWAYS` — health endpoint exposes internal state to all callers. This should be restricted to authenticated calls in production.
- **Circuit breakers**: Resilience4j circuit breakers configured for all Cambridge API calls; health indicator registered.
- **Logging**: `application.yml` enables `DEBUG` level for `com.wirecard.crossbordertransferservice.cambridgeclient` and Spring Security — note Wirecard package name in logging config.
- **Email alerts**: Job execution failure emails configured in `application.yml` to `test@wirecard.com` (placeholder addresses).
- **Batch job web UI**: `BatchJobController` exposes `/jobs` endpoint for job status and manual execution.
- **No APM integration**: No Datadog, New Relic, or Dynatrace configuration visible.
- **No distributed tracing**: No Spring Cloud Sleuth, OpenTelemetry, or Zipkin configuration visible in available source.

---

## 5. Infrastructure Dependencies

| Dependency | Type | Details |
|-----------|------|---------|
| Spring Cloud Config Server | Config management | `http://localhost:9990/config-server` — placeholder |
| SQL Server | Database | mssql-jdbc 9.2.1.jre11; Liquibase-managed schema |
| Cambridge Payments API | External partner | `https://beta.cambridgelink.com` — beta URL in config |
| Cambridge SFTP | File exchange | Host: `localhost:9099` (placeholder) — PGP-encrypted files |
| Ecount SFTP | File exchange | Host: `localhost:9099` (placeholder) — PGP-encrypted files |
| AWS S3 | File staging | `aws-java-sdk-s3` dependency in POM |
| Spring Boot 2.5.2 | Framework | Released May 2021; EOL Nov 2022 |
| Java 8 | Runtime | LTS (but Java 8 security support timeline varies by vendor) |
| `d-na-stk01.nam.wirecard.sys:8080/nexus` | Internal Maven repository | Wirecard-era Nexus |
| Self-hosted GitHub Actions runner | CI | `ubuntu-docker` runner for CodeQL |

---

## 6. Operational Risks

| Risk | Severity | Detail |
|------|---------|--------|
| Multiple credentials in source control | CRITICAL | Cambridge API signatures, SFTP password, PGP passphrase, app credentials all in `application.yml` |
| Config server password hardcoded (`s3cr3t`) | CRITICAL | Entry point to all externalised config is itself hardcoded |
| H2 console enabled | HIGH | `spring.h2.console.enabled: true` in `application.yml` — in-memory DB admin UI must be disabled in production |
| Cambridge base URL is `beta` | HIGH | `https://beta.cambridgelink.com` — production must use prod URL; easy to misconfigure |
| Actuator fully exposed without auth | HIGH | `exposure.include: '*'` exposes all management endpoints; health detail `ALWAYS` |
| `test@wirecard.com` email alerts | HIGH | Operational failure emails sent to Wirecard test inbox — operators would not receive alerts |
| Spring Boot 2.5.2 EOL | HIGH | EOL November 2022; known CVEs in transitive dependencies |
| Wirecard Nexus dependency | HIGH | Build fails if Wirecard Nexus is decommissioned |
| No deployment pipeline | HIGH | No automated build, test, or deployment |
| PGP private key path in config | MEDIUM | `/pgp/0x6392B27D-sec.asc` — private key must exist on server; must be protected |

---

## 7. CI/CD Assessment and Recommendations

**Current state**: CodeQL weekly scan only. No build, test, or deployment pipeline.

**Recommended full pipeline**:
```yaml
stages:
  - build          # mvn clean install (with JaCoCo 90% threshold)
  - checkstyle     # mvn checkstyle:check
  - codeql         # weekly security scan (existing)
  - liquibase-dev  # liquibase update on dev DB
  - docker-build   # docker build + push to ECR/ACR
  - deploy-dev     # helm upgrade --install on dev k8s namespace
  - integration    # run cross-border-transfer-service-qa tests
  - deploy-qa      # after QA approval
  - deploy-prod    # after change management approval
```

**Minimum immediate actions**:
1. Rotate all credentials in `application.yml` and `bootstrap.yml` and move to Spring Cloud Config + Vault.
2. Replace `test@wirecard.com` with Onbe-managed DL.
3. Change Cambridge URL from `beta` to production endpoint.
4. Disable H2 console in non-local environments via profile-specific config.
5. Restrict Actuator endpoints to authenticated requests.
