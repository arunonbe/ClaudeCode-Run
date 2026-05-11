# DevOps & Operations Report: scheduler_WAPP

## Build System

- **Build tool**: Apache Maven (wrapper version in `.mvn/wrapper`)
- **Parent POM**: `com.parents:prepaid-parent:6.0.12` (internal corporate parent)
- **Java version**: 21 (compiler source/target set in root `pom.xml`)
- **Packaging**: Multi-module Maven project — `scheduler-common` (API), `scheduler-impl` (Quartz implementation), `scheduler-service` (WAR)
- **Artifact**: `scheduler-service.war` deployed to embedded Tomcat 10.1.28 via Docker
- **Maven settings**: `.mvn/wrapper/settings.xml` references the internal Nexus/Artifactory repository at the Wirecard/Northlane network address

## CI/CD Pipeline

Three GitHub Actions workflows are defined:

1. **`deployment.yml`**: Triggers on push to `main` or PR to `main`. Calls the shared `Onbe/om-ci-setup/.github/workflows/java-workflow.yml@main` reusable workflow. Parameters include `PUBLISH_TO_APIM: true` (WSDL published to API management), `EXCLUDE_STAGE: true` (no staging environment gate), `MAVEN_ARGS: -Dmaven.test.skip` — tests are skipped on every build. `UPDATE_PARENT_VERSION: true` indicates automatic parent POM version bumping
2. **`redeploy.yaml`**: Manual/triggered redeploy workflow
3. **`github-package-publish.yml`**: Publishes artifacts to GitHub Packages
4. **Jenkinsfile**: A legacy Jenkinsfile is present at root, suggesting dual CI pipelines (Jenkins for legacy deployments, GitHub Actions for current)

**Notable CI risk**: `maven.test.skip` in the primary deployment pipeline means no automated test verification occurs before deployment to production.

## Deployment Model

- **Runtime**: Apache Tomcat 10.1.28 inside a Docker container based on `bellsoft/liberica-openjre-alpine:21`
- **Containerisation**: Dockerfile (`scheduler-service/Dockerfile`) builds a WAR-based Tomcat deployment
- **Container port**: 80 (HTTP only; no TLS termination at container level)
- **JVM flags**: Several `--add-opens` directives for Java 21 module system compatibility with legacy reflection-heavy Spring XML code
- **Deployment target**: GitHub Actions workflow suggests deployment to ECS/Kubernetes via the `om-ci-setup` shared workflow; the `Jenkinsfile` implies legacy ECS or VM-based deployment for some environments
- **Clustering**: Quartz cluster mode enabled; multiple container instances share the `jobsvc` SQL Server database for cluster coordination

## Secrets Management

- **Critical finding**: Database credentials stored in plaintext `.env` and `.env-dev` files committed to the repository (files: `scheduler-service/.env`, `scheduler-service/.env-dev`). These files are not in `.gitignore`
- **Runtime**: Tomcat reads credentials from environment variables (`${SCHDULERWAAP_JOBSVCDB_USERNAME}`, `${SCHDULERWAAP_JOBSVCDB_PASSWORD}`) via `EnvironmentPropertySource` in `catalina.properties` — the runtime pattern is correct, but the values are committed to source control
- **No vault integration**: No reference to AWS Secrets Manager, Azure Key Vault, or HashiCorp Vault in any configuration file
- **QA cert import**: A QA certificate (`certfile_qa.crt`) is hardcoded into the Docker image with default Java keystore password `changeit`

## Observability

- **Health check**: Simple `GET /hc` returning "OK" via `HealthCheck.java`; no Spring Boot Actuator, no metrics endpoint
- **Logging**: Log4j2 configuration loaded from an external file path (`${CBASE_HOME_URL}/config/service/scheduler/log4j2.xml`); no log aggregation configuration visible
- **Access logs**: Tomcat access log valve configured (`AccessLogValve`) writing to local `logs/` directory — not shipped to centralised logging
- **No distributed tracing**: No trace ID propagation visible

## EOL Runtimes and CVE Concerns

- Tomcat 10.1.28: patched at time of original build but not necessarily current — the pom.xml contains no version pinning for Tomcat CVEs
- Spring HTTP Invoker: deprecated by Spring since Spring 5.3, removed in Spring 6; this service still relies on it and cannot migrate to Spring 6 without a full rewrite of the RPC layer
- Apache XML-RPC dependencies are referenced via corporate parent — version status unknown without full dependency tree resolution
- `trustServerCertificate=true` in dev JDBC URLs disables TLS certificate validation, creating a man-in-the-middle risk in developer and potentially non-production environments
