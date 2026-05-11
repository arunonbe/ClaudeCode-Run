# Solution Architect — test-east-deploy-multiple

## Technical Architecture
- **Runtime**: Spring Boot 3.4.2 embedded Tomcat (WAR packaging for external servlet container deployment; `SpringBootServletInitializer` is extended in both `AppAApplication` and `AppBApplication`)
- **Module layout**: Multi-module Maven project. Parent POM declares Java 21, Spring Boot 3.4.2. Child modules `app-a` and `app-b` declare `<packaging>war</packaging>` with Tomcat as `provided`.
- **Context paths**: Derived from WAR filename — `test-east-deploy-a` and `test-east-deploy-b` respectively (set via `<finalName>`).
- **No persistence, no messaging, no caching**.

## API Surface
Both `AppAController` and `AppBController` expose identical REST endpoints (JSON responses via `@RestController`):

| Method | Path | Description |
|---|---|---|
| GET | `/` | Returns `{app, version, hostname}` |
| GET | `/health` | Returns `{status: "UP", app, hostname}` |
| GET | `/version` | Returns `{app, version}` |
| GET | `/hostname` | Returns `{app, hostname}` |
| GET | `/slow?seconds=N` | Sleeps N seconds, returns `{app, hostname, sleptSeconds}` |

No authentication or authorisation is applied to any endpoint. All endpoints are publicly accessible on the context root.

## Security Posture

### Authentication / Authorisation
- None. No Spring Security, no OAuth2, no API keys. All endpoints are unauthenticated.
- Acceptable for a non-production test harness, but the WAR must never be deployed to a production environment.

### Cryptography
- No custom cryptography. TLS is expected to be handled by the servlet container or reverse proxy at deployment time.

### Secrets Management
- `PAT_TOKEN_PACKAGE` GitHub Actions secret is the only secret in scope. It is referenced via `${{ secrets.PAT_TOKEN_PACKAGE }}` and not embedded in source.

### Known CVE / Dependency Risks
- Spring Boot 3.4.2 (released early 2025) is relatively current; no specific CVEs identified in the observed dependency set.
- Only runtime dependencies are `spring-boot-starter-web` and `spring-boot-starter-tomcat` (provided). Attack surface is minimal.

## Technical Debt
1. **No Actuator**: Custom `/health` endpoint duplicates work that Spring Boot Actuator provides with far richer integration. Requires manual maintenance.
2. **Unbounded `Thread.sleep`**: `AppAController.java:48` and `AppBController.java:48` — the `/slow` endpoint accepts an unbounded `seconds` parameter with no upper limit enforced. A client could request a 2-billion-second sleep.
3. **Shared workflow pinned to `@main`**: `.github/workflows/build.yml:19` — no SHA or version tag pinning. Upstream workflow changes can break builds without warning.
4. **SNAPSHOT publish on every feature branch push**: `DEPLOY_TO_PACKAGES: true` is unconditional, polluting GitHub Packages with feature-branch artefacts.

## Gen-3 Migration Requirements
Not applicable. Repository is already on Gen-3 stack (Java 21, Spring Boot 3.4.2).

## Code-Level Risks

| File | Line | Risk |
|---|---|---|
| `app-a/src/main/java/.../AppAController.java` | 48 | `Thread.sleep(seconds * 1000L)` — no upper bound on `seconds` parameter; potential thread exhaustion |
| `app-b/src/main/java/.../AppBController.java` | 48 | Same issue as above in app-b |
| `.github/workflows/build.yml` | 19 | `om-ci-setup/.github/workflows/build-east-java.yml@main` — floating ref, not pinned to SHA |
| `app-a/src/main/resources/application.properties` | 2 | `spring.application.version=@project.version@` requires Maven resource filtering enabled; if filtering is skipped the literal string appears in the running app |
