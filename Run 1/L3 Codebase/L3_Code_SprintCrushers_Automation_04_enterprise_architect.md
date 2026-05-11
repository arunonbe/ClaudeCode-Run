# SprintCrushers_Automation — Enterprise Architect View

## Platform Generation
**QA / Test tooling — Not applicable to Gen classification.** This repository is a test automation suite, not a business application service. It tests Gen-2 services (the Account Management API is a SOAP/JAX-WS service consistent with Gen-2 architecture). The tooling itself is Node.js/Newman (modern stack).

## Business Domain
Quality Assurance — Account Management API testing. Specifically:
- Multi-country prepaid account creation validation
- UAT smoke/regression testing for the `createAccount` SOAP operation

## Role in Ecosystem
| Role | Description |
|---|---|
| QA validation | Validates that the Account Management API creates prepaid accounts correctly across all supported countries |
| Release gate | Designed to run on CI/CD push/PR — intended as a quality gate before merges to main |
| Operations notification | Posts test results to Microsoft Teams for team visibility |
| Report publishing | Publishes HTML test reports to GitHub Pages for stakeholder access |

## Dependencies
| Dependency | Type | Notes |
|---|---|---|
| Account Management API (`com.citi.prepaid.accountmanagementapi`) | Runtime test target | SOAP/JAX-WS endpoint at `webservice-uat.mypaymentadmin.com:4005` |
| Newman (Postman CLI runner) | Test execution | `^6.0.0` |
| Microsoft Teams / Graph API | Notification delivery | Optional Teams integration |
| GitHub Pages | Report hosting | Optional |

## Integration Patterns
| Pattern | Implementation | Notes |
|---|---|---|
| SOAP/HTTP test execution | Newman with XML body templates | Postman collection drives SOAP calls |
| Webhook notification | HTTPS POST to Teams webhook | Adaptive Card format |
| OAuth2 client credentials | Azure AD token endpoint | For Graph API file upload |
| CI/CD artifact publishing | GitHub Pages | HTML report hosting |

## Strategic Status
| Dimension | Assessment |
|---|---|
| Maturity | Early / practice stage — described as a "playground" |
| Strategic value | Medium — validates a business-critical API (account creation) across multi-country scenarios |
| Alignment with QA strategy | Consistent with Newman-based API testing patterns used elsewhere in the Onbe estate |
| Gap | GitHub Actions workflow file (`.github/workflows/postman-tests.yml`) is missing — the CI gate does not exist |
| Recommended action | Add the missing workflow; add PAN/account masking to reports; formalise as a release gate for Account Management API |

## Migration Blockers
Not applicable — this is a test tooling repository, not a service to migrate. If/when the Account Management API migrates from SOAP to REST (Gen-3), the Postman collection will need to be replaced with REST-based request definitions.
