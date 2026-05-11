# Enterprise Architect — oneplatform-ui_LIB

## Platform Generation
**Gen-1 / Legacy Frontend** — RequireJS (AMD module system), Backbone.js MVC, Underscore.js, YUI Compressor, and jQuery-based HTML templates. This technology stack dates from approximately 2012-2015. It pre-dates React, Angular, and Vue.js. The consuming application `oneplatform-react_WAPP` (visible in the repos list) represents the Gen-3 React replacement.

## Business Domain
**Recipient Experience — Cardholder Self-Service UI (Mobile Web)**
Provides the shared UI component library for the legacy mobile web cardholder portal at `login.northlane.com/m`.

## Architectural Role
- **Shared UI component library**: CSS, JavaScript modules, and HTML templates consumed by the cardholder web application WAR.
- **Brand theming layer**: `cpBranding.css` provides per-affiliate skin customization; `cpBranding.css.properties` enables tokenized brand overrides.
- **Predecessor to React**: The existence of `oneplatform-react_WAPP` in the repo list indicates this library is being actively replaced.

## System Dependencies
| System | Direction | Notes |
|--------|-----------|-------|
| `oneplatform_WAPP` (WAR deployer) | Consumer | Includes this library's compiled assets |
| `oneplatform-rest_API` | Runtime API backend | AJAX calls from JavaScript modules |
| Maven repository | Build-time | Artifact published and consumed |

## Integration Patterns
- **Maven artifact distribution**: Library compiled to JAR/WAR and distributed via Maven; not a CDN or NPM package.
- **RequireJS AMD modules**: All JavaScript organized as AMD modules with explicit dependency declaration.
- **Backbone.js MVC**: Views, models, and routers follow Backbone conventions.
- **Mock data injection**: `datasource: 'MOCKJSON'` enables local development without API dependency.

## Strategic Status
- **Legacy / Sunset pending**: The `oneplatform-react_WAPP` repository indicates active migration to a React-based UI.
- This library is still deployed in production (implied by the complete CSS structure and build pipeline).
- SNAPSHOT version suggests ongoing maintenance but not active feature development.
- Parent POM `com.citi.prepaid:prepaid-parent:3` references the Citi/Wirecard-era parent — a historical artifact.
- SCM URL references `gitlab.com/northlane` — pre-Onbe branding.

## Migration Blockers
1. **RequireJS AMD architecture**: Must be completely rewritten for any modern module system (ESM, webpack, Vite).
2. **Backbone.js views**: All UI logic must be migrated to React (or equivalent) components.
3. **YUI Compressor**: Does not support ES6+; any JavaScript modernization requires replacing the build toolchain.
4. **Flash asset** (`rsa_fso.swf`): Must be removed and replaced with a pure JavaScript equivalent before migration can be certified.
5. **Per-affiliate CSS branding** (`cpBranding.css.properties`): The branding customization mechanism must be replicated in the new React component library (`oneplatform-ui_LIB` React equivalent or similar).
6. **Northlane/Citi branding in source**: All `northlane.com` URLs, Citi parent POMs, and legacy SCM URLs need cleanup.
