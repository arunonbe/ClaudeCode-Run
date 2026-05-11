# DevOps / Operations View — oneplatform-react_WAPP

## Build System

- **Package manager**: npm (Node.js)
- **Bundler**: Webpack 5 with separate config files per environment (`webpack.config.qa.js`, `webpack.config.stage.js`, `webpack.config.prod.js`)
- **Transpiler**: Babel 7 (`@babel/core`, `@babel/preset-env`, `@babel/preset-react`)
- **Test runner**: Jest with `jest-environment-jsdom`; `@testing-library/react` for component tests
- **Environment injection**: `env-cmd` reads `.env.*` files at build time; `dotenv-webpack` embeds values into bundles
- Root `package.json` wraps the inner `project/` SPA; `postinstall` script auto-installs the inner package

## CI/CD Pipeline

- **Platform**: GitHub Actions
- **Workflow file**: `.github/workflows/oneplatform-react_WAPP.yml`
- **Reusable workflow**: `Onbe/om-ci-setup/.github/workflows/spa-workflow.yml@feature/IN-9108-inverse-aks`
- **Triggers**: push to `master`, pull request (open/sync/label), `workflow_dispatch`
- **Parameters passed**:
  - `APP_NAME: mypaymentvault`
  - `BUILD_BY_ENV: true` — builds separate artifacts per environment
  - `JEST_COVERAGE: true` — enforces test coverage gate
  - `INVERSE_DEPLOY_ORDER: true` — deploys to production before lower environments (unusual; verify intent)
- **Secrets**: inherited from org-level secrets; no secrets hardcoded in workflow YAML
- **CodeQL**: separate `.github/workflows/codeql.yml` for static security analysis (JavaScript)

## Deployment Model

- **Runtime**: Static SPA deployed as container to Azure Kubernetes Service (AKS)
- **Artifact type**: Webpack-bundled static files served via container (likely nginx or similar)
- **Environment progression**: dev → qa → stage → prod (with inverse deploy order per workflow config)
- **No WAR/JAR**: Pure frontend; no JVM runtime

## Runtime Configuration

- Node.js (version not pinned in `package.json`; recommend pinning in `.nvmrc` or engine field)
- `react-scripts` 5.x (Create React App) is used for the `start` dev server; production builds use Webpack directly
- `webpack-dev-server` 5.x for local development

## Secrets Management

- Environment-specific `.env.*` files in repository — these files are present in the repo tree (`project/.env`, `project/.env.qa`, `project/.env.stage`, `project/.env.prod`). **Risk**: If these files contain API keys or tokens they will be bundled into the JavaScript artifact and visible to any user inspecting the bundle. Secrets must be moved to GitHub Actions secrets or Azure Key Vault and injected at CI build time only.
- No Azure Key Vault or secret manager integration observed in the SPA layer itself

## Observability

- **Mixpanel**: user behavior analytics (events, funnels) — third-party SaaS
- **No structured logging** from the SPA to a SIEM or log aggregator (expected for a static SPA)
- **No health/readiness endpoints** — these are provided by the AKS ingress and hosting container
- Error boundaries and error state components handle UI failures but errors are not observed being shipped to a centralized error tracking service (e.g., Sentry, Azure Application Insights) in available source

## Known EOL Runtimes and Risks

- `react-scripts` 5.x (Create React App) is community-deprecated; the Create React App project is no longer actively maintained. Migration to Vite or Next.js is recommended.
- `jest-environment-jsdom` version pinned at `^27.5.1` while other testing dependencies target `^16.x`; this version mismatch can cause flaky test behavior.
- `INVERSE_DEPLOY_ORDER: true` in the CI workflow means production receives deployments before QA/stage complete validation — this is a high-risk configuration requiring confirmation that it is intentional.
- Node.js version is not pinned; CI runner version drift can cause non-reproducible build failures.
