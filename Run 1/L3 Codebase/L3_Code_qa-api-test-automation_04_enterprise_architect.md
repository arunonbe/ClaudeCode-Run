# Enterprise Architect — qa-api-test-automation

## Platform Generation
**Cross-generational testing tool** — Tests Gen-1, Gen-2, and Gen-3 services. The test artefacts themselves are generation-agnostic (Postman JSON collections); the tooling (GitHub Actions, Pynt, Newman) is modern.

## Business Domain
**Quality Engineering / Test Automation** — Horizontal capability serving all Onbe business domains. Not aligned to a specific payment product domain.

## Role in the Architecture
This repository is the **central API test artefact registry** for Onbe. It:
- Provides smoke-test gating for deployment pipelines (consumed by service deployment workflows)
- Provides security-test gating for DAST coverage
- Acts as a single collection store referenced by ~80+ service workflows
- Spans QA, Staging, and Production environments

## Scope of API Coverage

Based on workflow and collection files, the following business domains are covered:

| Domain | Representative Services |
|---|---|
| Card Management | Account Management API, Card Notification, Debit API, OM Card Management |
| Payments | Push Pay SVC, Push Provisioning SVC, Manage Payment REST API, PayPal Redemption |
| Digital Wallets | Digital Wallet Recipient SVC, Digital Token |
| Customer Service | CS API v1/v3, Customer Service REST API |
| Compliance / KYC | KYC API, Recipient Sanctioning SVC, Recipient Screening API, AML (Address Verification) |
| Communications | OTP SVC, Push Notification SVC, Communication Hub |
| Platform / Internal | East Internal Services, Geo IP, Reporting |
| Developer Portal | Dev Portal Payment V1 Preview, One Platform REST API |
| Client/Admin Tools | Client API, Activation Portal API, User Management, Compass |
| Ordering | Order Manager, Order Service, Order Synchronizer, File Order Manager |
| International | International API, DW (Digital Wallet) API |

## Integration Patterns

| Pattern | Implementation |
|---|---|
| Per-service smoke workflow | Dedicated `.github/workflows/{service}-smoke.yml` calling shared `postman-smoke-test.yml` |
| Reusable workflow composition | `postman-smoke-test.yml`, `postman-reusable-job.yml`, `pynt-security-scan.yml` — DRY pattern |
| Secret injection | GitHub Secrets passed to Newman/Pynt at workflow runtime |
| Certificate authentication | `postman-smoke-test-with-certs.yml` handles mTLS for cert-protected APIs |
| DAST security testing | Pynt scans triggered per-service with `pynt-{service}.yml` workflows |

## Key External Dependencies

| System | Role |
|---|---|
| All Onbe API services (QA/STG/PROD) | Systems under test |
| `Onbe/om-ci-setup` | Shared reusable CI workflow library |
| GitHub Actions | Execution environment |
| Newman / Postman CLI | Postman collection runner |
| Pynt | DAST security scanner |
| Azure Key Vault (referenced in related ui-test workflows) | Secret retrieval in some test scenarios |

## Strategic Status
**Active and critical.** This repository is a production dependency for Onbe's CI/CD quality gates. It is actively maintained with new service collections being added (evident from diverse service coverage). The inclusion of Pynt security scanning demonstrates alignment with PCI DSS penetration testing requirements.

## Risks to Enterprise Architecture

| Risk | Impact |
|---|---|
| Single repo covering all services — one PR can affect all test gates simultaneously | High |
| No version pinning of collections to service versions — collection may be ahead or behind deployed service | Medium |
| Wirecard legacy environments suggest incomplete cleanup post-acquisition | Medium |
| PROD environment files in VCS — risk of test-induced production data mutation | High |
| No test result archiving beyond GitHub's 90-day retention | Medium — limits trend analysis and audit evidence |
