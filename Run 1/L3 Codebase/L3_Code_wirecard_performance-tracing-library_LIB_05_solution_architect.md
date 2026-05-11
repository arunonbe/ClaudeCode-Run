# Solution Architect — wirecard_performance-tracing-library_LIB

## Technical Architecture
- **Framework**: Spring Boot 2.0.7 BOM, Java 8, Gradle
- **Core mechanism**: Spring AOP `AspectJExpressionPointcutAdvisor` with custom `MethodInterceptor`
- **Configuration**: `@ConfigurationProperties("performance.tracing")` bound properties
- **AOP expression**: Built dynamically by `PointcutExpressionProvider` from monitored/skipped package lists
- **Activation**: `@EnablePerformanceTracing` imports `PerformanceTracingConfiguration` which wires the `AspectJExpressionPointcutAdvisor` bean
- **Measurement**: Spring `StopWatch` — wall-clock time in milliseconds

## API Surface (Library API)
| Element | Type | Description |
|---|---|---|
| `@EnablePerformanceTracing` | Annotation | Add to Spring `@Configuration` class to activate |
| `performance.tracing.monitored-packages` | Property | CSV of packages to trace (default: `com.wirecard`) |
| `performance.tracing.skipped-packages` | Property | CSV of packages to exclude |
| `performance.tracing.long-running-method-threshold` | Property | WARN threshold in ms (default: 1000) |
| `performance.tracing.is-enabled` | Property | Global on/off switch (default: true) |
| `logger.level.com.wirecard.performancetracing` | Logging property | Set to DEBUG for per-method logs |

## Security Posture
- No security controls required — library has no API surface, no auth, no data store
- Does not log method parameters or return values — no PII/PAN leakage risk by design
- If a consumer misconfigures `monitoredPackages` very broadly (e.g., including Spring Security internals), performance impact is the only concern — no security data is logged
- No known CVEs specific to this library's own code
- Spring Boot BOM 2.0.7 — inherited CVE exposure if the consuming service uses EOL Spring Boot

## Technical Debt
1. `PerformanceTracingConfiguration.java` has the primary configuration logic commented out (lines 10-17) — replaced with direct bean construction in `@Bean` methods; creates a disconnect between the configuration class and the `@Autowired` constructor in `PerformanceTracingInterceptor`
2. Spring Boot BOM 2.0.7 — EOL; consumers inherit old BOM versions
3. `compile` Gradle dependency scope — deprecated; should be `implementation`
4. `jar.manifest` declares `'Specification-Title': 'ccpr-client'` — incorrect artifact title (copy/paste from another project)
5. HTTP Nexus URL in build.gradle — artifact fetch over plaintext HTTP
6. `lombok:1.18.4` — available since 2018; current versions add more annotation processing improvements

## Gen-3 Migration Requirements
1. Replace with OpenTelemetry Java auto-instrumentation agent or Micrometer Tracing
2. If a custom library is still desired: upgrade to Spring Boot 3.x, replace `compile` scope with `implementation`, fix JAR manifest artifact title
3. Remove the commented-out configuration block or restore it to a working state
4. Publish to cloud-native artifact registry (GitHub Packages, AWS CodeArtifact, Azure Artifacts) instead of internal Nexus

## Code-Level Risks
| File | Line | Risk |
|---|---|---|
| `PerformanceTracingConfiguration.java` | Lines 10-17 | Configuration logic commented out; creates dead code and confusing coupling with `PerformanceTracingInterceptor`'s `@Autowired` constructor |
| `build.gradle` | Line 17-20 | `http://` Nexus URL — no TLS for artifact fetch |
| `build.gradle` | Line 33 | `jar.manifest` title set to `ccpr-client` — incorrect metadata |
| `PerformanceTracingInterceptor.java` | Line 22 | `if (properties.getIsEnabled())` — non-idiomatic Boolean getter (`isEnabled` generates `isIsEnabled()` with Lombok `@Data`); potential NullPointerException if properties not injected |
