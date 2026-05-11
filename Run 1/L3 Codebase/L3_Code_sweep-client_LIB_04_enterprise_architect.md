# Enterprise Architect View — sweep-client_LIB

## Platform Generation
**Gen-1** — Legacy batch utility. Characteristics:
- Spring 2.0.8 (released 2008).
- AspectJ 1.5.2a (released 2006).
- Spring XML configuration (`applicationContext.xml` with Spring 2.0 schema).
- Apache Commons Logging + Log4j 1.x.
- Spring `HttpInvoker` with XStream serialisation (pre-REST era RPC).
- Fat JAR with command-line entry point.
- No Spring Boot, no containerisation.

## Business Domain
**Prepaid Card / Order Management — Automation** — Automates creation and lifecycle management of instant sweep orders for promotional programmes. Sits at the intersection of marketing/programme management and payment order operations.

## Role in Ecosystem
- Standalone scheduled batch client; not a shared library despite the `_LIB` suffix.
- Bridges between: xPlatform/CBase profile store (upstream) and Order Service (downstream).
- No direct dependency on any other listed repository in this analysis set.

## Dependencies
| Artifact | Version | Notes |
|----------|---------|-------|
| `com.ecount.service:service-parent:5` | Parent POM | External |
| `com.ecount.service.order:order-common` | 2.4.8-SNAPSHOT | Order domain DTOs |
| `com.ecount:xPlatform` | 2.5.33-SNAPSHOT | CBase/xPlatform platform library |
| `org.springframework:spring` | 2.0.8 | Critically EOL |
| `aspectj:aspectjrt` / `aspectjweaver` | 1.5.2a | Critically EOL |

Note: Both `order-common` and `xPlatform` are SNAPSHOT dependencies — production deployments using SNAPSHOTs are anti-pattern (non-reproducible builds).

## Integration Patterns
| Pattern | Details |
|---------|---------|
| Batch / command-line | Invoked by OS scheduler; processes all profiles in one run |
| Spring HTTP Invoker | RPC to Order Service using Java serialisation over HTTP (XStream marshaller variant) |
| Profile pull | Reads enabled promotions from xPlatform CBase on each run |
| AOP audit | `AuditMethodInterceptor` wraps all `MethodInvoker.invoke()` calls for logging |

## Strategic Status
**Decommission or replace.** This component:
- Uses unsupported framework versions (Spring 2.0.8, AspectJ 1.5.2a) with known security vulnerabilities.
- Relies on SNAPSHOT dependencies, making build reproducibility impossible.
- Has no automated build pipeline.
- The functionality (creating/closing sweep orders on a schedule) is a good candidate for:
  - A Spring Batch job running inside a modern Spring Boot microservice.
  - A Kubernetes CronJob calling a REST API exposed by the Order Service.
  - A serverless function (AWS Lambda / Azure Function) triggered on a schedule.

## Migration Blockers
| Blocker | Description |
|---------|-------------|
| Spring 2.0.8 → Spring Boot 3.x | Full rewrite of XML configuration required |
| Spring HTTP Invoker + XStream | Order Service must expose a REST or gRPC API; HTTP Invoker is Spring-specific and deprecated |
| SNAPSHOT dependencies | `order-common:2.4.8-SNAPSHOT` and `xPlatform:2.5.33-SNAPSHOT` must be released to stable versions before migration |
| xPlatform coupling | `AppPromotionInstantSweepOrderProfileClass` is tightly coupled to the CBase/xPlatform platform; migration requires either a platform API or a profile query refactor |
| Missing production config | No production `sweep.client.properties` exists in this repo — config location and content must be discovered before migration |
