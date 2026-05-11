# Data Architect View — correlation-web_LIB

## 1. Data Stores

This library has **no data stores of its own**. There is no database, no file system writes, no cache, and no message queue. The only "data" managed is ephemeral, in-process, thread-local state held for the duration of a single HTTP request.

---

## 2. Schema / Data Structures

### CorrelationID (from `correlation-core` dependency)
- Defined externally in `com.ecount.opensource.CorrelationID` (imported at `CorrelationWebContext.java:4`).
- The concrete schema is in the `correlation-core` library, but based on usage it is an object wrapping an opaque string value.

### Thread-local Binding (CorrelationIDContext)
- Managed by `com.ecount.opensource.CorrelationIDContext` (imported at `CorrelationWebContext.java:5`).
- Acts as a `ThreadLocal<CorrelationID>` container.
- Lifecycle: set at request start (`CorrelationWebContext.init`, line 14), cleared at request end (`CorrelationWebContext.clear`, line 24).

### HTTP Header
- Header name sourced from `com.ecount.opensource.LogContextConstants.CORRELATION_ID_HEADER` (imported at `CorrelationWebContext.java:6`).
- The constant value is defined in `correlation-core`; by convention it is likely `X-Correlation-ID` or `correlation-id`.
- Read-only from the perspective of this library: `request.getHeader(LogContextConstants.CORRELATION_ID_HEADER)` at line 15.
- String type; format is not validated in this library.

---

## 3. Sensitive Data Handling

| Data Element | Classification | Present in This Library? |
|---|---|---|
| PAN / card number | PCI SAD | No |
| CVV/CVC | PCI SAD | No |
| Account numbers | PII / PCI | No |
| Cardholder name | PCI PII | No |
| SSN / Government ID | PII | No |
| Correlation ID | Non-sensitive identifier | Yes — transient, thread-local only |

The correlation ID string value is logged at TRACE level in two places:
- `CorrelationWebContext.java:17` — logs when no header is present: `"Correlation ID was not found in the header of this request, generating a new one"`
- `CorrelationWebContext.java:20` — logs when header is present: `"Correlation ID found in the header of this request, using it"`

Neither log statement emits the actual ID value, only the presence/absence status, reducing log-injection risk.

---

## 4. Encryption

No encryption is applied or required within this library. The correlation ID is not secret. Transport-layer encryption (TLS) is the responsibility of the consuming application's servlet container / load balancer. There is no key management concern here.

---

## 5. Data Flow

```
[Inbound HTTP Request]
        |
        | Header: <CORRELATION_ID_HEADER> = "<uuid or generated>"
        v
CorrelationHeaderFilter.doFilter()        [CorrelationHeaderFilter.java:19]
        |
        v
CorrelationWebContext.init(HttpServletRequest)  [CorrelationWebContext.java:14]
        |
        |-- request.getHeader(...)         [reads header string, line 15]
        |
        |-- [null]  --> CorrelationIDContext.requiresNew()           [line 18]
        |               generates new CorrelationID, stores in ThreadLocal
        |
        |-- [value] --> CorrelationIDContext.requiresNew(headerValue) [line 21]
                        wraps supplied value, stores in ThreadLocal
        |
        v
[Filter chain / downstream business logic]
        |  (reads CorrelationID from ThreadLocal via CorrelationIDContext)
        |
        v
CorrelationWebContext.clear()              [line 24]
        |
        v
CorrelationIDContext.clear()               [removes from ThreadLocal]
        |
        v
[Thread returned to pool — no residual state]
```

Data never leaves the JVM process. No outbound writes. No persistence.

---

## 6. Data Quality

| Quality Dimension | Assessment |
|---|---|
| Completeness | Guaranteed: every HTTP request will have a correlation ID after `init()` — either from the header or freshly generated. |
| Validity | Not validated: the library does not check whether the header value is a valid UUID or meets any format constraints. Any non-null string is accepted as-is (`CorrelationWebContext.java:21`). |
| Uniqueness | Depends on `correlation-core`'s `requiresNew()` implementation for generated IDs. Header-supplied values are trusted without uniqueness checks. |
| Consistency | Thread-local isolation ensures no cross-request contamination provided `clear()` is always called (guaranteed by the `finally` block at `CorrelationHeaderFilter.java:27–29`). |
| Timeliness | Synchronous, inline with every request — no latency concern. |

---

## 7. Data Compliance

| Regulation | Assessment |
|---|---|
| PCI DSS v4.0.1 Req 10 | Correlation IDs are audit-support data. The library correctly scopes them to a single request and clears them, preventing inadvertent cross-request data leakage in thread pools. |
| GDPR / CCPA | The correlation ID contains no PII. No personal data is processed by this library. |
| GLBA | No financial data in scope. |
| NACHA / Reg E | No payment data in scope. |

No data retention, deletion, or consent obligations apply because no personal or regulated data is processed.
