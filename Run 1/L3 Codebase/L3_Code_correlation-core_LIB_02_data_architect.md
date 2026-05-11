# correlation-core_LIB — Data Architect View

## Data Stores

This library has **no persistent data stores**. It operates entirely in-process using:

- **SLF4J MDC (Mapped Diagnostic Context)** — a thread-local `Map<String, String>` maintained by the SLF4J / Log4j2 runtime. The MDC is process-local and non-persistent; it lives only for the duration of a thread's execution.

No databases, message queues, caches, files, or external storage are read from or written to by this library directly.

## Schema & Tables

No database schema exists. The only "schema" is the MDC key space:

| MDC Key | Java Constant | Location | Value Type | Example Value |
|---|---|---|---|---|
| `correlationId` | `LogContextConstants.CORRELATION_ID` | SLF4J MDC (thread-local) | UUID string | `550e8400-e29b-41d4-a716-446655440000` |

Two additional constants define the wire-transport key names but are not used by this library internally to write data — they are provided for consumers:

| Transport | Header Name | Java Constant |
|---|---|---|
| HTTP | `CORRELATION-ID` | `LogContextConstants.CORRELATION_ID_HEADER` |
| JMS | `APP_CorrelationID` | `LogContextConstants.JMS_CORRELATION_ID_HEADER` |

## Sensitive Data Handling

- The library stores **only a UUID string** in MDC. No cardholder data (PAN, CVV, PIN), no PII (name, SSN, DOB, account number), and no credentials are ever placed in the MDC by this library.
- **Risk:** Consumer services that call `requiresNew(String id)` with a caller-supplied string (e.g., parsed directly from an HTTP header) could theoretically pass a value that encodes sensitive data. The library imposes no validation or masking — this is a consumer responsibility.
- The `CorrelationID` value object is `Serializable`. If an application serialises it (e.g., into a JMS `ObjectMessage`), the UUID string value would be included. This is low risk as UUIDs are not sensitive.

## Encryption & Protection

- **No encryption is applied** to the correlation ID at rest or in transit by this library. Correlation IDs are non-sensitive by design (they are opaque random UUIDs).
- Log output containing `correlationId` is governed by the consuming service's logging configuration (e.g., `log4j2-test.xml` uses `%X{correlationId}` in the pattern layout). Encryption or masking of log files is the responsibility of the platform logging infrastructure, not this library.
- The `GITHUB_TOKEN` used by `.mvn/wrapper/settings.xml` to authenticate against `https://maven.pkg.github.com/onbe/onbe_maven_releases` is injected via environment variable at build time and is never persisted in source.

## Data Flow

```
[Inbound HTTP Header: CORRELATION-ID]
         │
         ▼
CorrelationIDContext.requiresNew(String id)
         │
         ▼
SLF4J MDC.put("correlationId", id)        ← thread-local write
         │
         ├──► log4j2 PatternLayout: %X{correlationId}  → log sink (stdout / file / aggregator)
         │
         └──► CorrelationCallable / CorrelationRunnable
                  │
                  ▼
              MDC.put("correlationId", id)   ← propagated into worker thread
                  │
                  ▼
              doCall() / doRun() executes    ← worker thread log lines carry same ID
                  │
                  ▼
              MDC.remove("correlationId")    ← thread-local cleanup

[JMS outbound: APP_CorrelationID header set by consumer, not this lib]
```

Data leaves the library boundary only through:
1. The SLF4J MDC (consumed by the logging framework to enrich log records).
2. The `CorrelationID` return value passed back to the caller.

## Data Quality & Retention

- **Uniqueness:** IDs generated internally use `UUID.randomUUID()` (Java's `SecureRandom`-seeded UUID v4). Collision probability is negligible for operational volumes.
- **Format consistency:** No format constraint is enforced on caller-supplied IDs. Consumer services must enforce UUID format if required by downstream audit tools.
- **Retention:** The library itself retains no data. Log retention policy (e.g., 90-day minimum for PCI DSS Req 10.5) is the responsibility of the platform log aggregation layer.
- **Thread cleanup:** MDC entries are removed after each task completes (`CorrelationIDContext.clear()` called in `CorrelationCallable.call()` and `CorrelationRunnable.run()`). However, exception paths in `CorrelationCallable.call()` (lines 31–33 of `CorrelationCallable.java`) lack a `finally` block, meaning an unchecked exception leaves the MDC entry populated — a data quality defect.

## Compliance Gaps

| Gap | Detail | Applicable Control |
|---|---|---|
| No MDC cleanup on exception | `CorrelationCallable.call()` does not use `try/finally`; unchecked exceptions leave stale ID in MDC | PCI DSS Req 10 — log accuracy; SOC 2 logging controls |
| No ID format validation | `CorrelationIDContext.requiresNew(String id)` accepts any string; log injection possible if header value is attacker-controlled | NIST CSF — Protect; OWASP Log Injection |
| invokeAll / invokeAny not correlated | `CorrelationExecutorServiceDecorator` passes these through un-decorated, breaking correlation for bulk task submissions | PCI DSS Req 10 — completeness of audit trail |
| No log sanitisation | Log statements in `CorrelationExecutorServiceDecorator` (lines 59, 70, 112) use string concatenation with MDC-derived values, not parameterised logging — minor log injection vector | OWASP Logging Cheat Sheet |
