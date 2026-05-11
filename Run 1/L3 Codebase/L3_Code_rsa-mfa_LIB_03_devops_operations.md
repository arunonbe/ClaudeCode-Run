# DevOps / Operations Analysis: rsa-mfa_LIB

## Build System
- **Maven** multi-module project (mvnw wrapper present)
- **Java**: No explicit compiler target set in root POM; parent `service-parent:8` likely defaults to Java 8 (confirmed by Spring 2.0 dependency)
- **Parent POM**: `com.citi.prepaid.service:service-parent:8`
- **Root artifact**: `com.citi.prepaid.service.rsa-mfa:rsa-mfa:2019.4.1`
- **Modules**: rsa-mfa-common, rsa-mfa-impl

## Module Build Outputs
| Module | Artifact | Purpose |
|---|---|---|
| rsa-mfa-common | rsa-mfa-common JAR | `AuthenticationService` interface; RSA/TeleSign/KBA WSDL-generated WS types; `MFAConfigurationOptions` |
| rsa-mfa-impl | rsa-mfa-impl JAR | `AuthenticationServiceImpl`; Axis SOAP binding stubs; `TrustAllSSLSocketFactory` |

## Deployment
This is a **library** — not deployed standalone. Consumed by:
- One Platform web application
- Client Zone web application
- Any other application requiring MFA

Spring context wiring at: `rsa-mfa-impl/src/main/resources/com/ecount/one/service/rsa/rsa-mfa-Context.xml`

## Configuration Management
- RSA caller credentials (`rsausername`, `password`), org name, tenant ID, retry count, retry interval, TeleSign phone language, and phone country code map are all injected via Spring bean properties.
- `ApplicationSettings` objects for CZ (appId 10) and OP (appId 6) are injected by consuming application.
- `MFAConfigurationOptions` bean holds challenge question count and event types.
- No environment variable support; no Azure App Configuration; no secrets vault integration for credentials.
- **RSA password is stored in Spring XML configuration in plaintext** — wherever the consuming application's `rsa-mfa-Context.xml` is deployed, the password is in cleartext.

## Observability
- Logging via **Apache Commons Logging** (`LogFactory.getLog(...)`) — older pattern.
- Info/error level logging throughout `AuthenticationServiceImpl`.
- Log statements include OTP tokens: `LOG.info(">>> calling validateOTP, deliverOTPSessionId: " + deliverOTPSessionId + ", token: " + token)` at line 871 — **OTP token is logged at INFO level**, which is a security issue.
- Phone number arrays are also logged at INFO level (`LOG.info(">>> calling deliverOTP with... phone number " + phoneNumber[0] + " " + phoneNumber[1] + " " + phoneNumber[2])`) at line 760-763.
- No metrics, no distributed tracing.

## Infrastructure Dependencies
| Dependency | Type | Notes |
|---|---|---|
| RSA Adaptive Authentication Server | External SOAP WS | Core dependency; must be reachable from app servers |
| TeleSign service | External (via RSA ACSP plugin) | SMS/call OTP delivery |
| Apache Axis | SOAP framework | `rsa-mfa-impl` Axis-generated stubs |
| `com.ecount:xPlatform:2017.1.1` | Internal | eCount platform library |
| `org.springframework:spring:2.0` | Spring 2.0 | DI framework; extremely old |
| WSDL file | `wsdl/OLD/AdaptiveAuthentication_6_5.xml` | RSA WSDL for stub generation; file marked "OLD" |

## Operational Risks
1. **OTP tokens logged at INFO** (`AuthenticationServiceImpl.java:871`): OTP tokens written to log files compromise MFA security; logs may be accessible to support staff.
2. **Phone numbers logged at INFO** (lines 760-763): PII in logs; CCPA/GDPR logging governance gap.
3. **TrustAllSSLSocketFactory**: Certificate validation disabled — RSA calls over a network that can be MITM'd expose credentials and OTP tokens.
4. **RSA version dependency**: WSDL marked "OLD" — RSA API version may be deprecated; upgrade path unclear.
5. **Spring 2.0**: Released 2006; no longer receiving security patches.
6. **Version `2019.4.1`**: Calendar-based version suggests last release was 2019; library has not been updated in 5+ years.
7. **No retry circuit breaker**: Retry logic uses `Thread.sleep()` between retries; in a high-throughput scenario, sleeping threads can exhaust thread pool.
8. **No timeout configuration visible**: Axis SOAP calls have no explicit timeout; RSA slowness can block app threads indefinitely.

## CI/CD
No CI/CD pipeline configuration present. No Jenkinsfile, GitLab CI, or GitHub Actions YAML found.
