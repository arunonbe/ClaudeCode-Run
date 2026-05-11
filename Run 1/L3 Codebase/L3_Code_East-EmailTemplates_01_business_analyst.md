# East-EmailTemplates — Business Analyst Report

## Repository Overview

`East-EmailTemplates` is a collection of **15 HTML email notification templates** used by the Onbe East platform (formerly North Lane Technologies / eCount) for cardholder and payment recipient communications. These templates are sent at key moments in the payment disbursement lifecycle: when a virtual prepaid card is issued, when a recipient can choose their payment method, when a physical card is created and loaded, and when a refund is delivered.

The `README.md` (line 1) describes this simply as "Sample Email Templates," but the content analysis reveals these are production-grade client-branded notifications sent to end recipients of prepaid disbursements, rewards, rebates, and refund payments.

---

## Template Inventory and Business Purpose

| File | Business Scenario |
|---|---|
| `choicesTemplate.html` | Payment choice notification — NAPA Tools & Equipment Rewards, virtual debit card, prompts recipient to register and choose payment method |
| `createTemplate.html` | ACH bank deposit registration — Johnson & Johnson Vision Reward, prompts recipient to register bank account for ACH transfer |
| `create_loadTemplate.html` | Physical card create-and-load notification |
| `EAST_Email Notification_MPV_Choice.html` | MPV (MyPaymentVault) generic choice template — recipient selects payment method |
| `EAST_Email Notification_MPV_PhysicalCreate&Load_CI_Sunrise.html` | MPV physical card create and load — CI (cardholder-initiated) Sunrise branding |
| `EAST_Email Notification_MPV_PhysicalCreateOnly_CI_Sunrise.html` | MPV physical card create only |
| `EAST_Email Notification_MPV_PhysicalLoadOnly_CI_Sunrise.html` | MPV physical card load only |
| `EAST_Email Notification_MPV_Virtual_CI_Sunrise.html` | MPV virtual card — CI variant with Sunrise branding |
| `EAST_Email Notification_MPV_Virtual_CI_Sunrise_V2.html` | Version 2 of CI Sunrise virtual |
| `EAST_Email Notification_MPV_Virtual_NON-CI_DefaultCheck_Sunrise.html` | Non-CI variant — defaults to check if not claimed within deadline |
| `EAST_Email Notification_MPV_Virtual_NON-CI_DefaultPlastic_Sunrise.html` | Non-CI variant — defaults to plastic card if not claimed |
| `EAST_Email Notification_MPV_Virtual_NON-CI_Sunrise.html` | Non-CI base Sunrise virtual template |
| `EAST_Email Notification_MPV_Virtual_Refund_Sunrise.html` | Refund-specific virtual card notification |
| `virtualexpressTemplate.html` | Virtual express — Deaconess Specialty Physicians refund via Fifth Third Bank / Onbe, 30-day expiry |
| `EAST_Email Notification_MPV_Virtual_NON-CI_DefaultCheck_Sunrise.html` | Default-check fallback |

---

## Business Capabilities Provided

### 1. Payment Delivery Notification
These templates are the primary communication channel between the Onbe payment platform and end recipients. They notify recipients that funds have been loaded and provide the mechanism (link + PUID/LOGINCODE) to access those funds.

### 2. Multi-Rail Choice Orchestration
The "choice" templates (`choicesTemplate.html`, `EAST_Email Notification_MPV_Choice.html`) support Onbe's multi-rail disbursement model, where a recipient can elect virtual card, ACH transfer, physical prepaid card, or check payout. The registration URL `{CLIENT_URL}?puid={PUID}` drives this orchestration.

### 3. Brand-Specific Client Notifications
Templates are parameterized for individual client programs. Hardcoded client references visible in production-stage templates include:
- **NAPA Tools & Equipment Rewards** (`choicesTemplate.html`, line 6)
- **Johnson & Johnson Vision Reward for Performance Program** (`createTemplate.html`, line 5)
- **Deaconess Specialty Physicians** (`virtualexpressTemplate.html`, lines 5-6)
- Generic `((Company Name))` placeholders indicate templates are cloned and customized per client

### 4. Express Virtual Card Access
The `virtualexpressTemplate.html` and `EAST_Email Notification_MPV_Virtual_NON-CI_DefaultCheck_Sunrise.html` templates use a `{LOGINCODE}` token appended to `{CLIENT_URL}?virtualexpress=` to provide single-click card access without requiring full registration.

---

## Template Variable (Merge Field) Inventory

All templates use brace-delimited merge tokens substituted at send time:

| Token | Data Element | PII Risk Level |
|---|---|---|
| `{FIRSTNAME}` | Recipient first name | PII — CCPA/GDPR personal data |
| `{TOTAL}` | Dollar amount of card/payment | Financial data |
| `{PUID}` | Payment unique identifier / claim code | Credential — if intercepted, enables payment claim |
| `{CLIENT_URL}` | Program-specific portal URL | Configuration |
| `{EMAILHEADERURL}` | Client branding image URL | Configuration |
| `{LOGINCODE}` | Direct virtual card access token | Credential — single-factor access key |

**No full PANs, CVV codes, SSNs, or account numbers were identified in any template.** This is compliant with PCI DSS Requirement 3.3 (never display full PAN in cardholder communications). However, the `{PUID}` and `{LOGINCODE}` tokens represent **de facto payment access credentials** delivered via email, which creates risk if email accounts are compromised.

---

## Business Rules

1. **Payment Expiry Notice** — All templates include expiry language. Expiry periods vary: 24 months (`choicesTemplate.html` line 7, `EAST_Email Notification_MPV_Choice.html`), 30 days (`virtualexpressTemplate.html` line 6), and placeholder `((XX)) days` (`EAST_Email Notification_MPV_Virtual_NON-CI_DefaultCheck_Sunrise.html` line 11). Inconsistent expiry periods across templates may create cardholder disputes under Reg E.
2. **Default Payment Fallback** — The NON-CI templates specify that if access is not claimed within the deadline, the payment defaults to "a check mailed to the address on file" or "plastic card" — this is a business rule with escheatment and address-accuracy implications.
3. **CI vs NON-CI Flows** — Templates are bifurcated into Cardholder-Initiated (CI) and Non-CI variants. CI recipients have already activated on the portal; NON-CI recipients receive the first notification requiring registration.
4. **Single Registration** — The `createTemplate.html` (line 5) states that for ACH payments "you will only need to register once," establishing a persistent bank account linkage.
5. **Contact Information** — Several templates reference `800-439-9568` and `help@mypaymentvault.com` as the customer service endpoint; the `virtualexpressTemplate.html` (line 6) uses `800-439-9568` specifically.

---

## Regulatory Relevance

### GDPR / CCPA
`{FIRSTNAME}` is personal data. Email delivery logs associating an email address with a PUID and payment amount constitute personal data processing under GDPR Article 4 and CCPA. A data processing addendum (DPA) with the email delivery provider is required.

### Reg E (Electronic Fund Transfer Act)
These email notifications constitute the "error resolution" and "initial disclosure" notification required under Reg E for prepaid accounts subject to the 2016 Prepaid Rule. The expiry warning language and payment access instructions must meet Reg E §1005.18 short-form disclosure requirements where applicable.

### PCI DSS
While no full PANs appear in templates, the `{LOGINCODE}` direct-access token bypasses the portal authentication step. If the `LOGINCODE` value is derived from or equivalent to a card's account number or CVV, it may constitute Sensitive Authentication Data (SAD) under PCI DSS Requirement 3.2.1. This must be verified with the token generation implementation.

### NACHA
For the ACH/bank transfer templates (`createTemplate.html`), NACHA Rules require that consumers authorizing recurring ACH debits receive specific disclosure language. The template does not appear to include NACHA-required authorization language for ACH debit scenarios.

### CAN-SPAM / CASL
All templates include "This is an automatically generated email. Please do not reply" — required for commercial email compliance. However, they do not include a physical mailing address for the sender (required by CAN-SPAM §7704(a)(5)).
