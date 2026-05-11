# 03 DevOps & Operations — embedded-payments-sdk

## Build System

- Build tool: **Vite 5** with TypeScript 5.9
- Package manager: **npm** (`package-lock.json` present)
- Package type: `"type": "module"` (ESM)
- Version: `0.0.0`
- Private package: `"private": true` — not published to npm registry

Build commands (`package.json` lines 6–12):
```bash
npm run dev               # Vite dev server for sandbox
npm run build             # Build all three artefacts
npm run build:widget      # Build widget SPA
npm run build:shim        # Build shim.js
npm run build:sandbox     # Build sandbox portals
```

Each build runs `tsc` (TypeScript compilation) first, then Vite for bundling.

## Build Artefacts

| Command | Config | Output | Destination |
|---|---|---|---|
| `build:widget` | `vite.config.widget.ts` | `dist/widget/` | Copied to `embedded-payments-api/src/main/resources/static/` via CI |
| `build:shim` | `vite.config.shim.ts` | `dist/shim/` | Partner CDN deployment |
| `build:sandbox` | `vite.config.sandbox.ts` | `dist/sandbox/` | Developer/partner testing |

## Dependencies

`package.json`:

| Package | Type | Version | Purpose |
|---|---|---|---|
| `axios` | runtime | `^1.13.5` | HTTP client for widget API calls |
| `@types/node` | dev | `^25.2.0` | Node.js type definitions |
| `@vitejs/plugin-basic-ssl` | dev | `^1.1.0` | Local HTTPS for dev server |
| `cross-env` | dev | `^10.1.0` | Cross-platform env vars |
| `sass` | dev | `^1.97.3` | SCSS stylesheet compilation |
| `typescript` | dev | `^5.9.3` | TypeScript compiler |
| `vite` | dev | `^5.0.0` | Build tool and dev server |

### Dependency Overrides (`package.json` lines 22–26)

| Package | Pinned Version | Reason |
|---|---|---|
| `immutable` | `5.1.5` | Security/compatibility override |
| `rollup` | `4.59.0` | Vite underlying bundler pin |
| `qs` | `6.14.2` | Query-string library CVE fix |

## CI/CD Pipelines

### `.github/workflows/deploy-widget.yml` — Widget Deployment
- Trigger: push to `main` branch
- Runner: `ubuntu-latest`
- Steps:
  1. Checkout SDK repo
  2. Setup Node.js 20
  3. `npm ci` (clean install)
  4. `npm run build:widget`
  5. Clone `OnbeEast/embedded-payments-api` backend repo
  6. Create feature branch: `feature/APEX-1_UI-assets-{timestamp}`
  7. Copy `dist/widget/*` to `embedded-payments-api/src/main/resources/static/`
  8. Commit with message: `chore: update widget assets [skip ci]`
  9. Push branch to backend repo (creates PR for review)

This pipeline creates a pull request in `embedded-payments-api` on every widget merge, ensuring the widget assets are tracked through the backend's code review process before deployment.

### `.github/workflows/deploy-shim.yml`
Similar pipeline for shim deployment to CDN or backend.

### `.github/workflows/deploy-sandbox.yml`
Deploys sandbox portals for partner testing.

### `.github/workflows/codeql.yml`
GitHub CodeQL static analysis (JavaScript/TypeScript). Runs on schedule and `workflow_dispatch`.

## Environment Configuration (`.env.example`)

The `.env.example` file documents required environment variables for the Vite build:

| Variable | Purpose |
|---|---|
| `VITE_WIDGET_URL` | URL of the widget SPA load endpoint (`/embedded/shim/load-spa`) |
| `VITE_DEV_MODE` | `"true"` enables dev-mode header auth bypass |

## Operational Deployment Model

The SDK delivers browser-side JavaScript artefacts with no server-side runtime. Operations are:

1. **Widget build** → committed to `embedded-payments-api/src/main/resources/static/` → deployed as part of the Spring Boot WAR/JAR
2. **Shim build** → deployed to a CDN (likely Azure CDN) → partners reference `<script src="https://cdn.onbe.com/...">` in their pages
3. **Sandbox build** → deployed to a staging URL for partner integration testing

## DEPLOYMENT_STRATEGY.md and WORKFLOW.md

Two documentation files at the repo root document the deployment strategy and developer workflow respectively. These provide operational context for the CI/CD integration between the SDK and backend repo.

## Security in the Build Pipeline

The `deploy-widget.yml` workflow stores `API_TOKEN_GITHUB` in GitHub Secrets (`secrets.API_TOKEN_GITHUB`). This token is used to push to the backend repository. It must have minimal required permissions (contents:write on the target repo only, no admin rights). Periodic rotation should be enforced.
