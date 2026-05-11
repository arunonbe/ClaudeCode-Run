# api-logging-lib — Business Analyst View

## Business Purpose

`api-logging-lib` (Maven artifact `com.ecount.webservices:api-logging-lib` v1.0.0) is a shared Java library that provides standardised, reusable SOAP request/response/fault payload logging for any Apache Axis-based web-service client or server hosted within the Onbe (ecount) platform. Its sole business purpose is to produce auditable, sanitised trace logs of SOAP traffic without coupling individual services to logging infrastructure or scrubbing logic.

The library was previously known as `csapi-axis-soap-logging` (referenced in `README.md` build instructions) and lives under the `com.ecount.axis.soap.logging` package namespace.

## Business Capabilities

1. **SOAP Message Interception**: Intercepts inbound requests, outbound responses, and fault messages at the Apache Axis handler layer (`SoapLoggingHandler.invoke`, `SoapLoggingHandler.onFault`).
2. **Selective Sensitive-Field Redaction**: Automatically replaces the text content of named XML elements with `[REDACTED]` before any log output is written (`SoapMessageScrubber.scrub`).
3. **Configurable Field List**: The set of redacted fields is externally configurable at runtime — no code change or redeployment required to add or remove a field from scrubbing.
4. **Feature Toggle**: Logging can be switched on or off at the JVM or environment level (`soap.logging.enabled`) without touching application code.
5. **Hot Configuration Reload**: Settings are re-read from the configuration source at most every 60 seconds (`RELOAD_INTERVAL_MS = 60_000L` in `SoapLoggingSettingsLoader`), allowing operational teams to adjust behaviour on live systems.
6. **Fail-Safe Logging**: Any exception during logging or scrubbing is caught and swallowed (`SoapLoggingHandler` lines 31-34, 43-46; `SoapMessageScrubber` lines 30-34), ensuring that logging failures never disrupt payment transaction processing.

## Business Entities

| Entity | Representation | Source |
|--------|---------------|--------|
| SOAP Message | `org.apache.axis.Message` (raw XML string) | `SoapLoggingHandler.logMessage` |
| Logging Settings | `SoapLoggingSettings` record (`enabled`, `sensitiveFields`) | `SoapLoggingSettings.java` |
| Sensitive Field List | `List<String>` of XML element names | `soap-logging-default.properties` |
| Log Entry | SLF4J `INFO` log line: direction, service name, scrubbed XML | `SoapLoggingHandler`, line 59 |

## Business Rules & Validations

1. **Default-off**: Logging is disabled by default (`soap.logging.enabled=false` in `soap-logging-default.properties`, line 3). It must be explicitly enabled in each environment.
2. **Mandatory Redaction Fields (bundled defaults)**: The default sensitive field list in `soap-logging-default.properties` (line 4) is:
   - `card_number`, `ssn`, `new_pin`, `cvv`, `account_number`, `routing_number`, `dda_number`, `dda`, `application_id`
3. **Fail-Closed Scrubbing**: If the scrubbing routine throws any exception, the entire payload is replaced with `[SOAP_PAYLOAD_REDACTED]` rather than emitting raw data (`SoapMessageScrubber.java`, line 9, catch block lines 30-34).
4. **Distinct Field Enforcement**: Duplicate field names in configuration are de-duplicated (`parseCsv`, `SoapLoggingSettingsLoader` line 157).
5. **Configuration Priority** (highest to lowest): JVM system property > OS environment variable > external properties file > bundled classpath defaults.
6. **External File Override is Additive**: An external file overrides only the keys it defines; omitted keys fall back to bundled defaults (`loadBaseProperties`, lines 122-126).
7. **HTTP-scheme paths rejected**: Config file paths with `http://` scheme are rejected (test `normalizePathRejectsInvalidLocations`; `normalizePath` only handles plain paths and `file:` URIs).

## Business Flows

```
[Apache Axis Engine]
        |
        v
[SoapLoggingHandler.invoke / onFault]
        |
        +-- Check enabled flag (SoapLoggingSettingsLoader.getCurrent) -- disabled --> exit silently
        |
        +-- Determine direction: REQUEST (pre-pivot) / RESPONSE or FAULT (post-pivot)
        |
        +-- Retrieve SOAP XML from Message.getSOAPPartAsString()
        |
        +-- SoapMessageScrubber.scrub(xml, sensitiveFields)
        |       |
        |       +-- For each configured field: regex replace element text with [REDACTED]
        |       +-- On any exception: return [SOAP_PAYLOAD_REDACTED]
        |
        +-- LOG.info("SOAP {direction} [service={name}]\n{scrubbedXml}")
        |
        +-- On any exception: LOG.warn (no rethrow)
```

**Configuration Reload Flow** (occurs at most every 60 seconds):
```
getCurrent() -- cache fresh? --> return cached settings
            -- cache stale? --> load() --> read JVM props, env vars, optional external file, classpath defaults
                                       --> cache new SoapLoggingSettings
```

## Compliance & Regulatory Concerns

1. **PCI DSS**: The library directly addresses PCI DSS requirements around protecting PANs in logs. Fields `card_number` and `cvv` are in the default redaction list. However, the redaction is regex-based on XML element names — if a consuming service uses non-standard element names (e.g., `CardNbr`, `PAN`, `pan`) for card data, those fields will **not** be redacted unless explicitly added to the sensitive fields list. This is a residual PCI DSS risk.
2. **GLBA / Reg E**: Fields `ssn`, `account_number`, `routing_number`, `dda_number`, `dda` are included in the default redaction list, covering GLBA-sensitive financial account identifiers.
3. **Audit Trail**: The library produces an INFO-level audit trail of all SOAP interactions including service name and direction, which supports forensic and compliance investigations.
4. **Default-Disabled State**: The default-off configuration (`soap.logging.enabled=false`) means environments where logging is not explicitly enabled will have no SOAP trace audit trail, which may be a gap for compliance evidence requirements.

## Business Risks

1. **Non-Standard Element Names Not Scrubbed**: If consuming services use XML element names outside the default list (e.g., `PAN`, `cardNum`, `pan`), raw card/PII data could appear in logs. This requires per-integration review and configuration.
2. **No Namespace-Scoped Redaction**: The regex in `SoapMessageScrubber` strips the namespace prefix before matching (pattern `(?:[\\w.\\-]+:)?`) but matches by local element name only — a field named `card_number` in one namespace will be scrubbed even if the intent was namespace-specific.
3. **Regex-Based Scrubbing Limitations**: Multi-line element values or elements with child elements will not be matched by the current regex (which requires `[^<]*` between tags), potentially leaving structured card data unredacted.
4. **No Log Masking for Attributes**: Sensitive data stored in XML attributes rather than element text content will not be redacted.
5. **Logging Disabled by Default**: Teams that forget to enable logging will have no SOAP audit trail — an operational and compliance gap.
6. **Dependency on ecount/Onbe Legacy Infrastructure**: The `com.ecount` package namespace signals this is tied to the legacy ecount-era platform architecture.
