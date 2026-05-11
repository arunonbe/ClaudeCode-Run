# Enterprise Architect — OnbeUIFramework

## Platform Generation
**Gen-1 / Gen-2** — This library's code patterns (no TypeScript strictness, CommonJS/ES6 mix, manual observable implementation rather than RxJS, MobX 6) are characteristic of Gen-1/Gen-2 frontend development. The `Web/` module is empty, suggesting the web component effort was not completed or was deferred.

The Mobile sub-packages (OnbeStore, Onbelce) are used by React Native apps (e.g., oneplatform-react_WAPP, RecipientApp), making them relevant to current generation mobile.

## Business Domain
Cross-cutting: Frontend / Mobile UI Infrastructure.

## Role in the Platform
Shared UI component and utility library consumed by Onbe cardholder-facing web and mobile applications. Functions as a design-system primitive layer (password validation, reactive state, LCE pattern) rather than a full design system.

## Known Consumers
- `@onbeeast/password-validator`: consumed by any app using Onbe password validation UI.
- `@onbe/store`: consumed by React Native mobile apps implementing the Store pattern.
- `Onbelce`: consumed by React Native ViewModels using LCE state.
- `OnbeViewmodel`: consumed by React Native components using `useScopedViewModel`.

## Dependencies
- Peer dependencies (not declared explicitly): React, RxJS, MobX.
- Published via GitHub Packages (npm registry).

## Integration Patterns
- npm / yarn package dependency.
- No API contracts; consumed via import/require.

## Strategic Status
**Mixed** — Password validator is actively published with CI. The mobile packages appear to be in use but lack CI automation. The Web module is incomplete, which is a gap if web apps need standardized components.

## Migration Blockers
1. **Empty Web module**: any Gen-3 web application that needs shared UI components cannot find them here.
2. **No TypeScript source for OnbeStore/Onbelce**: type declaration files (`.d.ts`) are present but not the TypeScript source, making the origin of type definitions opaque.
3. **MobX / RxJS peer dependency versions undeclared**: upgrading either in a consumer could silently break Onbelce / OnbeViewmodel.
4. **Manual publish for most packages**: no repeatable, auditable publish process for Mobile packages.
