# DevOps / Operations — react-component_LIB

## Build System

| Property | Value |
|---|---|
| Package manager | npm |
| Build tool | Babel + Webpack |
| Package name | `react-bootstrap-onbe-library` |
| Version | `0.0.2` |
| Entry point | `dist/index.js` |
| Build command | `npm run build` → `rimraf dist && babel src --out-dir dist --copy-files` |
| Bundle command | `npm run bundle` → `webpack --mode production` |
| Test command | `npm test` → `react-scripts test` |
| React version | `^18.2.0` (peerDependency) |
| React Bootstrap | `^2.7.2` (peerDependency) |
| Node.js | `^20.3.1` (devDependency) |

The library is built using Babel transpilation (not TypeScript). No type declarations are generated.

## Deployment / Publishing

| Workflow | File | Trigger | Notes |
|---|---|---|---|
| CodeQL analysis | `.github/workflows/codeql.yml` | Push, PR, weekly Saturday 18:07 UTC, `workflow_dispatch` | Delegates to `om-ci-setup codeql-auto.yml` |

There is **no publish workflow** in this repository. The library (`dist/`) is committed directly to the repository. Distribution is likely via:
- Direct GitHub repository reference in consuming apps (`"react-bootstrap-onbe-library": "github:OnbeEast/react-component_LIB"`)
- Or local file path reference
- The `package.json` has no `publishConfig` or `registry` field — npm registry publishing is not configured

The `dist/` directory is committed to version control (built artefacts in VCS).

## Configuration Management

| Configuration | Location | Notes |
|---|---|---|
| Babel config | `.babelrc`, `src/babel.config.js`, `example/babel.config.js` | Multiple Babel configs — root `.babelrc` may conflict with module-level configs |
| Webpack config | `webpack.config.js`, `example/webpack.config.js` | Two separate webpack configs |
| ESLint | `.eslintrc` | `react-app`, `react-app/jest`, `@babel/core` extends |
| Build polyfills | `webpack.config.js` | Extensive Node.js polyfills for browser (`crypto-browserify`, `stream-browserify`, etc.) |
| Environment | `.env` | File exists but is empty (1 line) |
| VS Code settings | `.vscode/settings.json` | Workspace configuration |

## Observability
None — this is a UI library. No metrics, logging, or monitoring. Application-level observability is the consuming application's responsibility.

## Infrastructure Dependencies

| Dependency | Purpose |
|---|---|
| npm registry | `node_modules` dependency resolution |
| GitHub | Source control, CodeQL |
| `om-ci-setup` | Shared CodeQL workflow |
| Consumers' hosting infrastructure | Where the built library runs |

## Key Build Dependencies

| Dependency | Version | Notes |
|---|---|---|
| `@babel/core` | `^7.23.9` | Transpilation |
| `@babel/preset-react` | `^7.18.6` | JSX transformation |
| `webpack` | `^5.82.0` | Bundling |
| `react-scripts` | `^5.0.1` | CRA test runner |
| `react-bootstrap` | `^2.7.2` | UI framework |
| `bootstrap` | `^5.2.3` | CSS framework |
| `react-router-dom` | `^6.8.1` | Client-side routing |
| `i18next` + `react-i18next` | `^22.4.10` | Internationalisation |
| `react-google-recaptcha` | `^2.1.0` | reCAPTCHA widget |
| `lodash` | `^4.17.21` | Utility functions |
| `date-fns` | `^2.29.3` | Date utilities |
| `crypto-browserify` | `^3.12.0` | Browser crypto polyfill (in webpack config) |

## Operational Risks

| Risk | Severity | Notes |
|---|---|---|
| `dist/` committed to VCS — built artefacts in source control | High | No reproducible build; VCS bloat; consumers may use stale `dist/` if build not re-run after source changes |
| No publish pipeline — no versioned release to a package registry | High | Version `0.0.2` in `package.json` but no npm publish configured; version management unclear |
| Multiple Babel configs may produce inconsistent builds | Medium | `.babelrc` at root + `src/babel.config.js` + `example/babel.config.js` |
| `react-scripts:^5.0.1` uses CRA (Create React App) — CRA is deprecated | Medium | CRA is no longer maintained; `npm test` uses CRA test runner |
| `crypto-browserify` polyfill — all crypto operations polyfilled in browser | Medium | Custom crypto in browser context; review `generate-encrypted-token.mjs` equivalent use in UI |
| `react-google-recaptcha:^2.1.0` in devDependencies — v2 API | Low | reCAPTCHA v2; consuming apps should use v3 for modern UX |
| Empty `.env` file committed | Low | No risk in isolation, but establishes a pattern that could accidentally include secrets |

## CI/CD Pipeline Summary

```
Push / PR / Weekly (Saturday)
  --> .github/workflows/codeql.yml
      --> om-ci-setup codeql-auto.yml
          --> GitHub Security alerts

Manual (developer workflow)
  npm install
  npm run build      --> dist/ (Babel transpile)
  npm run bundle     --> dist/ (Webpack bundle)
  npm test           --> react-scripts test
```
