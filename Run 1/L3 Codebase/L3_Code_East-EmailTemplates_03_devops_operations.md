# East-EmailTemplates — DevOps & Operations Report

## Build System

`East-EmailTemplates` has no build system. It is a flat collection of 15 static HTML files with no:
- `package.json` (Node/npm)
- `pom.xml` (Maven)
- `Makefile`
- Templating engine configuration

There are no CI/CD pipeline files (no `.gitlab-ci.yml`, no GitHub Actions workflows). The `README.md` contains only the two-word description "Sample Email Templates."

---

## CI/CD Status

**No CI/CD pipeline exists for this repository.** This means:
- Template changes are committed to git but not automatically validated
- There is no build step to validate HTML syntax
- There is no automated test to verify required merge tokens (`{FIRSTNAME}`, `{PUID}`, etc.) are present in modified templates
- There is no staging/preview deployment mechanism
- There is no approval gate before templates go live

For a PCI DSS Level 1 payments provider, the absence of a change control pipeline for customer-facing email templates that contain payment access credentials (`{PUID}`, `{LOGINCODE}`) represents a significant operational risk.

---

## Deployment Model

Templates in this repository are presumed to be:
1. **Loaded into the notification service database** (likely `cbaseapp` or a notification-specific database) as stored template records, OR
2. **Deployed as files** to a notification service directory read by `NotificationManagerImpl`

The actual deployment mechanism is not visible from this repository. Based on patterns in the `ecore-batch_LIB` notification helpers (`EventACHEmailTemplate.java`, `EventIEFTEmailTemplate.java`), template names are referenced by enum constants — the HTML content is likely stored in a database and retrieved by template name at runtime.

---

## Template Versioning and Change Management

### Current State
- Templates are tracked only by git commit history
- No semantic versioning (no `v1.0`, `v2.0` in filenames except `EAST_Email Notification_MPV_Virtual_CI_Sunrise_V2.html`)
- The `_V2` suffix naming convention suggests an ad-hoc approach to versioning
- Multiple templates appear to be variants of the same base template (CI vs NON-CI, DefaultCheck vs DefaultPlastic) without a shared base component

### Risk of Silent Breakage
A change to the `{CLIENT_URL}` token syntax or the `{PUID}`/`{LOGINCODE}` parameter names would break payment delivery if the template service does not validate token consistency. There is no automated contract test to catch this.

---

## Operational Risks

### 1. Missing `{LOGINCODE}` Quote in virtualexpressTemplate.html
In `virtualexpressTemplate.html` (line 5), the `href` attribute for the access link is:
```html
<a href="{CLIENT_URL}?virtualexpress={LOGINCODE}" target="_blank">
```
This template correctly quotes the href. However, in `EAST_Email Notification_MPV_Virtual_CI_Sunrise.html` (line 13):
```html
<a href={CLIENT_URL}?virtualexpress={LOGINCODE} target="_blank">
```
The `href` attribute value is **unquoted**. Similarly, in `createTemplate.html` (line 3):
```html
src={EMAILHEADERURL}
```
The `src` attribute is also unquoted. These are HTML syntax errors. In some email clients, unquoted attribute values containing `?` and `=` characters may be misinterpreted, causing broken links in payment notification emails. This is a high-priority operational defect that could result in recipients being unable to access their payments.

### 2. No Email Rendering Testing
No automated testing validates these templates against:
- Major email clients (Outlook, Gmail, Apple Mail, Android Gmail)
- Mobile viewport rendering
- Dark mode email client rendering
- Accessibility (screen reader compatibility)

Email clients are notoriously inconsistent in HTML rendering. The inline CSS-heavy structure of these templates suggests awareness of this issue, but without automated rendering tests (e.g., Litmus, Email on Acid), production rendering failures are detected only via cardholder complaints.

### 3. Expiry Period Inconsistency
As noted in the BA report, expiry periods vary across templates:
- 24 months (most MPV templates)
- 30 days (`virtualexpressTemplate.html`)
- Placeholder `((XX)) days` (`EAST_Email Notification_MPV_Virtual_NON-CI_DefaultCheck_Sunrise.html` line 11)

The placeholder `((XX))` in a production-committed template suggests this template may be deployed without the expiry period being substituted. If a cardholder receives an email with `((XX)) days` as the expiry language, this is:
- A consumer-facing error that may trigger CFPB complaints
- A potential Reg E disclosure violation (no clear statement of expiry terms)
- An indication that deployment review is insufficient

### 4. Hardcoded Client Names
Templates for specific clients (`choicesTemplate.html` for NAPA, `createTemplate.html` for J&J, `virtualexpressTemplate.html` for Deaconess) are stored in a shared repository. A deployment process that uses the wrong template for a client program would send a competitor's branding to another client's recipients.

### 5. No Template Lifecycle Management
No process is visible for:
- Retiring deprecated templates (who decides when to remove a template from the library?)
- Tracking which programs use which templates
- Ensuring retired templates are not accidentally re-activated

---

## Dependency on External Services

Templates reference three external domains that must maintain 100% uptime for payment access:
1. `https://login.mypaymentvault.com` — primary portal for choice/registration flows
2. `{CLIENT_URL}` — client-specific portal URL (runtime-substituted)
3. `{EMAILHEADERURL}` — branding image CDN URL

If `mypaymentvault.com` is unavailable when a recipient receives the email and clicks "Access Your Payment," the recipient cannot access funds. No fallback instruction is provided in templates beyond the manual 4-step registration process.

---

## Security Considerations in Operations

### LOGINCODE Lifetime
The operational security of the `{LOGINCODE}` token depends entirely on:
1. How long the token remains valid (not visible from this repo)
2. Whether the token is single-use (not visible)
3. Whether token usage is logged and alerted on

If `LOGINCODE` tokens are long-lived (days or weeks) and multi-use, a phishing email forwarding attack could drain multiple recipients' cards.

### Email Delivery Provider Access
The email delivery provider (likely Mailgun based on the `mailgun-event-tracker` repo in the broader codebase) has access to:
- Recipient first names
- Payment amounts
- PUID credentials
- LOGINCODE credentials

The data sharing agreement with the email provider must be reviewed to ensure PCI DSS Requirement 12.8 (third-party service provider management) and GDPR Article 28 (processor agreements) are met.

---

## Recommendations

1. **Add HTML validation CI step** — Use an HTML linter (htmlhint, html-validate) in a GitHub Actions workflow to catch unquoted attributes and syntax errors before merge
2. **Add merge token validation CI step** — Write a simple script that validates all required tokens (`{FIRSTNAME}`, `{TOTAL}`, `{PUID}` or `{LOGINCODE}`) are present in every template
3. **Fix unquoted `href` and `src` attributes** — Immediately remediate in `EAST_Email Notification_MPV_Virtual_CI_Sunrise.html` (line 13) and `createTemplate.html` (line 3)
4. **Replace `((XX)) days` placeholder** — Confirm correct expiry period and substitute before production deployment
5. **Implement template registry** — Maintain a mapping of program IDs to template names to prevent wrong-template deployments
6. **Review LOGINCODE expiry policy** — Confirm tokens expire within 24 hours; implement single-use tokens where possible
