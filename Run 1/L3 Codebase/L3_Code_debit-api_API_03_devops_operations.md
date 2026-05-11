# DevOps & Operations Report — debit-api_API

## 1. Build System

| Attribute | Value |
|---|---|
| Build tool | Maven (Maven Wrapper `mvnw`) |
| Java version | 21 (compiler source/target in boot pom) |
| Packaging | Spring Boot fat JAR (`debitapiws.jar`) via `spring-boot-maven-plugin` |
| Multi-module layout | Parent `debitapi` → `debitapi-boot`, `debitapi-common`, `debitapi-impl`, `debitapi-ws` |
| Parent POM | `com.citi.prepaid.webservices.debitapi:debitapi:3.1.4-SNAPSHOT` |
| Settings file | `.mvn/wrapper/settings.xml` (private registry credentials) |
| Standard build command | `mvn clean install -s ./.mvn/wrapper/settings.xml -Dmaven.test.skip` |

---

## 2. CI/CD

### 2.1 GitHub Actions Workflows

| Workflow | File | Trigger |
|---|---|---|
| Main deployment | `deployment.yml` | Push to `main`, PRs to `main` |
| Code coverage build | `code_cov_build.yml` | Scheduled / manual |
| CodeQL SAST | `codeql.yml` | Push / PR |
| GitHub Package publish | `github-package-publish.yml` | Push to `main`, workflow_dispatch |
| App config update | `app-config.yml` | Manual |
| VM deployment | `vm-deployment.yml` | Manual |
| Redeploy | `redeploy.yaml` | Manual |

### 2.2 Deployment Pipeline (deployment.yml)
```yaml
uses: Onbe/om-ci-setup/.github/workflows/java-workflow.yml@main
with:
  APP_NAME: DebitAPI
  PACT_PACTICIPANT: debit-api
  VERIFY_PROVIDER_PACT: false
  TARGET_ROOT: ./debitapi-boot
  PUBLISH_TO_APIM: true
  EXTERNAL_APIM: true
  BACKEND_SUFFIX: /services/DebitService
  UPDATE_DEPENDENCIES: true
  EXCLUDE_STAGE: false
```
- WSDL is published to Azure APIM on every main-branch push.
- Pact consumer contract verification is disabled (`VERIFY_PROVIDER_PACT: false`).

### 2.3 GitLab CI
A `.gitlab-ci.yml` file is also present (legacy / dual-VCS period). Not analyzed in detail.

---

## 3. Container / Runtime

| Attribute | Value |
|---|---|
| Base image | `bellsoft/liberica-openjre-alpine:21` |
| Exposed ports | 80 (HTTP), 9090, 9091 (management/monitoring), 50505 |
| Default server port | `${SERVER_PORT:80}` |
| Context path | `${SERVER_CONTEXT_PATH:/}` |
| JVM entrypoint | `java -jar ./app.jar` (no JVM flags set — relies on container resource limits) |
| CA certificate | `nam.wirecard.sys.crt` imported into both OS and JVM trust stores (Dockerfile lines 20–27) |
| Dynatrace | Comment in Dockerfile: "injected when pod is deployed to K8S" |
| Kubernetes | Implied by Dynatrace injection; actual K8s manifests not present in repo |

---

## 4. Configuration Management

Configuration is layered:

1. **Classpath defaults** (`debitapi-boot/src/main/resources/config/`):
   - `director-client.yaml` — Director URL placeholder
   - `debitapi.yaml` — memberId, agent, thread-pool settings (all `from-app-config`)
   - `database.default.yaml` — DB timeout settings (600 s per datasource)
   - `service.monitor.default.yaml` — monitoring defaults
   - `ecount-config.yaml` — ECount system config

2. **Azure App Configuration** (`spring-cloud-azure-appconfiguration-config-web`):
   - Injects environment-specific properties at runtime
   - Per-environment files in `app-config/{qa,staging,prod}/appsettings.json`

3. **Azure Key Vault** (`spring-cloud-azure-starter-keyvault-secrets`):
   - All four datasource username/password pairs resolved from Key Vault
   - Key Vault reference names follow pattern `managepaymentapi-*db-username/password`

4. **Runtime overrides**: `SERVER_PORT`, `SERVER_CONTEXT_PATH` environment variables

---

## 5. Observability

| Signal | Mechanism |
|---|---|
| Health check | `GET /hc` → `HealthCheck.java` returns "OK" (line 12); also Spring Actuator `/actuator/health` |
| Actuator endpoints | `health`, `info` exposed (`management.endpoints.web.exposure.include`) |
| Metrics / APM | Dynatrace (injected by K8s) |
| Logging | Log4j2 (`spring-boot-starter-log4j2`); root=ERROR, `com.citi`/`com.onbe`=DEBUG |
| Request tracing | `GlobalRequestIDInterceptor` + `Log4jMDCWriter` (MDC) — assigns `global-request-id` per call |
| Audit | `AuditMethodInterceptor` with `collectStatistics=true` |
| Container scan | `.github/containerscan/allowedlist.yaml` — Trivy allowlist present |
| Dependency scan | Dependabot (`.github/dependabot.yml`) |

---

## 6. Infrastructure Dependencies

| Dependency | Address | Protocol |
|---|---|---|
| Director (prod) | `https://prod.nam.wirecard.sys:8080/service/dispatch.asp` | HTTPS / XML-RPC |
| Director (QA) | `https://qa.nam.wirecard.sys:8080/service/dispatch.asp` | HTTPS / XML-RPC |
| Director (staging) | `https://uat.nam.wirecard.sys:8080/service/dispatch.asp` | HTTPS / XML-RPC |
| cbaseapp SQL Server (prod) | `p-lis-db03.nam.wirecard.sys:2231` | JDBC/SQL Server |
| jobsvc / order / request SQL Server (prod) | `p-lis-db01.nam.wirecard.sys:2231` | JDBC/SQL Server |
| ECount Core2 XML-RPC | Resolved via Director at runtime | XML-RPC over HTTP |
| Azure App Configuration | Injected via spring-cloud-azure | HTTPS |
| Azure Key Vault | Injected via spring-cloud-azure | HTTPS |
| Azure APIM | Published via CI pipeline | WSDL/SOAP |

---

## 7. Operational Risks

| Risk | Impact | Recommendation |
|---|---|---|
| No JVM heap flags in Dockerfile | Memory pressure on large loads; OOM kills possible | Add `-Xms`/`-Xmx` or JVM ergonomics flags |
| `trustServerCertificate=true` | SQL Server TLS not verified | Replace with proper cert trust chain in all envs |
| No circuit breaker on ECount Core2 calls | Cascading failure if Core2 is slow | Add Resilience4j circuit breaker |
| Thread pool unbounded queue (`LinkedBlockingQueue` no capacity) | Memory growth under load | Set explicit capacity on queue bean (`DebitApiWsConfig` line 395) |
| Session timeout 5m (application.yml line 47) | Short sessions may expire mid-flow | Review against actual client SLA |
| `VERIFY_PROVIDER_PACT: false` | Consumer contract regressions go undetected | Enable Pact verification in CI |
| No observed readiness probe config in repo | K8s may route traffic before app is ready | Add readiness probe to deployment manifest |
