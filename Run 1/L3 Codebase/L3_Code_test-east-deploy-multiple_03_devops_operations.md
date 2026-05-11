# DevOps / Operations — test-east-deploy-multiple

## Build System
- **Tool**: Apache Maven 3.x via Maven Wrapper (`mvnw` / `mvnw.cmd`)
- **Language**: Java 21
- **Framework**: Spring Boot 3.4.2 (spring-boot-starter-parent)
- **Packaging**: WAR (both `app-a` and `app-b` produce `.war` files via `maven-war-plugin` implicit in Spring Boot parent)
- **Multi-module**: Parent POM (`test-east-deploy-multiple-parent`) aggregates `app-a` and `app-b` modules.
- **Maven Wrapper settings**: `.mvn/wrapper/settings.xml` — configures the internal Onbe package registry.
- **Release versioning**: `maven-release-plugin` 3.0.1, `tagNameFormat=@{project.version}`, `autoVersionSubmodules=true`.

## CI/CD Pipeline
- **Platform**: GitHub Actions
- **Trigger**: push to `main`, `release/**`, `feature/**`; `workflow_dispatch` (with optional `skip_tests` boolean input)
- **Reusable workflow**: `Onbe/om-ci-setup/.github/workflows/build-east-java.yml@main`
- **Runner**: `ubuntu-docker` (self-hosted)
- **Java version**: 21
- **Artefact publication**: `DEPLOY_TO_PACKAGES: true` — pushes to GitHub Packages on successful build
- **Secret**: `PAT_TOKEN_PACKAGE` — GitHub Personal Access Token scoped to write packages

## Configuration Management
- `application.properties` per module (`app-a`, `app-b`) contains only `spring.application.name` and `spring.application.version` (Maven token).
- No environment-specific config files; no Spring profiles; no external config server.
- Version is injected via Maven resource filtering: `@project.version@` is replaced at build time.

## Observability
- No Actuator dependency declared; no `/actuator/health` endpoint. Health checks are served by the custom `/health` endpoint.
- No distributed tracing, metrics exporter, or log aggregation configured in the codebase.
- No structured logging configuration (Logback or Log4j2).

## Infrastructure Dependencies
- GitHub Actions runners (self-hosted `ubuntu-docker`)
- GitHub Packages registry (Maven artefact destination)
- Target deployment environment (Tomcat or equivalent servlet container) — not defined in this repo

## Operational Risks
1. No Actuator integration means the deployment health probe is a custom endpoint, not standard Spring Boot liveness/readiness probes. This may be incompatible with Kubernetes or platform health-check tooling.
2. `Thread.sleep` in `/slow` endpoint is unbounded relative to thread-pool exhaustion — no request timeout guard is configured.
3. No `.gitignore` customisation was observed beyond the Maven wrapper standard — secrets could accidentally be committed.
4. The shared workflow `om-ci-setup@main` is pinned to `main`, not a tag or SHA, meaning workflow changes upstream can silently break this pipeline.
5. `DEPLOY_TO_PACKAGES: true` means every push to any feature branch publishes a SNAPSHOT to GitHub Packages, potentially cluttering the package registry.
