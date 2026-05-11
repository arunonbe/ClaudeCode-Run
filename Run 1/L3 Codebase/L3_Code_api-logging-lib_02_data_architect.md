# api-logging-lib — Data Architect View

## Data Stores

This library produces no persistent data stores of its own. It is a pure logging library — all data output is directed to whatever SLF4J logging backend the consuming application provides (e.g., Log4j2 via `log4j-slf4j2-impl`, Logback, etc.). The physical log destination (file, syslog, SIEM, Splunk, etc.) is entirely determined by the consumer's runtime configuration, outside the scope of this library.

**Configuration Store**: A Java `.properties` file (`soap-logging-default.properties`) is bundled in the JAR as a classpath resource. An optional external override file can be pointed to via JVM system property `soap.logging.config.file` or environment variable `SOAP_LOGGING_CONFIG_FILE`.

## Schema & Tables

No database schema. No tables. No ORM entities.

**Properties file schema** (`soap-logging-default.properties`):

| Key | Type | Default Value | Purpose |
|-----|------|--------------|---------|
| `soap.logging.enabled` | boolean string | `false` | Master on/off switch |
| `soap.logging.sensitive.fields` | comma-separated string | `card_number,ssn,new_pin,cvv,account_number,routing_number,dda_number,dda,application_id` | XML element names to redact |

Alternative key `soap.logging.sensitive-fields` (hyphenated) is also accepted by `SoapLoggingSettingsLoader` (`KEY_FIELDS_DASH` constant, line 32) for backward compatibility.

**Log record schema** (implicit, emitted to SLF4J):

| Field | Value | Source |
|-------|-------|--------|
| Logger name | `com.ecount.axis.soap.logging.SoapLoggingHandler` | `LoggerFactory.getLogger(SoapLoggingHandler.class)` |
| Level | INFO | `SoapLoggingHandler.logMessage`, line 58-60 |
| Message pattern | `"SOAP {} [service={}]\n{}"` | `SoapLoggingHandler`, line 59 |
| Arg 1 (`direction`) | `REQUEST`, `RESPONSE`, or `FAULT` | `SoapLoggingHandler.invoke` / `onFault` |
| Arg 2 (`serviceName`) | Apache Axis target service name string | `msgContext.getTargetService()` |
| Arg 3 (`scrubbedXml`) | Scrubbed SOAP XML string, or `[SOAP_PAYLOAD_REDACTED]` on failure | `SoapMessageScrubber.scrub` return value |

## Sensitive Data Handling (does it sanitise PII/PAN from logs?)

**Yes — partially and by configuration.**

The library implements active redaction via `SoapMessageScrubber.scrub` (`SoapMessageScrubber.java`). The mechanism works as follows:

- For each field name in the `sensitiveFields` list, a regex is applied to the XML string (lines 26-29):
  ```
  (<(?:[\w.\-]+:)?{fieldName}(?:\s[^>]*)?>)[^<]*(</(?:[\w.\-]+:)?{fieldName}>)
  ```
- Element text content is replaced with `[REDACTED]`.
- On any scrubbing exception, the entire payload is replaced with `[SOAP_PAYLOAD_REDACTED]` (line 9, catch block).

**Default bundled sensitive fields** (`soap-logging-default.properties`, line 4):
- `card_number` — PAN surrogate
- `ssn` — Social Security Number
- `new_pin` — PIN
- `cvv` — Card Verification Value
- `account_number` — Bank account number
- `routing_number` — ABA routing number
- `dda_number`, `dda` — Demand Deposit Account identifiers
- `application_id` — Internal application identifier

**Known gaps in PII/PAN sanitisation:**

1. **Element-name dependent**: Redaction only fires if the consuming service's SOAP XML uses exactly the element names in the configured list. Variants like `PAN`, `pan`, `cardNum`, `CardNumber`, `Cvv2` are not covered by default.
2. **Attribute values not scrubbed**: Sensitive data in XML attributes (e.g., `<card pan="4111111111111111"/>`) will not be redacted.
3. **Nested/structured elements not scrubbed**: The regex `[^<]*` matches only simple text content between opening and closing tags. An element with child elements will not be matched (no match if content contains `<`), leaving structured card data blocks unredacted.
4. **No tokenisation or format-preserving masking**: Redaction is full replacement with `[REDACTED]` — no BIN preservation (first 6 / last 4) is performed.
5. **Multi-line values**: The regex does not use `DOTALL` mode — a value spanning multiple lines will not be matched.

## Encryption & Protection

- No data encryption is implemented within this library.
- No TLS/transport configuration is present — transport security is the responsibility of the consuming Axis service.
- No at-rest encryption of log data — log storage security is the responsibility of the consuming application's logging backend and infrastructure.
- The `GITHUB_TOKEN` used in `.mvn/wrapper/settings.xml` (line 7) is injected via environment variable at CI time — no hardcoded credentials exist in the repository.

## Data Flow

```
Apache Axis SOAP Engine
        |
        | (raw SOAP XML string)
        v
SoapLoggingHandler.logMessage
        |
        | (xml + sensitiveFields list)
        v
SoapMessageScrubber.scrub
        |
        | (scrubbed XML string or [SOAP_PAYLOAD_REDACTED])
        v
SLF4J Logger (INFO)
        |
        v
[Consumer-provided logging backend — Log4j2, Logback, etc.]
        |
        v
[Physical log destination — file, syslog, SIEM, etc.]
```

**Configuration data flow:**
```
Classpath: soap-logging-default.properties (bundled JAR)
        +-- merge <-- External properties file (optional, path from JVM/env)
        +-- override <-- OS environment variables (SOAP_LOGGING_ENABLED, SOAP_LOGGING_SENSITIVE_FIELDS)
        +-- override <-- JVM system properties (soap.logging.enabled, soap.logging.sensitive.fields)
        |
        v
SoapLoggingSettings record (cached 60 seconds)
```

## Data Quality & Retention

- **No data quality controls** are implemented for the log data itself — the scrubbed XML is logged as-is.
- **No log rotation, retention policy, or archival** is implemented within this library — entirely delegated to the consuming application's logging backend and operational infrastructure.
- **Settings cache TTL**: 60 seconds (`RELOAD_INTERVAL_MS`, `SoapLoggingSettingsLoader` line 40). Changes to external configuration files take effect within 60 seconds without restart.
- **Null/empty XML handling**: `SoapMessageScrubber.scrub` returns `null` unchanged if the input XML is `null` (line 15), and `logMessage` returns early if `message == null` (line 53 of `SoapLoggingHandler`). No null pointer exceptions will propagate.

## Compliance Gaps

1. **PCI DSS Log Protection (Req 10.3)**: The library itself does not enforce any log integrity, access control, or tamper-evidence mechanism. These must be provided by the log infrastructure.
2. **PCI DSS PAN Masking (Req 3.3.1)**: The first 6 / last 4 masking requirement is not implemented — redaction is full replacement. This means no BIN or issuer context is preserved for operational analysis. However, full redaction satisfies the "do not log PANs" requirement more conservatively.
3. **Element-name variant coverage**: Custom or non-standard XML element names for card/PII data will bypass scrubbing unless operators maintain the sensitive fields list — a process/governance gap rather than a code gap.
4. **No Structured Data Scrubbing**: XML attributes and nested-element values are not scrubbed, creating a potential residual PAN/PII exposure path in logs.
5. **GDPR/CCPA (Req: Data Minimisation)**: No mechanism to suppress entire messages (e.g., by operation type) — all SOAP messages when enabled will be logged (minus configured field values), which may include more personal data than strictly necessary for audit purposes.
