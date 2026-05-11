# cicd-testlib_LIB — Data Architect View

## Data Stores

This library does **not** own or connect to any database, file store, message broker, or cache. It has no persistence layer. All state is held exclusively in-memory via the **SLF4J Mapped Diagnostic Context (MDC)**, which is a `ThreadLocal<Map<String,String>>` managed by the SLF4J runtime.

The single logical "data store" is:

| Store | Type | Scope | Key | Value |
|---|---|---|---|---|
| SLF4J MDC | ThreadLocal Map | JVM thread lifetime | `"correlationId"` (defined in `LogContextConstants.CORRELATION_ID`) | UUID string |

## Schema & Tables

No relational or document schemas exist. The only structured data element is:

**`CorrelationID`** (`src/main/java/com/ecount/opensource/CorrelationID.java`)
- Internal field: `private String value` — a UUID string (e.g., `"550e8400-e29b-41d4-a716-446655440000"`)
- Implements `java.io.Serializable` (serialVersionUID not declared — risk of serialisation incompatibility across versions)
- `equals()` and `hashCode()` delegate to `String.equals()` / `String.hashCode()` on `value`

**`LogContextConstants`** (`src/main/java/com/ecount/opensource/LogContextConstants.java`) defines three string constants that function as schema keys across transport layers:

| Constant | Value | Transport |
|---|---|---|
| `CORRELATION_ID` | `"correlationId"` | SLF4J MDC / log output |
| `CORRELATION_ID_HEADER` | `"CORRELATION-ID"` | HTTP headers |
| `JMS_CORRELATION_ID_HEADER` | `"APP_CorrelationID"` | JMS message headers |

## Sensitive Data Handling

The library itself does not handle sensitive data. Correlation IDs are synthetic UUIDs with no mapping to cardholder data, PII, or financial account information.

**However, a critical finding exists in `.mvn/wrapper/settings.xml`:**

```xml
<server>
    <id>nexus-qa</id>
    <username>deployment</username>
    <password>dwil15?</password>   <!-- line 38 — PLAINTEXT CREDENTIAL -->
</server>
<server>
    <id>ecount.release</id>
    <username>deployment</username>
    <password>d3v0nly</password>   <!-- line 43 — PLAINTEXT CREDENTIAL -->
</server>
<server>
    <id>ecount.snapshot</id>
    <username>deployment</username>
    <password>d3v0nly</password>   <!-- line 49 — PLAINTEXT CREDENTIAL -->
</server>
```

These are Maven repository deployment credentials stored in plaintext inside a file that is committed to source control. This constitutes a secret exposure risk relevant to PCI DSS Requirement 8 (strong authentication), NIST CSF 2.0 PR.AA-02, and internal secrets management policy. The `GITHUB_TOKEN` reference on line 54 is properly externalised via environment variable, which is the correct pattern.

A second infrastructure credential is also present:
```xml
<server>
    <id>wirecard-mavenproxy-repository</id>
    <username>acmng</username>
    <password>acmng</password>   <!-- line 33 — PLAINTEXT CREDENTIAL, username=password -->
</server>
```

The Nexus repository URL `https://d-na-stk01.nam.wirecard.sys:8081/nexus/...` references the Wirecard internal network, indicating this settings file is a legacy artefact from before the Wirecard/ecount/Northlane → Onbe transition.

## Encryption & Protection

- No data encryption is implemented or required by this library (no persistence, no PAN, no PII).
- Correlation ID values are transmitted in plaintext HTTP headers (`CORRELATION-ID`) and JMS headers (`APP_CorrelationID`). This is standard practice for non-sensitive tracing identifiers.
- The `CorrelationID` class is `Serializable`, meaning it can be transmitted via Java object serialisation over JMS. Consuming applications should ensure transport-layer TLS is in place on JMS brokers.

## Data Flow

```
[Inbound HTTP/JMS boundary]
        |
        | Header value read by consuming service (not this library)
        v
CorrelationIDContext.requiresNew(id)
        |
        v
MDC.put("correlationId", id)     ← ThreadLocal write
        |
        v
[Thread executes business logic]
        |
        | CorrelationExecutorServiceDecorator.submit()
        |   → CorrelationCallable captures ID at construction
        |   → Child thread: MDC.put("correlationId", capturedId)
        |   → doCall() executes
        |   → MDC.remove("correlationId")
        v
[SLF4J/Log4j2 appender reads MDC at each log call]
        |
        v
Log output: correlationId='<uuid>' in every log line
        |
        v
[Log aggregation system (Splunk/ELK/etc.) — not in this repo]
```

## Data Quality & Retention

- **Uniqueness**: UUIDs are generated via `java.util.UUID.randomUUID()` (cryptographically random, version 4). Collision probability is negligible for operational volumes.
- **Format consistency**: No validation enforces UUID format when an external ID is injected via `requiresNew(String id)`. A non-UUID string (e.g., an empty string or a caller-supplied transaction ID) will be accepted silently.
- **Retention**: Correlation IDs exist only for the duration of the thread's task execution. They have no persistent retention — log files are the sole persistent record, and log retention is governed by log aggregation infrastructure outside this library.
- **Null safety**: `CorrelationIDContext.requires()` handles a null MDC value by generating a new UUID (line 52–55). `requiresNew(CorrelationID id)` does not null-check the `id` parameter; passing `null` would cause a `NullPointerException` at `MDC.put(key, id.toString())`.

## Compliance Gaps

| Gap | Standard | Detail |
|---|---|---|
| Plaintext credentials in SCM | PCI DSS Req 8.2.1, NIST CSF PR.AA-02 | `.mvn/wrapper/settings.xml` contains three sets of deployment credentials in plaintext |
| No `serialVersionUID` on `CorrelationID` | Java best practice | Serialisation across different JVM/classloader versions may fail unexpectedly |
| `requiresNew(CorrelationID)` missing null guard | Defensive coding | A null argument produces an NPE, not a controlled exception |
| `invokeAll` / `invokeAny` pass-through | Logging completeness | Bulk callable submissions via `CorrelationExecutorServiceDecorator` do not propagate the correlation ID, creating log gaps for batch operations |
| No input validation on `requiresNew(String)` | Data quality | Empty strings or malformed values are accepted, potentially producing unreadable log entries |
