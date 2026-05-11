# Solution Architect — OnbeUIFramework

## Technical Architecture
- **Language / Runtime**: JavaScript (ES6 modules for OnbeStore; CommonJS for OnbeTyped, OnbeViewmodel, Onbelce; plain JS for PasswordRegExHandler).
- **No bundler / transpiler configured**: packages ship source files directly.
- **No monorepo tooling**: no shared node_modules, no workspace protocol.
- **TypeScript**: `tsconfig.json` present for PasswordRegExHandler but all implementations are `.js` files; `.d.ts` type declarations exist for Mobile packages but TypeScript source is absent.

## API Surface

| Package | Exports |
|---|---|
| `@onbeeast/password-validator` | `validatePassword(password: string): ValidationResult` |
| `@onbe/store` | `createStore`, `createInMemorySourceOfTruth`, `StoreImpl`, `InMemorySourceOfTruth`, `DefaultSerializer`, `SimpleObservable`, `SimpleSubject`, `StoreResponseLoading/Data/Error`, RxJS-compatible operators (`map`, `switchMap`, `catchError`, `startWith`, `filter`, `tap`) |
| `@onbe/typed` | `typed(item, type)` |
| `@onbe/viewmodel` | `ViewModelScope`, `useScopedViewModel` |
| `Onbelce` | `mutableLce`, `MergeLce`, `onEachSetTo`, `onEachStoreSetTo` |

## Security Posture

### Authentication / Authorization
None — these are client-side libraries.

### Cryptography
None.

### Secrets Management
None. `NODE_AUTH_TOKEN` is consumed by the CI pipeline from `secrets.GITHUB_TOKEN`.

### CVEs / Vulnerable Dependencies
- `rxjs` version not pinned in any `package.json` that declares it; consumers inherit whatever version they pull. No specific CVE risk identified at the library level.
- No lock files visible in the repo (`.gitignore` likely excludes `node_modules`); dependency resolution is non-deterministic for most packages.
- `jest: ^30.1.3` declared in `OnbeTyped/package.json` — a forward-leaning version that may not be published yet; verify availability.

### Code-Level Security Risks
- `OnbeUIFramework/Mobile/OnbeStore/src/index.js:412-417`: `DefaultSerializer.deserialize()` calls `JSON.parse()` without schema validation — if a cache key serializes to a value containing executable content and the consumer renders it as HTML, XSS is possible.
- `OnbeUIFramework/Mobile/Onbelce/src/Lce.js:9-16`: `require("@onbe/ui-framework/Mobile/OnbeStore")` wrapped in try/catch silently falls back to `rxjs/operators.tap` — this silent fallback is not logged anywhere and could mask misconfiguration.
- `OnbeUIFramework/Common/PasswordRegExHandler/src/OnbeRegExHandler.js:6`: special character regex `[!@#$%^&*()]` — excludes common characters like `-`, `_`, `+`, which may not meet all PCI DSS v4.0.1 interpretations of "special character".

## Technical Debt
1. **No test coverage for OnbeStore**: `"test": "exit 1"` — no tests at all.
2. **Custom Observable re-implementation**: OnbeStore ships its own `SimpleObservable` / `SimpleSubject` / operator set instead of using RxJS, increasing maintenance surface and creating subtle behavioral differences.
3. **Mixed module formats** across packages with no documented interoperability guidance.
4. **TypeScript source missing**: `.d.ts` files for Mobile packages suggest TypeScript was used historically but source has been replaced with compiled output.
5. **PasswordRegExHandler CI auto-bumps patch on every push**: no gate on whether the publish succeeded before tagging.

## Gen-3 Migration Requirements
1. Convert all packages to TypeScript with strict mode.
2. Adopt a monorepo tool (Nx or Yarn Workspaces) for unified build, test, and publish.
3. Replace `SimpleObservable` with RxJS directly.
4. Add comprehensive unit and integration test suites for all packages.
5. Implement CI/CD for all packages (currently only `PasswordRegExHandler` has a publish pipeline).
6. Implement the empty `Web/` module with React component primitives for Gen-3 web applications.

## Code-Level Risks (file:line references)
- `Common/PasswordRegExHandler/src/OnbeRegExHandler.js:6` — special char regex incomplete for PCI DSS compliance.
- `Mobile/OnbeStore/src/index.js:411-417` — `JSON.parse` without schema validation in `DefaultSerializer.deserialize`.
- `Mobile/Onbelce/src/Lce.js:9-16` — silent fallback from `@onbe/ui-framework` to `rxjs/operators.tap`; misconfiguration is invisible.
- `Mobile/OnbeViewmodel/src/ViewModel.js:36-38` — `console.error` for observable errors is the default handler; in production this logs to the console with no alerting.
- `Mobile/OnbeStore/package.json:7` — `"test": "exit 1"` — no tests; quality gate is absent.
