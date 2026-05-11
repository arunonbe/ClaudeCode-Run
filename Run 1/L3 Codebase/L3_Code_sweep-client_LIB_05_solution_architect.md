# Solution Architect View — sweep-client_LIB

## Technical Architecture
Single-module Maven project, packaged as a fat JAR with a `Main` class entry point. Spring IoC context loaded from classpath XML. Five `MethodInvoker` implementations dispatched via `MethodInvokerFactory` (strategy pattern with a `Map<String, MethodInvoker>`). AOP wraps all invoker calls with an audit interceptor.

```
Main (CLI args) --> SweepClient
                        |
                 ProfileReader.getSweepOrderProfileList()
                        |
                 [xPlatform CBase]
                        |
                 MethodInvokerFactory.find(method)
                        |
              ┌─────────┴────────────┐
         CreateMethodInvoker ... CheckNotificationThresholdMethodInvoker
              |
         OrderServiceMethodInvoker.orderService (HTTP Invoker)
              |
         [Order Service]
```

## API Surface
Command-line only. No HTTP server, no REST API.
```
java -jar sweep-client.jar -method <Create|Close|Reserve|Free|Notify> [-time <seconds>] [-dryRun]
```

Exit codes: 0 (success), 1 (partial/unknown failure), 2 (profile error), 3 (service unavailable), 4 (context load failure), 5 (usage error).

## Security Posture

### Authentication
- No authentication at the sweep client level for the Order Service call.
- xPlatform/CBase access uses `agent` + `affiliateId` + `memberId` identifiers — no token or certificate-based auth observed.

### Cryptography
None implemented in this client.

### Secrets Management
- `memberId` (a GUID) and `agent` are configuration properties, not credentials — no secret material.
- Order Service URL is externally configured via `CBASE_HOME_URL` environment variable.
- If `CBASE_HOME_URL` is unset or the properties file is missing, the application silently uses `B2CTEST` defaults.

### Known CVE / Vulnerable Dependencies
| Library | CVE Exposure | Severity |
|---------|-------------|---------|
| Spring 2.0.8 | EOL; numerous Spring Security CVEs (SpEL injection, SSRF, etc.) | Critical |
| AspectJ 1.5.2a | EOL | High |
| XStream (via xPlatform) | CVE-2021-39144, CVE-2022-40151, and numerous others — arbitrary code execution via deserialization | Critical |
| Log4j 1.x | CVE-2019-17571 (SocketServer RCE) | High |

XStream deserialization is the highest-severity risk: if the HTTP Invoker endpoint is reachable by an attacker and XStream is not configured with type filters, arbitrary code execution is possible.

## Technical Debt
| Item | Location | Severity |
|------|----------|----------|
| Spring 2.0.8 | `pom.xml:88-92` | Critical |
| AspectJ 1.5.2a | `pom.xml:94-103` | Critical |
| SNAPSHOT dependencies | `pom.xml:19-21` | High |
| XStream marshaller | `applicationContext.xml:70-72` | Critical |
| Log4j 1.x | `src/main/resources/log4j.properties` | High |
| Fallback to test defaults if production config missing | `configuration.xml:12-14` | Critical |
| No test classes | — | High |
| `maven-wrapper.jar` in VCS | `.mvn/wrapper/maven-wrapper.jar` | Medium |
| `noFalure` typo in `SweepClient.java` | `SweepClient.java:67` | Low |
| Spring schema references use `2.0` namespace (`spring-beans-2.0.xsd`) | `applicationContext.xml:7-8` | Medium |

## Code-Level Risks
| Risk | Location | Description |
|------|----------|-------------|
| Silent fallback to B2CTEST agent | `configuration.xml:13` | `ignoreResourceNotFound=true` on production config path — if missing, test agent `B2CTEST` with test member GUID is used silently. |
| XStream deserialization | `applicationContext.xml:70-72` | `XStreamMarshaller` used for HTTP Invoker; no type whitelist configured — full deserialization attack surface exposed. |
| No idempotency key | `CreateMethodInvoker.java:24-36` | `CreateSweepOrdersRequest` has no idempotency token; a duplicate run will create duplicate orders. |
| Broad catch swallows exceptions | `SweepClient.java:90-93` | `catch (Exception ex)` marks profile as failed and continues; root cause may be a transient infrastructure failure, leading to incorrect failure reporting. |
| `OrderServiceMethodInvoker` field access | All invoker classes | `orderService` is set via Spring setter injection; no null check — a misconfigured context would throw NPE at invocation time. |

## Gen-3 Migration Requirements
1. Replace fat JAR + cron invocation with a Spring Boot Batch application or a Kubernetes CronJob calling a REST API.
2. Replace XStream HTTP Invoker with authenticated REST calls (OAuth2 client credentials or mTLS).
3. Upgrade Spring to 6.x, remove AspectJ 1.5.2a (use Spring AOP with AspectJ 1.9.x).
4. Replace Log4j 1.x with Logback.
5. Pin all dependencies to release versions (no SNAPSHOTs in production).
6. Add production config validation at startup — fail-fast if required properties are absent or contain test values.
7. Implement idempotency for order creation (idempotency key per programme+promotion+date).
8. Add structured logging (JSON) and metrics (Micrometer) for observability.
