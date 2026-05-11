# contact-center-agent-api — DevOps & Operations View

## Build & Packaging

| Item | Detail |
|---|---|
| **Language / Runtime** | Java 21 (LTS) |
| **Framework** | Spring Boot 3.5.7 (Spring Cloud 2025.0.0, Spring Cloud Azure 5.23.0) |
| **Build tool** | Maven (Maven Wrapper `mvnw`) |
| **Artifact** | Uber JAR via `spring-boot-maven-plugin` |
| **Code generation** | `openapi-generator-maven-plugin 7.13.0` generates controller interfaces + models from three OpenAPI specs: `openapi.yml` (public API), `ecountcore.yaml` (ECount Core client), `otpapi.yaml` (OTP client) |
| **APIM JSON** | `swagger-codegen-maven-plugin` converts `openapi.yml` → `target/openapi.json` for Azure APIM publish |
| **Test split** | Unit tests `*Test.java` via `maven-surefire-plugin`; Integration tests `*TestIT.java` via `maven-failsafe-plugin`. Integration tests default-skipped (`skipIntegrationTests=true`) |
| **Lombok** | Used extensively for `@Getter`, `@Setter`, `@RequiredArgsConstructor`, `@Builder`, etc. Excluded from JAR |
| **JSpecify** | `org.jspecify:jspecify:1.0.0` — nullability annotations throughout |

### Maven Wrapper Settings
`.mvn/wrapper/settings.xml` is referenced in CI with `-s ./.mvn/wrapper/settings.xml` for private artifact resolution.

---

## Deployment

### Container
- **Base image**: `bellsoft/liberica-openjre-alpine:21` (Alpine-based minimal JRE 21).
- **Server port**: 80 (ENV `SERVER_PORT`), actuator on port 9090 (ENV `ACTUATOR_PORT`).
- **JVM heap**: `-Xms512m -Xmx2048m` (Dockerfile ENV `JAVA_ARGS`).
- **Exposed ports**: 80, 9090, 9091, 50505.
- **CA cert injection**: `bindings/ca-certificates/nam.wirecard.sys.crt` is imported into the JVM truststore via `keytool` during image build (required for ECount Core TLS handshake).
- **Dynatrace APM**: Injected by Kubernetes at pod startup (no code-level configuration required per Dockerfile comment).
- **Entry point**: `java -jar ./app.jar` (CMD `$JAVA_ARGS` not correctly expanded — shell variable substitution requires shell form; this is a minor Dockerfile bug, JAVA_ARGS will not be applied at runtime unless patched).

### Kubernetes / AKS
- Deployed to Azure Kubernetes Service (AKS) via the shared Onbe CI/CD pipeline.
- Application name in AKS: `contactcenteragentapieast` (from `redeploy.yaml`).
- Environment namespacing: `qa`, `staging`, `prod` (from `app-config/` directories).

### APIM
- Published to **external** Azure API Management (`EXTERNAL_APIM: true`, `INTERNAL_APIM: false`).
- API suffix: `contact-center-agent-east` (from `deployment.yml`).
- APIM base URL: `https://decagonapi.onbe.com` (from `openapi.yml` servers section).

---

## Configuration Management

### External Configuration Sources (runtime priority order)
1. **Azure App Configuration** (`spring-cloud-azure-appconfiguration-config`) — prefix `contact-center-agent-api` per environment label (`qa`, `staging`, `prod`). Published via `.github/workflows/app-config.yml`.
2. **Azure Key Vault** (`spring-cloud-azure-starter-keyvault-secrets`) — all secrets referenced via `key_vault_references` in `appsettings.json`.
3. **`application.yml`** (packaged) — baseline defaults with placeholder values (`url-from-app-config`, `secret-key-from-app-config`, etc.).

### Per-Environment Overrides

| Property | QA | Prod |
|---|---|---|
| `spring.datasource.cbaseapp.url` | `u-lis-db01.nam.wirecard.sys:2231` | `p-lis-db03.nam.wirecard.sys:2231` |
| `spring.datasource.ecountcore.url` | `u-lis-db02.nam.wirecard.sys:2231` | `p-lis-db02.nam.wirecard.sys:2231` |
| `ecount.core.base-url` | `https://uat.nam.wirecard.sys:8084/service` | `https://prod.nam.wirecard.sys:8084/service` |
| `api.settings.account-inquiry.default-max-transactions` | 50 | 50 |
| `api.settings.account-inquiry.max-transactions` | 100 | 100 |
| `api.settings.auditing.enabled` | `true` | `true` |
| `api.settings.ecount.agent` | `b2cstage` | `b2c` |
| OTP base URL | Dapr sidecar: `http://localhost:3500/v1.0/invoke/OmOtpSvc/method/api/v1/Otp` | Same |

### Key Vault Secret Names (from `app-config/prod/appsettings.json`)
| Secret Name | Maps To |
|---|---|
| `managepaymentapi-cbaseappdb-username` | `spring.datasource.cbaseapp.username` |
| `managepaymentapi-cbaseappdb-password` | `spring.datasource.cbaseapp.password` |
| `managepaymentapi-ecountcoredb-username` | `spring.datasource.ecountcore.username` |
| `managepaymentapi-ecountcoredb-password` | `spring.datasource.ecountcore.password` |
| `mypaymentvaultapi-aes-secret` | `encryption.mpv.aes.secret-key` |
| `mypaymentvaultapi-aes-iv` | `encryption.mpv.aes.iv-key` |
| `contact-center-agent-api-jwt-secret` | `jwt.secret` |

Note: DB credential Key Vault secret names share the prefix `managepaymentapi-` — they are the **same secrets** used by `manage-payment-api`, implying shared database credentials across services.

### Dapr Sidecar (OTP Service)
- OTP service URL uses Dapr service invocation: `http://localhost:3500/v1.0/invoke/OmOtpSvc/method/api/v1/Otp`.
- Dapr is not configured in this repo; it is assumed to be injected as a sidecar in the AKS pod.

---

## Observability

### Health / Actuator
- Endpoint base: `/` (not `/actuator`).
- Health endpoint: `/hc` (path-mapped from `health`).
- Exposed: `health`, `metrics`, `info`, `prometheus`.
- Health probes: liveness (`/livez`) and readiness (`/readyz`) enabled.
- Metrics tag: `app_name=contact-center-agent-api`.

### Logging
- Library: Logback (via Spring Boot).
- Format: `%d{yyyy-MM-dd HH:mm:ss.SSS} [%thread] %-5level %logger{36} - %msg%n` (console only).
- Non-local profiles: root level `INFO`.
- Local profile: root level `INFO`, `DEBUG` for Azure App Configuration, Spring Boot context, and Spring Cloud Bootstrap.
- No structured/JSON logging; no correlation ID / trace ID injection visible in log config.
- Sensitive data logging guards: `maskDda`, `maskCardNumber`, `maskSensitiveData` used selectively (not uniformly applied in all log statements).

### APM
- Dynatrace injected at pod level — no code-level instrumentation configured.

### Request Audit Logging
- `RequestAuditLoggingFilter` (`@Order(Ordered.HIGHEST_PRECEDENCE)`) wraps requests and persists to `api_request_audit_log`.
- Controlled by `api.settings.auditing.enabled` (both qa and prod: `true`).
- Only `encryptedDDA` and `channel` headers logged (not `token`, `accountNumber`, or `Authorization`).

### Distributed Tracing
- No Sleuth/Micrometer tracing dependency is present in `pom.xml`. Spring Boot 3.x Micrometer Tracing is not configured. This is an observability gap for distributed request correlation.

---

## Infrastructure Dependencies

| Dependency | Address (Prod) | Protocol |
|---|---|---|
| cbaseapp SQL Server | `p-lis-db03.nam.wirecard.sys:2231` | JDBC / TLS 1.2 |
| ecountCore SQL Server | `p-lis-db02.nam.wirecard.sys:2231` | JDBC / TLS 1.2 |
| ECount Core REST API | `https://prod.nam.wirecard.sys:8084` | HTTPS |
| OTP Shared Service | `http://localhost:3500` (Dapr) | HTTP (sidecar) |
| Azure App Configuration | Azure PaaS | HTTPS |
| Azure Key Vault | Azure PaaS | HTTPS |
| Azure APIM | `https://decagonapi.onbe.com` | HTTPS |
| Dynatrace | AKS pod injection | Agent |
| Container Registry | Onbe shared CI (Onbe/om-ci-setup) | HTTPS |

### Hikari Connection Pool (application.yml)
- `connection-timeout`: 5000 ms
- `validation-timeout`: 3000 ms
- `maximum-pool-size`: 20
- `minimum-idle`: 5

Applies to both cbaseapp and ecountCore datasources (shared pool config; no per-datasource pool tuning visible).

---

## Operational Risks

1. **`$JAVA_ARGS` not expanded in Dockerfile CMD**: `CMD ["$JAVA_ARGS"]` uses exec form — shell variable expansion does not occur. Heap settings (`-Xms512m -Xmx2048m`) are **not applied**. The JVM will use default heap sizing.

2. **Static IV in AES/GCM**: If the encrypted DDA scheme is widely used, key-stream reuse is possible (see `AesDecryptionService.java`). An attacker who can observe multiple ciphertexts encrypted with the same key+IV could potentially recover plaintext.

3. **Single pod cache for `appProfileLabelTypes`**: Default `ConcurrentMapCacheManager` is in-process with no TTL. After a pod restart the cache is cold and will generate extra DB queries until warm. In a multi-pod deployment each pod has an independent cache.

4. **Audit log unbounded growth**: `api_request_audit_log` with no purge policy will grow without bound on a high-traffic deployment. No index on `created_date` is visible in the DDL.

5. **Shared Key Vault secrets with `manage-payment-api`**: DB credentials are prefixed `managepaymentapi-*`, indicating credential sharing with another service. A credential rotation for one service will break the other if not coordinated.

6. **OTP timeout configuration mismatch**: `application.yml` defaults OTP base URL to `http://localhost:1080/api/v1/Otp/` (MockServer port) but prod/qa override to Dapr endpoint. A misconfigured environment could silently hit MockServer.

7. **Integration tests skipped by default**: `skipIntegrationTests=true` in `pom.xml`. CI pipeline (`deployment.yml`) passes `-DskipTests`, skipping all tests. No automated test gate enforces correctness at deploy time.

8. **No graceful shutdown or connection draining configuration** visible in `application.yml` for the Hikari pool or Spring web server.

---

## CI/CD

### Workflows (`.github/workflows/`)

| Workflow | Trigger | Purpose |
|---|---|---|
| `deployment.yml` | Push/PR to `main` (excluding `.mvn/**`, `.github/**`, README) | Build, test (skipped), package, push image, deploy to AKS via shared `Onbe/om-ci-setup` Java workflow |
| `app-config.yml` | Push to `main` on `app-config/**` changes | Publishes app-config JSON to Azure App Configuration via `Onbe/om-ci-setup` |
| `codeql.yml` | Push to `main`, PRs, weekly schedule (Thursday 09:48 UTC) | GitHub CodeQL SAST scanning via shared `Onbe/om-ci-setup` |
| `redeploy.yaml` | `workflow_dispatch` (manual) | Redeploys existing image to QA AKS without rebuild |

### Deployment Pipeline Details (`deployment.yml`)
- Shared workflow: `Onbe/om-ci-setup/.github/workflows/java-workflow.yml@main`
- `APP_NAME`: `ContactCenterAgentAPIEAST`
- `PACT_PACTICIPANT`: `contact-center-agent-api`
- `VERIFY_PROVIDER_PACT: false` — this service does not act as a pact provider
- `MAVEN_ARGS: '-DskipTests -s ./.mvn/wrapper/settings.xml -U'` — all tests are skipped in CI
- `PUBLISH_TO_APIM: true`, `EXTERNAL_APIM: true`
- `EXCLUDE_STAGE: false` — staging environment is included in the deployment chain
- `UPDATE_DEPENDENCIES: false`, `UPDATE_PARENT_VERSION: false`

### Pact Contract Testing
- Pact broker registered but `VERIFY_PROVIDER_PACT: false`. Consumer contracts from Decagon (or other callers) could be published but are not verified server-side on CI.

### Trivy Security Scanning
- `.trivyignore` file present (content not in scope), indicating some CVEs are knowingly suppressed.
