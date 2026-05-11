# DevOps & Operations Report — mpv (My Payment Vault)

## 1. Repository Contents and Build Tooling

The `mpv` repository as inspected contains only:
- `mock-data/` — JSON API mock responses for local development
- `mock-data/locaMockData.js` — JavaScript mock data loader
- `.github/workflows/codeql.yml` — CodeQL static analysis

There is no `package.json`, `Dockerfile`, `Makefile`, Webpack configuration, or any other build artifact in the repository at the inspected depth. This strongly suggests that either:
1. The actual front-end application code lives in a different branch or was not included in the repository snapshot, or
2. The `mpv` repository serves exclusively as the mock data provider for the front-end, with the application code in a separate repository (e.g., a `mpv-app` or `recipient-web-bff` repository).

Given the presence of `nexpay-recipientweb-bff` in the broader repository list, it is likely that MPV's backend-for-frontend (BFF) lives in that separate repository, and `mpv` is specifically the consumer-facing portal's UI mock layer or a standalone front-end repository.

## 2. CI/CD Configuration

Only one workflow is present: `.github/workflows/codeql.yml`. This workflow runs CodeQL on the codebase. For a JavaScript-heavy repository (given `locaMockData.js`), CodeQL would scan for JavaScript security vulnerabilities.

There is no deployment workflow. Without application source code or a Dockerfile, there is nothing to build or deploy from this repository. If MPV is a React/Angular SPA:
- The build output would be static assets (HTML, JS, CSS)
- Deployment would typically be to Azure Static Web Apps, Azure Blob Storage with CDN, or served via the BFF
- CI would include `npm install`, `npm run build`, and `npm test`

None of these are visible, suggesting incomplete repository content.

## 3. Mock Data Infrastructure

The `locaMockData.js` file and the directory structure suggest a **JSON Server** or **MSW (Mock Service Worker)** pattern where:
- Each directory under `mock-data/` corresponds to a feature area
- JSON files in each directory represent API response payloads for different endpoints or states
- The `locaMockData.js` loader maps URL patterns to specific JSON files for local development

This is a sound development practice that allows front-end development to proceed independently of backend readiness. However, it creates a governance risk: the mock data must stay synchronized with actual API contract changes, and currently the mock data contains values (full PAN, CVV) that should not exist in any form.

## 4. Operational Considerations

Since only mock/development infrastructure is visible:

- **Production runtime**: MPV in production is presumably a containerized SPA or server-side rendered Node.js application running on Azure Container Apps or Azure Static Web Apps, consistent with the NexPay Gen-3 deployment model.
- **CDN/edge caching**: Static front-end assets for an SPA would benefit from Azure CDN caching, but no configuration is visible.
- **Feature flags**: The `wizardSettings` and `menuSettings` in `dashboardDetails.json` mock reveal a feature flag pattern where menu items and wizard steps are conditionally enabled per affiliate. This implies a configuration service drives feature availability.

## 5. Security Scanning

The CodeQL workflow provides JavaScript/TypeScript security scanning. For a front-end application, key vulnerability categories would include:
- XSS (Cross-Site Scripting)
- Prototype pollution
- Insecure use of `eval()` or `innerHTML`
- Hardcoded secrets (the mock tokens in JSON files may generate false positive alerts)

## 6. Recommendations

1. **Rotate or replace mock tokens**: The JWTs in `login.json` are base64-decodable and will trigger secret scanning tools. Replace with obviously fake values like `MOCK_AUTH_TOKEN_12345`.
2. **Replace full PAN in mock data**: Change `cardNumber` in `dashboardDetails.json` from the current 16-digit value to a clearly test BIN value (e.g., `4111110000001234`) and add a comment marking it as test data.
3. **Remove CVV from mock data**: There is no legitimate reason for a CVV to appear in any mock response.
4. **Add a `package.json` or document the front-end technology stack**: The repository should include enough information for a developer to understand how to build and run the front-end locally.
