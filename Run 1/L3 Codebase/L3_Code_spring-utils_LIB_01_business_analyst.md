# spring-utils_LIB — Business Analyst View

## Business Purpose
`spring-utils_LIB` (artifact: `com.citi.prepaid.springutils:springutils:3.1.0`) is a shared internal Java library that provides reusable Spring Framework infrastructure plumbing for the Onbe prepaid card platform. Originally developed under the `com.citi.prepaid` (Citi/eCount) namespace, it supplies cross-cutting capabilities consumed by multiple back-end services. Its primary value is in reducing duplicate infrastructure code across the Gen-1/Gen-2 service fleet.

## Capabilities
| Capability | Module | Description |
|---|---|---|
| Method-level audit logging | `springutils-generic` — `AuditMethodInterceptor` | AOP interceptor that logs method entry, exit, duration, and arguments via XStream XML serialisation. Classifies calls as LOCAL, RPC-REMOTE, SQL, FDR, or ICS based on class package. |
| Global request ID propagation | `springutils-generic` — `GlobalRequestIDInterceptor` | Propagates a correlation/request ID across service calls. |
| MDC (Mapped Diagnostic Context) writing | `springutils-generic` — `Log4jMDCWriter`, `MDCWriter` | Writes structured method-level timing data into Log4j MDC for log correlation. |
| Visit / invocation statistics | `springutils-generic` — `MethodVisitStatistics`, `VisitStatisticsMethodInterceptor` | Tracks per-method call counts and timing for operational visibility. |
| Environment-switched property configuration | `springutils-generic` — `SwitchedPropertyPlaceholderConfigurer` | Selects a `PropertyPlaceholderConfigurer` at startup based on a switch property value read from a classpath resource — enables environment-specific configuration (dev/qa/prod). |
| Application health monitor UI | `springutils-generic` — `MonitorFormController`, `DatabaseMonitorTestExecutor` | Spring MVC controller exposing a `/monitor` endpoint that runs configurable health checks (DB connectivity, method invocations, bean reloads). |
| Hot-reloadable beans | `springutils-generic` — `ReloadableBean` (deprecated), `ReloadableContextBean`, `ReloadableContext` | AOP target sources that allow Spring beans to be re-initialised at runtime without restarting the JVM. |
| HTTP Invoker remoting | `springutils-generic` — `CustomHttpInvokerReqeustExecutor`, `CustomHttpInvokerServiceExporter` | Custom Spring HTTP Invoker transport with configurable connection/read timeouts and pluggable XML marshalling (XStream). |
| XML-RPC proxy support | `springutils-generic` — `AbstractGenericXmlRpcProxy` | Base class for XML-RPC client proxies. |
| JMS-based RPC | `springutils-jms` — `JmsInvokerClientInterceptor`, `JmsInvokerServiceExporter`, `ConfigurableJmsInvokerProxyFactoryBean` variants | JMS request/reply invocation infrastructure over point-to-point queues and pub/sub topics. Uses Jakarta JMS API. |
| JMS one-way messaging | `springutils-jms` — `ConfigurableOneWayJmsInvokerProxyFactoryBean` | Fire-and-forget JMS dispatch. |
| JMS message scattering | `springutils-jms` — `MessageScatteringSessionAwareMessageListener` | Fan-out of a single inbound JMS message to multiple downstream services. |
| XStream JMS marshalling | `springutils-jms` — `XStreamMessageMarshaller` | Serialises/deserialises JMS message payloads using XStream XML. |

## Key Entities
- `MonitorTest` — represents a single health-check test result (name, group, active, successful, executed, cause, message).
- `MonitorFormData` — aggregation of `MonitorTest` results for a named application.
- `ChannelConfig` — JMS channel configuration (queue/topic names, one-way vs two-way).

## Business Rules
1. The monitor endpoint runs only those tests marked active; prerequisites must pass before dependents execute.
2. Environment-switched configuration must match an exact key from the `cases` map; if `matchRequired=true` and no match, startup fails.
3. `ReloadableBean` falls back to a no-op proxy if the target bean cannot be loaded — preventing a failed optional integration from crashing the whole application.

## Business Flows
1. **Request tracing**: inbound HTTP/JMS call → `GlobalRequestIDInterceptor` injects correlation ID → `MDCWriter` populates MDC → `AuditMethodInterceptor` logs method entry/exit with timing.
2. **Health check**: operator opens `/monitor` → `MonitorFormController` iterates registered `MonitorTestExecutor` instances → results rendered via `MonitorView`.
3. **JMS RPC call**: client proxy → `JmsInvokerClientInterceptor` serialises invocation → JMS queue → `JmsInvokerServiceExporter` deserialises and invokes bean method → reply queue → client.

## Compliance Relevance
- Audit logging (`AuditMethodInterceptor`) supports PCI DSS Requirement 10 (logging and monitoring) and SOC 2 CC7.
- Request correlation IDs support traceability requirements under GLBA and FFIEC audit log guidance.
- Monitor endpoint may expose internal infrastructure state — access must be restricted (no authentication logic observed in code).

## Risks
| Risk | Severity | Notes |
|---|---|---|
| Monitor endpoint unauthenticated | High | `/monitor` controller has no auth enforcement in code; relies on container/network controls |
| XStream `AnyTypePermission.ANY` | High | Allows deserialisation of any class — known CVE vector if exposed to untrusted input |
| Legacy `com.citi.prepaid` namespace | Medium | Suggests pre-Onbe origin; IP/licensing provenance should be confirmed |
| `ReloadableBean` deprecated | Low | Callers should migrate to `ReloadableContextBean` |
