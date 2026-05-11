# Solution Architect View — recipient-screening-api

## API Surface

The service exposes two REST API groups via Spring MVC, generated from an OpenAPI spec (`openapi.json`):

**Screening API** (`RecipientScreeningApiDelegate`):
- `POST /api/v1/screening/request` — synchronous sanctions screening request; accepts `RecipientScreeningRequest`, returns `RecipientScreeningResponse`

**Webhook API** (`SanctionWebhookApiDelegate`):
- `POST /sanction/webhook` — receives asynchronous sanction status updates from the screening vendor; accepts `SanctionWebhookEvent`, returns `WebhookAck`

Both endpoints are served on port 80. The Spring Actuator management interface is on port 9090.

## Security Posture — Critical Vulnerability: Authentication Bypass

**File**: `recipientscreening-svc/src/main/java/com/onbe/recipientscreening/configuration/SecurityConfig.java`, lines 15–20

```java
return http
    .formLogin(AbstractHttpConfigurer::disable)
    .authorizeHttpRequests(auth -> auth.anyRequest().permitAll())
    .csrf(AbstractHttpConfigurer::disable)
    .build();
```

`anyRequest().permitAll()` grants unauthenticated access to **all endpoints**, including the screening API and the webhook endpoint. CSRF is also disabled. This means:

1. Any internal network actor can invoke `POST /api/v1/screening/request` to screen arbitrary identities without authentication.
2. Any actor who can reach the service can invoke `POST /sanction/webhook` and inject fake sanctions status changes (DECLINED, APPROVED) for arbitrary DDAs.

**Finding severity**: Critical. The webhook injection risk is particularly severe — an attacker who can reach the service (from within the internal network or via SSRF from another service) could force-block a legitimate recipient's account by injecting a fake DECLINED webhook, or unblock a sanctioned recipient by injecting a fake APPROVED webhook.

**Remediation**: Configure Spring Security as an OAuth 2.0 resource server (`http.oauth2ResourceServer(oauth2 -> oauth2.jwt(...))`) and require bearer token authentication for both endpoints. For the webhook endpoint, implement HMAC signature validation of the incoming payload as an additional control (already partially scaffolded in `SanctionWebhookRequestValidator`).

## Critical Finding: DDA Number Logged at INFO Level

**File**: `recipientscreening-svc/src/main/java/com/onbe/recipientscreening/service/RecipientScreeningService.java`, lines 65 and 84

```java
log.info("Processing recipient screening for member: {}, DDA: {}", 
    recipientScreeningRequest.getMemberId(), recipientScreeningRequest.getDdaNumber());
```

DDA numbers are financial account identifiers protected under GLBA. Writing them to application logs at INFO level means they will be captured by any log aggregation system (Azure Monitor, Splunk, etc.), potentially stored for years, and accessible to any operator with log read access. Under PCI DSS Req 3.4 (render PAN unreadable where stored) and GLBA safeguards, DDA numbers in logs require the same controls as other sensitive account data.

**Remediation**: Mask the DDA to last-4 digits in log output, or remove DDA from log messages entirely, retaining only the opaque memberId for correlation.

## Critical Finding: SQL Server Certificate Validation Bypass

**File**: `app-config/prod/appsettings.json`, lines 3–4

```json
"spring.datasource.cbaseapp.url": "...;trustServerCertificate=true",
"spring.datasource.ecountcore.url": "...;trustServerCertificate=true"
```

`trustServerCertificate=true` disables TLS certificate validation for the SQL Server connections. This means the service will accept any certificate presented by the database server, making it vulnerable to man-in-the-middle attacks on the database connection from the application container. For a service processing OFAC screening data, this is a significant network-layer security gap.

**Remediation**: Configure the SQL Server TLS certificate in the application's Java truststore and remove `trustServerCertificate=true`.

## Critical Finding: Port 50505 Exposed

**File**: `Dockerfile`, line 14 — `EXPOSE 80 9090 9091 50505`

Port 50505 is commonly used as a Java remote debugging port (JDWP) or agent port. If this port is accessible in production environments, it could allow remote code execution via the JDWP protocol. Even if not a JDWP port, the purpose is undocumented.

**Remediation**: Identify the purpose of port 50505 and if it is a debug port, remove it from production Docker images and Kubernetes service definitions.

## Additional Technical Debt

- **`ObjectMapper` as static field** (`RecipientScreeningService.java` line 32): `private static ObjectMapper objectMapper = new ObjectMapper()` — ObjectMapper is thread-safe after configuration but the static initialization bypasses Spring's bean management. Should be Spring-managed for proper module configuration and testability.
- **`convertApiStatusToDomainStatus` accepts `Object`** (line 320): `private SanctionStatus convertApiStatusToDomainStatus(Object apiStatus)` — using `Object` rather than the concrete API status type loses compile-time type safety and requires `apiStatus.toString()` casting.
- **Null return on error** (line 116): `return null` at the end of `apiV1ScreeningRequestPost` when all exception handlers have been invoked. A null return from an API delegate method may cause a NullPointerException in the framework or an empty 200 response instead of an appropriate error code.
- **`jq` and `curl` in production image**: These tools are useful for debugging but expand the container attack surface. They should be removed from production images or added only to a debug/sidecar image.

## Code-Level Findings Summary

| Finding | File | Line | Severity |
|---|---|---|---|
| All requests permitted without auth | `SecurityConfig.java` | 17 | Critical |
| CSRF disabled with no alternate protection | `SecurityConfig.java` | 18 | High |
| DDA number logged at INFO level | `RecipientScreeningService.java` | 65, 84 | High |
| SQL TrustServerCertificate=true | `app-config/prod/appsettings.json` | 3–4 | High |
| Port 50505 exposed (possible debug port) | `Dockerfile` | 14 | High |
| Null returned on API error | `RecipientScreeningService.java` | 116 | Medium |
| Static ObjectMapper | `RecipientScreeningService.java` | 32 | Low |
| `Object` type in status conversion | `RecipientScreeningService.java` | 320 | Low |
