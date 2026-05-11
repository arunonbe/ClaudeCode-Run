# api-logging-lib — Solution Architect View

## Technical Architecture

The library contains **4 production classes** and **3 test classes** in a single Maven module. There are no sub-modules, no Spring context, no DI framework, no database layer, and no network I/O.

**Class structure:**

```
com.ecount.axis.soap.logging
├── SoapLoggingHandler          (extends BasicHandler — Axis handler entry point)
├── SoapLoggingSettings         (Java record — immutable settings value object)
├── SoapLoggingSettingsLoader   (final utility class — config loading + 60s cache)
└── SoapMessageScrubber         (final utility class — regex-based XML redaction)
```

**Design patterns present:**
- **Interceptor / Handler Chain**: `SoapLoggingHandler` plugs into the Axis `requestFlow`/`responseFlow` via WSDD.
- **Immutable Value Object**: `SoapLoggingSettings` is a Java `record` (Java 16+), with defensive copy on `sensitiveFields` in the compact constructor (`List.copyOf`, line 10).
- **Double-Checked Locking with Volatile**: `SoapLoggingSettingsLoader` uses `volatile SoapLoggingSettings cached` and `volatile long nextReloadAtMs` with a `synchronized(LOCK)` inner check for thread-safe hot-path caching (lines 39-67).
- **Fail-Safe / Fail-Closed**: Both handler and scrubber catch all `Throwable`s/`Exception`s and degrade gracefully rather than propagating errors into the SOAP pipeline.
- **Layered Property Override**: Explicit priority chain (JVM > env > file > classpath) implemented without a third-party config framework.

**Threading model**: `SoapLoggingSettingsLoader` is safe for concurrent use. The double-checked lock ensures settings are loaded at most once per 60-second window even under high concurrency.

## API Surface

The library exposes **no HTTP API, no REST endpoints, no SOAP service, and no RPC interface.** Its public API surface is the Java class API:

### Public API

| Class | Public Method / Constructor | Purpose |
|-------|---------------------------|---------|
| `SoapLoggingHandler` | `invoke(MessageContext)` | Axis handler invocation — logs request/response |
| `SoapLoggingHandler` | `onFault(MessageContext)` | Axis handler fault logging |
| `SoapLoggingSettings` | `record SoapLoggingSettings(boolean, List<String>)` | Constructor |
| `SoapLoggingSettings` | `enabled()` | Record accessor |
| `SoapLoggingSettings` | `sensitiveFields()` | Record accessor |
| `SoapLoggingSettings` | `static disabled()` | Factory for disabled settings |
| `SoapLoggingSettingsLoader` | `static getCurrent()` | Returns current (cached) settings |
| `SoapLoggingSettingsLoader` | `static normalizePath(String)` | Package-visible; tested directly |
| `SoapMessageScrubber` | `static scrub(String, List<String>)` | Redacts XML elements in-place |

**Integration point for consumers**: Register `SoapLoggingHandler` in Axis WSDD:
```xml
<handler name="SoapLogger" type="java:com.ecount.axis.soap.logging.SoapLoggingHandler"/>
```

## Security Posture

### Strengths
1. **Fail-closed scrubbing** (`SoapMessageScrubber`, lines 30-34): On any scrubbing exception, returns `[SOAP_PAYLOAD_REDACTED]` — the entire payload is suppressed rather than leaking raw data.
2. **Default-off** (`soap-logging-default.properties`, line 3: `soap.logging.enabled=false`): Logging must be explicitly enabled; accidental exposure of SOAP payloads at rest (in logs) requires an active misconfiguration.
3. **Defensive immutable settings**: `SoapLoggingSettings` record uses `List.copyOf` (line 10) — consumers cannot mutate the sensitive fields list post-construction.
4. **No hardcoded credentials**: `GITHUB_TOKEN` is injected via environment variable at CI time only.
5. **CodeQL SAST**: Weekly scheduled CodeQL scan (`codeql.yml`) provides continuous static analysis against known vulnerability patterns.
6. **Volatile + synchronized double-check**: Thread-safe caching prevents race conditions that could cause brief windows of wrong settings being applied.

### Weaknesses / Vulnerabilities
1. **Regex-based scrubbing — element name match only**: As detailed in `SoapMessageScrubber.scrub` (lines 26-29), the regex pattern only matches element text content between matching open/close tags. It does **not** handle:
   - XML attributes: `<card number="4111111111111111"/>` — not scrubbed.
   - Nested child elements: `<card><number>4111111111111111</number></card>` where `card` is the configured field — not scrubbed (content contains `<`).
   - Multi-line values: The regex does not use `DOTALL` — values spanning newlines will not match.
   - CDATA sections: `<cardNumber><![CDATA[4111111111111111]]></cardNumber>` — not scrubbed.
2. **No XML parsing — regex only**: Using regex on XML is inherently fragile. Malformed XML, unusual encoding, or whitespace in element names can defeat the pattern.
3. **Tests skipped in CI publish workflow**: `-Dmaven.test.skip` in `github-package-publish.yml` line 42 means a regression in scrubbing logic could be published without the test gate catching it.
4. **Axis 1.4 EOL dependency**: CVEs in `jakarta-axis` 1.4 (e.g., known deserialization vulnerabilities in Axis 1.x) cannot be remediated upstream. Consuming services inherit this CVE surface.
5. **`normalizePath` accepts any filesystem path**: There is no allowlist or sandboxing of the config file path — an attacker with JVM property injection capability could point `soap.logging.config.file` to an arbitrary filesystem path. However, only `.properties` format files are read, limiting exploitability.
6. **INFO log contains full scrubbed SOAP XML**: Large SOAP payloads (bulk card loads, etc.) will produce large log entries. No payload size limiting or truncation is implemented.

## Technical Debt

| Item | Severity | Evidence |
|------|----------|---------|
| Apache Axis 1.4 EOL dependency | High | `pom.xml` lines 25-39; Axis 1.x unmaintained |
| `com.ecount` package namespace (legacy brand) | Low | All source files — should be `com.onbe` |
| Regex-based XML scrubbing instead of DOM/StAX parsing | Medium | `SoapMessageScrubber.java` lines 26-29 — fragile against XML variants |
| No XML attribute scrubbing | Medium | `SoapMessageScrubber.scrub` — attributes completely unhandled |
| No CDATA section scrubbing | Medium | `SoapMessageScrubber.scrub` — CDATA values not matched |
| Tests skipped in CI publish pipeline | High | `github-package-publish.yml` line 42: `-Dmaven.test.skip` |
| Static version `1.0.0` with no SNAPSHOT/semver automation | Low | `pom.xml` line 9 |
| No payload size limiting in logs | Low | `SoapLoggingHandler.logMessage` — no truncation |
| No structured logging (JSON) | Low | Log message is plain string with embedded XML |
| No OpenTelemetry/distributed tracing span propagation | Low | No trace context injection — logging only |
| `commons-discovery:0.2` test dependency | Low | `pom.xml` line 48 — very old artifact, test scope only |

## Gen-3 Migration Requirements

To migrate SOAP services that consume this library to a Gen-3 (cloud-native, REST/gRPC) architecture, the following must be addressed:

1. **Replace Axis handler chain with modern interceptor**: The equivalent in Gen-3 would be a servlet `Filter`, Spring `HandlerInterceptor`, gRPC `ServerInterceptor`, or an OpenTelemetry span processor — depending on the target protocol.
2. **Replace regex scrubbing with structured masking**: Implement a JSON/Protobuf field masking library (e.g., using Jackson `@JsonFilter`, OpenTelemetry attribute masking, or a custom serialiser). Regex on XML is not applicable to REST/JSON or gRPC/Protobuf payloads.
3. **Adopt OpenTelemetry for distributed tracing**: Replace the current INFO-log-per-request approach with OTel spans that carry `service.name`, `http.method`, `http.url`, etc., and attach scrubbed request/response body as span attributes or events.
4. **Implement PAN masking at the field level with BIN preservation**: Gen-3 services should use format-preserving masking (first 6 / last 4) rather than full `[REDACTED]` replacement to retain operational context.
5. **Replace JVM property / environment variable config with a config server**: Kubernetes ConfigMap/Secrets, AWS Parameter Store, or a dedicated config service replaces the current properties file model.
6. **Rename package from `com.ecount` to `com.onbe`**: Align with current brand and namespace conventions.
7. **Remove Axis 1.4 dependencies entirely**: The migration of consuming services away from Axis is a prerequisite — this library becomes obsolete when those services are migrated.

## Code-Level Risks

1. **`SoapLoggingHandler.logMessage` — `Message.getSOAPPartAsString()` is potentially expensive**: Serialising the SOAP part to a string for every request/response adds latency to every SOAP call when logging is enabled. No asynchronous or buffered logging is implemented.

2. **`SoapLoggingSettingsLoader.load()` — outer try/catch swallows all `Throwable`** (lines 93-95): If the classpath resource `soap-logging-default.properties` is missing from the JAR, the loader silently returns disabled settings with no indication. Observed at `loadFromClasspath` (lines 139-148) which also catches all `Throwable`.

3. **`SoapLoggingSettingsLoader.getCurrent()` — outer try/catch swallows all `Throwable`** (lines 63-66): Any unexpected error during settings load resets the cache to disabled and reschedules reload in 60 seconds. This is safe but silent — no operator alert.

4. **`SoapMessageScrubber.scrub` — `Pattern.quote(field.trim())` called on every request** (line 25): For each SOAP message, a new `Pattern` is compiled per sensitive field. Under high load with a large sensitive fields list, this creates unnecessary object churn. Pre-compiling patterns during settings load would be more efficient.

5. **`SoapLoggingHandler.onFault` catches `Throwable`** (line 43) vs `invoke` catches `Exception` (line 31): Inconsistency — `onFault` is marginally safer but the asymmetry is a code smell.

6. **Test uses reflection to reset static `cached` and `nextReloadAtMs` fields** (`SoapLoggingHandlerTest` lines 45-53, `SoapLoggingSettingsLoaderTest` lines 154-162): This is necessary due to the static cache design, but it means tests are sensitive to field name changes and the static caching design is not easily testable without reflection hacks.

7. **`SoapLoggingSettingsLoader.normalizePath` is package-private** (no access modifier, line 171): It is directly tested in `SoapLoggingSettingsLoaderTest` — adequate coverage, but the package-private visibility exposes an implementation detail.
