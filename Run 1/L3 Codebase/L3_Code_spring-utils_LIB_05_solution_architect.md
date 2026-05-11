# spring-utils_LIB — Solution Architect View

## Technical Architecture
Multi-module Maven JAR library (`springutils:3.1.0`). Two active modules:

```
springutils (parent pom)
├── springutils-generic   — AOP, remoting, monitor, config, POJO utilities
└── springutils-jms       — JMS invoker infrastructure (depends on springutils-generic)
```

The library is pure Java 21 with no main class or startup entry point. Consumers wire it into their Spring application contexts via XML bean definitions or annotation-based configuration.

## API Surface
The library exposes no HTTP API of its own. Its public surface is the Java API:

| Class | Public Surface | Notes |
|---|---|---|
| `AuditMethodInterceptor` | Spring `MethodInterceptor` — add to ProxyFactoryBean interceptor chain | Configurable prefix/suffix, statistics, MDC writer |
| `GlobalRequestIDInterceptor` | Spring `HandlerInterceptor` | Injects request correlation ID |
| `SwitchedPropertyPlaceholderConfigurer` | Spring `BeanFactoryPostProcessor` | Environment switching |
| `MonitorFormController` | Spring MVC `@Controller` at `/monitor` | Health check UI |
| `DatabaseMonitorTestExecutor` | `MonitorTestExecutor` | DB health probe |
| `ReloadableContextBean` | Spring `TargetSource` | Hot-reload bean wrapper |
| `CustomHttpInvokerReqeustExecutor` | Spring `HttpInvokerRequestExecutor` | HTTP remoting client |
| `CustomHttpInvokerServiceExporter` | Spring MVC `HttpRequestHandler` | HTTP remoting server |
| `JmsInvokerClientInterceptor` | AOP `MethodInterceptor` | JMS RPC client |
| `JmsInvokerServiceExporter` | JMS `MessageListener` | JMS RPC server |
| `ConfigurableJmsInvokerProxyFactoryBean` variants | `ProxyFactoryBean` wrappers | Queue / one-way / pub-sub |
| `XStreamMessageMarshaller` | JMS `MessageMarshaller` | XStream XML marshalling |

## Security Posture

### Authentication
- The `/monitor` endpoint (`MonitorFormController`) has no authentication or authorisation enforcement in its own code. Access control must be implemented at the Servlet container or API gateway level.
- HTTP Invoker: `CustomHttpInvokerConfig.setRequestContextHeaders(con)` injects headers — content unknown without the `request-context` library, but no credential challenge is visible.

### Cryptography
- No cryptographic operations are performed by this library.
- TLS for HTTP Invoker depends on the consuming service's `HttpURLConnection` / JVM TLS configuration.
- JMS transport security depends on the broker configuration, not this library.

### Secrets Management
- No hardcoded secrets observed in source code.
- `settings.xml` uses `${env.GITHUB_TOKEN}` — correct pattern.

### Known CVE Concerns

| Component | Risk | CVE Context |
|---|---|---|
| XStream (version unknown — inherited from parent) | **Critical** | XStream has had numerous CVEs for unsafe deserialisation (CVE-2021-29505, CVE-2021-39140, CVE-2022-40151, others). `AuditMethodInterceptor` uses `AnyTypePermission.ANY` which disables the security framework. |
| Spring HTTP Invoker (`SimpleHttpInvokerRequestExecutor`) | High | Spring HTTP Invoker uses Java serialisation over HTTP; deprecated by Spring team as a security risk. |
| JMS ObjectMessage (`SimpleMessageConverter`) | High | Java ObjectMessage deserialisation is a known gadget-chain attack vector if the JMS broker is reachable by untrusted parties. |

## Technical Debt

| Item | File / Class | Detail |
|---|---|---|
| `ReloadableBean` deprecated | `springutils-generic/.../pojo/ReloadableBean.java:34` | Marked `@Deprecated` — consumers should migrate to `ReloadableContextBean` |
| `@SuppressWarnings("unchecked")` raw type | `MonitorFormController.java:125` | `Class clazz` raw type in `supports()` method |
| Tests skipped in CI build | `.github/workflows/github-package-publish.yml:42` | `-Dmaven.test.skip` means no test execution on publish |
| Spring HTTP Invoker usage | `springutils-generic/.../remoting/` | Spring deprecated the HTTP Invoker in Spring 5.3 and removed it in Spring 6. The library uses a `jakarta-spring-remoting` bridge (separate artifact) — indicates a compatibility shim, not a clean upgrade. |
| XStream `AnyTypePermission.ANY` | `AuditMethodInterceptor.java:61` | Explicitly grants unrestricted deserialisation permission |
| `System.out.println` in TraverseAll (in sql-validator, not here) | N/A | Not applicable to this repo |
| `springutils-mock` commented out | `pom.xml:42` | Module disabled; unclear if maintained |
| Typo in class name | `CustomHttpInvokerReqeustExecutor.java` | "Reqeust" is a misspelling of "Request"; public class name cannot be fixed without a breaking API change |

## Gen-3 Migration Requirements
1. Replace `AuditMethodInterceptor` with Spring AOP + Micrometer tracing (or OpenTelemetry) for distributed tracing.
2. Replace `JmsInvokerClientInterceptor` / `JmsInvokerServiceExporter` with Kafka or Azure Service Bus event-driven messaging.
3. Replace `CustomHttpInvokerReqeustExecutor` with Spring `WebClient` or `RestClient` (standard REST).
4. Replace `SwitchedPropertyPlaceholderConfigurer` with Spring Boot profiles + Azure App Configuration.
5. Replace `/monitor` endpoint with Spring Boot Actuator health endpoints and Micrometer metrics.
6. Replace XStream serialisation with Jackson JSON or Protocol Buffers.
7. Enforce XStream type filtering before any interim usage continues.

## Code-Level Risks
| Risk | File | Line | Notes |
|---|---|---|---|
| XStream AnyTypePermission.ANY | `springutils-generic/src/main/java/com/ecount/springutils/aop/AuditMethodInterceptor.java` | 61 | `this.xstream.addPermission(AnyTypePermission.ANY)` — arbitrary class deserialisation enabled |
| Java object serialisation over JMS | `springutils-jms/src/main/java/com/ecount/springutils/jms/remoting/JmsInvokerClientInterceptor.java` | 117–121 | `SimpleMessageConverter` serialises to/from `ObjectMessage` |
| Unauthenticated monitor endpoint | `springutils-generic/src/main/java/com/ecount/springutils/monitor/controller/MonitorFormController.java` | 30 | `@RequestMapping(path = {"","/", "/monitor"})` — no auth annotation |
| Raw SQL execution in monitor | `springutils-generic/src/main/java/com/ecount/springutils/monitor/test/DatabaseMonitorTestExecutor.java` | 43–45 | `getJdbcTemplate().execute(sql)` — SQL is configuration-driven but not parameterised; caller must ensure safe SQL content |
