# Data Architect — react-component_LIB

## Data Stores

This repository contains no backend data stores. It is a pure UI component library. Data artefacts present:

| Artefact | Location | Description |
|---|---|---|
| Client theme configuration | `example/public/clientColor.json`, `example/src/assests/clientColor.json` | JSON file defining per-client colour palette for theming |
| Country/State data | `example/src/assests/CountryState.json` | Static reference data for form dropdowns |
| Library component manifest | `example/src/assests/ReusableComponent.json` | Component catalogue/metadata |
| Library demo data | `example/src/assests/librarydata.js` | Static demonstration data for example app |

No runtime databases, Redis, or external data services are used by this repository.

## Schema / Data Structures

### `clientColor.json` Structure (inferred)
Per-client theming configuration — JSON object with CSS variable overrides (primary colours, fonts, border radii). Not directly sensitive.

### Component Props Schema
Components define `PropTypes` validation (e.g., `ButtonComponent.propTypes`). No JSON schema or OpenAPI spec is generated.

## Sensitive Data

| Data Class | Location | Risk |
|---|---|---|
| Login form credentials (username, password) | `LoginSection.js` — React state `form` | Transient browser state only; never persisted by this library |
| Card number in `LoginSection` (via `cardnumber` state) | `LoginSection.js:19, 111–113` | Card number entered in login form stored in React state — must not be logged |
| Password in component state | `LoginSection.js` — `form["_login-password"]` | Browser state only; not transmitted by library directly |
| Client branding assets | `public/images/`, `example/public/images/` | Brand logos including T-Mobile assets — IP concern |

No PAN, CVV, or other CHD is processed, stored, or transmitted by this library as a library. However, the `LoginSection` composite component accepts card number input (`cardnumber` state field) which is then passed to `TextboxComponent` with `typefield="mobile"` — this flow must be reviewed by consuming applications to ensure card numbers are not logged.

## Encryption

Not applicable — this is a UI component library. Encryption of data in transit and at rest is the responsibility of the consuming application and backend services.

## Data Flow

```
Browser user interaction
  --> React component state (useState hooks)
      --> Form field values (username, password, card number) held in memory only
          --> onClick/onSubmit handlers in consuming application
              --> Application-layer authentication/API calls (out of scope for this library)
```

The library itself does not make any API calls, HTTP requests, or network operations. All data handling beyond browser state is delegated to the consuming application.

## Data Quality / Retention

| Concern | Detail |
|---|---|
| No input sanitisation at component level | Components pass `e.target.value` directly; XSS prevention is the consuming application's responsibility |
| `countryState.json` — static reference data | Must be kept current with valid country/state codes |
| `clientColor.json` — no schema validation | Invalid colour values would silently fail CSS variable application |

## Compliance Gaps

| Gap | Standard | Impact |
|---|---|---|
| `LoginSection` card number state (`cardnumber`) — not masked in component state | PCI DSS Req 3.3 | Card number is stored in plain React state while user types; masking should occur at component level |
| Login validation commented out | PCI DSS Req 8 (consuming app) | Incomplete client-side validation allows empty credential submission — consuming app must enforce server-side |
| No CSP (Content Security Policy) headers | PCI DSS Req 6.4 | CSP must be set at the hosting layer; library does not configure it |
| T-Mobile and other brand assets included | IP/Legal | Licensing must be verified for each brand asset set |
