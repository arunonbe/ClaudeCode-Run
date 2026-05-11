# Enterprise Architect Analysis: rsa-mfa_LIB

## Platform Generation
**Gen-1 (security-critical)**

Strong Gen-1 indicators:
- Apache Axis SOAP client (Axis 1.x — EOL since ~2012)
- Spring 2.0 dependency (released 2006; EOL)
- WSDL-generated Axis stub classes (code generation from SOAP WSDL)
- `TrustAllSSLSocketFactory` (disables SSL certificate validation)
- Commons Logging (pre-SLF4J era)
- Calendar-based version `2019.4.1` — last updated 2019
- Citi-branded package names (`com.citiprepaid.common`) — legacy platform origin
- Hard-coded application ID switch (only values 10 and 6 are valid)

No Gen-2 or Gen-3 characteristics present.

## Business Domain
**Security Infrastructure — Multi-Factor Authentication**

Critical security control for the Onbe prepaid card platform. Implements PCI DSS Req 8 MFA and FFIEC layered security authentication controls for consumer-facing and internal portals.

## Architectural Role
**Shared Security Library** — The sole MFA integration layer for the legacy platform. All MFA-requiring applications embed and depend on this library:
- One Platform (OP) — appId 6
- Client Zone (CZ) — appId 10
- Potentially other internal portals

This library is a **single point of security control** — a failure or vulnerability in it affects all authenticated applications simultaneously.

## Dependency Map
### Upstream consumers
- One Platform web application
- Client Zone web application

### Downstream dependencies
- RSA Adaptive Authentication server (external SOAP WS)
- TeleSign (third-party SMS/call provider, via RSA ACSP plugin)
- `xPlatform:2017.1.1` (internal eCount platform)

## Integration Patterns
- **SOAP Web Service Client (Apache Axis)**: All RSA communication via WSDL-generated Axis stubs.
- **Shared Library (JAR)**: Embedded in consuming applications; no service boundary.
- **Spring Dependency Injection**: All configuration injected via Spring XML beans.
- **Retry Pattern (basic)**: Thread.sleep + recursion for SOAP fault/remote exception retry.

## Strategic Status
**Replace Immediately — Highest Security Risk**

This library represents the most urgent security modernisation requirement across all six repositories:

1. `TrustAllSSLSocketFactory` disabling SSL certificate validation exposes MFA tokens and credentials to MITM attacks.
2. OTP tokens logged at INFO level.
3. Spring 2.0 and Apache Axis are EOL frameworks with no security patching.
4. RSA Adaptive Authentication SOAP API integration uses a WSDL marked "OLD".
5. No secrets vault for RSA credentials.
6. Last updated 2019 — 5+ years without security review.

The business function (MFA) is security-critical; the implementation is the most vulnerable in the portfolio.

**Recommended replacement**: Migrate to a modern MFA service (Microsoft Entra MFA, Okta, Auth0, or Azure AD B2C) via a thin adapter, removing the RSA Adaptive Authentication dependency entirely. Until then, at minimum:
- Fix `TrustAllSSLSocketFactory` immediately.
- Move RSA credentials to a secrets vault.
- Mask OTP tokens and phone numbers in logs.

## Migration Blockers
1. **RSA Adaptive Authentication platform**: Decommissioning RSA requires a parallel MFA provider cutover; consumers must be migrated simultaneously.
2. **TeleSign integration via RSA ACSP**: TeleSign is embedded in RSA's plugin architecture; direct TeleSign API integration requires new library development.
3. **Axis SOAP stubs**: 100+ WSDL-generated classes must be replaced when moving to a new MFA provider.
4. **Hard-coded application IDs (6 and 10)**: Tightly couples the library to specific application contexts; must be redesigned.
5. **Spring 2.0**: Upgrading the consuming application's Spring version may break other Spring 2.x dependencies.
6. **Wide consumer impact**: Both major consumer portals (OP and CZ) must be migrated simultaneously.
