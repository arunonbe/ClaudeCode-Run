# Business Analyst — oneplatform_WAPP

## Business Purpose
OnePlatform is the primary cardholder-facing web application for Onbe's prepaid card and disbursement programs. It is a Java EE web application (WAR) that provides the complete cardholder self-service portal: login, card activation, account management, bank transfers, payment hub, KYC identity verification, and mobile API endpoints. It serves both desktop browser users and mobile app clients (via a JSON API layer).

Originally branded under "NorthLane" / "ecount" / "Citi Prepaid", the application carries the internal URL `http://login.northlane.com` and uses the package root `com.ecount.one`.

## Capabilities
- **Cardholder Authentication**: Username/password login with Multi-Factor Authentication (RSA MFA, OTP, security questions), session management, CSRF token protection, CAPTCHA.
- **Card Activation**: Multi-step card activation flow including card authentication, PIN set, KYC identity verification.
- **Account Management**: Dashboard, transaction history, account summary, profile editing, contact info updates.
- **Payment Access (Bank Transfers / Global Deposits)**: ACH domestic transfers, IEFT (International Electronic Funds Transfer / Cambridge FX), add/edit/delete bank accounts, recurring and one-time transfers.
- **Payment Hub**: Multi-rail payment selection including FX transfer, standard ACH, claimable payments (eChecks), mobile wallet setup (Apple Pay / Google Pay implied).
- **Claimable Payments (Spin)**: Claim code redemption, spin-game integration, animated claim flow.
- **Content Management**: Dynamic affiliate-specific content, localization (i18n), Terms & Conditions.
- **Mobile API**: JSON-based action endpoint for mobile clients (iOS/Android) exposing all above capabilities plus MFA resolution.
- **Security Audit Logging**: Structured audit events (login, payment events, profile changes) sent to a downstream audit service.
- **Biocatch Integration**: Device behavioral analytics for fraud detection.
- **SSO / Express Login**: FSSO token-based login, Express Login with optional CAPTCHA.

## Entities / Domain Objects
- `IEcountProfile` — top-level session profile aggregating security, affiliate, user, device, app contexts.
- `LoginResult` / `LoginDetails` — authentication outcome and user credential data.
- `AuditData` / `DeviceData` — security audit event payloads.
- `CardActivationForm` — form model for card activation workflow.
- `PaymentSelectionVO` / `PaymentSelectionUserVO` — payment hub selection data.
- `ClaimPaymentStatusVO` — claimable payment outcome.
- `CertificateInfo` — eCheck / claimable payment certificate.
- `MobileIEFTBaseBean` — global deposit (FX transfer) data model.
- `WesternUnionContext` — Western Union disbursement context.
- `OPConstants` — constant definitions for the entire application.

## Business Rules
1. Users failing authentication receive generic error messages (no enumeration of accounts).
2. Velocity check: if invalid login attempts exceed threshold within a time window, account is locked for 2 hours.
3. RSA/OTP MFA is required for certain sensitive operations (bank adds, PIN change, recurring ACH).
4. CSRF token is generated and validated for card activation and other state-changing flows.
5. Affiliate context drives skin, locale, feature flags (e.g., `display_recipient_web`, `spin_option`, `pin_change`).
6. If `display_recipient_web = Y`, cardholder is redirected away from OnePlatform to the new Recipient Web; login is denied on this application.
7. KYC is required for certain programs (status: Required → InProgress → Failure/Success/Watchlisted).
8. Password: salted hash (new format) with fall-through for MD5 legacy hashes (migrated on next successful login).
9. Express ACH supports same-day settlement; feature flagged per affiliate.
10. Biocatch: `ACTION_CODE_DENY` from behavioral analytics blocks login.

## Key Flows
1. **Mobile Login**: JSON request → username/password validation → DB auth → MFA resolution (OTP / challenge / RSA) → audit event → claim code check → session setup → JSON response.
2. **Card Activation**: redirect to card activation landing page → CSRF token → card auth → PIN setup → success.
3. **Bank Transfer (ACH)**: user adds bank account → MFA gate → one-time or recurring transfer scheduled.
4. **KYC**: user directed to KYC portal (external) → status polled back via `kycPortalUrl`.
5. **Claim Payment (Spin)**: post-login claim code detection → intermediate page or auto-claim → confirm.

## Compliance Relevance
- Cardholder data environment (CDE) application: handles card activation (card number entry), PIN management, account balances.
- PCI DSS Req 8: Authentication (MFA for remote access, CSRF, session management).
- PCI DSS Req 10: Audit logging (structured security audit events for login, payment, profile changes).
- Reg E: Dispute and transfer rules for ACH / electronic fund transfers.
- GLBA / CCPA: Consumer financial data protection (profile, transaction data).
- KYC / AML: Identity verification gate for program enrollment.

## Risks
1. **End-of-life technology stack**: Struts 1.3, Spring 2.0.3, Log4j 1.2.17. Multiple EOL components with unpatched CVEs in the CDE.
2. **MD5 password hashes still in production**: legacy users may have MD5-hashed passwords; migration happens lazily on login.
3. **Hardcoded paths in config**: `log4jConfigLocation = file:D:/c-base/config/oneplatform/log4j.xml` — Windows path embedded in `web.xml`.
4. **`display_recipient_web` redirect**: if migration flag is set incorrectly, legitimate cardholders could be locked out.
5. **Biocatch behavioral analytics**: external dependency for fraud scoring; unavailability could block legitimate logins.
