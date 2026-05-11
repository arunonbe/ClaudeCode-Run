# East-EmailTemplates — Enterprise Architect Report

## Platform Generation and Architectural Positioning

`East-EmailTemplates` spans multiple platform generations:

- **Gen-1 legacy templates**: `choicesTemplate.html`, `createTemplate.html`, `create_loadTemplate.html`, and `virtualexpressTemplate.html` show inline CSS patterns and naming conventions consistent with the early eCount/North Lane era
- **Gen-2 current templates**: The `EAST_Email Notification_MPV_*` series uses the "Sunrise" branding and "MyPaymentVault" (MPV) portal, which represent the current East platform's cardholder-facing brand

The repository itself appears to have been created as a consolidation point for templates that were previously embedded within applications or maintained ad-hoc. The `README.md`'s minimal content ("Sample Email Templates") suggests it is still treated as informal rather than a formally managed component.

---

## Role in the Enterprise Architecture

### Layer: Presentation / Notification
Email templates occupy the **cardholder-facing presentation layer** of the notification subsystem. They sit at the boundary between the Onbe platform and the end consumer.

```
┌────────────────────────────────────────────────────────────┐
│  Cardholder / Recipient                                    │
│  (Email inbox)                                             │
└──────────────────────────┬─────────────────────────────────┘
                           │ receives notification via
┌──────────────────────────▼─────────────────────────────────┐
│  Email Delivery Provider                                   │
│  Mailgun (mailgun-event-tracker repo exists in platform)   │
└──────────────────────────┬─────────────────────────────────┘
                           │ template + merge data from
┌──────────────────────────▼─────────────────────────────────┐
│  Notification Service Layer                                │
│  - NotificationManagerImpl (ecap-backend-process_LIB)     │
│  - NotificationServiceHelperImpl (ecore-batch_LIB)        │
│  - notification-framework_SVC (separate service)          │
│  - notification-service-client_SVC                        │
└──────────────────────────┬─────────────────────────────────┘
                           │ triggered by
┌──────────────────────────▼─────────────────────────────────┐
│  Business Event Producers                                  │
│  - ecap-backend-process_LIB (card creation events)        │
│  - ecore-batch_LIB (ACH/IEFT withdrawal events)           │
│  - xcontent_SVC (content/notification management)         │
└────────────────────────────────────────────────────────────┘
```

### Dependency Map

**Systems that depend on East-EmailTemplates:**
- All notification pathways that deliver payment access credentials to cardholders
- `ecap-backend-process_LIB` — sends card creation success/failure notifications using templates
- `ecore-batch_LIB` — sends ACH and IEFT withdrawal notifications
- `notification-framework_SVC` — likely the centralized notification orchestrator
- `xcontent_SVC` / `eccm_LIB` — content management system that may store template content

**Systems East-EmailTemplates depends on:**
- `mypaymentvault.com` — the portal URL embedded in all MPV templates
- Email delivery infrastructure (Mailgun or equivalent)
- Runtime configuration for `{CLIENT_URL}`, `{EMAILHEADERURL}` substitution

---

## Notification Architecture Assessment

### Template Storage Model (Inferred)
Based on analysis of `ecore-batch_LIB` notification helpers:
- `EventACHEmailTemplate.java` and `EventIEFTEmailTemplate.java` reference notification events by enum name (e.g., `EventACHEmailNotificationEnums.EVENT`)
- `NotificationManagerImpl` from the `cbase` business layer appears to look up templates by event name
- The actual HTML may be stored in a CMS/database table, with this git repository serving as the **source of record** for what gets loaded

This means changes to this repository must be accompanied by a database migration or CMS import step — a process that is not documented or automated.

### Template Naming vs. Event Name Disconnect
The template file names (`EAST_Email Notification_MPV_Virtual_CI_Sunrise.html`) do not follow the same naming convention as the notification event enums in the Java code (`ACH_WITHDRAWAL_COMPLETED`, `IEFT_WITHDRAWAL_FAILED`, etc.). There is no visible mapping document connecting template files to the notification event codes that trigger them.

---

## Cross-Repository Coupling

| Repository | Coupling Type | Strength |
|---|---|---|
| `ecap-backend-process_LIB` | Uses `EmailNotificationToRecipient`, `FailureNotificationToCardPurchaser` — references template event names | High |
| `ecore-batch_LIB` | `EventACHEmailTemplate`, `EventIEFTEmailTemplate` — uses notification events mapped to templates | High |
| `notification-framework_SVC` | Likely the runtime template store and delivery orchestrator | High (inferred) |
| `xcontent_SVC` / `eccm_LIB` | CMS content management — may store and serve template HTML at runtime | Medium (inferred) |
| `message-center_SVC` | Likely another notification pathway | Medium (inferred) |

---

## Multi-Rail and Multi-Brand Complexity

The template library reflects the **complexity of Onbe's multi-rail, multi-brand payment model**:

1. **Multiple payment rails**: Virtual card, physical card, ACH deposit, check — each requires different email language
2. **Multiple brands**: NAPA, J&J, Deaconess, generic Onbe/MPV Sunrise branding
3. **Multiple flows**: CI (Cardholder-Initiated) vs NON-CI, with different fallback behaviors
4. **Multiple expiry policies**: 30 days, 24 months, placeholder — each a different contractual arrangement

From an enterprise architecture perspective, maintaining 15+ separate template files for these permutations is not scalable. As Onbe adds new clients, payment rails, or regional variants, the template library will grow unbounded without a **templating framework** (e.g., Handlebars, Thymeleaf, or Jinja2) that supports shared base layouts with client/program-specific overrides.

---

## Recommended Target Architecture

### Immediate (0–3 months)
- **Centralize template registry**: Create a `template-manifest.json` or database table mapping program IDs to template file names, with version and status fields
- **Fix HTML defects**: Remediate unquoted `href`/`src` attributes and `((XX))` placeholder before next deployment

### Short-term (3–6 months)
- **Introduce base template + override pattern**: Extract the common HTML header/footer into a `base.html` and use server-side template inheritance (Thymeleaf fragments or equivalent)
- **Add CI/CD validation**: Lint, token validation, and email client preview rendering in a pipeline

### Medium-term (6–12 months)
- **Migrate to notification microservice template management**: Store templates in the `notification-framework_SVC` database with versioning, rollback, and A/B testing support
- **Implement LOGINCODE single-use enforcement**: Ensure `{LOGINCODE}` tokens expire within 24 hours and are single-use at the portal layer

### Long-term (12+ months)
- **Internationalization (i18n)**: Templates currently exist only in English (and the `ecap-backend-process_LIB` references Spanish notification events, but no Spanish templates are present in this repo). A proper i18n framework is needed for LATAM and Canadian programs.
