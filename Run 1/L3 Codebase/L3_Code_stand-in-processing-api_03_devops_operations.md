# DevOps & Operations Report: stand-in-processing-api

## Build System

- **Build tool**: Apache Maven (wrapper in `.mvn/wrapper/`)
- **Parent POM**: `org.springframework.boot:spring-boot-starter-parent:3.5.5`
- **Java version**: 21
- **Module structure**: Three Maven modules
  - `stip-transaction-models`: Domain models
  - `stip-generated`: Code generated from WSDL (Apache CXF), OpenAPI (openapi-generator), and Fiserv YAML
  - `stip-main`: Application code, Spring Boot entry point `SasiApplication.java`

- **Key dependency overrides in root `pom.xml`**:
  - `tomcat.version=10.1.45`: Explicitly overrides Spring Boot's managed Tomcat to patch **CVE-2025-55752**
  - `jackson-bom.version=2.21.1`: Explicitly overrides Jackson to patch **GHSA-72hv-8253-57qq**
  - This proactive CVE patching pattern is commendable and shows active security maintenance

## CI/CD Pipeline

- **`deployment.yml`**: Uses shared `Onbe/om-ci-setup` reusable GitHub Actions workflow; triggers on push to `main`
- **`redeploy.yaml`**: Manual/triggered redeploy workflow

Unlike `scheduler_WAPP`, tests are not skipped in the deployment workflow — the default Maven lifecycle runs tests. The `pom.xml` has `<skipTests>false</skipTests>` as explicit default with separate `skipUnitTests` and `skipIntegrationTests` controls for fine-grained test execution.

The `.ai/` directory contains AI-assisted development guidelines (security standards, Java/Spring standards, testing standards) — indicating AI-assisted development practices are formally adopted for this service.

## Deployment Model

- **Runtime**: Spring Boot 3.5.5 embedded Tomcat 10.1.45, running on Java 21
- **Containerisation**: Dockerfile at repo root; deployed as a Docker container
- **Cloud target**: Azure Kubernetes Service (AKS) with multi-zone deployment (East US 2 primary, Central US DR) per architecture document
- **Auto-scaling**: Horizontal Pod Autoscaler (2–20 pods per AZ) for burst traffic during failover
- **Database**: Azure SQL Database (Premium tier) with geo-replication
- **Load balancing**: Azure Application Gateway with WAF in front

## Secrets Management

- **Azure Key Vault**: Primary secret store; accessed via Azure Managed Identity (`AZURE_MANAGED_IDENTITY_CLIENT_ID` environment variable)
- **Azure App Configuration**: Configuration management with feature flags; connection controlled by `AZURE_APP_CONFIG_ENABLED`
- **Local development**: `src/main/resources/local-secrets.properties` (git-ignored) for developer secrets

**Critical finding**: The `.env` file committed to the repository (line 2) contains:
```
AZURE_APP_CONFIG_ENDPOINT=https://appcs-shared-qa-ss.azconfig.io;Id=zvgN;Secret=[REDACTED — rotate immediately]
```
This is a full Azure App Configuration connection string including an access key committed to the repository. Even if this is a QA-only configuration, the access key must be immediately rotated. The Azure App Configuration instance `appcs-shared-qa-ss` may contain sensitive configuration shared across multiple services.

The `SPRING_PROFILES_ACTIVE=local` in the same `.env` file suggests it is intended for local development only, but its presence in the Git repository means the key is in version control history.

## Observability

- **Health endpoints**: `/hc` and `/hc/info` (custom) plus Spring Boot Actuator
- **Metrics**: Micrometer with `MetricsConfiguration` class; integrates with Azure Monitor
- **Logging**: SLF4J with Logback; `ConfigLogger` class logs configuration on startup
- **Tracing**: Spring Cloud Sleuth optional; correlation IDs mentioned in architecture
- **Alerting**: P0 (PagerDuty/immediate), P1 (Email/Slack/15min), P2 (daily dashboard) per architecture document

## EOL Runtimes and CVE Status

- **Java 21**: Current LTS, no EOL concern
- **Spring Boot 3.5.5**: Current release, actively maintained
- **Tomcat 10.1.45**: Explicitly patched for CVE-2025-55752 — current as of build date
- **Jackson 2.21.1**: Explicitly patched for GHSA-72hv-8253-57qq — current as of build date
- **Apache CXF 4.1.2**: SOAP framework; should be reviewed against known CXF CVEs
- **Resilience4j 2.3.0**: Current release

No EOL runtime concerns identified. This is the most up-to-date and actively maintained codebase in the batch, consistent with Gen-3 status.

## Testing Strategy

- **Unit tests**: JUnit 5, `@WebMvcTest` for controllers with H2 in-memory database
- **Integration tests**: Testcontainers with SQL Server for `@SpringBootTest` tests using `integration-test` profile
- **Contract tests**: Pact broker referenced in deployment workflow (`PACT_PACTICIPANT: sasi-api`)
- **Coverage**: JaCoCo available in POM (commented out thresholds in related repos suggest coverage gates may not be enforced)
