# Business Analyst — qa-api-test-automation

## Business Purpose
A centralised repository of **Postman API test collections and environments** for Onbe's entire API portfolio, plus a small set of GitHub Actions workflows that execute those tests as automated CI/CD smoke and security gates. This repo is the single source of truth for API test artefacts across QA, staging, and production environments.

## Capabilities

| Capability | Mechanism | Description |
|---|---|---|
| API smoke testing | Postman collections + Newman / GitHub Actions | Validates that deployed APIs are reachable and returning expected responses |
| API security scanning | Pynt security scan workflows | Automated DAST/API security testing against deployed endpoints |
| Multi-environment execution | Postman environment files (QA / STG / PROD per service) | Same collection executed against different environments via environment file swap |
| Encrypted token generation | `scripts/generate-encrypted-token.mjs` (Node.js) | Generates AES-256-GCM encrypted tokens for Decagon API authentication in tests |
| Certificate-based API testing | `postman-smoke-test-with-certs.yml`, `pynt-security-test-with-certs.yml` | mTLS-authenticated test execution |

## Services Under Test

The repository covers tests for the following Onbe services (from `collections/` and `environments/` directory):

| Service | Collection |
|---|---|
| Account Management API | `account-management-api_API.json` |
| Activation Portal API | `ActivationPortalApi Automation*.json` |
| Card Notification (RESTful) | `card-notification-restful_API.json` |
| Client API | `clientapi_API.json` |
| CS API v1, v3, v3-payout | `cs-api-v*.json` |
| Customer Service REST API | `customer-service-rest-api.json` |
| Debit API | `debit-api_API.json` |
| Decagon Chat API | `om-decagonchat-api.json` |
| Developer Portal Payment V1 Preview | `DevPortalAndApis.PaymentV1Preview.Api.json` |
| Digital Wallet Recipient SVC | `OmDigitalWalletRecipientSvc.postman_collection.json` |
| Digital Token | `DigitalTokenCollection.postman_collection.json` |
| East API (internal services) | `east-internal-services.json` |
| File Order Manager | `file-order-manager-controller-rest-api.postman_collection.json` |
| Geo IP Service | `geo-ip-service.postman_collection.json` |
| KYC API | `KYCAPI*.json` |
| Manage Payment REST API | `manage-payment-rest-api.json` |
| OM Card Management SVC | `om-cardmanagement-svc.json` |
| OM Check SVC | `om-check-svc.postman_collection.json` |
| OM Client Cards API | `om-client-cards-api.json` |
| OM Compass | `OmCompass.postman_collection.json` |
| OM CPM SVC | `om-cpm-svc.postman_collection.json` |
| OM Merchant Enrichment SVC | `om-merchantenrichment-svc.json` |
| OM OTP SVC | `om-otp-svc.postman_collection.json` |
| OM PayPal Redemption SVC | `om-paypalredemption-svc.postman_collection.json` |
| OM Push Notification SVC | `om-pushnotification-svc.json` |
| OM Push Pay SVC | `om-pushpay-svc.postman_collection.json` |
| OM Push Provisioning SVC | `om-pushprovisioning-svc.postman_collection.json` |
| OM Redemption SVC | `om-redemption-svc.postman_collection.json` |
| OM Reporting SVC | `om-reporting-svc.postman_collection.json` |
| One Platform REST API | `oneplatform-rest_API.json` |
| Order Manager / Service / Synchronizer | `order-*-controller-rest-api.postman_collection.json` |
| OTP Service | `OTPService_AutomationSuite.postman_collection.json` |
| Push Payment API | `Push Payment API*.json` |
| Recipient Sanctioning SVC | `RecipientSanctioningSVC_AutomationSuite.postman_collection.json` |
| Recipient Screening API | `recipient-screening-api.postman_collection.json` |
| User Management / Promotions | `usermanagement-promotions-hierarchy-roles-reports.json` |
| Address Verification SVC | `om-addressverification QA.postman_collection.json` |
| International API | `InternationalAutomation.postman_collection.json` |
| Balance Inquiry | `Balance Inquiry-STBR.postman_collection.json` |
| West API | (referenced in workflows) |
| DW API | `DW_Api_QA_Smoke_Test_Suite.postman_collection.json` |
| Crypto Decryptor API | `CryptoDecryptor_API_QA_STG_PROD.postman_collection.json` |

## Key Entities

| Entity | Description |
|---|---|
| Postman Collection | JSON file defining API requests, pre-request scripts, test assertions |
| Postman Environment | JSON file containing environment-specific variables (base URLs, API keys, tokens) |
| GitHub Actions Workflow | YAML file triggering collection execution (smoke or security) |
| Encrypted token | AES-256-GCM encoded payload for Decagon API authentication |

## Business Rules
1. Collections are executed against QA, STG, and PROD environments using separate environment files.
2. Security scans (Pynt) run as separate workflow triggers from smoke tests.
3. Certificate-based tests require mTLS credentials (injected via GitHub Secrets).
4. Encrypted token generation requires `DECAGON_ENCRYPTION_KEY_BASE64` as a 32-byte base64-encoded key.
5. Email notifications for test results are restricted to `@onbe.com` domain addresses only (enforced in playwright-test.yml; logic exists in that adjacent repo).

## Compliance Relevance

| Standard | Relevance |
|---|---|
| PCI DSS Req 6.2 / 6.3 | Smoke tests provide post-deploy validation; security scans (Pynt) provide DAST coverage |
| PCI DSS Req 11.3 | Pynt security scanning provides automated penetration-test-like coverage of API endpoints |
| SOC 2 (Availability) | Smoke tests confirm service availability after deployment |

## Business Risks

| Risk | Severity | Notes |
|---|---|---|
| Postman environments may contain real credentials/tokens | High | Environment JSON files are version-controlled; must verify no secrets committed |
| Collections span PROD environment — test errors may affect production data | High | PROD environment files present; test isolation required |
| No test result archiving or trending visible in this repo | Medium | Results exist per-run in GitHub Actions artefacts but no persistent dashboard |
| Wireless/legacy environment files (Wirecard domains) present | Medium | `p-app01.nam.wirecard.sys.json` etc. — may reference decommissioned systems |
