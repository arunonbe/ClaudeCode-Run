# DevOps / Operations — OnbeUIFramework

## Build System
- No monorepo build orchestrator (no Lerna, Nx, Yarn Workspaces, or Turborepo configuration at the root).
- Each sub-package is independently managed:
  - `Common/PasswordRegExHandler`: npm, `package.json` present. `tsconfig.json` present but the main file is plain JS.
  - `Mobile/OnbeStore`: npm, `package.json` (type: `module`, no test script configured — `exit 1`).
  - `Mobile/OnbeTyped`: npm / yarn, uses `jest` for tests, `packageManager: yarn@4.9.2`.
  - `Mobile/OnbeViewmodel`: npm, depends on `rxjs` and `react`.
  - `Mobile/Onbelce`: npm, depends on `mobx` and `rxjs`.

## CI/CD Pipeline

### Password Validator (only automated pipeline)
- `.github/workflows/publish-password-validator.yml`: triggers on push to `main` or PR affecting `Common/PasswordRegExHandler/**`.
- Steps: checkout → Node 18 setup → `npm ci --ignore-scripts` → `npm version patch --no-git-tag-version` → `npm publish` (GitHub Packages) → Git tag and push.
- `NODE_AUTH_TOKEN: ${{ secrets.GITHUB_TOKEN }}` used for publishing.

### All Other Packages
- No CI/CD pipeline exists for `OnbeStore`, `OnbeTyped`, `OnbeViewmodel`, or `Onbelce`. Publishing is manual.

### CodeQL
- `.github/workflows/codeql.yml` present (content not separately read; assumed to be standard Onbe CodeQL workflow).

## Config Management
- No runtime configuration. Consumer applications configure these libraries at import time.
- `tsconfig.json` in `PasswordRegExHandler` uses default settings (no strict mode or explicit targets).

## Observability
- None. These are frontend libraries.

## Infrastructure Dependencies
- GitHub Packages npm registry for publishing.
- Node 18 runner for CI.

## Operational Risks
1. **No CI for most packages**: OnbeStore, OnbeTyped, OnbeViewmodel, Onbelce have no automated test or publish pipelines. Version management and quality control are entirely manual.
2. **OnbeStore has no tests** (`"test": "echo \"Error: no test specified\" && exit 1"`).
3. **Yarn 4 packageManager pin on OnbeTyped**: consumers must use Yarn 4.9.2 or risk lock file conflicts.
4. **Password validator auto-bumps patch version on every `main` push**: with no test gate beyond a single integration call, broken builds could publish to GitHub Packages.
5. **Mixed module systems**: OnbeStore uses ES6 `export`, OnbeTyped uses CommonJS `module.exports`, OnbeViewmodel uses CommonJS — consumers must handle interop.
