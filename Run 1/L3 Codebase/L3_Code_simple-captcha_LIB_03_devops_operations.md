# simple-captcha_LIB — DevOps / Operations View

## Build System
- **Apache Ant** (`build.xml`) — not Maven. This is the original open-source build system.
- Java 1.6 source/target (`<javac source="1.6" target="1.6">`).
- Build targets: `build-project`, `build-jar`, `j2ee-example` (WAR), `javadocs`.
- Dependencies (local `lib/` directory):
  - `lib/imaging.jar` — custom image processing library (bundled into final JAR).
  - `lib/jstl-1.2.jar` — JSTL for JSP examples.
  - `lib/standard.jar` — JSTL standard tag library.
  - `lib/simplecaptcha-latest.jar` — pre-built library copy.
- Output: `dist/simplecaptcha-1.2.1.jar` — committed to source control.
- Servlet API sourced from `${env.CATALINA_HOME}/lib/servlet-api.jar` — requires Tomcat on build machine.

## CI/CD Pipelines
**None.** No GitHub Actions, no GitLab CI, no Jenkins configuration. The repository has no CI/CD pipeline.

There is also no `.github/` directory — no Dependabot, no CodeQL scanning, no automated security analysis. This library is completely unscanned by automated tooling.

## Config Management
- No external configuration files. All parameters (CAPTCHA dimensions, TTL) are configurable via servlet `<init-param>` entries in the embedding application's `web.xml`.
- No Spring/Spring Boot integration in the library itself.

## Observability
None. No logging framework used in the CAPTCHA library code — no Log4j, no SLF4J, no JUL.

## Infrastructure Dependencies
| Dependency | Notes |
|---|---|
| Tomcat (any version with javax.servlet) | Runtime container; servlet-api from `$CATALINA_HOME` |
| `imaging.jar` | Local library — provenance unclear, bundled in repository |

## Operational Risks
- **No security scanning** — no CodeQL, no Dependabot, no SAST. Vulnerabilities in the library are undetected.
- **Compiled binaries committed**: `bin/` directory contains `.class` files; `dist/` contains the JAR. These should not be in source control — creates confusion about which version is authoritative.
- **Ant build requires `$CATALINA_HOME`** — not reproducible without Tomcat installed; no Maven wrapper alternative.
- **Java 1.6 target** — compiled bytecode may not run on newer JVMs if newer class file features are needed, though backwards compatibility means it likely runs on Java 8–21.
- **`imaging.jar` provenance unknown** — this bundled JAR has no version or source indicated. If it contains vulnerabilities, they cannot be tracked via dependency scanning.
- **No test automation** — test classes exist (`MixerTest`, `StickyCaptchaServletTest`) but are not wired into the build process.

## Deployment
This library is deployed by embedding the JAR in the consuming web application's WEB-INF/lib. No standalone deployment.
