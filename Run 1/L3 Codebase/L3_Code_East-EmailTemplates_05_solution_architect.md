# East-EmailTemplates — Solution Architect Report

## Critical Flags

### FLAG-1: Unquoted `href` Attribute in MPV Virtual CI Template — HIGH
**File**: `EAST_Email Notification_MPV_Virtual_CI_Sunrise.html` (line 13)
**Code**:
```html
<a href={CLIENT_URL}?virtualexpress={LOGINCODE} target="_blank">
```
The `href` attribute value is unquoted. This is invalid HTML5. Email clients parsing this may truncate the URL at the space before `target="_blank"`, rendering the entire "ACCESS YOUR PAYMENT" button non-functional. Recipients would be unable to access their funds.

### FLAG-2: Unquoted `src` Attribute in createTemplate.html — MEDIUM
**File**: `createTemplate.html` (line 3)
```html
src={EMAILHEADERURL}
```
Unquoted image `src` attribute. In strict HTML parsers used by some email clients, this may fail to render the header image, impacting brand presentation and potentially triggering spam filters that penalize broken images.

### FLAG-3: Unfilled Placeholder `((XX)) days` in Production-Committed Template — HIGH
**File**: `EAST_Email Notification_MPV_Virtual_NON-CI_DefaultCheck_Sunrise.html` (line 11)
```html
Make sure to access your payment within ((XX)) days of receiving this email
```
This template contains an unfilled variable placeholder (`((XX))`) in the consumer-visible expiry language. If this template is deployed as-is, cardholders receive legally ambiguous expiry language. Under Reg E §1005.18, prepaid account disclosures must be clear and complete. A template with `((XX)) days` is neither.

### FLAG-4: Hardcoded Patient-Adjacent Program Reference — MEDIUM
**File**: `virtualexpressTemplate.html` (lines 5-6)
```html
Deaconess Specialty Physicians has sent a refund worth ${TOTAL}.
...Fifth Third Bank, National Association. Member FDIC.
```
This template is for a **healthcare provider refund program** using Fifth Third Bank as the issuer. Recipients are patients of Deaconess Specialty Physicians. If this program processes Protected Health Information (PHI) at the payment orchestration layer, HIPAA Business Associate Agreement obligations may apply to Onbe. The template storing a healthcare provider's name in a git repository visible to all developers is an information disclosure concern.

### FLAG-5: Hardcoded Internal Program ID in Consumer Email — LOW
**File**: `createTemplate.html` (line 10)
```html
<p>  2024PP16888</p>
```
Internal program/job reference ID appearing in the consumer-facing email footer. This discloses internal program numbering conventions to recipients and could assist social engineering attacks targeting program administrators.

---

## Technical Debt Register

### TD-1: No Template Validation Framework
No mechanism exists to validate:
- Required merge tokens are present in each template
- HTML is well-formed
- URLs use HTTPS protocol
- Expiry language is not placeholder text

**Remediation**: Add a CI/CD pipeline with `htmlhint` for syntax, a custom script for token validation, and a link checker for hardcoded URLs.

### TD-2: No Shared Base Template
15 templates share approximately 80% of their HTML structure (table layout, CSS, footer, contact info). Changes to the shared header URL pattern, footer legal text, or accessibility attributes must be made in 15 separate files.

**Remediation**: Implement a Thymeleaf, Handlebars, or Jinja2 base template with `extends`/`block` inheritance. Each specific template becomes a 10–20 line override file.

### TD-3: No Internationalization Support
`ecap-backend-process_LIB`'s `EcapEmailNotificationImpl.java` (line 52) references:
```java
EcapProcessConstants.LANGUAGE_CODE_ENGLISH
EcapProcessConstants.RECIPIENT_NOTIFICATION_EVENT_SPANISH
```
Spanish notification events are defined in the Java code, but no Spanish-language templates are present in this repository. The Spanish notification path likely fails silently or falls back to English, which may violate Reg E Spanish disclosure requirements for Spanish-language programs.

**Remediation**: Add Spanish-language variants for all MPV templates; enforce language selection at template lookup time.

### TD-4: No Template Versioning
No semantic version numbers are embedded in templates or their names (except the ad-hoc `_V2` suffix on one file). There is no way to know which version of a template a recipient received, making complaint investigation and A/B testing analysis impossible.

**Remediation**: Add a hidden `<!-- template-version: 1.2.3 -->` comment to each template and maintain a `CHANGELOG.md`.

---

## All Template Files — Purpose and Risk Profile

| File | Lines | Business Event | PII Tokens | Credential Tokens | HTML Defects | Risk |
|---|---|---|---|---|---|---|
| `choicesTemplate.html` | 7 | NAPA payment choice | `{FIRSTNAME}` | `{PUID}` | None | Medium |
| `createTemplate.html` | 10 | J&J ACH registration | `{FIRSTNAME}` | `{PUID}` | Unquoted `src` | High |
| `create_loadTemplate.html` | ~7 | Physical create+load | `{FIRSTNAME}` | `{PUID}` | TBD | Medium |
| `EAST_Email Notification_MPV_Choice.html` | 7 | Generic MPV choice | `{FIRSTNAME}` | `{PUID}` | None | Medium |
| `EAST_Email Notification_MPV_PhysicalCreate&Load_CI_Sunrise.html` | ~8 | Physical card CI | `{FIRSTNAME}` | `{PUID}` | TBD | Medium |
| `EAST_Email Notification_MPV_PhysicalCreateOnly_CI_Sunrise.html` | ~8 | Physical create only | `{FIRSTNAME}` | `{PUID}` | TBD | Medium |
| `EAST_Email Notification_MPV_PhysicalLoadOnly_CI_Sunrise.html` | ~7 | Physical load only | `{FIRSTNAME}` | `{PUID}` | TBD | Medium |
| `EAST_Email Notification_MPV_Virtual_CI_Sunrise.html` | 15 | Virtual CI | `{FIRSTNAME}` | `{LOGINCODE}` | Unquoted href | **Critical** |
| `EAST_Email Notification_MPV_Virtual_CI_Sunrise_V2.html` | ~15 | Virtual CI v2 | `{FIRSTNAME}` | `{LOGINCODE}` | TBD | High |
| `EAST_Email Notification_MPV_Virtual_NON-CI_DefaultCheck_Sunrise.html` | 11 | Virtual → check fallback | `{FIRSTNAME}` | `{LOGINCODE}` | `((XX))` placeholder | **Critical** |
| `EAST_Email Notification_MPV_Virtual_NON-CI_DefaultPlastic_Sunrise.html` | ~11 | Virtual → plastic fallback | `{FIRSTNAME}` | `{LOGINCODE}` | TBD | High |
| `EAST_Email Notification_MPV_Virtual_NON-CI_Sunrise.html` | ~11 | Virtual NON-CI base | `{FIRSTNAME}` | `{LOGINCODE}` | TBD | High |
| `EAST_Email Notification_MPV_Virtual_Refund_Sunrise.html` | ~11 | Refund virtual | `{FIRSTNAME}` | `{LOGINCODE}` | TBD | High |
| `virtualexpressTemplate.html` | 7 | Deaconess refund express | `{FIRSTNAME}` | `{LOGINCODE}` | Unquoted `src` | **Critical** |
| `create_loadTemplate.html` | ~7 | Create+load | `{FIRSTNAME}` | `{PUID}` | TBD | Medium |

---

## Security Vulnerability Analysis

### VULN-1: `{LOGINCODE}` Single-Factor Access Token — HIGH
The `{LOGINCODE}` token provides single-click access to a prepaid card account without requiring a password. This is intentional UX design but creates security risk:
- Email-to-email forwarding = fund access transfer
- Phishing attack targeting the email = instant card access
- No 2FA or device binding at the email click step

**Remediation**: Implement device fingerprint check or one-time CAPTCHA at the `virtualexpress` landing page; set `{LOGINCODE}` expiry to 24 hours maximum; log all `{LOGINCODE}` redemptions to a security event stream.

### VULN-2: `{PUID}` Lifetime Not Bounded in Template
The `choicesTemplate.html` (line 7) states: "Please make sure to access and use your payment within **24 months**." A 24-month-valid `{PUID}` in a forwarded email is a 24-month open access window for fund theft.

**Remediation**: If PUID expiry is truly 24 months for card value access, implement additional authentication after the first 30 days of inactivity (e.g., re-confirm email or provide last-4 SSN for identity reverification).

### VULN-3: CAN-SPAM Physical Address Missing
No template includes the required physical mailing address of the sending organization under CAN-SPAM Act §7704(a)(5). All templates include "This is an automatically generated email. Please do not reply." but lack the sender's street address.

---

## Remediation Priority Matrix

| Item | Priority | Effort | Risk if Unaddressed |
|---|---|---|---|
| Fix unquoted `href` in `EAST_Email Notification_MPV_Virtual_CI_Sunrise.html` line 13 | P1 — Immediate | Minutes | Broken payment access button |
| Replace `((XX)) days` in `NON-CI_DefaultCheck` template | P1 — Immediate | Minutes | Reg E disclosure violation |
| Fix unquoted `src` in `createTemplate.html` and `virtualexpressTemplate.html` | P1 — Immediate | Minutes | Broken header image |
| Remove internal program ID `2024PP16888` from `createTemplate.html` | P1 — Immediate | Minutes | Internal info disclosure |
| Add CI/CD pipeline with HTML lint + token validation | P2 — 14 days | Small | Recurring defects at deployment |
| Add Spanish-language template variants | P2 — 30 days | Medium | Reg E Spanish disclosure gap |
| Implement base template inheritance | P3 — 60 days | Medium | Maintenance scalability |
| Review LOGINCODE lifetime policy with Security team | P1 — 7 days | None (policy) | Payment fraud exposure |
| Add CAN-SPAM physical address to all templates | P2 — 7 days | Small | CAN-SPAM compliance |
| HIPAA BAA review for Deaconess program | P1 — 7 days | None (legal) | HIPAA exposure |
