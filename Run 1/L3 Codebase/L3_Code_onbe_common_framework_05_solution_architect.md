# onbe_common_framework — Solution Architect View

## Technical Architecture

`onbe_common_framework` (`@onbeeast/common-framework` v1.2.6) is a stateless, universal JavaScript library with no runtime server dependency. Its architecture achieves execution in three distinct host environments from a single npm package:

```
GitHub Packages (private registry)
  └── @onbeeast/common-framework@1.2.6
        ├── dist/index.js          (Node.js / SSR entry point)
        ├── dist/browser.js        (Browser / React Native entry point)
        └── dist/components/
              └── ReactComponent.js (React component entry point)
```

The entry-point selection is controlled by:
1. `package.json` `exports` map — bundlers resolve `browser` vs `node` conditions at build time.
2. `package.json` `browser` field overrides — `./dist/index.js` → `./dist/browser.js` for browser bundlers.
3. Runtime environment detection in `src/index.js` — falls back to `window` / `process.versions.node` checks for environments that do not support conditional exports.

This triple-layered resolution strategy ensures compatibility with legacy bundlers (webpack 4, Create React App) while supporting modern conditional exports (webpack 5, Vite, Node.js 12+ ESM).

## API Surface

### Public Exports (flat namespace)

| Export | Type | Source Module |
|---|---|---|
| `isEmpty(value)` | Function | `common-services/validation.js` |
| `isEmail(email)` | Function | `common-services/validation.js` |
| `isNumber(value)` | Function | `common-services/validation.js` |
| `isString(value)` | Function | `common-services/validation.js` |
| `validatePIN(pin)` | Function | `common-services/validation.js` |
| `formatCurrency(amount)` | Function | `common-services/validation.js` |
| `validatePhone(phone)` | Function | `common-services/validation.js` |
| `validateEmail(email)` | Alias | → `isEmail` |
| `validateRequired(value)` | Alias | → `!isEmpty(value)` |
| `CrossPlatformLoader` | React Component | `components/crossplatform/loadercomponent/` |
| `PlatformDetector` | Class | `components/crossplatform/utils/PlatformDetector.js` |
| `DynamicLoader` | Utility | `components/crossplatform/utils/DynamicLoader.js` |
| `validation` | Namespace object | all validation functions grouped |
| `components` | Namespace object | all component exports grouped |
| `_config` | Object | runtime config (projectType, reactNativeSupport) |
| `_mode` | String | `'web-only'` or `'full'` |

### Sub-path Export
`@onbeeast/common-framework/components` → `dist/components/ReactComponent.js` (React-only component bundle, separate from validation-only consumers).

### No TypeScript Definitions
The package claims TypeScript support in README but ships no `.d.ts` files in source. Consuming TypeScript projects will resolve to `any` types unless definitions are generated at build time. This must be addressed before broader platform adoption.

## Security Posture

### In-Scope Data Handling
| Data Type | Function | Risk | Mitigation |
|---|---|---|---|
| Email address (PII) | `isEmail()` | Transient validation only | No storage; function is pure |
| Phone number (PII) | `validatePhone()` | Transient validation only | No storage; function is pure |
| 4-digit PIN | `validatePIN()` | Format check only | No storage; char-code comparison avoids ReDoS |
| Currency amount | `formatCurrency()` | Display formatting only | No storage; uses native `Intl.NumberFormat` |

### Security Controls Present
- **ReDoS prevention**: `isEmail` uses a length-capped (254 char) regex documented as ReDoS-safe. `validatePIN` uses char-code comparison instead of regex entirely.
- **DoS prevention**: `isEmpty` truncates values exceeding 10,000 characters. `validatePhone` caps at 20 characters before stripping non-digits.
- **SAST**: CodeQL GitHub Actions workflow (`codeql.yml`) scans JavaScript source on every push/PR.
- **Dependency vulnerability**: `npm audit --audit-level=moderate` gates every build.
- **Private registry**: Published with `access: restricted` to GitHub Packages — not publicly accessible on npmjs.com.

### Security Gaps
1. No input type assertion before char-code access in `validatePIN` — if a non-string is passed, `pin.length` and `pin.charCodeAt()` will throw. The upstream consumer is responsible for type safety.
2. No SBOM (Software Bill of Materials) generation. PCI DSS Requirement 6.3.2 requires component inventory. CycloneDX or SPDX generation should be added to the build.
3. README TypeScript claim is misleading — consumers who rely on it for type-safe handling of sensitive data (e.g., `validatePIN`) may not realise the library provides no type contracts.

## Technical Debt

| Item | Severity | Detail |
|---|---|---|
| No TypeScript source or `.d.ts` generation | Medium | README claims full TS support; not implemented |
| Backup/broken files in working tree | Low | `.backup`, `.broken`, `.clean` file variants belong in git history only |
| USD-only `formatCurrency` | Medium | Hardcoded `'USD'` — blocks international payouts adoption |
| US-only `validatePhone` | Medium | 10/11-digit US format only — blocks international recipient onboarding |
| `cleanup.bat` in repo root | Low | Windows-only cleanup script suggests some operations require manual cleanup |
| Manual publishing scripts still present | Low | `scripts/manual-release.js` etc. are fallbacks from pre-automation era |
| 2 named contributors (bus factor) | Medium | Knowledge concentration risk; no documented ownership transfer process |

## Gen-3 Migration Assessment

`onbe_common_framework` is a Gen-2 front-end library. Its Gen-3 migration path is:

1. **TypeScript migration**: Convert `src/` to TypeScript, generate `.d.ts` declarations at build time. This is the highest-value migration step — it enables all consuming Gen-3 React/Next.js applications to consume the library with type safety.

2. **Internationalization**: Extend `formatCurrency(amount, currencyCode, locale)` to accept currency code and locale parameters, maintaining backward compatibility via default `'USD'` / `'en-US'`. Extend `validatePhone(phone, countryCode)` to support E.164 validation for non-US numbers.

3. **ESM-first build**: Add an ESM output (`dist/esm/index.mjs`) alongside the CommonJS output for tree-shaking optimization in Next.js and Vite-based Gen-3 apps.

4. **React 18+ optimization**: The `CrossPlatformLoader` component should be audited for Server Component compatibility if consuming apps adopt Next.js App Router.

5. **SBOM generation**: Add CycloneDX Maven (or `@cyclonedx/cyclonedx-npm`) to CI/CD for PCI DSS 6.3.2 compliance.

## Code-Level Risks

### `src/index.js` — Conditional `require()` at Module Load
Lines 37–61 use synchronous `try/catch` around `require()` calls to load component bundles. In a browser bundler (webpack, Rollup), static `require()` calls are analysed at bundle time, so the conditional logic may not prevent all three code paths from being included in the bundle if tree-shaking is insufficient. The `browser` field override in `package.json` is the primary mitigation, but a webpack configuration error in a consuming application could result in Node.js modules being bundled for the browser.

### `PlatformDetector._platform` — Mutable Singleton State
The `_platform` property is a class-level static with a `reset()` method provided for test isolation. In SSR (Server-Side Rendering) contexts with request isolation, a stale `_platform` value could persist across requests if the module is cached (standard Node.js module caching behaviour). This is unlikely to cause a security issue but could cause platform-detection mismatches in SSR environments.

### `src/components/crossplatform/loadercomponent/CrossPlatformLoader.js` — Fallback `console.warn`
The fallback in `src/index.js` lines 55–59 creates a `CrossPlatformLoader` that calls `console.warn('CrossPlatformLoader not available')`. In production builds, console output should be stripped (via Terser `drop_console`) to avoid information disclosure in browser developer tools.

### `validate-cicd.js` in Repo Root
A script named `validate-cicd.js` exists at the repo root. If this script is inadvertently executed in CI by a misrouted command, it could produce false-positive or false-negative pipeline signals. It should be moved to `scripts/` to reduce root-level clutter and prevent accidental execution.
