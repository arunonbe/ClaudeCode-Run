# spring-utils_LIB — Enterprise Architect View

## Platform Generation
**Gen-2** — confirmed by:
- Group ID rooted in `com.citi.prepaid` (legacy Citi/eCount heritage namespace adopted into the Onbe estate)
- Parent POM `com.parents:prepaid-parent:6.0.13` which is the Gen-2 prepaid parent
- Spring XML application context patterns (`ClassPathXmlApplicationContext`, `PropertyPlaceholderConfigurer`)
- Spring HTTP Invoker and XML-RPC remoting — these are Gen-1/Gen-2 inter-service communication mechanisms absent from Gen-3 REST/event-driven architectures
- XStream serialisation for inter-service invocations
- JMS-based RPC with temporary reply queues — a Gen-2 SOA pattern

## Business Domain
Cross-cutting infrastructure — serves the prepaid card platform (card issuance, account management, disbursements). Consumed across the Gen-2 service fleet regardless of specific business sub-domain.

## Role in Ecosystem
| Role | Description |
|---|---|
| Shared library | Provides AOP infrastructure (audit logging, statistics, MDC) consumed by services in the Gen-2 fleet |
| Communication plumbing | HTTP Invoker and JMS Invoker allow Gen-2 services to call each other using serialised Java objects rather than REST |
| Operational tooling | Monitor endpoint gives operations teams visibility into running service health |
| Configuration management | Environment-switching configurer allows a single WAR to run in dev/qa/prod with different property sets |

## Dependencies
| Dependency | Version (declared in parent) | Notes |
|---|---|---|
| Spring Framework | Inherited from `prepaid-parent:6.0.13` | Specific version not visible without parent POM, but `jakarta-spring-remoting` and `jakarta.jms-api` indicate Spring 6.x / Jakarta EE migration |
| XStream | Inherited from parent | Critical security dependency — must be pinned to a non-vulnerable version |
| `request-context` | `2.1.0` (`com.citi.prepaid.module`) | Internal correlation ID library |
| Jakarta JMS API | Inherited | JMS 3.x (Jakarta namespace) |
| Lombok | Implied by `@Slf4j` annotations | |

## Integration Patterns
| Pattern | Component | Notes |
|---|---|---|
| AOP Interceptor | `AuditMethodInterceptor`, `VisitStatisticsMethodInterceptor` | Spring AOP proxy chain |
| Request/Reply JMS | `JmsInvokerClientInterceptor` + `JmsInvokerServiceExporter` | Synchronous over async transport using temporary queues |
| Publish/Subscribe JMS | `ConfigurablePubSubJmsInvokerProxyFactoryBean` | Topic-based event fan-out |
| One-Way JMS | `ConfigurableOneWayJmsInvokerProxyFactoryBean` | Fire-and-forget dispatch |
| HTTP Invoker | `CustomHttpInvokerReqeustExecutor` | Java object serialisation over HTTP — not REST |
| Spring XML Configuration | `SwitchedPropertyPlaceholderConfigurer` | Environment-conditional XML application context wiring |

## Strategic Status
| Dimension | Assessment |
|---|---|
| Current usage | Actively maintained (Java 21, Jakarta EE migration completed) |
| Strategic trajectory | Declining — Gen-3 strategy uses REST + Spring Boot + event streaming; these patterns are not needed there |
| Blocking migration? | Yes — services that depend on `JmsInvokerClientInterceptor` or `CustomHttpInvokerReqeustExecutor` for inter-service calls cannot simply be lifted to Gen-3 without replacing the communication mechanism |
| Recommended action | Maintain for Gen-2 fleet continuity; do not introduce new consumers; deprecate JMS invoker and HTTP invoker patterns in migration planning |

## Migration Blockers
1. **Java serialisation over JMS**: `JmsInvokerClientInterceptor` uses Java ObjectMessage serialisation. Any consumer must replace this with event streaming (Kafka/Azure Service Bus) or REST calls before Gen-3 migration.
2. **HTTP Invoker**: `CustomHttpInvokerReqeustExecutor` serialises Java objects over HTTP. Replacement is a standard REST HTTP client.
3. **XML application context wiring**: `SwitchedPropertyPlaceholderConfigurer` is Spring XML-specific. Replacement is Spring Boot profiles + Azure App Configuration / environment variables.
4. **XStream deserialisation**: All services consuming this library inherit the XStream `AnyTypePermission.ANY` risk. This must be addressed before any of those services can be PCI-cleared for Gen-3.
