# Solution Architect Report — onbe-spring-boot

## API Surface

This is a library with no HTTP API surface of its own. Its public API is the set of Spring auto-configuration classes, Kotlin extension functions, and Java utility classes it exposes to consuming services.

**Key public API components:**

| Component | Package | Purpose |
|---|---|---|
| `DaprSecretsConfiguration` | `com.onbe.dapr` | Auto-configure Dapr secrets loading into Spring env |
| `OnbeEnvironmentPostProcessor` | `com.onbe.spring.context` | Load bootstrap YAML defaults at highest precedence |
| `WebAutoConfiguration` | `com.onbe.spring.autoconfigure.web` | Configure standard RestClient with retry/timeouts |
| `RestClientConfiguration` | `com.onbe.web` | Configuration properties for REST client |
| `RetryRateLimitRequestInterceptor` | `com.onbe.web` | Rate-limit retry interceptor for RestClient |
| `ConnectionFactoryFactory` | `com.onbe.r2dbc` | Factory for R2DBC reactive connection pools |
| `TextUtils` (Kotlin) | `com.onbe.text` | Masking, Base64, password generation |
| `OnbeAutoConfiguration` | `com.onbe.spring.autoconfigure` | Root auto-configuration entry point |

## Security Posture

### Strengths
- Dapr secret store integration removes hardcoded credentials from YAML/properties files.
- `TextUtils.mask()` is integrated into debug-level secret logging in `DaprSecretsConfiguration`, preventing accidental secret exposure.
- CodeQL static analysis is enabled in CI.
- CycloneDX SBOM is generated at build time for dependency vulnerability tracking.
- Actuator shutdown endpoint is explicitly disabled.
- Management endpoints in QA/prod are restricted to a whitelist (`health`, `metrics`, `info`, `prometheus`, `appconfiguration-refresh`).
- `maven-enforcer-plugin` enforces minimum Java 21 and Maven 3.9+, preventing builds on vulnerable runtimes.

### Weaknesses / Findings

**Finding 1 — Thread.sleep() in Reactive-Compatible Interceptor**
File: `onbe-spring-boot-autoconfigure/src/main/kotlin/com/onbe/web/RetryRateLimitRequestInterceptor.kt`, line 53
`Thread.sleep(retryAfter.toMillis())` is called inside a `ClientHttpRequestInterceptor`. When this interceptor is used on a reactive WebFlux thread (not a virtual thread), this is a blocking call on a non-blocking thread, which can cause reactor thread starvation. While Java 21 virtual threads mitigate this in MVC contexts, any Webflux service using this interceptor directly (not via the Onbe autoconfiguration's JdkClientHttpRequestFactory) is at risk. Mitigation: document that this interceptor must only be used with virtual-thread-backed executors.

**Finding 2 — Secrets Map Not Zeroed After Use**
File: `onbe-spring-boot-autoconfigure/src/main/kotlin/com/onbe/dapr/DaprSecretsConfiguration.kt`, lines 43–48
The `secrets: MutableMap<String, Any>` holding resolved Dapr secret values is inserted into the Spring environment but is never explicitly cleared from the local variable. In a PCI CDE JVM, secret values should be held in `char[]` and zeroed post-use where possible, rather than `String` references which are immutable and GC-dependent. This is a common JVM limitation but worth noting for PCI Requirement 8.

**Finding 3 — `OnbeEnvironmentPostProcessor` Uses `println` for Logging**
File: `onbe-spring-boot-autoconfigure/src/main/kotlin/com/onbe/spring/context/OnbeEnvironmentPostProcessor.kt`, lines 21, 27, 34, 47, 55
All diagnostic output uses raw `println()` rather than SLF4J, because `EnvironmentPostProcessor` runs before the logging system is initialized. While this is a known Spring Boot constraint, the output includes the literal phrase "Loading internal bootstrap properties from classpath:onbe-bootstrap-default.yaml" which goes to stdout and may appear in container logs that are not formatted for SIEM ingestion. This creates a mixed structured/unstructured log stream.

**Finding 4 — SNAPSHOT Parent in CI**
File: `pom.xml`, lines 8–11 and `.github/workflows/github-package-publish.yml`, line 9
The parent POM version is `0.0.22-SNAPSHOT` and the CI workflow delegates to `@feature/spring-boot-build-image` (a non-main branch). Both introduce non-reproducibility risk. A malicious or accidental update to the feature branch or the SNAPSHOT artifact could affect all downstream builds.

**Finding 5 — `randomPassword()` Uses `kotlin.random.Random` (Insecure RNG)**
File: `onbe-spring-boot-core/src/main/kotlin/com/onbe/text/TextUtils.kt`, line 22
The `randomPassword()` function uses Kotlin's default `Random`, which is a pseudo-random number generator (PRNG), not a cryptographically secure RNG. For password generation in a PCI context, `java.security.SecureRandom` should be used. If this function is used to generate service credentials or API tokens, this is a PCI DSS Requirement 6.2 / 8 concern.

## Technical Debt

- Module count (16 modules) creates significant build complexity. Starters pattern is appropriate but may be over-segmented for the current feature set.
- `kapt.use.k2=false` indicates the Kotlin compiler is not using K2 for annotation processing — a known transitional limitation with Kotlin 2.x that should be resolved as Kapt/KSP tooling matures.
- `kotlin.compiler.incremental=false` disables incremental Kotlin compilation, slowing CI builds — likely a stability workaround.
- The `spring-boot-thin-layout` artifact referenced in the Azure Functions profile is from the `org.springframework.boot.experimental` group ID, indicating it is a non-production Spring artifact.

## Recommendations

1. Replace `randomPassword()` PRNG with `SecureRandom` immediately.
2. Document `RetryRateLimitRequestInterceptor` as unsuitable for use on reactive schedulers without virtual thread backing.
3. Pin the CI workflow to `@main` instead of `@feature/spring-boot-build-image` for production library releases.
4. Evaluate moving from SNAPSHOT to a release version for the parent POM once the current development cycle stabilizes.
