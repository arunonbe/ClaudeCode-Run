# Business Analyst View — nexpay-parent

## Service Identity

| Attribute | Value |
|-----------|-------|
| Artifact ID | `nexpay-parent` |
| Group ID | `com.onbe.nexpay` |
| Current version | `0.2.8-SNAPSHOT` |
| Packaging | `pom` (not a deployable service) |
| Inception Year | 2025 |
| GitHub URL | `https://github.com/OnbeEast/nexpay-parent` |
| Published to | GitHub Packages (`maven.pkg.github.com/onbe/onbe_maven_releases`) |

## Business Purpose

The nexpay-parent is not a deployable service — it is the Maven BOM (Bill of Materials) and build configuration parent for all NexPay Gen-3 microservices. Its business purpose is to ensure consistency, traceability, and standards compliance across the entire NexPay platform by managing:

1. **Dependency versions**: All NexPay services inherit dependency versions from this POM, ensuring that a security patch applied to one library (e.g., upgrading Spring Boot or Jackson) propagates to all services through a single parent POM update.

2. **Build plugin configuration**: Compiler settings, test runner configuration, code coverage (JaCoCo), and OpenAPI code generation are standardised across all services.

3. **Quality gates**: The `maven-enforcer-plugin` enforces minimum versions of Maven (4.0.0-rc-5) and Java (25) across all services, preventing deployment of services compiled with older, potentially insecure toolchains.

4. **Observability standards**: OpenTelemetry is a first-class dependency in the parent POM (`spring-boot-starter-opentelemetry`), ensuring all NexPay services emit traces, metrics, and logs in a consistent format.

## Business Value

### Governance Through Convention

For a PCI DSS Level 1 certified payments platform, the ability to enforce consistent versions across all services is a governance necessity, not just a developer convenience. PCI DSS Requirement 6.3 requires systematic patching of vulnerabilities. A shared parent POM means that patching a vulnerable library requires updating only the parent POM and redeploying all services — without requiring each team to independently discover and apply the patch.

### Platform-Wide Standards

The parent POM establishes the following platform-wide standards:
- **Spring Boot 4.0.5**: All NexPay services run on the same Spring Boot version. This is significant because Spring Boot 4 requires Java 17+ and introduces breaking changes from Boot 3. The parent POM comment explicitly warns: "NOT backwards compatible with previous Spring Boot 3."
- **Java 25**: The platform targets Java 25 (LTS candidate), taking advantage of virtual threads (Project Loom) as a first-class feature.
- **Testcontainers**: All services have Testcontainers available for integration tests, enabling realistic testing against actual database and messaging infrastructure.

### Release Cadence

The parent POM version (`0.2.8-SNAPSHOT`) indicates the platform is in active, early-stage development (pre-1.0). The SNAPSHOT suffix means the parent POM itself is not yet at a stable release, which introduces a risk: services inheriting from a SNAPSHOT parent may get different dependency resolutions at different build times if the parent is modified between builds. For production deployments, the parent POM version should be a released (non-SNAPSHOT) artifact.

## Key Dependencies Managed

| Dependency | Version | Purpose |
|---|---|---|
| Spring Boot | 4.0.5 | Core framework for all services |
| Spring Cloud Azure | 7.1.0 | Azure App Configuration, Key Vault, Service Bus |
| MapStruct | 1.6.3 | Object mapping (DTO ↔ entity) |
| SpringDoc OpenAPI | 3.0.3 | Swagger UI and API documentation |
| OpenAPI Generator | 7.21.0 | Code generation from OpenAPI specs |
| Spring Retry | 2.0.12 | Retry logic for resilient service calls |
| Lombok | Managed by Spring Boot | Boilerplate reduction |
| Testcontainers | Managed by Spring Boot | Integration testing |
| OpenTelemetry | Managed by Spring Boot | Distributed tracing and metrics |

## Developer and Organisation Information

The POM lists two developers:
- Andrew Smirnoff (andrew.smirnoff@onbe.com)
- Rubens Gomes (rubens.gomes@onbe.com)

This identifies the platform owners responsible for parent POM governance decisions, including security patching, dependency upgrades, and build standard changes.

## Regulatory Relevance

- **PCI DSS Requirement 6.3**: The enforcer plugin's minimum version rules and Dependabot configuration on the parent POM provide the mechanism for systematic dependency patching required by PCI DSS.
- **PCI DSS Requirement 6.2**: The JaCoCo coverage enforcement and testing framework standards support the secure development lifecycle requirement.
- **NIST CSF Protect**: Centralised dependency management is a key asset protection control.
