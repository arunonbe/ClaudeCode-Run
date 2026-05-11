# DevOps & Operations View — cs-api-v1_API

## Build System
- **Build tool**: Maven (mvnw wrapper, `.mvn/wrapper/settings.xml` for internal artifact repo)
- **Maven parent**: `com.parents:prepaid-parent:6.0.13` (modernised parent)
- **Artifact**: Spring Boot JAR via `card-management-boot` module; WAR via `card-management-war`
- **Java version**: 21 (LTS)
- **Spring Boot version**: 3.5.7
- **Spring Cloud version**: 2025.0.0
- **Spring Cloud Azure version**: 5.23.0

## Modules
| Module | Artifact | Purpose |
|---|---|---|
| card-management-ws | JAR | Core SOAP web service classes and business logic |
| card-management-war | WAR | Legacy Tomcat WAR packaging (for existing deployment targets) |
| card-management-boot | Executable JAR | Spring Boot packaging with Azure App Config bootstrap |

## Key Dependencies
| Dependency | Version | Notes |
|---|---|---|
| com.ecount:xplatform | 6.5.8 | ecount C-Base RPC library |
| com.ecount.one.service.affiliate:xaffiliate-service | 4.0.1 | Affiliate metadata service |
| com.citi.prepaid.service.core:xmlrpc | 3.1.4 | SOAP/XML-RPC support |
| spring-cloud-azure (BOM) | 5.23.0 | Azure App Config + Key Vault integration |
| msal4j | 1.22.0 | Microsoft authentication for Azure services |

## CI/CD Pipeline
| Workflow | Trigger | Action |
|---|---|---|
| `deployment.yml` | Push/PR to `main` | Build + deploy via `om-ci-setup` reusable workflow |
| `vm-deployment.yml` | (separate trigger) | VM-based deployment |
| `redeploy.yaml` | Manual/scheduled | Redeploy without code change |
| `app-config.yml` | App config changes | Config-only deployment |
| `code_cov_build.yml` | Build with coverage | JaCoCo code coverage |
| `codeql.yml` | Weekly (Thursday) | CodeQL static analysis |
| `github-package-publish.yml` | Release | Publish to GitHub Packages |
| `.gitlab-ci.yml` | Push | SAST only (GitLab Security template) |

The `deployment.yml` delegates to `Onbe/om-ci-setup/.github/workflows/java-workflow.yml@main` with:
- `APP_NAME: CardManagementAPIV1`
- `PACT_PACTICIPANT: card-management-api-v1`
- `PUBLISH_TO_APIM: true` — WSDL published to Azure API Management
- `EXTERNAL_APIM: true` — published to external-facing APIM
- `BACKEND_SUFFIX: /services/AccountManagement`
- `EXCLUDE_STAGE: false` — stage environment is included

## Configuration Management
- **Azure App Configuration**: Primary config store; connected via managed identity in non-local profiles
- **Azure Key Vault**: Secrets (DB credentials, etc.) injected via App Config Key Vault references
- **Local development**: Uses `${AZURE_APP_CONFIG_CONNECTION_STRING}` environment variable
- **Refresh interval**: 15 minutes for App Config values
- **Config keys**: `cardmanagementws/*` namespace in App Config, with label filtering by Spring profile

## Deployment Configuration
```yaml
# application.yml placeholders (actual values from Azure App Config)
spring.datasource.jobsvc.url:      url-from-app-config
spring.datasource.cbaseapp.url:    url-from-app-config
ecount.config.system.defaultSystem.bootAddress: url-from-app-config

# Server
server.port: ${SERVER_PORT:80}
server.servlet.context-path: ${SERVER_CONTEXT_PATH:/}
server.servlet.session.timeout: 5m
```

## Observability
| Aspect | Implementation |
|---|---|
| Health endpoint | `/actuator/health` + `/actuator/info` exposed |
| Custom health check | `HealthCheck.java` class (content not read — likely maps to `/hc`) |
| Logging | SLF4J with Logback (Spring Boot default); log levels: ERROR for most, DEBUG for com.citi/com.onbe/Azure |
| Metrics | Spring Boot Actuator (basic); no Prometheus/Grafana config visible |
| Tracing | No distributed tracing config found |
| Request ID | `ProgramIdAwareGlobalRequestIDGenerator` writes affiliate program ID to MDC for log correlation |
| WSDL published to APIM | Via CI/CD deploy workflow |

## Container / Infrastructure
- `card-management-boot/docker-compose.yaml` exists — Docker-based local development
- Deployment to Onbe cloud infrastructure via `om-ci-setup` reusable workflow
- No Kubernetes manifests visible in this repo — infrastructure likely managed by CI workflow
- `containerscan/allowedlist.yaml` exists — container security scanning with allowlist

## Risks
1. **Dual deployment paths (WAR + Boot JAR)**: Two modules (`card-management-war` and `card-management-boot`) produce different artifact types. Operational teams must ensure the correct artifact is deployed to each environment.
2. **`allow-bean-definition-overriding: true`**: Required to resolve conflicts between JNDI beans from the imported XML context and Boot-defined beans. This can mask misconfiguration silently.
3. **`allow-circular-references: true`**: Should ideally be resolved by refactoring; circular references indicate a design smell.
4. **C-Base `bootAddress` timeout**: `connectTimeout: 120000ms` (2 min), `readTimeout: 120000ms` — very long timeouts. Under load, slow C-Base responses will hold threads for up to 2 minutes.
5. **SNAPSHOT version**: `3.1.3-SNAPSHOT` — Maven enforcer rule disallows snapshots for non-self dependencies, but the artifact itself is a snapshot. Production deployments should use release versions.
