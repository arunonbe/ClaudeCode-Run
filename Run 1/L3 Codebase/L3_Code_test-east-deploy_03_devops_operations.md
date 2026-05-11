# DevOps / Operations Report — test-east-deploy

## Build System

**Maven 3.x** via Maven Wrapper (`mvnw` / `mvnw.cmd`). Maven wrapper properties reference the standard Apache Maven distribution. The `pom.xml` uses:
- `spring-boot-starter-parent:3.4.2` as the parent BOM.
- `spring-boot-maven-plugin` for packaging.
- `maven-release-plugin:3.0.1` for versioned release tagging (tag format: `@{project.version}`).
- Java 21 compiler target.
- WAR packaging for Tomcat deployment.

## CI/CD Pipeline

**GitHub Actions** via two workflow files:

1. **`.github/workflows/build.yml`** — Main build trigger:
   - Fires on push to `main`, `release/**`, `feature/**`, and manual dispatch.
   - Calls shared reusable workflow: `Onbe/om-ci-setup/.github/workflows/build-east-java.yml@main`.
   - Parameters: `JAVA_VERSION: '21'`, `BUILD_RUNNER: 'ubuntu-docker'`, `DEPLOY_TO_PACKAGES: true`.
   - Passes `PAT_TOKEN_PACKAGE` secret as `PAT_TOKEN`.
   - Supports `skip_tests` boolean input (default: `false`).

2. **`cicd-deployment.yml`** (workflow_dispatch only):
   - Same shared workflow call but with `BUILD_RUNNER: 'self-hosted'`.
   - Adds `deploy_to_production` input (default: `false`).
   - This suggests the east-deploy pipeline supports self-hosted runners for on-premises environments.

## Deployment Model

WAR artifact deployed to a Tomcat 10.x container. The `spring-boot-starter-tomcat` is scoped `provided`, confirming Tomcat is provided by the target server rather than embedded. GitHub Packages is used as the artifact registry.

## Runtime

- **Java 21** (LTS, not EOL — supported until September 2029).
- **Spring Boot 3.4.2** — current supported release.
- **Tomcat 10.x** (Jakarta EE 9+, Jakarta namespace).
- Maven Wrapper pinned to the version in `.mvn/wrapper/maven-wrapper.properties`.

No EOL runtime concerns in this repository.

## Secrets Management

- `PAT_TOKEN_PACKAGE` is consumed from GitHub Actions encrypted secrets — correct practice.
- `settings.xml` uses `${env.GITHUB_TOKEN}` for Maven server authentication — correct environment variable injection pattern.
- No hardcoded credentials detected anywhere in the repository.

## Observability

No runtime observability is configured (no actuator endpoints, no log configuration, no metrics). This is appropriate for a throwaway pipeline-test application. The application does not run in production and therefore does not require monitoring.

## EOL Runtimes / CVEs

None in this repository. Java 21 and Spring Boot 3.4.2 are both current. The only dependency risk would be inherited transitively from Spring Boot's BOM, which should be evaluated by the organization's SCA tooling.

## Operational Notes

- The `maven-release-plugin` configuration uses `autoVersionSubmodules: true` and tag format `@{project.version}`, consistent with standard Onbe release practices.
- The shared `build-east-java.yml` workflow is the single point of failure for the east-deploy pipeline pattern. Any breaking change to that workflow affects this repo and all repos that reference it.
