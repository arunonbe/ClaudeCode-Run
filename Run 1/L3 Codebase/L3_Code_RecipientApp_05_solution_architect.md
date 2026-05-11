# Solution Architect View — RecipientApp

## Source Availability Limitation

The `RecipientApp` repository has a `.git` directory but no checked-out working tree files. No source code, API definitions, configuration, Dockerfile, or CI pipeline files are available for analysis. This document documents the limitation and provides guidance for when source becomes available.

## API Surface

**Cannot be assessed.** No OpenAPI specification, controller classes, route definitions, or API documentation files are present in the repository working tree.

If this is a Spring Boot service, the API surface would typically include:
- Recipient registration and identity management endpoints
- DDA enrollment and validation endpoints
- Payment/disbursement status inquiry endpoints
- Possibly a webhook receiving endpoint for payment status updates

If this is a mobile application (React Native, Flutter), the "API surface" is the internal UI component architecture rather than HTTP endpoints, with the application acting as an API consumer rather than provider.

## Security Posture

**Cannot be assessed.** Without source code:
- Authentication and authorization configuration is unknown
- Input validation patterns are unknown
- Secrets management implementation is unknown
- TLS configuration is unknown
- Dependency vulnerabilities cannot be scanned

The highest-risk security concern for an application in this domain (recipient identity and DDA management) would be:
1. Insufficient authentication/authorization allowing one recipient to access another's data (IDOR vulnerabilities)
2. Insufficient input validation on DDA/routing number fields (format injection, invalid account enrollment)
3. PII exposure in logs (consistent finding across other recipient-domain services)
4. Insecure storage of OAuth tokens or API credentials on mobile devices (if mobile app)

## Critical Findings

No specific code-level findings can be cited without source. The following findings apply at the repository management level:

### Finding 1: Repository Contains No Source in Working Tree

The analysis corpus includes a shallow clone of `RecipientApp` with no working tree content. This means:
- This service is excluded from all automated code scanning (SAST, dependency scanning, secret detection) that may be applied to the full analysis corpus.
- The production codebase of this application is invisible to this assessment.
- If `RecipientApp` is a production service handling recipient PII and DDA data, its exclusion from security and compliance review is itself a material gap.

**Action**: Obtain a full working-tree checkout and re-perform all 5 analysis documents.

### Finding 2: No Evidence of CI/CD Pipeline Controls

Without a `.github/workflows/` directory, it cannot be confirmed that this repository has container scanning, CodeQL analysis, or any automated security controls in its CI pipeline. This is inconsistent with the Gen-3 standard established by `recipient-screening-api`, which includes CodeQL and container scanning.

### Finding 3: Unknown Relationship to recipient-screening-api

The two repositories (`RecipientApp` and `recipient-screening-api`) are clearly related by domain. The direction of the dependency (does `RecipientApp` call `recipient-screening-api`, or are they independent services in the same domain?) cannot be determined without source.

## Technical Debt (Inferred)

The primary technical debt item is **analysis debt**: a production service (if this is one) with no reviewed source code represents a compliance and security gap in the assessment program.

## Recommended Next Steps

1. Confirm with the owning team whether `RecipientApp` is in production, under development, or archived.
2. If in production: obtain full source checkout, re-run analysis, and apply all security scanning controls.
3. If under development: ensure all Gen-3 standards are applied from the start (OAuth 2.0 authentication, Azure Key Vault, container scanning, CodeQL).
4. If archived: confirm archival status and ensure the repository is marked as such in the enterprise repository catalog.
