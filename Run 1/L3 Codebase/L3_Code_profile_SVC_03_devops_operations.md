# DevOps / Operations — profile_SVC

## Build System

| Property | Value |
|---|---|
| Build tool | Apache Maven (Wrapper `./mvnw` provided) |
| Java version | 21 (`maven.compiler.source/target = 21`) |
| Parent POM | `com.parents:prepaid-parent:6.0.13` |
| Root artifact | `com.ecount.service.core.Profile:profile-parent:4.0.4-SNAPSHOT` |
| Modules | `profile-common`, `profile-client`, `profile-impl`, `profile-xmlrpc`, `profile-monitor` |
| Code coverage | JaCoCo 0.8.11 (prepare-agent, report, report-aggregate phases) |
| Build scripts | `mvn_core2_Profile.bat` and `mvn_core2_Profile_without_dependencies.bat` (Windows batch — indicates legacy developer workflow) |

## Deployment

| Workflow | File | Trigger | Target |
|---|---|---|---|
| Deploy ProfileSVC | `deployment.yml` | Push to `main` (non-infra paths); PR to `main` | `Onbe/om-ci-setup java-workflow.yml@main` |
| Publish library to GitHub Packages | `github-package-publish.yml` | Push to `main`; PR to `main`; `workflow_dispatch` | GitHub Packages |
| CodeQL | `codeql.yml` | Push; PR; schedule | GitHub Security |

### Deployment Parameters (`deployment.yml`)
| Parameter | Value |
|---|---|
| `APP_NAME` | `ProfileSVC` |
| `PACT_PACTICIPANT` | `profile-svc` |
| `VERIFY_PROVIDER_PACT` | `false` |
| `TARGET_ROOT` | `./profile-xmlrpc` |
| `PUBLISH_TO_APIM` | `true` (WSDL published to API Management) |
| `INTERNAL_APIM` | `false` |
| `EXTERNAL_APIM` | `false` |
| `MAVEN_ARGS` | `-s ./.mvn/wrapper/settings.xml -Dmaven.test.skip` |
| `EXCLUDE_STAGE` | `true` |
| `BACKEND_SUFFIX` | `/services/ProfileWebServices` |
| `UPDATE_PARENT_VERSION` | `true` |
| `UPDATE_DEPENDENCIES` | `false` |

Note: `-Dmaven.test.skip` means **all tests are skipped** in the production deployment pipeline.

Also note: `.gitlab-ci.yml` is present, indicating this service was previously (or concurrently) deployed via GitLab CI in addition to GitHub Actions.

## Configuration Management

Configuration is managed by the consuming infrastructure (not stored in this repo). Key configurable parameters:
- `NamedDataSourcesList` — JDBC datasource names and connection strings (Spring/infrastructure config)
- Director service URL — injected at deployment into `ProfileImpl.directorAddress`
- XML-RPC servlet endpoint configuration — in `profile-xmlrpc` module's Spring application context

Maven settings are in `.mvn/wrapper/settings.xml` (contains repository credentials — not visible in source but referenced in build commands).

## Observability

| Signal | Mechanism |
|---|---|
| Logging | SLF4J / Logback (`@Slf4j` on `ProfileImpl`); exceptions printed via `logException()` with full stack trace to ERROR |
| Metrics | None visible in source |
| Distributed tracing | None (Gen-2 service — no OTel instrumentation) |
| Audit trail | `ClassLogInquiry` provides application-level query of change history from the database |
| Health monitoring | `profile-monitor` module exists; contains `MonitorMain.java` and `ConfiguredProfileServiceLocationResolver` — a standalone monitoring utility |

## Infrastructure Dependencies

| Dependency | Purpose | Notes |
|---|---|---|
| FDR / Core2 RDBMS | Profile class and scope data | Legacy; connection via `NamedDataSourcesList` |
| Director service | XML-RPC service location resolution | Cached 1 hour; failure leaves client with stale endpoint |
| Apache HttpClient 3.x | XML-RPC transport | Legacy library (`org.apache.commons.httpclient.HttpClient`) — EOL, not `httpclient4` or `httpclient5` |
| GitLab CI (`.gitlab-ci.yml`) | Previous or parallel CI | Suggests dual-platform deployment history |
| Azure API Management | WSDL publication (`PUBLISH_TO_APIM: true`) | WSDL exposed through APIM |
| Trivyignore (`.trivyignore`) | Container vulnerability scan exceptions | Trivy used for container scanning — indicates Docker/containerised deployment |

## Operational Risks

| Risk | Severity | Notes |
|---|---|---|
| Tests skipped in production deploy (`-Dmaven.test.skip`) | High | Regressions will not be caught before deployment |
| Apache HttpClient 3.x (legacy EOL) | High | `org.apache.commons:commons-httpclient:3.1.4` — known CVEs, no maintenance since 2011 |
| Director service 1-hour cache — stale routing after failover | Medium | Client may route to dead instance for up to 1 hour |
| `.gitlab-ci.yml` present alongside GitHub Actions — dual CI paths | Medium | Risk of divergent deployment configurations |
| `4.0.4-SNAPSHOT` version — mutable artifact | Medium | Downstream consumers may pick up unintended changes |
| PACT verification disabled | Medium | No contract verification; API changes may silently break consumers |
| Windows `.bat` build scripts committed | Low | Indicates local developer workflow not containerised |

## CI/CD Pipeline Summary

```
Push to main
  --> deployment.yml
      --> om-ci-setup java-workflow.yml
          mvn -s .mvn/wrapper/settings.xml -Dmaven.test.skip
          --> Deploy to environment (QA; STAGE excluded)
          --> Publish WSDL to APIM

Push to main / PR
  --> github-package-publish.yml
      --> om-ci-setup java-package-publish.yml
          mvn -s .mvn/wrapper/settings.xml -Dmaven.test.skip
          --> Publish JAR to GitHub Packages

Always (push/PR/schedule)
  --> codeql.yml
      --> om-ci-setup codeql-auto.yml
```
