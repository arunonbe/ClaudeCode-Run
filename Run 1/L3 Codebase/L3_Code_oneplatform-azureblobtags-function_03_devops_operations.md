# DevOps & Operations Report — oneplatform-azureblobtags-function

## Source Availability Note

The repository contains only a `.git` directory with no working tree files. No `pom.xml`, `build.gradle`, `Dockerfile`, `host.json`, GitHub Actions workflows, or `local.settings.json` are available for analysis. All observations are inferred from the repository name, naming conventions used in the Onbe estate, and the parent POM's Azure Functions profile.

## Build System (Inferred)

Based on the repository name suffix `-function` and the Gen-3 platform context, this application is an Azure Functions app likely built with:
- **Build tool:** Apache Maven (consistent with all other Gen-3 Onbe repos analyzed)
- **Parent POM:** `com.onbe.spring.boot:onbe-spring-boot-parent` (the standard Gen-3 parent)
- **Maven profile:** `spring-cloud-azure-function` (defined in the parent POM, targeting Azure Functions v4 on Java 21 Linux)
- **Framework:** Spring Cloud Function on Azure Functions v4 runtime

Azure Functions Java apps in the Onbe estate are expected to follow the pattern:
- `host.json` — Azure Functions runtime configuration
- `local.settings.json` — local development environment variables (should not contain real secrets)
- `azure-functions-maven-plugin` — for packaging and deployment to Azure

## CI/CD Pipeline (Inferred)

Based on patterns observed in other Onbe Gen-3 repos (`petstore-spring-flux-rest-server`):
- **Platform:** GitHub Actions, delegating to `Onbe/om-ci-setup/.github/workflows/java-workflow.yml@main`
- **Expected triggers:** Push to `main` (deploy), pull request (build + test)
- **Expected steps:** Maven build → CodeQL analysis → container/function package → Azure deployment

Without the actual workflow file, it is impossible to confirm the specific deployment target (Azure subscription, resource group, function app name).

## Deployment Model (Inferred)

**Azure Functions (consumption or premium plan, Java 21, Linux):**
- The function app would be deployed to Azure via the `azure-functions-maven-plugin`
- Secrets (storage connection strings, service principal credentials) would be sourced from Azure Key Vault via Dapr or Azure App Configuration, consistent with Onbe Gen-3 patterns
- The function app identity would use Azure Managed Identity for authentication to Azure Blob Storage (no static connection strings in code)

**Trigger type candidates:**
- Azure Event Grid trigger (blob created/modified events)
- Azure Service Bus trigger (event-driven from another OnePlatform service)
- HTTP trigger (REST-invoked tagging operation)
- Timer trigger (batch tagging job)

## Secrets Management (Inferred)

Following Onbe Gen-3 standards:
- No hardcoded Azure Storage connection strings — Managed Identity or Dapr secret store
- Azure Key Vault referenced via Dapr `service-secret-store` component
- `local.settings.json` would contain development placeholders only (should be in `.gitignore`)

## Observability (Inferred)

Consistent with other Gen-3 Onbe services:
- Azure Application Insights integration (standard for Azure Functions)
- Micrometer metrics (if Spring Boot Actuator is included)
- Structured Logstash JSON logging (from `onbe-spring-boot-starter-logback`)
- Azure Monitor Diagnostic Logs for blob tag operation audit trail

## EOL / Risk Assessment

- The repository being empty in the clone is itself an operational risk: if the source code is not in version control or is on a branch not cloned, then there is no auditable code history, no ability to review changes, and no CI/CD pipeline validation.
- Azure Functions v4 (Java 21) is the current generation — no EOL risk for the runtime itself.
- If this function uses the `spring-boot-thin-layout` experimental artifact (referenced in the parent POM's Azure Functions profile), that artifact carries long-term supportability risk.

## Operational Risks

1. **Empty repository:** Source code is not available for review, CI/CD analysis, or security scanning. This is a significant governance gap.
2. **Unknown error handling:** If the function silently fails on blob tag write operations, no observable error will surface and blobs will be left without classification tags — breaking downstream lifecycle management without an alert.
3. **Permissions scope:** Azure Blob tag write operations require the `Storage Blob Data Owner` or custom role with `Microsoft.Storage/storageAccounts/blobServices/containers/blobs/tags/write`. Overly broad permissions (e.g., subscription-level `Contributor`) would violate least-privilege (PCI DSS Req 7).

**Recommended action:** Restore source code to the repository, establish CI/CD pipeline, and perform a full security review of the function's RBAC configuration and error handling.
