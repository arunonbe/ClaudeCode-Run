# az-appconfig-demo — Enterprise Architect View

## Platform Generation (Gen-1/Gen-2/Gen-3)

**Assessment: Gen-2 transitioning toward Gen-3 patterns.**

Evidence for Gen-2/Gen-3 characteristics:
- **Java 21** with virtual threads (`AppConfig.java` line 29: `executor.setVirtualThreads(true)`) — this is a Gen-3 runtime choice.
- **Spring Boot 3.x** (implied by `onbe-spring-boot-parent:0.0.22-SNAPSHOT` and the explicit note in README.md line 22 about Spring Boot 3.x compatibility).
- **Azure-native configuration** via Azure App Configuration and Key Vault — cloud-native config management, consistent with a Gen-2/Gen-3 platform posture.
- **Managed Identity authentication** for qa/stage/prod (`bootstrap.yaml` lines 53–64) — eliminates static credentials in deployed environments, a Gen-3 security baseline.
- **Structured JSON logging** (Logstash format) — consistent with centralised log aggregation expected in a Gen-3 platform.
- **SBOM generation** via CycloneDX (`pom.xml` lines 112–114) — a Gen-3 supply chain security practice.

Gen-1/Gen-2 residue:
- **SNAPSHOT dependency** on parent POM — non-production-grade dependency management.
- **No test suite** — absent automated testing is characteristic of older generation services.
- **Feature branch CI references** in workflow files — indicates the platform tooling itself is still maturing.
- **Static `GET /` endpoint** — no OpenAPI spec, no versioned API surface.

## Business Domain

**Internal Platform Infrastructure / Developer Enablement**

This is not a business-domain service (not payments, not disbursements, not cardholder management). It belongs to the **Developer Platform** domain — specifically the **Configuration Management** sub-domain. Its primary consumers are Onbe engineering teams building production microservices who need a reference implementation for Azure App Configuration integration.

Secondary association: The QA `appsettings.json` uses `PetStoreAPI` prefix and `petstore` database references, linking it operationally to the **PetStore reference application** ecosystem used by Onbe for integration testing.

## Role in Platform

`az-appconfig-demo` plays three distinct roles:

1. **Reference Implementation**: The canonical, Onbe-approved pattern for consuming Azure App Configuration, Key Vault references, and Feature Management in a Spring Boot service. Teams are explicitly directed to copy `pom.xml` dependencies from this project (README.md lines 20–24).

2. **Integration Testbed**: Deployed to QA AKS, it exercises the live Azure App Configuration instance (`as-app-configuration.azconfig.io`) and Key Vault integration. This validates the Onbe shared CI/CD pipelines (`om-ci-setup`, `om-cd-setup`) against real Azure infrastructure.

3. **Platform Pipeline Validation**: The `app-config.yml` workflow tests the `app-config-call.yml` reusable workflow (from `om-ci-setup`) for publishing configuration to Azure App Configuration — validating the config-publish pipeline end-to-end.

## Dependencies

### Upstream (this service depends on)

| Dependency | Type | Version/Ref | Risk |
|---|---|---|---|
| `com.onbe.spring.boot:onbe-spring-boot-parent` | Internal parent POM | `0.0.22-SNAPSHOT` | HIGH — SNAPSHOT, non-deterministic |
| `com.onbe.spring.boot:onbe-spring-boot-starter` | Internal library | `0.0.22-SNAPSHOT` | HIGH — SNAPSHOT |
| `com.onbe.spring.boot:onbe-spring-boot-starter-logback` | Internal library | `0.0.22-SNAPSHOT` | HIGH — SNAPSHOT |
| `com.azure.spring:spring-cloud-azure-appconfiguration-config` | Azure SDK | Managed by parent | Medium |
| `com.azure.spring:spring-cloud-azure-feature-management` | Azure SDK | Managed by parent | Medium |
| `com.azure.spring:spring-cloud-azure-starter-storage-blob` | Azure SDK | Managed by parent | Low — declared but unused in visible source |
| `com.microsoft.azure:msal4j` | Microsoft auth | Managed by parent | Medium |
| `Onbe/om-ci-setup` (feature branches) | Shared CI | `@feature/spring-boot-build-image`, `@feature/CLOUDADM-948-app-config` | HIGH — mutable refs |
| `Onbe/om-cd-setup` | Shared CD | `@main` | Medium |
| Azure App Configuration | Azure PaaS | `as-app-configuration.azconfig.io` | Medium |
| Azure Key Vault | Azure PaaS | Not named in this repo | Medium |
| AKS (QA) | Azure PaaS | Managed externally | Low |

### Downstream (services that depend on this)

No downstream service dependencies exist. This service exposes only `GET /` (a static string), has no published API contract, and is not registered in APIM (`PUBLISH_TO_APIM: false`). Other Onbe services copy its patterns but do not call it at runtime.

## Integration Patterns

| Pattern | Implementation | Evidence |
|---|---|---|
| Externalised Configuration | Spring Cloud Azure AppConfig client | `bootstrap.yaml` lines 21–46 |
| Secrets Management via Reference | Azure Key Vault reference in App Config | `appsettings.json` lines 7–10; `bootstrap.yaml` lines 62–64 |
| Feature Flags | Azure App Configuration Feature Management | `AppConfig.java`, `AppConfigController.java`, `appsettings.json` lines 11–14 |
| Dynamic Config Refresh (Push) | Event Grid webhook + token auth | `bootstrap.yaml` lines 36–39 |
| Dynamic Config Refresh (Poll) | Sentinel key polling, 15-minute interval | `bootstrap.yaml` lines 29–35 |
| Managed Identity Auth | Azure Managed Identity (UAMI) | `bootstrap.yaml` lines 53–64 |
| Structured Logging | Logstash JSON via Logback | `compose.yaml` lines 34–35 |
| Container Build | Spring Boot Buildpacks (not Dockerfile for image) | `deployment.yml` line 29; `pom.xml` lines 116–128 |
| SBOM | CycloneDX at build time | `pom.xml` lines 112–114 |

No message broker, event streaming, REST client calls to other Onbe services, or database write patterns are present.

## Strategic Status

**Status: ACTIVE REFERENCE — Strategic for Platform Onboarding**

This repository is strategically important as a template accelerator. Its value is not in the running service but in the patterns it encodes. Key strategic concerns:

- The CI workflow references to **feature branches** (`@feature/spring-boot-build-image`, `@feature/CLOUDADM-948-app-config`) suggest the platform tooling that this demo validates is itself not yet stabilised. Once those feature branches merge to `main` in `om-ci-setup`, the workflow refs should be updated.
- The **SNAPSHOT parent version** must be resolved to a release version before this can serve as a reliable reference. Engineers copying `pom.xml` will inherit the SNAPSHOT dependency.
- **`spring-cloud-azure-starter-storage-blob`** is declared as a dependency (`pom.xml` line 95) but no Blob Storage integration is present in the source code. This may be an aspirational dependency or a copy-paste artefact. It should be removed to keep the reference clean.
- The **`appsettings.json` prefix mismatch** (`PetStoreAPI` vs `om-audit-logging-api`) suggests incomplete alignment between the demo's identity and the config it actually manages. This should be corrected so the reference is internally consistent.

## Migration Blockers

For Gen-3 promotion of the **pattern** this repo represents (i.e., for teams adopting this pattern in production services):

1. **SNAPSHOT dependencies**: `onbe-spring-boot-parent:0.0.22-SNAPSHOT` must be released. Production services must not inherit SNAPSHOT parents.
2. **Feature branch CI references**: `om-ci-setup@feature/spring-boot-build-image` must be merged and tagged before production use.
3. **No test suite**: Reference implementations should include at least one integration test demonstrating successful App Config binding (e.g., a `@SpringBootTest` that verifies `DatabaseConfigProperties` fields are non-null when environment variables are set).
4. **`sa` account pattern in QA config**: `appsettings.json` must not use `sa` credentials; this would be a direct migration blocker if replicated in a production service.
5. **Container scan suppressed**: Must be re-enabled and all CVEs addressed before any derived production service can pass security gates.
6. **Root container execution** (local compose): Should be corrected in the reference to prevent teams from copying the `user: "0:0"` pattern.
7. **Unused `spring-cloud-azure-starter-storage-blob` dependency**: Adds attack surface and build weight without value; must be removed from the reference pom.
