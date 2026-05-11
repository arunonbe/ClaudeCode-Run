# az-appconfig-demo — Solution Architect View

## Technical Architecture

**Stack**: Java 21 / Spring Boot 3.x / Spring Cloud Azure / Maven / Docker / AKS

The application is a minimal Spring Boot web service with four source classes and two YAML configuration files. Its architecture is intentionally thin — its value is in the wiring, not the logic.

```
AzAppConfigDemoApplication          (entry point)
    |
    +-- AppConfig                   (@Configuration, @EnableScheduling)
    |       |
    |       +-- FeatureManager      (Azure SDK bean, injected)
    |       +-- AsyncTaskExecutor   (@Bean, virtual-thread executor)
    |       +-- logFeatureFlags()   (@Scheduled every 5 min)
    |
    +-- AppConfigController         (@RestController)
    |       |
    |       +-- FeatureManager      (injected)
    |       +-- DatabaseConfigProperties (injected)
    |       +-- AppConfigurationProperties (Azure SDK bean, injected)
    |       +-- GET /               (static greeting)
    |       +-- handleAppStartedEvent() (@EventListener)
    |
    +-- DatabaseConfigProperties    (@ConfigurationProperties "database.cbaseapp")
            fields: url, username, password
            toString(): omits password
```

**Configuration loading sequence**:
1. `bootstrap.yaml` loaded first (Spring Cloud bootstrap context).
2. Azure App Config client authenticates (Managed Identity or SPN) and fetches key-value pairs.
3. Key Vault references resolved.
4. Spring application context refreshed with resolved properties.
5. `application.yaml` overlays (logging levels only in this repo).
6. Beans instantiated; `ApplicationStartedEvent` fired.

**Virtual threads**: `AppConfig.java` line 29 configures `SimpleAsyncTaskExecutor` with `setVirtualThreads(true)`. The executor is named `"appconfig-"`. This is Java 21 Project Loom virtual threads, reducing thread-per-request overhead. However, this executor is registered as a bean but is not explicitly wired to the web server's request handling thread pool — its practical use in this minimal app is the scheduled task execution context.

## API Surface

| Method | Path | Controller | Return Type | Auth |
|---|---|---|---|---|
| GET (any method) | `/` | `AppConfigController.index()` | `String` | None (no Spring Security) |

`@RequestMapping("/")` without a method constraint responds to all HTTP verbs. No OpenAPI/Swagger spec is generated or published. No versioning (`v1`, `v2`) is applied. No APIM registration (`PUBLISH_TO_APIM: false`). This is intentional for a demo application, but must not be replicated in production services.

No additional actuator endpoints, health checks, or management endpoints are configured in the visible source files.

## Security Posture

### Authentication & Authorisation
- **To Azure services (deployed)**: User-Assigned Managed Identity (`AZURE_MANAGED_IDENTITY_CLIENT_ID`) — no static credentials in deployed environments. This is the correct production pattern (`bootstrap.yaml` lines 53–64).
- **To Azure services (local)**: SPN client credentials (`AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID`) sourced from `.env` file. Credentials are not in source control.
- **Application-level auth**: None. `GET /` is unauthenticated. No Spring Security dependency is present. For a demo/internal tool this is acceptable; for a production service it is a gap.

### Secret Management
- Database password resolved via Azure Key Vault reference — not stored in App Config, not in source code (`appsettings.json` line 8–9).
- `DatabaseConfigProperties.toString()` (`DatabaseConfigProperties.java` lines 12–15) excludes `password` — prevents accidental log exposure.
- Push-notification webhook token secret via `AZURE_APP_CONFIG_PUSH_TOKEN_SECRET` env var (`bootstrap.yaml` line 39) — not in source.

### Transport Security
- All Azure SDK connections use HTTPS (TLS 1.2+ enforced by Azure endpoints).
- HTTP client timeouts configured: connect=30s, read=30s, response=30s (`bootstrap.yaml` lines 15–17).

### Supply Chain
- CycloneDX SBOM generated at build (`pom.xml` lines 112–114).
- Dependabot weekly Maven updates (`.github/dependabot.yml`).
- CodeQL weekly scan (`codeql.yml`).
- Container scan **disabled** (`deployment.yml` line 24) — gap.
- Two CVEs allow-listed in `.github/containerscan/allowedlist.yaml`:
  - `CVE-2024-24790`: paketo buildpacks issue
  - `CVE-2024-45337`: unspecified (no comment in the file)

### Known Security Findings (code-level)
1. **`user: "0:0"` in `compose.yaml` line 9**: Root container execution in local dev.
2. **`BODY_AND_HEADERS` HTTP logging** (`bootstrap.yaml` line 14): Logs full request/response bodies and headers for Azure SDK calls. In local/dev this exposes bearer tokens and config values in log output.
3. **`sa` database account** (`appsettings.json` line 5): System admin account used for DB connection in QA reference config.
4. **No Spring Security**: Application has no authentication layer.
5. **`msal4j` exclusion then re-inclusion** (`pom.xml` lines 74–84, 86–88): `msal4j` is excluded from `spring-cloud-azure-appconfiguration-config` and then re-added as a direct dependency. This pattern is used to control the MSAL4J version explicitly — acceptable, but requires careful version management.

## Technical Debt

| Item | Severity | Location | Description |
|---|---|---|---|
| SNAPSHOT parent POM | HIGH | `pom.xml` line 9 | `onbe-spring-boot-parent:0.0.22-SNAPSHOT` — non-deterministic builds |
| No test suite | HIGH | (absent) | `spring-boot-starter-test` declared; no test files exist |
| CI on feature branches | HIGH | `deployment.yml` lines 11, 9; `app-config.yml` line 9 | `@feature/spring-boot-build-image`, `@feature/CLOUDADM-948-app-config` are mutable refs |
| Unused dependency | MEDIUM | `pom.xml` line 95 | `spring-cloud-azure-starter-storage-blob` — no Blob Storage code exists |
| Sentinel key is a data key | MEDIUM | `compose.yaml` line 27 | `database.cbaseapp.username` used as refresh trigger; should be a dedicated sentinel |
| App Config prefix mismatch | MEDIUM | `app-config.yml` line 12 vs `compose.yaml` line 22 | `PetStoreAPI` prefix published vs `om-audit-logging-api` filter consumed |
| No `@ConfigurationPropertiesBinding` validation | LOW | `DatabaseConfigProperties.java` | No `@NotBlank`/`@NotNull` on fields |
| HTTP logging at BODY_AND_HEADERS | LOW (dev only) | `bootstrap.yaml` line 14 | Must be downgraded before any production hardening |
| Root container (compose) | LOW (dev only) | `compose.yaml` line 9 | `user: "0:0"` — bad pattern for reference material |
| Container scan disabled | HIGH | `deployment.yml` line 24 | Comment: "frequently fails" — root cause not addressed |

## Gen-3 Migration Requirements

This repository already incorporates several Gen-3 patterns. The following items are required to fully qualify as a Gen-3 reference implementation:

1. **Release the parent POM**: Cut `onbe-spring-boot-parent` version `0.0.22` as a release. Update `pom.xml` line 9 to a non-SNAPSHOT version. All SNAPSHOT references in the POM must be resolved.

2. **Stabilise CI workflow refs**: Merge `om-ci-setup` feature branches to `main` (or a stable tag). Update `deployment.yml` line 11 to `@main` or a tagged version. Same for `app-config.yml` line 9.

3. **Add test coverage**: Implement at minimum:
   - `@SpringBootTest` with `@ActiveProfiles("test")` verifying `DatabaseConfigProperties` binds correctly from test YAML.
   - Feature flag evaluation test using a mock/test `FeatureManager`.

4. **Re-enable and fix container scan**: Investigate the root cause of container scan failures. Address `CVE-2024-45337` (no justification comment currently in `allowedlist.yaml`). Ensure the scan runs on every PR.

5. **Remove unused dependency**: Delete `spring-cloud-azure-starter-storage-blob` from `pom.xml` line 95.

6. **Add `@ConfigurationPropertiesBinding` validation**: Apply `@NotBlank` to `url`, `username`, and `password` fields in `DatabaseConfigProperties.java`. Add `@Validated` to the record or its binding point.

7. **Implement proper health endpoint**: Add Spring Boot Actuator (`spring-boot-starter-actuator`) and expose `/actuator/health` with a meaningful indicator (e.g., Azure App Config connectivity check).

8. **Fix local dev security**: Change `compose.yaml` `user:` to a non-root UID (e.g., `user: "1001:1001"`).

9. **Downgrade HTTP logging for production profile**: Add a production profile override setting `spring.cloud.azure.client.http.logging.level: NONE`.

10. **Resolve App Config prefix/key filter alignment**: Ensure the prefix published by `app-config.yml` (`PetStoreAPI`) matches the key-filter consumed by the running application, or update the demo to use a self-consistent prefix (e.g., `az-appconfig-demo`).

## Code-Level Risks

### Risk 1: `AppConfigController.java` line 28 — Config logged at startup
```java
log.info("DatabaseConfigProperties: {}", config);
```
`DatabaseConfigProperties.toString()` correctly omits `password`. However, if Lombok `@ToString` is ever added to the record (e.g., by a future developer unaware of the manual override), the password will be logged. The manual `toString()` is a fragile control. **Recommendation**: Add `@SuppressWarnings("java:S2068")` or a test that asserts the log output does not contain the password value.

### Risk 2: `AppConfig.java` line 29 — Virtual thread executor naming
```java
val executor = new SimpleAsyncTaskExecutor("appconfig-");
executor.setVirtualThreads(true);
```
The `AsyncTaskExecutor` bean is declared but Spring's default `@Scheduled` executor is separate (the `TaskScheduler`). The scheduled `logFeatureFlags()` method does not explicitly use this executor. The virtual thread setting here may not affect the scheduled task execution unless Spring Boot's auto-configuration routes scheduled tasks through this executor. This is a behavioural ambiguity that warrants verification.

### Risk 3: `bootstrap.yaml` line 28 — Key-filter default value references wrong app
```yaml
key-filter: "${AZURE_APP_CONFIG_KEY_FILTER:om-user-api/}"
```
The default key-filter is `om-user-api/` — a different application's namespace. If `AZURE_APP_CONFIG_KEY_FILTER` is not set, this application will consume `om-user-api/` configuration keys, which could produce unexpected behaviour or expose configuration that should not be accessible to this service.

### Risk 4: `DatabaseConfigProperties.java` — Java record with `password` field
```java
record DatabaseConfigProperties(String url, String username, String password)
```
Java records generate a canonical constructor and accessor methods. The `password()` accessor is public and returns the plain string value. Any code that calls `config.password()` will access the credential. This is inherent to the record pattern — no obfuscation or `char[]` protection is applied. Acceptable for a demo; production services handling high-sensitivity credentials should consider a `SecretString` wrapper or credential provider pattern.

### Risk 5: `AppConfigController.java` line 32 — `getFirst()` on stores list
```java
appConfigProperties.getStores().getFirst().getMonitoring().getRefreshInterval()
```
`getFirst()` (Java 21 `SequencedCollection`) will throw `NoSuchElementException` if the stores list is empty. This executes in `@EventListener(ApplicationStartedEvent.class)` — a startup failure at this point would crash the application. No null/empty guard is present.

### Risk 6: `compose.yaml` line 15 — `onbe.bootstrap.default.enable=false`
```yaml
JAVA_TOOL_OPTIONS: -Donbe.bootstrap.default.enable=false ...
```
The Onbe bootstrap default is explicitly disabled for local compose runs. The implications depend on what `onbe.bootstrap.default` controls in `onbe-spring-boot-starter` (not visible in this repo). If it governs security defaults, tracing, or observability initialisation, disabling it for local testing may mask integration problems.
