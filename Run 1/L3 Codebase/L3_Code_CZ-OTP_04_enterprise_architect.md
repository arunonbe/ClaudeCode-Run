# CZ-OTP — Enterprise Architect View

## Repository Status
The `CZ-OTP` repository is empty. No architectural analysis can be grounded in code.

## Anticipated Platform Generation
- If built following current Onbe standards: **Gen-2/3** — Spring Boot 3.x, Java 21, reactive WebFlux, containerised, APIM-published.
- ClientZone (`clientzone_WAPP`) is an existing Gen-1/2 application; an OTP service supporting it would need to bridge appropriately.

## Domain
- **Identity & Access Management (IAM) Subdomain** within the ClientZone / Cardholder Self-Service domain.
- Cross-cutting concern: authentication reinforcement for sensitive cardholder operations.

## Anticipated Role
| Role | Detail |
|---|---|
| OTP Generator | Issues time-limited or single-use OTP codes |
| OTP Validator | Validates submitted OTP against issued code |
| Delivery Orchestrator | Routes OTP to cardholder via SMS or email channel |
| Audit Logger | Records OTP lifecycle events for compliance |

## Anticipated Integrations
| Integration | Purpose |
|---|---|
| ClientZone WAPP | Upstream caller triggering OTP flow |
| SMS gateway (Twilio / Azure Communication Services) | OTP delivery via SMS |
| Email relay (Office 365 / SendGrid) | OTP delivery via email |
| Strongbox / Azure Key Vault | OTP seed/secret storage |
| Correlation service | Request tracing |

## Strategic Alignment
- OTP/MFA aligns with PCI DSS Req 8.4 (multi-factor authentication for CDE access) and Req 8.6 (authentication for all system components).
- An internal OTP microservice would replace any hardcoded or external OTP mechanism in ClientZone.

## Blockers
1. Repository is empty — no implementation exists to review.
2. Relationship to existing `nexpay-auth-svc` (another auth service in the inventory) needs clarification to avoid duplication.
3. Architecture decision needed: TOTP (time-based, RFC 6238) vs. HOTP (counter-based, RFC 4226) vs. random server-issued OTP.
