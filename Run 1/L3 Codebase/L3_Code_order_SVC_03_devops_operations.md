# DevOps / Operations View — order_SVC

## Build System

- **Build tool**: Maven with Maven Wrapper (`.mvn/wrapper/maven-wrapper.properties`)
- **Java version**: Java 21 (`maven.compiler.source=21`, `maven.compiler.target=21`)
- **Parent POM**: `com.parents:prepaid-parent:6.0.13` (Onbe internal parent)
- **Modules**: `order-common`, `order-manager`, `order-processor`, `order-xmlrpc`, `order-war`, `order-service`, `order-rest-controller`
- **Test coverage**: JaCoCo 0.8.12 configured in parent POM; reports generated at `test` phase
- **Enforcer**: Maven enforcer blocks external SNAPSHOT dependencies in production builds; same-groupId SNAPSHOT artifacts are exempted for intra-service development
- **SBOM**: CycloneDX Maven plugin present in `order-service` (inferred from platform standard); SBOM artifacts published to GitHub packages
- **Settings**: `.mvn/wrapper/settings.xml` provides private registry credentials placeholders

## CI/CD Pipeline

- **Primary CI**: GitHub Actions
- **Workflow files**:
  - `.github/workflows/deployment-ordersvc.yml` — deploys the Spring Boot order service (container)
  - `.github/workflows/deployment-orderxmlrpc.yml` — deploys the XML-RPC WAR separately
  - `.github/workflows/cicd-deployment.yml` — general CI/CD entry point
  - `.github/workflows/github-package-publish.yml` — publishes Maven artifacts to GitHub Packages
  - `.github/workflows/redeploy-ordersvc.yaml` / `redeploy-orderxmlrpc.yaml` — manual redeploy workflows
  - `.github/workflows/codeql.yml` — CodeQL static analysis (Java)
- **Legacy CI**: `.gitlab-ci.yml` also present — migration from GitLab to GitHub Actions is in progress; both pipelines must be kept in sync during transition
- **Reusable workflow**: `Onbe/om-ci-setup/.github/workflows/java-workflow.yml@main` handles build, test, containerize, and deploy
- **PACT**: Consumer-driven contract testing enabled (`PACT_PACTICIPANT: order_svc-api`); provider pact verification disabled
- **APIM publishing**: `PUBLISH_TO_APIM: true` — WSDL/API spec is published to API management on deploy

## Deployment Model

- **order-service**: Containerized (Dockerfile at `./order-service/Dockerfile`); deployed to AKS
- **order-xmlrpc**: WAR artifact (`order-war` module); deployed separately (likely to Tomcat or JBoss)
- **Backend suffix**: `/services/order_SVC` — indicates path-based routing in the AKS ingress

## Runtime

- **Java 21** (LTS, current)
- **Spring Boot**: version inherited from `prepaid-parent` (likely Spring Boot 3.x based on Java 21 and Jakarta namespace usage — `jakarta.servlet` import in services-common)
- **IBM MQ Client**: `com.ibm.mq.jakarta.client:9.4.0.0` — Jakarta EE compatible IBM MQ client
- **XML-RPC**: custom `xmlrpc` library (`com.citi.prepaid.service.core:xmlrpc:3.1.4`)

## Secrets Management

- Secrets are inherited from GitHub Actions org-level secrets (`secrets: inherit`)
- `.mvn/wrapper/settings.xml` likely contains registry credentials placeholders resolved at CI time
- `.trivyignore` present — Trivy container vulnerability scanning is configured; some CVEs are explicitly suppressed (content not read; should be reviewed for appropriateness)
- Container scan allow-list at `.github/containerscan/allowedlist.yaml`

## Observability

- **Logging**: `ecount-host-log4j_LIB` dependency in platform ancestry; likely SLF4J with Logback in the Spring Boot service layer
- **JaCoCo**: Code coverage reports generated per build
- **IBM MQ**: Message queue depth and error queue monitoring should be in place; dead-letter queue handling is critical for order reliability
- **No distributed tracing**: No OpenTelemetry or Zipkin dependency observed directly; may be inherited from parent POM or sidecar

## Known EOL Runtimes and CVEs

- The XML-RPC WAR deployment path (`order-xmlrpc` / `order-war`) uses legacy packaging that predates container-native deployment. The WAR target runtime (Tomcat version) must be confirmed — if on Tomcat 9.x or earlier, Jakarta migration is incomplete.
- `.trivyignore` suppresses some container CVE findings; suppressed CVEs must be reviewed quarterly per PCI DSS Requirement 6.3.3.
- `dependabot.yml` is present, enabling automated dependency update PRs.
- Dual CI pipelines (GitLab + GitHub Actions) increase operational risk; the GitLab pipeline must be disabled or removed once GitHub Actions migration is complete to avoid conflicting deployments.
- Stage environment is excluded from the deployment pipeline (`EXCLUDE_STAGE: true`) — implications for pre-production validation must be understood by the team.
