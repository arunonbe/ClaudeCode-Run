# prepaid-parent_PARENT — Business Analyst View

## 1. Repository Purpose and Business Context

`prepaid-parent_PARENT` (`com.parents:prepaid-parent`, version 6.0.13) is the **Maven parent POM** for all modern prepaid platform services at Onbe. It is a governance artifact, not a deployable service. Its business value lies in enforcing platform-wide consistency: every service that extends this POM inherits standardized dependency versions, build tooling, Java runtime requirements, and security policies.

This parent POM represents Onbe's **engineering standards contract** — it defines what runtime libraries are acceptable for use across the prepaid platform, which Java version to target, and what build governance rules apply.

## 2. Business Governance Capabilities

| Capability | Mechanism | Business Value |
|---|---|---|
| Dependency version management | `<dependencyManagement>` block | Prevents version conflicts; ensures all services use security-patched libraries |
| Java version enforcement | `maven-enforcer-plugin` rule `requireJavaVersion: 21` | Ensures all services run on a supported, maintained Java release |
| Maven version enforcement | `requireMavenVersion: 3.6` | Consistent build tooling across all development environments |
| Ban legacy Log4j 1.x | `bannedDependencies` rule (line 836) | Prevents reintroduction of Log4Shell-vulnerable Log4j 1.x |
| No SNAPSHOT dependencies in release | `requireReleaseDeps` (line 855) | Enforces dependency stability for production releases |
| No duplicate dependency versions | `banDuplicatePomDependencyVersions` | Eliminates silent dependency resolution conflicts |
| Code coverage | JaCoCo 0.8.12 | Mandates test coverage measurement across all child projects |

## 3. Platform Standardization Summary

This POM establishes Onbe's modern platform as a **Spring Boot 3.4.5 / Java 21 / Spring Cloud 2023.0.2** platform. Every new service inheriting from this parent is guaranteed to build against these modern, supported releases.

Notable business-relevant framework choices:
- **Spring Boot 3.4.5**: Production-grade microservices framework; LTS-aligned
- **Spring Cloud 2023.0.2**: Service discovery, circuit breakers, config management
- **ActiveMQ 6.1.3**: Message broker for asynchronous payment event processing
- **Resilience4j 2.1.0**: Circuit breaker for payment API resilience (critical for uptime SLAs)
- **MSAL4J 1.16.1**: Microsoft Azure Active Directory authentication (Azure-hosted platform)
- **AWS S3 SDK 1.12.747**: Cloud storage integration (multi-cloud presence)

## 4. Compliance and Security Governance via POM

The enforcer plugin rules directly support PCI DSS and security compliance:

| Rule | PCI DSS Relevance |
|---|---|
| `bannedDependencies` (exclude `log4j:log4j`) | Req 6.3.3 — removes known-vulnerable Log4Shell component |
| `requireReleaseDeps` | Req 6.3.1 — production code must not use development/SNAPSHOT versions |
| `requireJavaVersion: 21` | Java 21 is an LTS release with current security patches |
| `banTransitiveDependencies` (except Spring, Jackson, Hibernate, log4j2) | Controls transitive dependency sprawl; reduces attack surface |

## 5. Child Project Obligations

Any project declaring `prepaid-parent_PARENT` as its Maven parent inherits:
- Mandatory Lombok dependency (compile-time, excluded from JAR)
- Spring Boot starter with Log4j2 (not Logback) as logging framework
- Spring Boot test starter for testing
- JaCoCo code coverage agent execution on `verify` phase

## 6. Version Governance Table — Key Managed Versions

For full stakeholder reference, the following major versions are pinned:

| Library | Version | Notes |
|---|---|---|
| Spring Boot | 3.4.5 | BOM imported; governs all spring-* versions |
| Spring Cloud | 2023.0.2 | BOM imported |
| Java (compile/runtime) | 21 | LTS; Jakarta EE 10 compatible |
| ActiveMQ broker | 6.1.3 | Messaging |
| mssql-jdbc | 12.6.0.jre11 | SQL Server connectivity |
| Bouncy Castle (PGP/crypto) | bcpg-jdk18on 1.78 / bcprov-jdk18on 1.78 | Cryptography for file signing/encryption |
| Resilience4j circuit breaker | 2.1.0 | Payment API fault tolerance |
| Feign (REST client) | 13.1 | Inter-service REST calls |
| AWS S3 SDK | 1.12.747 | Cloud storage |
| MSAL4J | 1.16.1 | Azure AD authentication |
| JaCoCo | 0.8.12 | Code coverage |

## 7. Governance Gap: Legacy Repos Not Inheriting Parent

Significant services analyzed (e.g., `pos-connector_LIB`, `prepaid-batch-framework_LIB`) do **not** inherit from `prepaid-parent_PARENT`. They continue to use severely outdated dependency stacks. Onbe should define a migration roadmap to bring all active services under this parent POM to achieve platform-wide compliance with the version governance it establishes.
