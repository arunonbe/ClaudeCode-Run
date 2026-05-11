# Solution Architect — oneplatform-ui_LIB

## Technical Architecture
- **Language**: JavaScript (AMD/CommonJS modules via RequireJS), CSS3, HTML5.
- **Framework**: Backbone.js + Underscore.js (MVC), jQuery (implied by standard Backbone stack).
- **Module system**: RequireJS (AMD); `r.js` optimizer for production bundles.
- **CSS**: Plain CSS3; YUI Compressor for minification and aggregation.
- **Templates**: HTML templates in `src/templates/`; aggregated via Maven plugin.
- **Build**: Maven with `yuicompressor-maven-plugin` (CSS) and `requirejs-maven-plugin` (JS).
- **Fonts**: Custom fonts embedded in source: Interstate-Regular, Interstate-ExtraLight, OCRAStd, Futura.

## API Surface
This is a library — it has no API surface (no REST endpoints, no gRPC).

The JavaScript modules consume the `oneplatform-rest_API` REST API at the browser level.

## Security Posture

### Client-Side Security Issues
- **`debug: true` in `config.js`** (line 4): Enables verbose logging; may expose sensitive data in browser developer console in production. This setting must be overridden at deploy time.
- **`datasource: 'MOCKJSON'`** (line 4): The default mock data mode means if config is not overridden, no real API calls are made and no authentication occurs — catastrophic if deployed as-is.
- **No Content Security Policy** visible in `index.html` — CSP must be set via HTTP response header by the serving application.
- **No X-Frame-Options / frame-ancestors** visible in `index.html` — clickjack protection relies on the `.antiClickJack` CSS class and corresponding JS frame-buster (not yet confirmed).
- **Flash asset** (`rsa_fso.swf`): Flash is end-of-life and disabled in all modern browsers (including Chrome since 2021, Safari since 2020, Firefox since 2017). Presence in a PCI-scoped application is an audit finding. **File**: `src/rsa_fso.swf`.

### Authentication
- No authentication logic lives in this library; all authentication is handled server-side by `oneplatform-rest_API`.
- The UI passes credentials via AJAX to the API; no token storage or management is visible in the inspected source.

### Third-Party Dependencies
- **RequireJS, Backbone.js, Underscore.js**: These are old library versions (versions not pinned in the observed source); must be inventoried and scanned for CVEs.
- **YUI Compressor**: Unmaintained; potential CVEs in the Maven plugin.
- No third-party CDN dependencies visible in `index.html` — this is positive for PCI SAQ A-EP compliance as all scripts load from the same origin.

## Technical Debt
- **Entire technology stack is legacy**: RequireJS AMD, Backbone.js, YUI Compressor — all functionally deprecated in modern frontend development.
- **`config.js` hardcodes mock mode**: Must be overridden externally; no environment-aware configuration mechanism.
- **Font binaries in source** (`interstateregular.ttf`, `Interstate-ExtraLight.otf`, `OCRAStd.otf`, `Futura.ttc`): Binary files should be stored in artifact repository.
- **Flash asset** (`rsa_fso.swf`): Dead and a compliance risk.
- **`target/` directory present in source tree**: Build artifacts committed to source (`ls` output showed `target` folder).
- **No JavaScript unit tests**: No test runner configuration observed.
- **SNAPSHOT version** (`1.0.31-SNAPSHOT`): Non-reproducible artifact.
- **Parent POM `com.citi.prepaid:prepaid-parent:3`**: Very old parent carrying stale plugin management.
- **SCM URL references `northlane`**: Stale branding.

## Gen-3 Migration Requirements
1. Replace with React-based component library (`oneplatform-react_WAPP` / React migration project).
2. Remove Flash asset `rsa_fso.swf`.
3. Implement CSP headers in the serving application.
4. Set `debug: false` and remove `MOCKJSON` as a default.
5. Add Subresource Integrity (SRI) hashes if any third-party scripts are added.
6. Move font files to an artifact repository (Nexus/Artifactory).
7. Remove `target/` directory from source control.
8. Upgrade parent POM to `onbe-spring-boot-parent`.
9. Update SCM URL to current Onbe GitLab.

## Code-Level Risks (File:Line References)
| Risk | File | Line(s) |
|------|------|---------|
| `debug: true` and mock datasource in source | `src/config.js` | 3-4 |
| Flash end-of-life asset | `src/rsa_fso.swf` | N/A |
| No CSP in HTML shell | `src/index.html` | 1-30+ |
| SNAPSHOT version | `pom.xml` | 12 |
| Old Citi/Northlane parent POM | `pom.xml` | 3-7 |
| Build artifact in source control | `target/` directory | N/A |
