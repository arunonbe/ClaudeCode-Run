# DevOps & Operations — oneplatform-ui_LIB

## Build
- **Build tool**: Apache Maven with `yuicompressor-maven-plugin 1.1` and `requirejs-maven-plugin 1.0.4`.
- **Java**: Not applicable (no Java source); Maven is used as the build orchestrator for front-end asset compilation.
- **Artifact**: JAR / WAR containing compiled static assets; `finalName` = `oneplatform-ui`.
- **CSS compilation**: YUI Compressor aggregates all `src/client/common/css/*.css` (excluding `jquery-ui.css` and `cpBranding.css`) into `cpmain.css`.
- **HTML templates**: All `src/templates/**/*.html` files aggregated into `cpmain.html`.
- **JavaScript optimization**: `r.js` (RequireJS optimizer) runs against `build.js` configuration to trace module dependencies and produce optimized bundles.
- **Release plugin**: `maven-release-plugin:3.0.0-M1` configured.
- **Wrapper**: `mvnw` / `mvnw.cmd` present.
- **No CI/CD file** found in repository root.

## Deployment
- The Maven artifact is published to a Maven repository and consumed as a dependency by the WAR project (`oneplatform_WAPP` or equivalent).
- At WAR build time, the library's compiled assets are unpacked and included in the WAR's static resource path.
- No Dockerfile — purely a library artifact, not independently deployable.
- No runtime Spring Boot context; this library has no runtime JVM process.

## Configuration Management
- `config.js` is the only runtime-configuration file; it must be overridden at deployment:
  - `datasource` must be set to `JSON` (not `MOCKJSON`).
  - `debug` must be set to `false`.
- No environment-specific property files — configuration is managed by the consuming WAR application or a JavaScript config injection mechanism at deploy time.
- `cpBranding.css.properties` suggests a properties-based CSS token substitution mechanism for affiliate-specific branding.

## Observability
- No server-side observability — this is a static asset library.
- Client-side: `debug: true` in `config.js` enables verbose JavaScript logging to browser console (should be disabled in production).
- No client-side error tracking (Sentry, Application Insights, etc.) visible in the observed files.

## Infrastructure Dependencies
- **None** at runtime — assets are served as static files by the WAR deployer (Tomcat or equivalent).
- Build-time dependencies: Maven, `r.js` (bundled in repository root), Java runtime (for YUI Compressor Maven plugin).

## Operational Risks
- **SNAPSHOT version** (`1.0.31-SNAPSHOT`): Published snapshots can be overwritten in the Maven repository, causing non-reproducible builds for consumers.
- **`config.js` mock mode**: If not overridden, the production app will use mock JSON data silently.
- **Flash asset** (`rsa_fso.swf`): Dead asset that adds confusion and potential compliance findings during PCI audits.
- **Old YUI Compressor** (v1.1): YUI Compressor is unmaintained; JavaScript minification may fail on ES6+ syntax if any modern JS is added to the library.
- **Old RequireJS Maven plugin** (v1.0.4): Similarly unmaintained; may not support modern module patterns.
- **No automated tests**: No JavaScript unit tests (Jasmine, Jest, etc.) in the observed source tree.
- **Fonts committed to source**: Binary font files (`.ttf`, `.otf`, `.ttc`) are committed directly to source — increases repo size; should be managed via an artifact repository.

## CI/CD
- No CI/CD pipeline definition file found in this repository.
- Downstream consumers must rebuild when this SNAPSHOT artifact changes.
