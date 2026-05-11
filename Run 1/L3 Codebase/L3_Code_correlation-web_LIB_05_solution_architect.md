# Solution Architect View — correlation-web_LIB

## 1. Architecture Summary

`correlation-web` is a **micro-library** (2 source files, ~63 lines of production code) that solves one narrow problem: bridging inbound HTTP headers to a thread-local correlation ID context for Onbe's Jakarta Servlet-based services. It is architecturally correct for its purpose — small, cohesive, and dependency-light.

```
┌─────────────────────────────────────────────────────────────┐
│  Consuming Web Application (e.g. AccountManagementAPI)      │
│                                                             │
│  web.xml / @WebFilter                                       │
│    └─► CorrelationHeaderFilter                              │
│            ├─► CorrelationWebContext.init()                 │
│            │       └─► CorrelationIDContext [ThreadLocal]   │
│            ├─► chain.doFilter()  [business logic runs]      │
│            └─► CorrelationWebContext.clear()                │
└─────────────────────────────────────────────────────────────┘
         ▲
  HTTP request arrives with/without X-Correlation-ID header
```

---

## 2. API Surface

The public API of this library is two classes with the following contracts:

### `CorrelationHeaderFilter` (`CorrelationHeaderFilter.java`)

Implements `jakarta.servlet.Filter`. Intended to be registered as a servlet filter in consuming applications.

| Method | Signature | Line | Behaviour |
|---|---|---|---|
| `init` | `void init(FilterConfig filterConfig)` | 15–17 | No-op; no initialisation needed. |
| `doFilter` | `void doFilter(ServletRequest, ServletResponse, FilterChain) throws IOException, ServletException` | 19–30 | Core logic: init correlation ID if HTTP, delegate chain, clear on exit. |
| `destroy` | `void destroy()` | 32–35 | Calls `CorrelationWebContext.clear()` on container shutdown. |

### `CorrelationWebContext` (`CorrelationWebContext.java`)

Stateless utility class with two static methods.

| Method | Signature | Line | Behaviour |
|---|---|---|---|
| `init` | `static CorrelationID init(HttpServletRequest request)` | 14–22 | Reads header; creates/propagates `CorrelationID` via `CorrelationIDContext`. Returns the active `CorrelationID`. |
| `clear` | `static void clear()` | 24–26 | Delegates to `CorrelationIDContext.clear()`, removing ThreadLocal entry. |

**No interfaces, no abstract classes, no inheritance hierarchy** beyond the `Filter` interface contract. The design is intentionally flat.

---

## 3. Security Assessment

### Positive Controls
- **No secrets in code**: No credentials, tokens, or keys in source files.
- **No external I/O**: Library makes no network calls, no file writes.
- **Thread-safety via cleanup**: The `finally` block at `CorrelationHeaderFilter.java:27–29` ensures thread-local state is always cleared, preventing correlation ID leakage between requests on shared thread pools.
- **No header reflection / injection**: The library does not write the correlation ID back to the response headers, avoiding header-injection vectors.
- **CodeQL scanning**: Weekly automated scanning via `codeql.yml`.

### Potential Security Concerns

| Concern | Severity | Detail | Line Reference |
|---|---|---|---|
| Unvalidated header value | Low | `request.getHeader(...)` result is passed directly to `CorrelationIDContext.requiresNew(headerValue)` with no length, format, or character-set validation. A malicious caller could inject a very long string or special characters that surface in logs. | `CorrelationWebContext.java:21` |
| Log injection via TRACE logs | Very Low | Though the trace messages do not include the header value itself (lines 17, 20 only log presence/absence), consuming code that logs the returned `CorrelationID` object could expose the raw header value. | `CorrelationWebContext.java:17,20` |
| Non-HTTP requests bypass init | Low | If a `ServletRequest` is not `HttpServletRequest`, no correlation ID is set; downstream code may NPE or silently omit IDs from logs. | `CorrelationHeaderFilter.java:21` |
| `deployment_temp.yml` APIM publish | Medium | The stale workflow has `PUBLISH_TO_APIM: true` and `EXTERNAL_APIM: true`; if it runs successfully it could publish an incorrect API definition to the external API gateway. | `deployment_temp.yml:29–30` |

---

## 4. Technical Debt

| Item | Category | Severity | Detail |
|---|---|---|---|
| `deployment_temp.yml` misattribution | Operational debt | High | Entire file references a different application (`AccountManagementAPI`). Should be deleted from this repository. |
| No unit tests | Quality debt | Medium | `CorrelationHeaderFilter.doFilter` and `CorrelationWebContext.init/clear` have zero test coverage. Adding tests (e.g., with `jakarta.servlet` mocks) is straightforward. |
| `@Slf4j` / Lombok not declared in `pom.xml` | Dependency debt | Low-Medium | Lombok is an implicit transitive dependency from `prepaid-parent`. This should be an explicit compile-time annotation-processor dependency. |
| Static-only `CorrelationWebContext` | Design debt | Low | The class cannot be easily mocked or overridden in tests; constructor is implicitly public. Making it a proper instantiable class or adding an interface would improve testability. |
| Header value not validated | Hardening debt | Low | No format enforcement on the inbound correlation ID; consider adding a max-length check and basic character validation. |
| README omits registration instructions | Documentation debt | Low | No guidance on how to register `CorrelationHeaderFilter` in a `web.xml` or Spring `FilterRegistrationBean`. |
| No Javadoc | Documentation debt | Low | Neither class has any Javadoc comments on public methods. |
| `mvnw.cmd` / `mvnw` binary-adjacent files | Maintenance debt | Very Low | Maven Wrapper files are committed; the wrapper JAR (`.mvn/wrapper/maven-wrapper.jar`) is a binary in source control. Acceptable but worth tracking for supply-chain hygiene. |

---

## 5. Gen 3 Readiness Assessment

| Criterion | Status | Notes |
|---|---|---|
| Java 21 | Pass | `maven.compiler.source/target=21` (`pom.xml:21–22`) |
| Jakarta EE namespace | Pass | All imports use `jakarta.servlet.*` not `javax.servlet.*` |
| Spring Boot 3.x compatibility | Pass (inferred) | Jakarta Servlet API (`provided` scope) is compatible with Spring Boot 3.x embedded containers. |
| Reactive / non-blocking | Not applicable | Synchronous servlet filter; reactive coroutine-based frameworks would need a different integration module. |
| Cloud-native / containerised | Not applicable | Library; no runtime footprint. |
| Observability (OTel) | Partial | Correlation IDs enable trace linkage but the library does not inject IDs into OpenTelemetry `Span` attributes or MDC context directly. Consuming services must wire the `CorrelationIDContext` value into their MDC/OTel spans manually. |
| Zero-downtime deploy | Not applicable | Stateless library; no deploy concern. |
| Test automation | Fail | No tests; CI skips test compilation. |

---

## 6. Code-Level Risks

| File | Line(s) | Risk | Recommendation |
|---|---|---|---|
| `CorrelationHeaderFilter.java` | 21 | `instanceof` check without `else` — non-HTTP requests silently proceed with no ID | Add an `else` branch that either generates a default ID or logs a warning. |
| `CorrelationHeaderFilter.java` | 33–35 | `destroy()` calls `clear()` which clears a thread-local on the container thread; if the container thread is the same one that served requests this may be superfluous or incorrect depending on container implementation | Verify with container lifecycle documentation; likely harmless but worth confirming. |
| `CorrelationWebContext.java` | 14 | Return type `CorrelationID` is unused by the calling filter; the filter ignores the return value (`CorrelationHeaderFilter.java:23`) | Either make the method `void` or document that callers can capture the returned ID for further use. |
| `CorrelationWebContext.java` | 21 | `headerValue` passed to `requiresNew()` with no trimming, length cap, or sanitisation | Add `headerValue.trim()` at minimum; consider enforcing a max length (e.g., 128 characters). |
| `.github/workflows/deployment_temp.yml` | 25–37 | Entire configuration references `AccountManagementAPI`; will trigger on `main` push | Delete this file from the repository. |
