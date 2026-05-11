# DevOps & Operations Report — demoaccessibilitytesting

## 1. Build System

| Attribute | Value |
|---|---|
| Package manager | npm (+ optional yarn per README) |
| Framework | Create React App (react-scripts 5.0.1) |
| React version | 18.2.0 |
| Build output | `project/build/` (static assets) |
| Environment selection | `env-cmd` library switching between `.env`, `.env.qa`, `.env.stage`, `.env.prod` |

### Build Commands (from `project/package.json`)

| Command | Script | Purpose |
|---|---|---|
| `npm start` | `env-cmd -f .env react-scripts start` | Local dev (default env) |
| `npm run start-qa` | `env-cmd -f .env.qa react-scripts start` | Local dev (QA env) |
| `npm run start-stage` | `env-cmd -f .env.stage react-scripts start` | Local dev (staging) |
| `npm run start-prod` | `env-cmd -f .env.prod react-scripts start` | Local dev (prod env) |
| `npm run build` | `react-scripts build` | Production bundle |
| `npm test` | `react-scripts test` | Unit tests |

Mock server startup: `node mock-server/server-mocker.js` (port 8080)

---

## 2. CI/CD

### 2.1 GitHub Actions Workflows

| Workflow | File | Trigger |
|---|---|---|
| SPA Build + Axe Accessibility Test | `.github/workflows/axe.yml` | `workflow_dispatch` only (manual) |
| CodeQL JS | `.github/workflows/codeql-js.yml` | Push / PR |
| CodeQL | `.github/workflows/codeql.yml` | Push / PR |

### 2.2 Axe Pipeline (`axe.yml`)

```yaml
Steps:
1. Checkout repository
2. npm install --prefix ./project/
3. (optional) npm run test-headless --prefix ./project/
4. npm run build --prefix ./project/
5. npm install -g @axe-core/cli
6. axe https://mypaymentvault.qa.onbe.dev/          → default.json
7. axe https://mypaymentvault.qa.onbe.dev/activation → activation.json
8. axe https://mypaymentvault.qa.onbe.dev/registration → registration.json
9. Upload *.json as "Accessibility Test Reports" artifact
```

**Note**: The axe scans target the **live QA environment**, not the locally built application. Step 4 (npm run build) does not connect to the scan in step 6. The build artifact is unused by the scanner.

Secrets injected via GitHub secrets:
- `REACT_APP_API_BASE_URL`
- `REACT_APP_AUTH_CLIENT_ID`
- `REACT_APP_AUTH_AUTHORITY`
- `REACT_APP_AUTH_REDIRECT_URI`

---

## 3. Configuration Management

| Config File | Purpose | Status |
|---|---|---|
| `project/.env` | Default (QA) environment | **Committed to repo — risk** |
| `project/.env.qa` | QA environment | **Committed to repo — risk** |
| `project/.env.stage` | Staging environment | **Committed to repo — risk** |
| `project/.env.prod` | Production environment | **Committed to repo — risk** |

All four `.env*` files contain identical content (same reCAPTCHA key, different `REACT_APP_BASE_URL` and `REACT_APP_ENV`). None are gitignored.

Production API base: `https://external.prod.onbe.dev/mypaymentvaultapi`  
QA API base: `https://external.qa.onbe.dev/mypaymentvaultapi`  
Staging API base: `https://external.stage.onbe.dev/mypaymentvaultapi`

---

## 4. Observability

| Signal | Mechanism |
|---|---|
| Accessibility findings | Axe JSON reports published as GitHub artifacts |
| Build output | npm/React build console output |
| Unit test results | react-scripts test output (if `npm test` run) |
| No application monitoring | Not a deployed service; no APM/logging configured |

---

## 5. Infrastructure

| Component | Details |
|---|---|
| Target environment (axe scan) | `mypaymentvault.qa.onbe.dev` (live QA) |
| Static content | Azure Blob Storage `staz1recipientappqass.blob.core.windows.net` |
| Backend API | `external.{env}.onbe.dev/mypaymentvaultapi` |
| CI runner | `ubuntu-latest` (GitHub Actions) |

---

## 6. Operational Risks

| Risk | Severity | Detail |
|---|---|---|
| `.env*` files in version control | Critical | All environment config including prod API URL committed to repo |
| Axe scan hits live QA (not built app) | Medium | Build step is disconnected from test; real QA environment is scanned, not the built artefact |
| Manual-only CI trigger | Medium | Accessibility regressions go undetected on PRs |
| No `.gitignore` for `.env*` | Critical | No prevention of accidental secret commits |
| `xContent` URL mismatch in prod env | Medium | `project/.env.prod` references staging blob storage URL (`staz1recipientappqass`) |
| `CI: false` in axe.yml | Low | Suppresses React build warnings as errors; may hide real issues |
| No headless browser test in CI | Medium | `npm run test-headless` is conditional on `inputs.NPM_TEST` which is not set in workflow trigger |
