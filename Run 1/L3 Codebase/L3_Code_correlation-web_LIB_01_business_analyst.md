# Business Analyst View — correlation-web_LIB

## 1. Business Purpose

`correlation-web` (artifact `com.ecount.opensource:correlation-web:2.0.1`) is an internal shared Java library that provides **HTTP-level correlation ID propagation** for Onbe's servlet-based web applications. Its sole responsibility is to intercept every inbound HTTP request, extract or generate a correlation ID, bind it to the current request thread, and clean it up after the request completes.

This is an **infrastructure / observability enablement** library, not a business-domain application. It has no UI, no persistence, and no end-user-facing functionality. Its value is felt indirectly: it makes distributed-tracing possible across Onbe's multi-service payment platform by ensuring every log line emitted during a request carries the same correlation ID that the client or upstream service injected.

---

## 2. Capabilities

| Capability | Description | Source |
|---|---|---|
| Correlation ID extraction | Reads the `X-Correlation-ID` (or equivalent) HTTP header from an inbound request | `CorrelationWebContext.java:15` |
| Correlation ID generation | If no header is present, generates a new correlation ID via `CorrelationIDContext.requiresNew()` | `CorrelationWebContext.java:18` |
| Thread-local binding | Stores the ID in `CorrelationIDContext` (from `correlation-core`) for downstream use within the same thread | `CorrelationWebContext.java:21` |
| Request lifecycle cleanup | Clears the thread-local state after the filter chain completes (in `finally` block) | `CorrelationHeaderFilter.java:27–29` |
| Servlet destroy cleanup | Clears state on servlet container shutdown | `CorrelationHeaderFilter.java:33–35` |

---

## 3. Business Entities

There are no business domain entities (e.g., accounts, cardholders, transactions) managed by this library. The only domain concept is:

- **CorrelationID** — an opaque string identifier that correlates a single request flow across multiple services and log sinks. Sourced from `com.ecount.opensource.CorrelationID` (defined in `correlation-core`, not this repo).

---

## 4. Business Rules

| # | Rule | Evidence |
|---|---|---|
| BR-1 | Every inbound HTTP request must be associated with a correlation ID before processing begins | `CorrelationHeaderFilter.doFilter` lines 19–23 |
| BR-2 | If the upstream caller supplies a correlation ID header, that value must be preserved (pass-through, not overwritten) | `CorrelationWebContext.init` lines 16–21 |
| BR-3 | If no header is present, a new ID must be generated | `CorrelationWebContext.init` line 18 |
| BR-4 | The correlation ID must be cleared from thread state after every request, regardless of success or failure | `CorrelationHeaderFilter.doFilter` finally block lines 27–29 |
| BR-5 | The library must NOT break the servlet filter chain — `chain.doFilter` is always called | `CorrelationHeaderFilter.doFilter` line 26 |

---

## 5. Business Flows

### Normal Request Flow
```
Client → HTTP Request (with or without X-Correlation-ID header)
  → CorrelationHeaderFilter.doFilter()
      → CorrelationWebContext.init(httpServletRequest)
          → Read header [LogContextConstants.CORRELATION_ID_HEADER]
          → [if present]  CorrelationIDContext.requiresNew(headerValue)
          → [if absent]   CorrelationIDContext.requiresNew()   [generates new ID]
      → chain.doFilter(request, response)   [business logic executes with ID in thread-local]
      → [finally] CorrelationWebContext.clear()
                        → CorrelationIDContext.clear()
```

### Non-HTTP Request (e.g., direct servlet call)
```
Non-HttpServletRequest → CorrelationHeaderFilter.doFilter()
  → instanceof check fails (line 21) → no init called
  → chain.doFilter(request, response)
  → [finally] CorrelationWebContext.clear()   [no-op if nothing was set]
```

---

## 6. Compliance Relevance

| Framework | Relevance |
|---|---|
| PCI DSS v4.0.1 | Log integrity and traceability (Req 10.2, 10.3): Correlation IDs support forensic linkage of log events across services that may touch the CDE. |
| SOC 1 / SOC 2 | Audit trail continuity: correlation IDs allow audit events to be linked end-to-end across microservices. |
| NIST CSF 2.0 | DE.CM (Detect / Continuous Monitoring): correlated logs improve anomaly detection and incident response. |
| FFIEC | IT audit and logging controls benefit from consistent correlation across API calls. |

This library contains no PAN, SAD, PII, or credentials. It does not store, process, or transmit regulated data directly.

---

## 7. Business Risks

| Risk | Severity | Detail |
|---|---|---|
| Silent skip on non-HTTP requests | Low | If a `ServletRequest` is not an `HttpServletRequest` (line 21 check), no correlation ID is set; downstream code that assumes an ID will find none. |
| Misused `deployment_temp.yml` | Medium | The `deployment_temp.yml` workflow references `AccountManagementAPI` — a completely different application — suggesting the file was copied from another repo and never updated. This creates CI/CD confusion risk. |
| No test suite | Medium | There are zero unit or integration tests in this repository (`-Dmaven.test.skip` used in CI build, no `src/test` directory). Regressions in core behaviour cannot be caught automatically. |
| Single commit history | Low | The repository appears to have been bootstrapped in one merge (PR #17); full commit history for prior versions may not be present in this shallow clone. |
| Stale `deployment_temp.yml` | Medium | The file name contains `_temp`, implying it was meant to be replaced; it is still present and references an unrelated application. |
