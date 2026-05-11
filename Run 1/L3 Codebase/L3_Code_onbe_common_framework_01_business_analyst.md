# onbe_common_framework — Business Analyst View

## Executive Summary

`onbe_common_framework` (published as `@onbeeast/common-framework`) is a cross-platform JavaScript/React component and utility library serving as the shared foundation for Onbe East's front-end applications. It is a developer-focused inner-source product owned by the OnbeEast organization. Its primary business value is eliminating duplicated utility code across multiple front-end applications, enforcing consistent validation logic, and providing platform-adaptive UI components that work across both web (React) and mobile (React Native) surfaces.

## Business Purpose and Audience

### Primary Consumers
The framework is consumed by Onbe East's front-end application teams building:
- **Recipient Web Application** (`oneplatform-react_WAPP`, `oneplatform_WAPP`) — cardholder self-service portal
- **Client Zone** (`clientzone_WAPP`) — program sponsor administration interface
- **Mobile applications** — React Native apps (inferred from `react-native` peer dependency and `CrossPlatformLoader` component)

### Business Capabilities Delivered

| Capability | Package Export | Business Value |
|---|---|---|
| Email validation | `isEmail`, `validateEmail` | Prevents invalid email entry in recipient onboarding forms; reduces failed notification delivery |
| Phone validation | `validatePhone` | Ensures contact details are valid before account creation; US phone format (10/11 digits) |
| PIN validation | `validatePIN` | 4-digit PIN validation for card activation and secure operations |
| Required field validation | `isEmpty`, `validateRequired` | Standard form field completeness checks |
| Currency formatting | `formatCurrency` | Consistent USD display across balance, transaction, and disbursement UIs |
| String/Number type checking | `isString`, `isNumber` | Type-safe data handling in payment forms |
| Cross-platform loading indicator | `CrossPlatformLoader` | Consistent loading UX across web and mobile |
| Platform detection | `PlatformDetector` | Enables adaptive behavior for web vs. React Native vs. Node environments |

### Package Identity
- **NPM package name**: `@onbeeast/common-framework`
- **Current version**: `1.2.6` (package.json line 3)
- **Registry**: GitHub Packages (`https://npm.pkg.github.com`)
- **License**: Proprietary — "Onbe. All rights reserved" (README.md line 287)

## Validation Library — Business Rules

### PIN Validation (`validatePIN`)
Validates exactly 4 numeric digits. This maps to the standard 4-digit PIN model for Onbe prepaid cards. The implementation uses charCode comparison rather than regex — a deliberate choice for security (comment in source: "more secure than regex for simple cases").

### Phone Validation (`validatePhone`)
Accepts 10-digit US numbers and 11-digit numbers starting with country code 1. This is US-centric — international phone numbers (non-US) will fail validation. For Onbe's global payouts use case (serving GDPR, PIPEDA, Quebec Law 25 jurisdictions), this is a potential gap if the framework is used for international recipient onboarding.

### Email Validation (`isEmail`)
Uses a ReDoS-safe regex (comment: "More secure email regex that prevents ReDoS attacks") with a 254-character length limit (RFC 5321 maximum). This is a security-conscious implementation.

### Currency Formatting (`formatCurrency`)
Uses `Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' })` — hardcoded to USD. For Onbe's cross-border transfer and international payouts business, this needs to be extended for multi-currency formatting.

## Versioning and Release Management

The repository uses **Changesets** (`@changesets/cli:2.29.7`) for version management:
1. Developers add changeset files (`.changeset/*.md`) describing changes.
2. CI/CD pipeline detects changesets on merge to `main`.
3. Workflow publishes current version to GitHub Packages and creates a version-bump PR.

The `CHANGELOG.md`, `.changeset/comprehensive-publishing-fix.md`, and `.changeset/odd-dryers-joke.md` files indicate active iteration. The presence of backup files (`ci-cd.yml.backup`, `ci-cd.yml.broken`, `index.test.js.backup`, `index.test.js.clean`) suggests the CI/CD setup has been through troubleshooting cycles — a signal of a maturing but still-evolving release process.

## Organizational and Governance Observations

### Author Attribution
`package.json` identifies:
- **Author**: `Jeraldin Gerard <Jeraldin.Gerard@onbe.com>`
- **Contributor**: `Abhishek Singh <Abhishek.Singh@onbe.com>`

This small authorship footprint means the framework has limited bus-factor and knowledge distribution. Broader adoption requires more contributors and documented contribution guidelines.

### Internal Tooling Maturity
The `scripts/` directory (13 JS files) contains sophisticated publishing, validation, and workflow tooling:
- `prepare-for-publishing.js`, `manual-release.js`, `sync-published-version.js` — indicates publishing has historically been manual and complex.
- The automated CI/CD workflow (`ci-cd.yml`) replaced this manual process, but the scripts remain as fallbacks.

### Security and Compliance Posture
- No payment data (PAN, CVV, SSN) flows through or is processed by this library.
- The `validatePIN` function handles 4-digit PINs — these are short-lived UI-side values used for form entry, not stored credentials.
- The library has a `codeql.yml` workflow indicating static security analysis is applied.
- `npm audit --audit-level=moderate` runs as part of CI (ci-cd.yml line 186) — known vulnerabilities at moderate+ severity would block the build.

## Business Risk Assessment

| Risk | Severity | Notes |
|---|---|---|
| USD-only currency formatting | Medium | Limits use in international payouts applications |
| US-only phone validation | Medium | Limits use for international recipient onboarding |
| Small authorship team | Medium | Knowledge concentration risk |
| No SLA or versioning policy documented | Low | Consuming teams have no formal compatibility guarantee |
| Proprietary license with no distribution controls in code | Low | README states proprietary, but no license check enforces this in npm |
