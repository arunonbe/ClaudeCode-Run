# East-EmailTemplates — Data Architect Report

## Data Architecture Overview

`East-EmailTemplates` is a **static HTML template repository** with no database schema, no ORM entities, and no data access layer of its own. From a data architecture perspective, the significance of this repository lies in:

1. The **PII fields injected as merge tokens at send time** by the calling email delivery service
2. The **payment credential tokens** embedded in template URLs
3. The **implicit data contracts** between the template merge variables and the upstream data sources that populate them

---

## Template Merge Variables as a Data Contract

Each template uses brace-delimited tokens that act as a de-facto API contract between the template system and the notification delivery service (likely `NotificationManagerImpl` in the `ecap-backend-process_LIB` or `ecore-batch_LIB` libraries). The following table maps each token to its likely data source:

| Token | Data Class | Upstream Source | DB Table / Field |
|---|---|---|---|
| `{FIRSTNAME}` | PII — Personal Name | Recipient profile | `cbaseapp.dbo.registration` or `recipient` table — first_name column |
| `{TOTAL}` | Financial | Payment record | `cbaseapp.dbo.payments` — amount field (displayed as dollars, stored as cents) |
| `{PUID}` | Payment Credential | Payment / recipient link | `nexpay_claimable.dbo` or `cbaseapp` — unique payment/redemption code |
| `{CLIENT_URL}` | Configuration | Program/affiliate config | Program configuration table — affiliate or program portal URL |
| `{EMAILHEADERURL}` | Configuration | Program branding | Client branding/assets configuration |
| `{LOGINCODE}` | Payment Credential | Virtual card access | Likely derived from card's tokenized access record in `ecountcore` or `strongbox` |

---

## PII Fields in Templates — Detailed Analysis

### `{FIRSTNAME}` (All templates, line 5-8 in most files)
Present in every template. This is the recipient's legal first name, sourced from the registration or recipient profile. Under GDPR Article 4(1) and CCPA Section 1798.140(o), this constitutes personal data.

- **choicesTemplate.html** (line 5): `Hello {FIRSTNAME},`
- **createTemplate.html** (line 4): `Hello {FIRSTNAME},`
- **EAST_Email Notification_MPV_Virtual_CI_Sunrise.html** (line 8): `Dear {FIRSTNAME},`
- **virtualexpressTemplate.html** (line 5): `Dear {FIRSTNAME},`

The first name appears in the email body in plain text — it is not masked or tokenized. If an email is forwarded, printed, or stored in a third-party email system, this constitutes PII egress.

### `{TOTAL}` (All templates)
The monetary value of the payment, e.g., `$250.00`. This is financial data. While not individually classified as sensitive under PCI DSS, the combination of recipient name + payment amount in a single email message creates a data element that:
- Is subject to financial privacy rules under GLBA (Gramm-Leach-Bliley Act) for bank-issued cards (e.g., Fifth Third Bank issuer referenced in `virtualexpressTemplate.html`)
- Must be retained and retrievable under Reg E error resolution obligations

---

## Payment Credential Token Analysis

### `{PUID}` — Payment Unique Identifier
Used in `choicesTemplate.html` (line 6), `createTemplate.html` (line 4), `EAST_Email Notification_MPV_Choice.html` (line 6), and multiple MPV templates. The URL pattern is:
```
{CLIENT_URL}?puid={PUID}
```
The PUID serves as the **single authentication factor** for the first-time registration flow. It is equivalent to a one-time password (OTP) for fund access. If intercepted:
- An attacker can access the payment portal
- Direct funds to an alternate payment destination
- Redirect ACH to attacker-controlled bank account

This makes `{PUID}` a **high-value target** and its transmission security is critical. The template itself does not enforce HTTPS (the URL `{CLIENT_URL}` is a variable), though in practice all endpoints should be HTTPS.

### `{LOGINCODE}` — Direct Virtual Card Access Token
Used in `virtualexpressTemplate.html` (line 5) and `EAST_Email Notification_MPV_Virtual_*` templates. URL pattern:
```
{CLIENT_URL}?virtualexpress={LOGINCODE}
```
This is a **single-click access mechanism** — no additional authentication required. It provides immediate access to a virtual prepaid card's account details (card number, CVV, expiry date) after login. The `LOGINCODE` has a higher risk profile than `{PUID}` because it bypasses the registration step entirely.

If the `LOGINCODE` is long-lived (not expiring within hours), it creates a persistent phishing risk where a forwarded email grants card access.

---

## Data Flows Involving These Templates

### Inbound Data Flow (Populate → Template → Send)
```
ecountcore DB / cbaseapp DB
    └─► NotificationManagerImpl (ecap-backend-process_LIB or ecore-batch_LIB)
           └─► Token substitution: {FIRSTNAME}, {TOTAL}, {PUID}, {LOGINCODE}
                  └─► Email delivery service (Mailgun / SMTP)
                         └─► Recipient inbox
```

### Downstream Data Retention Risk
- **Email delivery provider logs**: First name + PUID + payment amount stored in third-party system
- **Email client storage**: Recipient's email client (Gmail, Outlook, etc.) stores PII + credential indefinitely
- **Email forwarding**: No technical control prevents recipients from forwarding the email with the embedded PUID/LOGINCODE

---

## Client-Specific Data Exposure

Two templates contain **hardcoded client and patient identifiers**:

1. `createTemplate.html` (line 5): References "Johnson & Johnson Vision Reward for Performance Program" — this identifies the program sponsor.
2. `virtualexpressTemplate.html` (lines 5-7): References "Deaconess Specialty Physicians" and "Fifth Third Bank, National Association. Member FDIC." This template is used for **healthcare refund disbursements**, meaning recipients are patients. Patient financial transactions may be subject to **HIPAA** if the template is used in a context where Deaconess is a covered entity or business associate, creating an additional regulatory obligation beyond standard payments compliance.

The hardcoded program name `2024PP16888` in `createTemplate.html` (line 10) appears to be an internal program or job reference ID — its presence in a consumer-facing email could expose internal program identifiers.

---

## Template Storage and Version Control Risk

- Templates are stored as flat HTML files with no versioning metadata beyond git history
- No template variable schema/contract documentation exists in the repository
- A template change that removes a `{PUID}` token or alters the URL structure could silently break payment delivery without build-time validation
- No automated testing framework validates that all required merge tokens are present before a template is deployed
- The `README.md` (2 lines, no content) provides no guidance on token definitions, available templates, or deployment process

---

## Sensitive Data Summary

| Data Element | Classification | Present In | Risk |
|---|---|---|---|
| `{FIRSTNAME}` | PII | All 15 templates | GDPR/CCPA — transmitted to third-party email provider |
| `{TOTAL}` | Financial | All 15 templates | GLBA — payment amount in clear text |
| `{PUID}` | Payment Credential | 6+ templates | High — single factor for fund access |
| `{LOGINCODE}` | Payment Credential | 6+ templates | Critical — single-click card access, no 2FA |
| Hardcoded "Deaconess Specialty Physicians" | PHI-adjacent | `virtualexpressTemplate.html` | Potential HIPAA nexus |
| Hardcoded program ID `2024PP16888` | Internal Config | `createTemplate.html` | Information disclosure |
| `800-439-9568` phone number | Customer Service | Multiple templates | Low — public information |

**No full PANs, CVV codes, SSNs, full account numbers, or routing numbers were found in any template.** This is the expected and compliant state for a PCI DSS Level 1 service provider.
