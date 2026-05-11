# Enterprise Architect Report — test-east-deploy

## Platform Generation

**Gen-3 pipeline pattern**. The use of Java 21, Spring Boot 3.4.2, Jakarta EE namespace (Tomcat 10.x), GitHub Actions with a shared reusable workflow (`om-ci-setup`), and GitHub Packages as the artifact registry all indicate this is a Gen-3 (NexPay/Onbe) infrastructure pattern. The repository was created to validate the Gen-3 CI/CD pipeline, not to deploy a business service.

## Integration Patterns

- **Shared reusable GitHub Actions workflow**: The `build-east-java.yml` pattern enforces pipeline standardization across all Gen-3 Java repositories. This is the correct enterprise pattern for pipeline governance.
- **Self-hosted runner support**: The `cicd-deployment.yml` references `BUILD_RUNNER: 'self-hosted'`, indicating that the east-deploy pipeline is also designed to work with on-premises Jenkins-style runner infrastructure, not just cloud-native GitHub-hosted runners.
- **GitHub Packages as artifact registry**: All Gen-3 artifacts flow through `https://maven.pkg.github.com/onbe/onbe_maven_releases`, consolidating the artifact registry from the legacy Nexus instances used in Gen-1 (Wirecard/Northlane).

## External Dependencies

- `Onbe/om-ci-setup` repository (shared GitHub Actions workflows) — critical dependency.
- GitHub Packages (`onbe/onbe_maven_releases`) — artifact registry.
- Maven Central (`https://repo1.maven.org/maven2`) — public dependency resolution.
- No runtime external dependencies (no database, no messaging, no external APIs).

## Position in the Broader Platform

This repository acts as a **pipeline canary** or **smoke test** for the east-deploy infrastructure. It should be the first repository updated when the shared build workflow changes, and its green status is a prerequisite for deploying other services. In a mature DevOps organization, this function would be handled by a dedicated pipeline integration test framework rather than a separate application repo.

## Migration Blockers

None. The repository is already at Gen-3 standards (Java 21, Spring Boot 3.x, GitHub Actions). It does not need migration.

## Strategic Status

**Active infrastructure support**. This repository is actively needed while the east-deploy pipeline is in use. Once the pipeline is stable and covered by integration tests in the `om-ci-setup` repository itself, this throwaway repo could be archived. Recommend keeping it active as a pipeline health indicator. It should be included in release smoke tests for the shared CI/CD infrastructure.
