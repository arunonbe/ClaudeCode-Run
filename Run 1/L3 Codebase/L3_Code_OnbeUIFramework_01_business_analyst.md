# Business Analyst — OnbeUIFramework

## Business Purpose
OnbeUIFramework is a multi-package frontend component library for Onbe's cardholder-facing and mobile applications. It provides reusable, standardized UI building-blocks shared across web and mobile platforms, reducing duplication and enforcing consistent UX patterns across Onbe products.

## Capabilities

### Common / Web
- **`@onbeeast/password-validator`** (`Common/PasswordRegExHandler`): A JavaScript / Node package that validates password complexity. Enforces minimum length 12, maximum 65, and at least 3 of 4 conditions (special chars, uppercase, lowercase, digits). Published to GitHub Packages npm registry.

### Mobile (JavaScript / ES6 modules)
- **`@onbe/store`** (`Mobile/OnbeStore`): A reactive data store implementing the Dropbox Store pattern. Provides `StoreImpl` (cache-and-fetch with observable streams), `InMemorySourceOfTruth` (in-memory key-value cache with observable change notifications), and RxJS-compatible operator set (`map`, `switchMap`, `catchError`, `startWith`, `filter`, `tap`). Designed for use in React Native or browser environments.
- **`@onbe/typed`** (`Mobile/OnbeTyped`): A tiny polymorphic factory helper — `typed(item, type)` performs a shallow copy and stamps a `type` property. Used for type-tagged union patterns in Redux-style or discriminated union architectures.
- **`@onbe/viewmodel`** (`Mobile/OnbeViewmodel`): A React lifecycle management utility for ViewModel-style patterns. Provides `ViewModelScope` (manages a composite RxJS `Subscription` and disposes on React component unmount) and `useScopedViewModel` React hook.
- **`Onbelce`** (`Mobile/Onbelce`): Loading/Content/Error (LCE) state management using MobX observables. Provides `mutableLce`, `MergeLce`, `onEachSetTo`, and `onEachStoreSetTo` utilities for binding observable streams to UI loading/error states.

### Web (placeholder)
- `Web/Readme.md` exists but contains no implementations. The Web component layer is not yet built out in this repo.

## Entities / Domain Objects
- `ValidatePasswordResult` (implicit): `{isValid, minLengthMet, maxLengthMet, conditionsMet, conditionsMetCount, conditionsNeeded}`.
- `StoreResponseLoading`, `StoreResponseData`, `StoreResponseError`: store response discriminated union types.
- `LCE` state: `{loading: boolean, content: T, error: E}`.

## Business Rules
1. Password minimum: 12 characters, maximum: 65 characters.
2. Password requires at least 3 of: special chars `[!@#$%^&*()]`, uppercase, lowercase, digits.
3. `ViewModelScope` disposes all subscriptions on component unmount to prevent memory leaks.
4. Store cache returns `EMPTY_CACHE` sentinel when no cached value exists; triggers a fresh fetch.

## Key Flows
1. **Password validation**: UI calls `validatePassword(password)` → receives structured result object → renders per-condition feedback.
2. **Data fetch with caching**: UI creates `StoreImpl` with a `Fetcher` function → calls `store.cached(key)` → subscribes to observable → receives `StoreResponseLoading`, then `StoreResponseData` (from cache or fetcher).
3. **LCE binding**: ViewModel creates an observable pipeline → passes to `onEachSetTo(lce, anyToError)` → LCE MobX state is mutated as data flows → React component re-renders reactively.

## Compliance Relevance
- Password validation rules enforce a minimum complexity policy consistent with PCI DSS Req 8 (Identify Users and Authenticate Access).
- The 12-character minimum aligns with PCI DSS v4.0.1 Req 8.3.6 requirements for user passwords.

## Risks
1. **No Web module implementations**: the `Web/` directory is empty; any consumer expecting web-specific components will find none.
2. **No versioning strategy for Mobile packages**: `@onbe/store` and `@onbe/typed` have `version: "1.0.0"` with no CI publishing workflow.
3. **Password validator allows `!@#$%^&*()` only**: other common special characters (e.g., `-`, `_`, `.`) do not count toward the special-char condition, which may surprise users.
4. **MobX and RxJS peer dependency assumptions**: `Onbelce` requires MobX and `OnbeViewmodel` requires RxJS, but neither package.json declares these as dependencies; they are assumed to be provided by the consumer.
