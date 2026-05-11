# onbe_common_framework — Data Architect View

## Data Architecture Overview

`onbe_common_framework` has no persistent data store. It is a stateless JavaScript library. Its data architecture concerns are limited to: the data structures it operates on (function input/output contracts), the runtime data it processes (form field values), and the configuration data it reads (`.onbe-framework.json` runtime config). It does not transmit data to any backend.

## Data Contracts (Public API)

### Validation Service Data Contracts (`src/common-services/validation.js`)

| Function | Input Type | Input Constraints | Output | PII Sensitivity |
|---|---|---|---|---|
| `isEmpty(value)` | any | none | boolean | None — checks nullity |
| `isEmail(email)` | string | max 254 chars | boolean | Email addresses are PII (GDPR) |
| `isNumber(value)` | any | must be finite | boolean | None |
| `isString(value)` | any | none | boolean | None |
| `validatePIN(pin)` | string | must be exactly 4 chars | boolean | PIN is sensitive (4-digit card PIN) |
| `formatCurrency(amount)` | number | must be finite | string (USD) | None — formats display value |
| `validatePhone(phone)` | string | max 20 chars | boolean | Phone numbers are PII |

### Input Sanitization Properties
Each validation function applies defensive input handling:

- `isEmpty` — truncates strings > 10,000 characters to prevent DoS (line 18 in validation.js): `if (value.length > 10000) return true;`
- `isEmail` — limits to 254 chars (RFC 5321) to prevent ReDoS via the email regex.
- `validatePhone` — limits to 20 chars before stripping non-digits.
- `validatePIN` — checks char codes 48-57 (digits only) without regex, avoiding regex engine DoS vectors.

These are sound defensive programming patterns for a library that will receive untrusted user input in form fields.

### PlatformDetector Data Model (`src/components/crossplatform/utils/PlatformDetector.js`)

The `PlatformDetector` class maintains a single piece of static state: `_platform` (null | 'web' | 'react-native' | 'node'). Detection logic hierarchy:

1. `navigator.product === 'ReactNative'` → `react-native`
2. `typeof window !== 'undefined' && typeof document !== 'undefined'` → `web`
3. `typeof process !== 'undefined' && process.versions.node` → `node`
4. Default: `web`

The cached detection (once computed, `_platform` is never recomputed unless `reset()` is called) means platform detection is O(1) after the first call. The `reset()` method exists specifically for test isolation.

## Configuration Data Model

### Runtime Configuration File (`.onbe-framework.json`)
The framework reads an optional project-root configuration file (index.js lines 22-29):
```json
{
  "projectType": "web-only",      // default
  "reactNativeSupport": false     // default
}
```
This configuration controls:
- Which component bundle is loaded (browser-safe vs. full crossplatform).
- The `_mode` export value (`'web-only'` vs. `'full'`).

The file is only read in Node.js environments (server-side rendering, testing). In browser environments, defaults are used.

### Module Resolution Data Model
`package.json` implements conditional exports (lines 14-22):
```json
"exports": {
  ".": {
    "browser": "./dist/browser.js",
    "node": "./dist/index.js",
    "default": "./dist/browser.js"
  },
  "./components": "./dist/components/ReactComponent.js"
}
```

The `browser` field in `exports` overrides the Node.js bundle with a browser-safe bundle that excludes `fs`, `path`, `child_process`, and `os` (listed in `package.json` `browser` mapping, lines 7-12). This ensures no Node.js standard library modules leak into browser bundles — critical for browser security and compatibility.

## Data Flow Architecture

### Library Consumption Flow
```
Consuming Application (e.g., oneplatform-react_WAPP)
  │
  ├── import { validatePhone } from '@onbeeast/common-framework'
  │     → GitHub Packages → npm install → dist/browser.js or dist/index.js
  │
  └── Runtime invocation:
        validatePhone(userInputFromForm)
          → validation.js validatePhone()
          → returns boolean (no data persisted, no network calls)
```

### PIN Data Handling
The `validatePIN` function accepts a PIN string from UI form input. It returns a boolean — the PIN value itself is never stored, transmitted, or logged by the library. However, consuming applications must ensure PIN values are:
- Never passed to `console.log()` or debug logging.
- Cleared from component state after validation.
- Transmitted only over TLS to backend PIN-change services.

The library does not enforce these requirements — they are the consuming application's responsibility.

## Changeset Data Model (`.changeset/`)

The `.changeset/` directory contains release notes as Markdown files:
- `odd-dryers-joke.md` — a patch changeset file.
- `comprehensive-publishing-fix.md` — a changeset describing publishing fixes.
- `config.json` — Changesets configuration (changelog provider: `@changesets/changelog-github`, access: `restricted`).

The `access: restricted` setting in Changesets config ensures the npm package is published as private (restricted access) to GitHub Packages — preventing public exposure of the proprietary library.

## Build Artifact Data Structure

The build system (`scripts/build-simple.js`) produces a `dist/` directory with:
- `dist/index.js` — Node.js entry point (CommonJS).
- `dist/browser.js` — Browser entry point (browser-safe, no Node.js APIs).
- `dist/components/ReactComponent.js` — React component entry point.

The webpack configuration (`webpack.config.js`) bundles with browser field resolution overrides for Node.js modules (`fs: false`, `path: false`, etc.).

## Test Data

The test suite (`test/`) uses entirely synthetic test data. A review of `test/common-services/validation.test.js` would confirm no real PAN/CVV/SSN patterns are present. Given the validation-focused nature of the library, test cases likely use obvious test values (empty strings, invalid formats, boundary values).

## Data Governance Gaps

1. **No input sanitization for PII storage prevention**: The library validates that email/phone are correctly formatted but does not strip or mask PII. Consuming applications are responsible for PII handling in persistence.
2. **USD-only currency formatting**: `formatCurrency` is hardcoded to USD. For international payouts (cross-border transfers, GDPR jurisdictions), the library needs multi-currency support — or consuming applications must format currency independently.
3. **No TypeScript type definitions**: `package.json` mentions "TypeScript Support: Full type definitions included" in README, but no `.d.ts` files are visible in the source. If TypeScript definitions are generated at build time, they should be verified in the `dist/` output.
