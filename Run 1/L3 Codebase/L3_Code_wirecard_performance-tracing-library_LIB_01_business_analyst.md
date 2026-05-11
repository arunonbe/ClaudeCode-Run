# Business Analyst — wirecard_performance-tracing-library_LIB

## Business Purpose
A shared Java library that provides method-level execution-time tracing for all services in the Wirecard/Northlane Gen-2 platform. It is an AOP-based cross-cutting observability capability distributed as a Maven/Gradle dependency and consumed by any Spring Boot service that needs performance monitoring.

## Capabilities
- Intercepts all method invocations in configured Java packages using Spring AOP
- Logs execution time for every intercepted method at DEBUG level
- Logs methods exceeding a configurable threshold at WARN level (default 1000 ms)
- Can be enabled or disabled globally via a configuration property
- Supports inclusion list (`monitoredPackages`) and exclusion list (`skippedPackages`)
- Enabled by a single `@EnablePerformanceTracing` annotation on the consumer application context

## Key Entities / Concepts
| Concept | Description |
|---|---|
| `@EnablePerformanceTracing` | Import annotation to activate the library |
| `PerformanceTracingProperties` | Config holder (`performance.tracing.*` prefix) |
| `PerformanceTracingInterceptor` | AOP MethodInterceptor that measures execution time |
| `PerformanceTracingConfiguration` | Spring `@Configuration` that wires the AOP advisor |
| `PointcutExpressionProvider` | Builds AspectJ pointcut expression from properties |
| `Trace` | Value object logged as JSON: `className`, `methodName`, `executionTime` |

## Business Rules
1. Default monitored package: `com.wirecard` — all Wirecard services are traced by default
2. Default threshold: 1000 ms — methods over 1 second are logged at WARN
3. Library must not depend on any other internal project (enforced by Gradle configuration check)
4. Tracing is purely observational — no side effects on the intercepted methods
5. Version published to Nexus and AWS S3; consumed as a dependency by other services

## Business Flows
1. **Library usage**: Consumer service adds `@EnablePerformanceTracing` → library wires AOP advisor → all method calls in configured packages are timed → execution times logged
2. **Alerting**: Long-running methods (> threshold) emit WARN log → Logstash/ELK picks up → operations team can set alerts on performance degradation

## Compliance Relevance
- Supports PCI DSS Requirement 10.x (logging and monitoring) by providing detailed method-execution logging
- WARN-level logs for slow operations support anomaly detection and performance SLA monitoring
- No sensitive data is logged — only class name, method name, and execution time in milliseconds

## Risks
1. If `monitoredPackages` is misconfigured to include packages handling sensitive data (e.g., encryption utilities), parameter values are NOT logged (only timing), so PII/PAN leakage risk is low but exists if a future version adds parameter logging
2. Library is very small and focused — low business risk
3. Spring Boot BOM version (2.0.7) is EOL — dependency consumers inherit this risk
