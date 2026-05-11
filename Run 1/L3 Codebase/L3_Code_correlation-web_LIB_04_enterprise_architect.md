# Enterprise Architect View — correlation-web_LIB

## 1. Platform Generation & Classification

| Attribute | Value |
|---|---|
| Platform generation | Gen 2 → Gen 3 transitional |
| Runtime target | Jakarta EE (Servlet 5.x, Tomcat 10.x+) |
| Java version | 21 (LTS) |
| API style | Servlet Filter — classical synchronous, request/response |
| Deployment model | Shared library JAR (not a standalone service) |
| Parent POM lineage | `com.parents:prepaid-parent:6.0.12` — Onbe internal BOM |
| Artifact registry | GitHub Packages (`onbe/onbe_maven_releases`) |

The migration from `javax.servlet` to `jakarta.servlet` (Jakarta EE namespace) at `CorrelationHeaderFilter.java:3–10` and `CorrelationWebContext.java:7` confirms this library has been updated for the Java EE → Jakarta EE rename, making it compatible with Tomcat 10+ and Spring Boot 3.x consumers. This is a meaningful platform modernity indicator.

---

## 2. Domain Placement

This library belongs to the **cross-cutting concerns / platform services** domain, not to any business domain (payments, disbursements, card management). It is an internal developer platform (IDP) building block.

```
Onbe Platform Map (library placement)
─────────────────────────────────────────────────────
  Business Domain Services
    ├── AccountManagementAPI
    ├── DisbursementsService
    ├── PrepaidCardService
    └── ...
  ─────────────────────────────────────────────
  Platform / Shared Libraries  ◄── THIS REPO
    ├── correlation-core          (CorrelationIDContext, CorrelationID)
    ├── correlation-web           (CorrelationHeaderFilter, CorrelationWebContext)
    └── ...
  ─────────────────────────────────────────────
  Infrastructure
    ├── Tomcat 10.x (servlet container)
    └── GitHub Actions / om-ci-setup (CI/CD)
```

---

## 3. Role in the Enterprise

`correlation-web` is one half of the two-library correlation ID solution:

| Library | Role | Scope |
|---|---|---|
| `correlation-core` v2.0.1 | Core ID model, thread-local storage, constants | All Java applications (non-web too) |
| `correlation-web` v2.0.1 | Servlet filter integration for HTTP extraction/injection | Web applications only |

Any Onbe service that uses both libraries and registers `CorrelationHeaderFilter` as a servlet filter automatically gains request-scoped correlation ID propagation. Services using only `correlation-core` can manually manage ID lifecycle.

---

## 4. Inter-Service Dependencies

### Inbound (what this library depends on)

| Dependency | GroupId:ArtifactId | Version | Scope | Source |
|---|---|---|---|---|
| correlation-core | `com.ecount.opensource:correlation-core` | 2.0.1 | compile | `pom.xml:28–31` |
| Jakarta Servlet API | `jakarta.servlet:jakarta.servlet-api` | from parent BOM | provided | `pom.xml:32–36` |
| Lombok | implicit via `@Slf4j` annotation | from parent BOM | compile/annotation | `CorrelationWebContext.java:8` |
| Parent BOM | `com.parents:prepaid-parent:6.0.12` | 6.0.12 | parent | `pom.xml:7–11` |

### Outbound (what consumes this library)
Not determinable from this repo alone. Any Onbe servlet-based service needing correlation IDs would declare this as a dependency. Based on the `deployment_temp.yml` copy-paste evidence, `AccountManagementAPI` is at minimum one known consumer.

---

## 5. Architectural Patterns

| Pattern | Application |
|---|---|
| **Servlet Filter Chain** | `CorrelationHeaderFilter implements jakarta.servlet.Filter` (`CorrelationHeaderFilter.java:12`) — standard GoF Chain of Responsibility / Interceptor pattern for cross-cutting concerns. |
| **ThreadLocal Context** | `CorrelationIDContext` (in core) stores the ID in thread-local storage; a stateless facade pattern is applied by `CorrelationWebContext` (no instance state, all static methods). |
| **Null Object / Safe Init** | If header is absent, a new ID is generated rather than propagating null (`CorrelationWebContext.java:18`). |
| **Separation of Concerns** | Web-layer filter (`correlation-web`) is decoupled from core ID management (`correlation-core`), allowing non-web consumers of `correlation-core`. |
| **Reusable CI Workflow** | GitHub Actions `uses:` delegation to `Onbe/om-ci-setup` centralises pipeline logic and reduces per-repo CI code. |

---

## 6. Platform Status

| Dimension | Status |
|---|---|
| Active development | Stable / maintenance — single commit (PR #17, Sep 2024); no outstanding open work visible. |
| Version alignment | Versions of `correlation-web` (2.0.1) and `correlation-core` (2.0.1) are in lock-step, which is appropriate for a tightly coupled pair. |
| Jakarta EE migration | Complete — all `javax.servlet` imports replaced with `jakarta.servlet`. |
| Java 21 compliance | Complete — `maven.compiler.source/target = 21`. |
| Test coverage | Zero — no `src/test` directory exists. |
| Documentation | Minimal — README covers only setup and build. No Javadoc. |

---

## 7. Blockers & Gaps

| # | Item | Impact | Owner Suggestion |
|---|---|---|---|
| B-1 | `deployment_temp.yml` references `AccountManagementAPI` | This workflow will execute on `main` pushes and may interfere with or confuse the correct `github-package-publish.yml` run; it targets an entirely different application. | DevOps / Repo owner — delete or correct immediately. |
| B-2 | No test coverage | Any future change to `CorrelationHeaderFilter` or `CorrelationWebContext` carries regression risk; CI cannot provide a safety net. | Engineering |
| B-3 | No Javadoc or API contract documentation | Consuming teams have no formal contract to program against, increasing coupling to implementation details. | Engineering |
| B-4 | `correlation-core` dependency is at the same version as this library — any breaking change to `correlation-core` requires a synchronised release | The version pin `${correlation-core.version}=2.0.1` (`pom.xml:23`) means the two libs must be released together. | Architecture — evaluate whether to use a BOM. |
| B-5 | `@Slf4j` and Lombok dependency is implicit (from parent BOM) | If the parent BOM changes or Lombok is removed, this library will fail to compile with no explicit declaration. | Engineering — add explicit Lombok dependency to `pom.xml`. |
