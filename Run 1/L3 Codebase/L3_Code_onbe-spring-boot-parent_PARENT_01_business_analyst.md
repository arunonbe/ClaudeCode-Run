# Business Analyst Report — onbe-spring-boot-parent_PARENT

## Business Purpose

`onbe-spring-boot-parent` is Onbe's enterprise-wide Maven Bill of Materials (BOM) and parent POM for all Spring Boot microservices built on the Gen-3 platform. It is a pure POM artifact (`<packaging>pom</packaging>`) with no executable code — its sole function is to centralize and govern dependency versions, plugin versions, build conventions, and Maven profiles used by every Onbe Spring Boot service. It is the topmost dependency governance artifact in the Gen-3 platform hierarchy.

In the payments context, this artifact ensures that all Onbe services — whether handling ACH disbursements, prepaid card loads, push-to-card, or wallet operations — are built on consistent, vetted library versions that satisfy PCI DSS software supply chain requirements. It is a risk management artifact as much as a technical convenience.

## Capabilities

- **Dependency Version Governance:** Manages versions for 50+ dependencies including Spring Boot (3.4.3), Spring Cloud Azure (5.20.0), Dapr SDK (1.13.3), Kotlin (2.1.10), Resilience4j (2.3.0), R2DBC MSSQL (12.8.1), Debezium (3.0.7), and OpenTelemetry (2.13.1-alpha).
- **Build Plugin Management:** Standardizes Maven plugin versions and configurations for compilation (Kotlin 2.1 + Java 21), testing (JUnit 5, Surefire 3.5.2), SBOM generation (CycloneDX 2.9.1), static analysis (CodeQL via CI), dependency analysis (depclean), and Docker image building (Spring Boot build-image, Fabric8 Docker plugin).
- **OpenAPI Code Generation Standards:** Pre-configures `openapi-generator-maven-plugin` (v7.11.0) with Onbe-standard settings: Spring Boot 3 compatibility, WebFlux reactive delegate pattern, Lombok builder annotations, Jakarta EE, Jackson serialization, and bean validation.
- **Azure Functions Deployment Profile:** The `spring-cloud-azure-function` Maven profile provides plugin management for Azure Functions deployment (Java 21, Linux runtime, Azure Functions Extension v4).
- **License Compliance:** Enforces GPL/AGPL license exclusion via the license-maven-plugin, preventing copyleft dependency contamination.
- **Avro Schema Support:** Manages the Avro Maven plugin for schema-driven event serialization, supporting event-driven payment notification patterns.

## Client/Cardholder Impact

No direct client or cardholder interaction. However, this POM's decisions affect every Onbe payment service. A vulnerability introduced through a dependency version change here (e.g., a compromised library version, an insecure Spring Boot update) would affect all Gen-3 services simultaneously, potentially exposing cardholder data or disrupting payment processing.

## Business Rules in Code

- Maven enforcer requires Java ≥ 21 and Maven ≥ 3.9.0 for all builds — prevents accidental compilation on EOL JVMs.
- Pre-release versions (alpha, beta, RC, M, Dev, preview) are excluded from version update candidates via the `maven-versions-plugin` `ignoredVersions` pattern — enforcing production-quality dependency selection.
- GPL v1/v2/v3 and AGPL v3 licenses are explicitly excluded from allowed licenses.
- The `openapi.schema.download.skip=true` default prevents unintended schema downloads during builds that don't opt in.
- Container image build is skipped by default (`spring-boot.build-image.skip=true`) and must be explicitly enabled per-service.

## Regulatory Obligations

- **PCI DSS v4.0.1 Req 6.3 (Software Composition Analysis):** CycloneDX SBOM generation at every package phase creates an auditable record of all third-party components, enabling vulnerability management per PCI DSS 6.3.2.
- **PCI DSS Req 6.2 (Secure Development):** Enforcing minimum Java 21 LTS eliminates EOL runtime risk. Dependency version governance reduces the risk of known-vulnerable library versions entering production.
- **PCI DSS Req 12.3 (Supply Chain Risk):** Centralized version management provides a single control point for responding to supply-chain security events (e.g., Log4Shell-class incidents). License exclusion prevents GPL/AGPL contamination.
- **GLBA/GDPR:** Consistent security library versions across all services reduce the surface area of data protection vulnerabilities.

## Key Business Risks

- **Single Point of Version Control:** Any error in this POM — a mismanaged dependency override, a vulnerable library version, or a broken plugin configuration — propagates to all Gen-3 services. The blast radius of a mistake here is the entire Gen-3 fleet.
- **SNAPSHOT Version in Production Chains:** The parent is currently at `0.0.22-SNAPSHOT`. Services consuming a SNAPSHOT parent receive non-reproducible builds and are at risk of unexpected behavior if the SNAPSHOT is updated without a coordinated release.
- **OpenTelemetry Alpha:** `opentelemetry-instrumentation.version=2.13.1-alpha` is an alpha artifact managed in the BOM. Alpha dependencies in a payments context carry stability and support risks.
- **QueryDSL Plugin JDBC URL with Placeholder Password:** The `querydsl-maven-plugin` configuration in the parent POM contains a literal `password=*****` placeholder in the JDBC URL comment. This should be confirmed as a documentation placeholder only, not an actual credential.
