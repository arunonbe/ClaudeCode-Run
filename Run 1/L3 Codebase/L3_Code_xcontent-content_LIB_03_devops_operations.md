# xcontent-content_LIB — DevOps / Operations View

## Build
- **Build tool**: Maven (Maven Wrapper `mvnw`/`mvnw.cmd`)
- **Java version**: Java 1.5 (POM compiler config: `<source>1.5</source>`, `<target>1.5</target>`)
- **Packaging**: WAR (`<packaging>war</packaging>`), version `2.0.0-SNAPSHOT`
- **Parent POM**: `com.citi.prepaid.service:service-parent:8`
- **Key dependencies**:
  - `spring:1.2.7` (Spring Framework 1.2.7 — 2006 era)
  - `lucene-core:2.0.0` (Lucene 2.0.0 — 2006 era)
  - `junit:3.8.1` (test scope only)
  - `servlet-api:2.4` (compile scope — ancient Servlet API)
- **Local dev server**: Jetty 6 (`maven-jetty-plugin`) on port 9001
- **No active CI/CD pipeline** beyond GitHub's Dependabot and CodeQL scanning

## Deployment
- **CI/CD**: Only GitHub Actions for CodeQL analysis and Dependabot (`codeql.yml`, `dependabot.yml`)
- **No deployment workflow** defined — this library is consumed by `xcontent_SVC` as a dependency, not deployed independently
- **SCM URL**: `gitlab.wirecard-cloud.com/issuing/wdnam/prepaid/...` (Wirecard era, legacy hosting)
- **Git branch**: `master` (older convention; `xcontent_SVC` uses `main`)
- **No Dockerfile** — library only, not a deployable service

## Configuration Management
- **Hardcoded config path**: `CMSApplicationContext.xml` hardcodes `file:D:/c-base/config/xContent/applicationContext-xContent.properties` — no environment variable injection, no override mechanism
- **Properties file**: `src/main/resources/applicationContext-xContent.properties` contains:
  - `lucene.cms.dir=D:/c-base/src/xContent/content`
  - `lucene.cms.name=cms`
  - `lucene.cms.analyzer=WhitespaceAnalyzer`
- No externalized secrets or external config source

## Observability
- No logging framework configuration visible in this library
- No health endpoints, metrics, or tracing
- Library produces no operational telemetry itself; consumers inherit whatever logging framework they use

## Infrastructure Dependencies
| Dependency | Type | Notes |
|-----------|------|-------|
| Local filesystem | Content store | `D:/c-base/src/xContent/content` — Windows path |
| Jetty 6 (dev only) | Local dev server | Port 9001, context `/xContent` |

## Operational Risks
1. **SNAPSHOT version**: Any consumer of `com.ecount.one.web:xContent:2.0.0-SNAPSHOT` may receive a different artifact with each Maven resolution — non-deterministic builds
2. **Java 1.5 target bytecode**: Extremely old; modern JVMs can run it, but security fixes, generics, and modern APIs are absent
3. **Spring 1.2.7 dependency**: End-of-life since ~2007; multiple known vulnerabilities
4. **Servlet API 2.4 (compile scope)**: Overrides container-provided API; may conflict with modern Tomcat 10 (Servlet 6.0)
5. **No active CI deployment**: No build on every commit; no artifact published automatically
6. **Hardcoded Windows path**: Library is unusable in a containerized environment without modifying source XML

## CI/CD Pipeline
```
No deployment pipeline defined.

GitHub Actions (supplemental only):
  → codeql.yml: CodeQL security analysis on push/PR to master
  → dependabot.yml: Automated dependency update PRs

Local development:
  → mvn jetty:run (Jetty 6, port 9001, context /xContent)
```
