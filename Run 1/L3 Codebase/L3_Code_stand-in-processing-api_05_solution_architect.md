# Solution Architect Report: stand-in-processing-api

## API Surface

| Path Pattern | Protocol | Auth Mechanism | Notes |
|---|---|---|---|
| `/api/**` | REST (HTTP/JSON) | `External-Auth-Response` header + IP validation | CSRF disabled; `permitAll` in Spring Security |
| `/v1/**` | REST (HTTP/JSON) | Same as `/api/**` | Alternate REST path |
| `/ws/**` | SOAP (XML) | X.509 certificate + IP validation | Auth failure returns HTTP 200 |
| `/hc/**` | HTTP | None | Health check, public |
| `/swagger-ui/**`, `/v3/api-docs/**` | HTTP | None | OpenAPI docs, public |

All paths are declared `permitAll` in Spring Security and rely entirely on the custom `OncePerRequestFilter` implementations for access control. Standard Spring Security features (CSRF protection, session management) are largely disabled.

## Security Posture

**Moderate — better than Gen-1 but with notable flaws.**

Strengths:
- Azure Key Vault + Managed Identity for secrets — no hardcoded credentials in application config
- Mutual TLS with Fiserv
- Resilience4j circuit breakers on external calls
- TLS 1.3 for client-facing communication
- Java 21 / Spring Boot 3.5.5 with actively patched CVEs

Weaknesses:
- SOAP authentication failure returns HTTP 200 (not 401/403)
- `sasi.dev.disable-security-filter` bypass flag exists in production code
- Azure App Config connection string committed to `.env` file
- IP-based access control is the primary authentication mechanism, which is vulnerable to IP spoofing (acknowledged in the architecture document Risk 3)
- `External-Auth-Response` header is parsed from the request without verifying its origin cryptographically — it could be forged by anyone who can make HTTP requests to SASI

## Critical Vulnerabilities

1. **Azure App Configuration access key committed to VCS** (`stand-in-processing-api/.env`, line 2):
   - Full connection string `https://appcs-shared-qa-ss.azconfig.io;Id=zvgN;Secret=[REDACTED — rotate immediately]` committed to repository
   - Immediate action required: rotate the access key in Azure Portal; audit access logs for the App Configuration instance for unauthorised reads
   - PCI DSS Requirement 8: API keys are credentials that must not be stored in plaintext in version control

2. **SOAP authentication returns HTTP 200 on failure** (`SecurityConfig.java`, lines 66–70):
   - Comment in code: "We always return 200 and let the caller figure it out. Yuck."
   - SOAP callers cannot distinguish an authentication failure from a successful (but empty) response
   - This creates a silent authentication bypass detection failure: a misconfigured or compromised caller will not receive a clear error signal

3. **Security bypass property** (`SecurityConfig.java`, line 29):
   - `@Value("${sasi.dev.disable-security-filter:false}")` with `disableSecurityFilter` used in both SOAP and REST filters
   - If this property is set to `true` in any deployed environment (misconfiguration, CI environment, etc.), all authentication for all SASI endpoints is disabled
   - This is a PCI DSS Requirement 6.3 finding: a "back door" security bypass mechanism exists in production code

4. **`External-Auth-Response` header is client-supplied and not cryptographically verified** (`RestSecurityValidator.java`, lines 37–62):
   - The header is read, JSON-parsed, and its `validationResult.isValid()` field is trusted
   - An internal caller that can reach SASI can forge this header with `{"validationResult":{"valid":true},"requestInfo":{"apiUsername":"fakeuser"}}` and pass validation
   - The architecture document (Risk 3) acknowledges this gap: "Limited protection against sophisticated IP spoofing attacks and header manipulation"

5. **CSRF protection disabled for all functional endpoints** (`SecurityConfig.java`, line 49):
   - CSRF disabled for `/ws/**`, `/cs/**`, `/api/**`, `/hc/**`, `/v1/**` — effectively all functional paths
   - While CSRF is less relevant for API-only services that use header-based auth, the wholesale disabling without explanation is a technical debt item

## Technical Debt

- **Duplicate filter logic**: `SecurityConfig` defines both inline anonymous `OncePerRequestFilter` classes (lines 54–103) and named inner classes `SoapValidationFilter`/`RestValidationFilter` (lines 126–165) doing the same thing; only the anonymous versions are registered. The named inner classes are dead code
- **SOAP protocol lock-in**: Apache CXF 4.1.2 SOAP stack adds complexity; as Gen-1 SOAP clients are decommissioned, the SOAP layer can be removed
- **`LegacyCryptoService`**: The ECount data access layer references a `LegacyCryptoService` whose implementation is in the Gen-1 eCount codebase — this is a maintenance burden requiring knowledge of eCount encryption formats
- **Five separate database JPA configurations**: Each of the five databases has its own `@Configuration` class, `EntityManagerFactory`, `TransactionManager`, and package scan — while architecturally correct, this requires careful transaction boundary management to avoid cross-database consistency issues
- **`stip-generated` version**: Parent POM version is `0.0.1-SNAPSHOT`, indicating SASI is not yet in production release cadence; snapshot versions should not be deployed to production
