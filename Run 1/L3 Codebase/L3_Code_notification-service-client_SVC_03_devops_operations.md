# DevOps & Operations — notification-service-client_SVC

## Build
- Build tool: Maven Wrapper.
- Group: `com.northlane`, artifact: `notification-service-client`, version: `2.0.0-SNAPSHOT`.
- Java source/target: **Java 8** (`maven-compiler-plugin source/target: 8`).
- Spring Framework: **4.3.27.RELEASE** (not Spring Boot; plain Spring).
- Packaging: `jar` (library, not executable).
- Notable build plugins: maven-checkstyle-plugin 3.1.1, JaCoCo 0.8.5, maven-surefire-plugin 3.0.0-M5.
- WebDAV wagon for deployment to Nexus.

## Deployment
- This is a **library JAR** — it is not deployed as a standalone service.
- Distributed to internal Maven repository (Nexus) at `http://d-na-stk01.nam.wirecard.sys:8080/nexus/` (legacy Wirecard/NorthLane infrastructure).
- Consuming services declare a Maven dependency on `com.northlane:notification-service-client:2.0.0-SNAPSHOT`.
- No Dockerfile, no container, no Azure deployment.

## Configuration (consumed by callers)
Callers must provide the following Spring properties:
```
notification.urls.base-url=<notification service URL>
notification.http-client.read-timeout=<ms>
notification.http-client.connect-timeout=<ms>
notification.circuit-breaker.failure-rate-threshold=<float>
notification.circuit-breaker.wait-duration-in-open-state=<seconds>
notification.circuit-breaker.slow-call-duration-threshold=<ms>
notification.circuit-breaker.minimum-number-of-calls=<int>
```
No default values observed in the library for `base-url` — must be supplied by the consuming application.

## Observability
- SLF4J logging via `@Slf4j` Lombok annotation — log output controlled by consuming application's logging config.
- No metrics or tracing instrumentation built into this library.
- Correlation ID propagated via `CorrelationIdInterceptor` as an HTTP request header — consuming applications must populate `RequestContext` with a correlationId for distributed tracing.
- Error handling: `ErrorHandler` converts non-2xx Feign responses into typed exceptions (`NotificationServiceRestErrorResponseException`, `NotificationServiceRestException`).

## Infrastructure Dependencies
| Dependency | Notes |
|-----------|-------|
| Notification Service REST API | `${notification.urls.base-url}` — external service |
| Internal Nexus (`d-na-stk01.nam.wirecard.sys`) | Artifact repository — legacy Wirecard infrastructure |
| `notification-event-handler-common:2.0.0-SNAPSHOT` | NorthLane internal dependency |
| `notification-rest-controller:2.0.0-SNAPSHOT` | NorthLane internal dependency |
| `correlation-web:1.0.0` | eCount/NorthLane correlation library |

## CI/CD
- `.gitlab-ci.yml` present — GitLab CI used (not GitHub Actions for primary builds).
- GitHub Actions: CodeQL analysis only (`.github/workflows/codeql.yml`, `codeql-java.yml`).
- Dependabot configured.
- Jenkinsfile present — Jenkins pipeline also configured (multi-CI environment).
- JaCoCo coverage thresholds enforced at build: instruction 37%, class 44%, line 41%, branch 27%, method 50% — these thresholds are low.
- Checkstyle enforced at `validate` phase using custom `checkstyle.xml`.

## Operational Risks
- **Java 8 / Spring 4.3.27**: both are end-of-life or approaching EOL; security patch availability limited.
- Nexus URL references legacy Wirecard infrastructure (`d-na-stk01.nam.wirecard.sys`) — artifact resolution may fail if this host is decommissioned.
- SNAPSHOT dependencies (`notification-event-handler-common:2.0.0-SNAPSHOT`, `notification-rest-controller:2.0.0-SNAPSHOT`) — non-deterministic builds.
- `plain HTTP` Nexus URL — artifact downloads over unencrypted transport.
- Resilience4j 1.6.1 — not the latest; check for known CVEs.
- Commons-lang 2.2 (2004 vintage) — very old; potential security vulnerabilities.
- `regexp:regexp:1.3` (Apache ORO, 2001 vintage) — extremely old library.
