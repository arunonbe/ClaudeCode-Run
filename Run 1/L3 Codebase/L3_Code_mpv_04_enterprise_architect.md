# Enterprise Architect Report — mpv (My Payment Vault)

## 1. Position in the Onbe Architecture

MPV is the **primary consumer-facing digital touchpoint** in the NexPay Gen-3 platform. It is the front-end orchestrator that aggregates capabilities from across the NexPay microservice landscape and presents them as a unified cardholder experience. In the enterprise architecture, MPV occupies the **Presentation Layer** of the Gen-3 platform:

```
Internet → Azure Front Door / CDN
                │
                ▼
    MPV (SPA / SSR front-end)
          │           │
          ▼           ▼
  nexpay-           nexpay-
  recipientweb-bff  auth-svc
          │
          ▼ (orchestrated by BFF)
  ┌──────────────────────────────┐
  │  nexpay-cardprocessor-svc    │
  │  nexpay-claim-code-svc       │
  │  nexpay-order-orchestrator   │
  │  nexpay-recipient-profile    │
  │  message-center_SVC (Gen-2)  │
  └──────────────────────────────┘
```

The presence of `message-center_SVC` in this call graph creates a **cross-generation integration dependency**: the Gen-3 portal must call back to a Gen-2 XML-RPC service for in-app notifications, introducing reliability and protocol heterogeneity risks.

## 2. Multi-Rail Architecture Implications

MPV's support for 10+ disbursement rails makes it one of the most complex consumer front-ends in the payments industry. Enterprise architecture considerations:

- **Rail orchestration**: The choice page (`choicePage/`) implies a backend service (likely `nexpay-order-orchestrator`) that manages which rails are available for a given claim code and program configuration.
- **Affiliate customization**: `branding/affiliateVanity.json` and `wizardSettings`/`menuSettings` in `dashboardDetails.json` reveal a multi-tenant architecture where each Onbe client (affiliate) can enable or disable specific payment rails and UI features. This is a significant B2B differentiation capability.
- **International support**: FX transfer and language support (French, Spanish locales) indicate the portal serves both US and international recipients.

## 3. Authentication Architecture

The three-token login response (`cardToken`, `authToken`, `refreshToken`) reveals a sophisticated authentication architecture:

- `authToken` (HS256 JWT, ~10-minute lifetime): Standard bearer token for API authorization.
- `refreshToken` (HS256 JWT, ~60-minute lifetime): Used to obtain new access tokens without re-authentication.
- `cardToken` (JWE, AES-256-GCM encrypted): Carries encrypted card identity data. The encrypted payload likely contains the cardholder's card identifier in a format that allows the front-end to perform card operations without decrypting sensitive card data in JavaScript.

The HS256 signing algorithm for auth and refresh tokens is noteworthy. HS256 uses a shared symmetric secret, which means the signing key must be shared between the token issuer (likely `nexpay-auth-svc` or its BFF) and any service that validates the token. This is less architecturally clean than RS256/ES256 (asymmetric), where the public key for validation can be distributed freely. A move to RS256 with JWKS endpoint discovery would improve the architecture.

## 4. Gen-3 Assessment

MPV is explicitly a Gen-3 artifact (NexPay platform, Azure deployment, modern development tooling). However, the cross-generation dependency on `message-center_SVC` (XML-RPC) represents a Gen-3 architectural compromise that should be addressed.

| Aspect | Assessment |
|---|---|
| Runtime target | Azure Container Apps or Static Web Apps |
| Auth model | JWT-based with short-lived tokens (modern) |
| API protocol | REST/JSON (modern) |
| Multi-tenancy | Affiliate-level feature flags (modern) |
| Notification channel | Gen-2 XML-RPC dependency (legacy debt) |
| PII handling in mock data | Full PAN and CVV present (critical finding) |

## 5. Security Architecture Concerns

1. **Full PAN display**: The dashboard mock shows `"displayFullCardNumber":"Y"` (`dashboardDetails.json` line 28) and a full 16-digit card number. Displaying full PANs in a web browser requires that the cardholder's device not be compromised and that the front-end does not log or cache the PAN. This is a PCI DSS Requirement 3 and 4 concern — PAN in transit over HTTPS is acceptable, but PAN stored in browser `localStorage`, logged in application logs, or visible in DevTools network tab requires careful control.
2. **CVV display for virtual cards**: Virtual card holders need to see their CVV for online purchases. PCI DSS Requirement 3.3 permits displaying SAD to the legitimate cardholder, but the display must be on a secured, time-limited basis (not persistent storage). The architecture for this flow needs explicit PCI DSS scoping.
3. **Session management**: The 10-minute access token window is appropriate. The 60-minute refresh token window is reasonable but should be invalidated on logout and on suspicious activity detection.
