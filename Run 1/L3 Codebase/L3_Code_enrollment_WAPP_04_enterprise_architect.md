# Enterprise Architect Analysis — enrollment_WAPP

## Repository Overview

**Repo:** `enrollment_WAPP`
**Platform generation:** Gen-2 (Java 8, Spring XML, Struts 1, Tomcat WAR — transitional from Gen-1)
**Heritage:** Wirecard/eCount → North Lane → Onbe
**SCM origin:** `gitlab.wirecard-cloud.com` (Wirecard infrastructure)

---

## Platform Generation Assessment

`enrollment_WAPP` represents Onbe's **Gen-2 web application architecture** — it has moved beyond pure batch processing to a user-facing web application but retains Gen-1 characteristics in its framework choices:

| Dimension | Gen-1 (`enrollment_LIB`) | Gen-2 (`enrollment_WAPP`) | Gen-3 Exemplar |
|-----------|--------------------------|--------------------------|----------------|
| Java | 1.6 | 1.8 | 11 |
| Web framework | None (batch) | Struts 1.3.8 (2007) | Spring Boot REST |
| Spring | 2.0.8 XML | 2.0.3 XML | Boot 2.4–2.5, YAML |
| Deployment | JAR / cron | Tomcat WAR | Docker / Kubernetes |
| CI/CD | None → CodeQL | Jenkins + GitLab CI | GitHub Actions + CodeQL |
| Authentication | N/A | RSA MFA + SSO | Spring Security |
| Event handling | File-based | None (sync) | Dapr pub/sub |
| Testing | None | Integration tests (allow_failure) | JUnit 5 + Cucumber BDD |

---

## Enterprise Architecture Position

### Application Landscape Role

`enrollment_WAPP` is the **primary cardholder-facing enrollment interface** for Onbe's prepaid card programmes. It is a **System of Engagement** that:
1. Receives enrollment decisions from cardholders.
2. Writes those decisions to the backend profile service (cBase).
3. Triggers email notifications.
4. Feeds the `enrollment_LIB` extract process which delivers data to partner banks.

### System Context Diagram

```
[Cardholder Browser]
        |
        v
[enrollment_WAPP - Tomcat WAR]
        |
        |-- cBase Profile Service (enrollment state)
        |-- SQL Server (login, user management)
        |-- Director (DB connection routing)
        |-- CMS (brand/content)
        |-- SMTP (notifications)
        |-- RSA SecurID (MFA)
        |-- xPlatform / xSecurity (auth framework)
        |-- Affiliate Service (brand metadata)
        |
        v
[enrollment_LIB batch process] --> [FTP files to partner banks]
```

### Integration Architecture Concerns

1. **Struts 1 is end-of-life** — Apache Struts 1 was officially retired in 2013 (EOL announcement). It is not patched for new vulnerabilities. Running a PCI-scoped cardholder enrollment application on an EOL MVC framework is a significant security and compliance risk.
2. **eCount/cBase dependency lock-in** — `AppProfileUserEnrollment`, `AppProfileUserEnrollmentClass`, the xPlatform/xSecurity libraries, the Director service, and the cBase config server are all proprietary eCount components. Migration away from these requires significant refactoring effort.
3. **No API contract** — the application exposes no documented API. Downstream systems (including `enrollment_LIB`) cannot discover the enrollment state without direct database or cBase access.

---

## Strategic Architecture Concerns

### 1. Struts 1 CVE Exposure

Struts 1.x has multiple unpatched CVEs including:
- CVE-2014-0114 — ClassLoader manipulation via ActionForm fields (CVSS 7.5).
- CVE-2016-1181 — Remote code execution via multipart handling.

A cardholder-facing application using Struts 1 is in direct conflict with PCI DSS v4.0.1 Req 6.3 (protect bespoke software from known vulnerabilities).

### 2. Multi-Brand Architecture

The application supports multiple brands/affiliates via `AppContextService` and the CMS. This is an important business capability, but the implementation is tightly coupled to eCount's proprietary `AppContext` model. Migrating to a cloud-native multi-tenancy pattern (e.g., per-brand configuration in Spring Cloud Config) requires significant rearchitecting.

### 3. Legacy Nexus Repository

Distribution management points to `d-na-stk01.nam.wirecard.sys:8080/nexus/` — a legacy Nexus instance on Wirecard/North Lane infrastructure. If this server is decommissioned, CI/CD pipelines will break. Migration to a cloud-hosted artefact registry (e.g., AWS CodeArtifact, Azure Artifacts) is required.

### 4. Dual CI System

Both Jenkins and GitLab CI pipelines exist. This indicates a migration in progress (from Jenkins to GitLab CI) that was never completed. Maintaining two pipelines creates operational overhead and inconsistency.

---

## Compliance Architecture Assessment

| Control | Implementation | Status |
|---------|---------------|--------|
| PCI DSS Req 6.2 — Patch management | Struts 1.x EOL; Log4j 1.x CVE | Non-compliant |
| PCI DSS Req 8 — Authentication | RSA MFA present | Partially compliant |
| PCI DSS Req 6.3 — Bespoke software | No DAST evidence, CodeQL not configured | Gap |
| Reg E — Enrollment consent | T&C service present | Partially addressed |
| GDPR/CCPA — Data subject rights | No evidence of deletion/portability | Gap |

---

## Enterprise Architecture Recommendations

1. **Priority 1 — Migrate off Struts 1** — rewrite enrollment UI as a Spring Boot + Thymeleaf or React + Spring Boot REST application. Aligns with Gen-3 patterns.
2. **Priority 2 — Decouple from cBase/eCount** — replace `AppProfileUserEnrollment` with a Gen-3 microservice (enrollment-service) that owns enrollment state in SQL Server, exposed via REST API.
3. **Priority 3 — Consolidate CI/CD** — retire Jenkins pipeline; use GitLab CI exclusively (or migrate to GitHub Actions with `om-ci-setup` templates as used in Gen-3 repos).
4. **Priority 4 — Containerise** — deploy as a Docker container on Kubernetes, replacing Tomcat WAR deployment.
5. **Priority 5 — Event-drive enrollment notifications** — publish enrollment events to a message bus (Dapr/MQTT or Kafka) for downstream consumption, eliminating the file-based `enrollment_LIB` extract.
