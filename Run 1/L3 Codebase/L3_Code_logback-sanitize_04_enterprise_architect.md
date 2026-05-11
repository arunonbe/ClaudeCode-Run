# Enterprise Architect View — logback-sanitize

## Architectural Classification

`logback-sanitize` is a **cross-cutting compliance utility** at the logging/observability layer of Onbe's enterprise architecture — the Logback-framework counterpart to `log4j2-sanitize`. Enterprise architecture governance must treat these two repos as a pair, ensuring they provide consistent security controls regardless of which logging framework a service uses.

## Framework Coverage Gap in Onbe's Service Estate

Based on the repo listing, Onbe's service portfolio includes:
- Services using Logback (default Spring Boot): the majority of Spring Boot services that do not explicitly switch to Log4j2
- Services using Log4j2 (`spring-boot-starter-log4j2`): newer services and `manage-payment-rest-api`
- Services using Log4j 1.x (`js-import_SVC`): legacy WAR deployments
- Services with no Spring Boot logging at all: legacy J2EE applications

Neither `logback-sanitize` nor `log4j2-sanitize` is currently mandated across the portfolio. The enterprise architecture gap is the absence of a **mandatory, uniformly enforced logging security standard**.

## Comparison with log4j2-sanitize at the Enterprise Level

| Dimension | log4j2-sanitize | logback-sanitize |
|---|---|---|
| Extension mechanism | Log4j2 Filter (event-level) | Logback MessageConverter (pattern-level) |
| Automatic coverage of new appenders | No (must add filter to each) | Yes (pattern-token override is global) |
| Code complexity | Higher (plugin + factory + cast) | Lower (single method override) |
| Risk of missed appenders | Higher | Lower |
| Shared business logic | `StringEscapeUtils.escapeHtml4()` | `StringEscapeUtils.escapeHtml4()` (same) |
| Test coverage | None | None |
| Production readiness | PoC only | PoC only |

The Logback implementation has a slightly stronger architecture for coverage guarantees (global `%m` override vs per-appender filter), but both need the same functional enhancements (PAN masking, CRLF stripping, SSN masking).

## Enterprise Governance Recommendations

### 1. Establish a Canonical Logging Security Library

Create a `com.onbe.logging:logging-security` Maven BOM/library containing:
- `LogSanitizer.java` — core static utility with PAN masking, CRLF stripping, SSN masking, HTML encoding
- `SanitizedMessageConverter.java` — Logback adapter (consumes `LogSanitizer`)
- `SanitizingFilter.java` — Log4j2 adapter (consumes `LogSanitizer`)
- Reference `logback-spring.xml` and `log4j2-spring.xml` configurations

### 2. Mandate Adoption via Onbe Spring Boot Parent POM

The `onbe-spring-boot-parent_PARENT` and `service-parent_PARENT` repos should include the logging security library and reference configurations, ensuring all inheriting services get sanitisation automatically without individual team action.

### 3. Policy: PAN Never in Logs

A formal policy statement should be issued: "No PAN, CVV, SSN, or full bank account number shall appear in application log output." The logging security library should enforce this programmatically.

## Standards and Regulatory Alignment

| Standard | Requirement | Gap addressed by logback-sanitize | Remaining Gap |
|---|---|---|---|
| PCI DSS v4.0.1 Req 10.3.2 | Protect audit log files from unauthorised modifications | Log injection prevention (partial) | No OS-level protection |
| PCI DSS v4.0.1 Req 3.3.1 | Mask PAN in all media | Not met | No PAN masking |
| OWASP ASVS V7.1.1 | All auth, access, and validation events logged | Out of scope for this library | Separate logging library needed |
| OWASP ASVS V7.1.2 | No sensitive data in logs | Partially met | PAN/SSN/CVV not masked |
| GDPR Art 25 | Data minimisation by design | Partially met | PII not stripped |

## Relationship to Other Repos

- **log4j2-sanitize**: Direct functional twin; should share core masking logic.
- **api-logging-lib**: Another logging utility in the Onbe estate. Governance should clarify whether this handles sanitisation or other concerns (structured logging format, correlation ID injection). Avoid duplication.
- **onbe-log4j-utils** / **onbe-log4j1-utils**: Legacy log4j utilities. These must be assessed for PII handling.
- **manage-payment-rest-api**: This service uses Log4j2, has `logbook` (Zalando) for HTTP request/response logging with `json-body-fields: [ssn,cardNumber,cvv]` obfuscation configured — that is a positive finding for HTTP-level masking, but application-level log statements within the service are still unprotected by `log4j2-sanitize` patterns.

## Risk Register

| Risk | Severity | Likelihood | Owner |
|---|---|---|---|
| PAN in application logs of payment services | Critical | High | Security Architecture |
| XSS in log viewers via injection | High | Medium | Application Security |
| Log injection creating false audit trail | High | Low-Medium | Application Security |
| Inconsistent adoption across services | High | High | Platform Engineering |
