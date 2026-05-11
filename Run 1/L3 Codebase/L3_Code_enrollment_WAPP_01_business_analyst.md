# Business Analyst Analysis — enrollment_WAPP

## Repository Overview

**Repo name:** `enrollment_WAPP`
**Type:** Cardholder enrollment web application (WAR)
**Primary language:** Java 1.8
**Framework:** Apache Struts 1.3.8 + Spring 2.0.3 (XML config)
**Artifact:** `com.citi.prepaid.one.web:enrollment:2020.1.1-SNAPSHOT` (`pom.xml` line 14)
**README description:** "Rebate Card Inquiry" — note the README is mismatched with the actual application (it was likely copied from a related project). The application code clearly implements cardholder enrollment.
**SCM origin:** `gitlab.wirecard-cloud.com/issuing/wdnam/prepaid/applications/webapps/enrollment.git` — Wirecard heritage.

---

## Business Purpose

`enrollment_WAPP` is a **cardholder-facing and operations-facing web application** that enables cardholders to **enroll in or unenroll from prepaid card programmes**. It handles the full self-service registration flow, including:

1. **Authentication** — Login via SSO (`SSOUserInfo`, `ExternalSSOUserInfo`) or standard credentials. MFA is supported via RSA SecurID (`rsa-mfa-impl` dependency).
2. **Enrollment/Unenrollment** — `EnrollmentManagerImpl.setUsersEnrollmentOption()` writes enrollment events to the backend profile service (`AppProfileUserEnrollment`).
3. **E-card management** — `IUserEcardUpdateService` / `UserEcardUpdateServiceImpl` manage virtual card (e-card) preferences.
4. **Terms and Conditions** — `IUserTermsAndConditionsService` / `TermsAndConditionsDTO` track T&C acceptance.
5. **Email notifications** — `EnrollSuccessTemplate`, `UnenrollSuccessTemplate`, `AddressChangeTemplate` (with EMEA and UA variants) trigger notification emails on key events.
6. **OTP/MFA status** — `IUserOTPStatusService` queries one-time password status.
7. **Content management** — `ContentManagementServiceClient` / `CmsQueryBuilder` retrieve programme-specific UI content (branding, text) from a CMS.

### Enrollment Event Types

Defined in `EnrollmentEventType.java`:
- Card enrollment options (paper statement, e-statement, etc.)

Defined in `EnrollmentOptionType.java`:
- ACH, e-card, mailed card options

Defined in `EnrollNotificationEvents.java`:
- Events that trigger notification emails

### Business Process Flow

```
Cardholder accesses web application
    |
    +--> Login (SSO or credential-based, with CAPTCHA)
    |
    +--> View/update enrollment options
    |       |
    |       +--> EnrollmentManagerImpl.setUsersEnrollmentOption()
    |              +--> AppProfileUserEnrollment (backend profile service)
    |
    +--> View/update e-card preferences
    |       |
    |       +--> UserEcardUpdateServiceImpl
    |
    +--> Accept Terms and Conditions
    |       |
    |       +--> IUserTermsAndConditionsService
    |
    +--> Notification email sent on success
    |       |
    |       +--> EnrollSuccessTemplate / UnenrollSuccessTemplate
    |
    +--> Logout
```

### Multi-Programme and Multi-Brand Support

The application is heavily parameterised for multi-brand, multi-affiliate operation:
- `AppContextService` / `AppContextConfig` load programme-specific configuration.
- `ContentManagementServiceClient` retrieves brand-specific UI content.
- `MailContextService` selects the appropriate email template per brand.
- Address change notifications have EMEA, UA (Ukraine?), and default variants, indicating multi-region support.

---

## Compliance Relevance

| Regulatory Requirement | Relevance |
|-----------------------|-----------|
| PCI DSS Req 8 — Authentication | RSA MFA (`rsa-mfa-impl`), CAPTCHA (`simplecaptcha`), session management |
| Reg E — Consumer Protection | Enrollment/unenrollment of ACH and prepaid card programmes |
| CCPA / GDPR | Cardholder PII collected at enrollment; T&C acceptance tracking |
| GLBA — Privacy Notice | T&C service tracks consumer consent |
| ADA / Accessibility | Not assessed from this repo |

---

## Business Gaps and Observations

| Item | Observation |
|------|-------------|
| README mismatch | `README.md` describes "Rebate Card Inquiry" but the app is the enrollment webapp; documentation is stale |
| No WSDL/API contract | The application communicates with backend services via Spring beans; no REST API contract is documented |
| EMEA/UA notification templates | Suggests historic international cardholder base; compliance obligations for non-US regions (GDPR, Quebec Law 25) may apply |
| CAPTCHA | `simplecaptcha:1.2.1` — an old library; accessibility concerns for screen-reader users |
| MFA dependency | `rsa-mfa-impl:1.0.9` — RSA SecurID integration; requires ongoing licence and infrastructure support |

---

## Stakeholders

| Role | Concern |
|------|---------|
| Cardholders | Self-service enrollment, T&C acceptance, e-card preferences |
| Programme Managers | Branding, content, email templates per programme |
| Operations | Application availability, error monitoring |
| Compliance | MFA, T&C capture, PII handling |
| Security | Authentication flows, session management, CAPTCHA |
| Partner Banks / Issuers | Downstream enrollment data via `enrollment_LIB` extract |
