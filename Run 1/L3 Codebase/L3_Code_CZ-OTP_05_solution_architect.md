# CZ-OTP — Solution Architect View

## Repository Status
The `CZ-OTP` repository is empty. No solution architecture can be derived from code.

## Architecture (Anticipated)
For a ClientZone OTP service consistent with Onbe's current technology standards, the expected architecture would be:

```
ClientZone WAPP
    |  REST (internal APIM / service mesh)
    v
CZ-OTP Service (Spring Boot 3.x, WebFlux)
    |
    +-- OTP Generation Endpoint   POST /v1/otp/generate
    |       --> Generate random/TOTP code
    |       --> Store hashed OTP + expiry (Redis or DB)
    |       --> Dispatch to delivery channel
    |
    +-- OTP Validation Endpoint   POST /v1/otp/validate
    |       --> Look up stored OTP by correlation ID
    |       --> Compare submitted value
    |       --> Mark as used / invalidate
    |
    +-- Delivery Service
            +-- SMS Gateway client
            +-- Email client
```

## Security Design Requirements (anticipated)
- OTP values must be hashed (bcrypt or Argon2) before storage — storing cleartext OTP is equivalent to storing a password.
- OTP expiry: 5–10 minutes maximum; single-use enforcement.
- Rate limiting: max 3–5 attempts before lockout per session/account (PCI DSS Req 8.3).
- Delivery channel (phone number, email) must be validated against registered cardholder profile before dispatch — prevents OTP diversion attack.
- Correlation ID (session token) must be cryptographically random (at least 128 bits).
- All OTP events (generate, validate success, validate failure, expiry) must be audit-logged with timestamp, cardholder identifier, and source IP.

## Technical Risks (anticipated)
- If OTP seeds for TOTP are used: seed compromise allows infinite OTP generation — seeds must be stored in HSM/Key Vault, never in DB plaintext.
- Replay attack window: even short TTLs allow replay within the window; single-use enforcement is the primary mitigation.
- SMS delivery is susceptible to SIM-swap attacks; for high-value operations, TOTP app or hardware token is preferred.
- Shared OTP state across multiple service instances requires a distributed cache (Redis) with atomic compare-and-swap to prevent race conditions in multi-pod deployments.

## Integration with ClientZone
- `clientzone_WAPP` would call this service's generate endpoint on step-up authentication trigger.
- Response returns a correlation ID (not the OTP) to the frontend.
- User submits OTP on the frontend; the WAPP calls the validate endpoint with the correlation ID and submitted code.
- On success, WAPP proceeds with the protected operation.

## Action Required
Repository must be populated. Recommend creating from the Onbe Spring Boot exemplar (`exemplar-customer-service_WAPP` or `onbe-spring-boot` starter) to ensure consistent build, observability, and security configuration.
