# Business Analyst View — RecipientApp

## Source Availability Limitation

The `RecipientApp` repository contains only the `.git` directory with no working tree files (source code, configuration, build files, or README). The repository is a shallow clone with two pack files but no checked-out content. All analysis in this document is therefore based on the repository name, the context of its position in the NexPay/Onbe Gen-3 recipient-side platform, and cross-domain knowledge from related repositories (particularly `recipient-screening-api`).

## Inferred Business Purpose

Based on the repository name and its presence alongside `recipient-screening-api` in the Onbe codebase, `RecipientApp` is most likely one of the following:

1. **A recipient-facing web or mobile application** — a front-end or BFF (Backend for Frontend) application that provides recipients of Onbe disbursements with an interface to view payment status, register banking information (DDA), or manage their payout preferences.
2. **A recipient management backend** — an API service that manages recipient registration, identity, and DDA enrollment in the NexPay platform, serving as the upstream system that feeds `recipient-screening-api`.
3. **A mobile application** — a consumer-facing mobile app (React Native, Flutter, or native iOS/Android) for payment recipients to track and receive disbursements.

Given the NexPay context and the `RecipientApp` (capitalized, no hyphen) naming convention consistent with mobile or SPA applications in the Onbe ecosystem, option 1 or 3 is most probable.

## Inferred Capabilities

If this is a recipient-facing application:
- Recipient registration and identity verification (name, address, DOB, email, phone)
- DDA (bank account) enrollment for ACH payouts
- Payment status tracking (payout initiated, processed, received)
- Sanction screening status visibility (if a disbursement is blocked, the recipient may see a status message)
- Prepaid card activation and balance inquiry (if the disbursement instrument is a prepaid card)

## Client and Cardholder Impact

If the inferred purpose is correct, this application is a direct cardholder/recipient touchpoint. Any availability or usability failure directly prevents recipients from enrolling their payment information, tracking disbursements, or receiving funds. This has direct Reg E implications (right to timely access to funds).

## Regulatory Obligations

If this application handles recipient registration:
- **GLBA**: Recipient financial information (DDA, routing number) is collected and must be safeguarded.
- **GDPR/CCPA**: PII collection (name, DOB, address, email, phone) for EU and US residents requires consent, data minimization, and retention controls.
- **Reg E**: If the application facilitates enrollment for electronic funds transfers, Reg E disclosures and error resolution procedures apply.
- **PCI DSS**: If any card data flows through the application, PCI DSS scope must be assessed.

## Key Business Risks

1. **No source available for analysis**: The repository's empty working tree means no compliance or security assessment of actual code is possible. This is a process gap — if this is a production service, its absence from the analysis corpus is itself a risk.
2. **Unknown regulatory scope**: Without source code, it is impossible to determine what data is collected, how it is stored, or whether appropriate security controls are implemented.

**Recommendation**: Obtain a fully checked-out clone of this repository and perform a complete analysis before any production assessment sign-off.
