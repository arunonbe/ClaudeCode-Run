# Enterprise Architect View — log4j2-sanitize

## Architectural Classification

`log4j2-sanitize` is a **cross-cutting compliance utility** — specifically, a logging security pattern library. Within Onbe's enterprise architecture, it addresses a horizontal concern (secure logging) that spans all application services. It is positioned at the observability / audit layer of the enterprise architecture stack.

## Enterprise Context

Onbe processes payments data across multiple service generations (Gen-1 legacy services through Gen-3 modern REST APIs). All services emit application logs to centralised log aggregation infrastructure (evidence: ELK/Logstash stack referenced in other repos; Splunk or equivalent likely in use). These logs are:

1. Consumed by security operations for incident detection (NIST CSF DE.CM)
2. Required for PCI DSS audit trail evidence (Req 10)
3. Subject to CCPA / GDPR data minimisation obligations if they contain PII

The enterprise risk addressed by this library is: **uncontrolled PII and attack vectors entering the log stream from application inputs**.

## Architectural Fit and Gap Analysis

### Current State
The `log4j2-sanitize` repo exists as a proof-of-concept. Based on the codebase survey, the sanitisation pattern is **not yet consistently deployed across the Onbe service portfolio**. Evidence: `manage-payment-rest-api` uses Log4j2 but its `log4j2-spring.xml` does not include `SanitizingFilter`. The `js-import_SVC` still uses Log4j 1.x without any sanitisation.

### Target State
Every Spring Boot service using Log4j2 should have `SanitizingFilter` (or an enhanced version) in its Log4j2 configuration, combined with MDC field sanitisation and exception message scrubbing.

## Enterprise Logging Architecture

```
Services (Log4j2 + SanitizingFilter)
         │ structured JSON log events
         ▼
Container stdout (Docker / Kubernetes)
         │ captured by
         ▼
Log Shipping Agent (Filebeat / Fluent Bit)
         │ forwards to
         ▼
Log Aggregation (ELK / Splunk)
         │ indexed and searchable
         ▼
Security Operations / Compliance Dashboards
```

The `SanitizingFilter` operates at the source (service) level — this is the most cost-effective and lowest-latency point to prevent sensitive data from entering the log pipeline. Centralised masking at the aggregation layer is a fallback, not a substitute.

## Pattern Library Governance

For this proof-of-concept to become an enterprise capability:

1. **Publish as a shared Maven library** to the internal Nexus repository under `com.onbe.logging:log4j2-sanitize`.
2. **Mandate adoption** via enterprise security standards for all new Spring Boot / Log4j2 services.
3. **Version and maintain** the library centrally — security updates (e.g., new PAN pattern recognition, new encoding library version) propagate to all consumers via a BOM (Bill of Materials).
4. **Extend the filter** to include PAN masking, CRLF stripping, and SSN masking before mandating adoption (see Data Architect view for recommended regex patterns).

## Standards Alignment

| Standard | Clause | Relevance |
|---|---|---|
| PCI DSS v4.0.1 | Req 10.3.3 | Log files must be protected from destruction and modification; sanitisation prevents log forging |
| PCI DSS v4.0.1 | Req 3.3.1 | PAN must be masked when displayed — this applies to log output |
| OWASP Top 10 | A03 Injection | Log injection is a variant of injection attack |
| OWASP ASVS | V7.1.1, V7.1.2 | Log all security events; ensure logs do not contain sensitive data |
| NIST SP 800-92 | Section 3 | Log management — protect log integrity |
| GDPR | Art 5(1)(f) | Integrity and confidentiality of personal data in logs |

## Enterprise Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| XSS via log viewer if unsanitised | Medium | Medium (ops staff) | Addressed by current library |
| PAN exposure in logs | High | Critical (PCI DSS violation) | Not addressed; requires extension |
| Log injection / forging | Medium | High (audit trail corruption) | Partially addressed (HTML) but CRLF not stripped |
| CRLF injection | Medium | High | Not addressed |
| PII in exception stack traces | High | High (GDPR/CCPA) | Not addressed |

## Relationship to Other Repos

- **logback-sanitize**: The parallel implementation for the Logback framework. Enterprise policy should mandate one or the other depending on the logging framework in use, with consistent PII masking logic shared between both.
- **manage-payment-rest-api**: Uses Log4j2 but does not implement `SanitizingFilter`. This is the highest-priority service for adopting this pattern given its payment data scope.
- **api-logging-lib**: Another Onbe logging library — alignment between these repos should be assessed to prevent duplicate / conflicting logging utility libraries.
- **onbe-log4j-utils**: Another log utility repo in the estate — governance should clarify which is the canonical logging security library.
