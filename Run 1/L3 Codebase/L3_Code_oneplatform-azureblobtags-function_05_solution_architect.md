# Solution Architect Report — oneplatform-azureblobtags-function

## Source Availability Note

No source files, build files, configuration files, or CI/CD pipeline definitions are present in this repository clone. The repository contains only a `.git` directory with HEAD pointing to `main` and remote references to `origin`. All findings below are structural/governance observations about the repository state itself, supplemented by inferred technical analysis based on the repository name and Onbe Gen-3 patterns.

## API Surface (Inferred)

Azure Functions applications expose one or more function handlers. Based on the inferred purpose:

- **Potential HTTP trigger endpoint:** `POST /api/tag-blobs` — accepts a request body specifying blob URIs and tag key-value pairs to apply
- **Potential Event Grid trigger:** Responds to `Microsoft.Storage.BlobCreated` / `Microsoft.Storage.BlobModified` events
- **Potential Service Bus trigger:** Processes tagging command messages from an internal OnePlatform queue

No actual endpoint definitions can be confirmed without source code.

## Security Posture

### Critical Finding — Repository Contains No Source Code

This is the primary and most critical security finding. A repository with no working tree content means:

1. **No SDLC controls are applied:** The code cannot be reviewed, scanned (CodeQL, SAST, OWASP Dependency-Check), or subject to pull request approval workflows if it doesn't exist in the repository.
2. **No reproducible build:** Without source code and build configuration in version control, the deployed function artifact cannot be reproduced, audited, or verified. This violates PCI DSS Requirement 6.2 (secure development lifecycle) and the concept of a trustworthy software supply chain.
3. **No SBOM:** CycloneDX SBOM generation (required by PCI DSS Req 6.3.2) cannot occur without a build file.
4. **No dependency vulnerability management:** Without a `pom.xml` or `build.gradle`, dependency versions cannot be tracked or scanned.

If this function is deployed in a production environment handling OnePlatform data, this represents a critical compliance gap.

### Potential Security Considerations (Inferred)

**Blob Tag Write Permissions:**
Azure Blob tag write operations require elevated storage RBAC roles. If the function's managed identity is assigned `Storage Blob Data Owner` at the account or subscription scope rather than the minimum required container scope, it violates least-privilege (PCI DSS Req 7).

**Tag Value Injection Risk:**
If tag values are constructed from externally provided inputs (e.g., an HTTP request body containing arbitrary tag values), and those inputs are not validated, an attacker with access to the function endpoint could write arbitrary tag values to blobs. While Azure Blob tags do not execute code, malicious tags could corrupt lifecycle management policies by assigning incorrect retention categories.

**Event Grid Validation:**
If triggered via Azure Event Grid, the function must implement Event Grid's handshake validation (subscription validation event handling). Failure to do so would cause the Event Grid subscription to fail. This is a reliability concern, not a direct security vulnerability, but misconfigured Event Grid subscriptions can cause silent message loss.

## Technical Debt

- **Empty repository as deployed artifact:** The most significant technical debt item is the apparent disconnect between the deployed function (if it exists in production) and its source code repository. This must be resolved as the highest priority action.

## Findings Summary

| Finding | Severity | Regulatory Mapping |
|---|---|---|
| No source code in repository | Critical | PCI DSS Req 6.2, 6.3.2 |
| No SBOM generation possible | High | PCI DSS Req 6.3.2 |
| No dependency vulnerability scanning | High | PCI DSS Req 6.3.3 |
| No CI/CD pipeline observable | High | PCI DSS Req 6.2.4 |
| RBAC scope unverifiable | Medium | PCI DSS Req 7 |
| Tag value injection risk | Medium | PCI DSS Req 6.2 |

## Recommendations

1. **Immediate:** Investigate whether source code exists on a non-default branch (`dev`, `develop`, `feature/*`) or in a different repository. If found, consolidate to `main`. If not found, treat this as a lost-code incident and conduct an emergency security review of the deployed function artifact.
2. **Short-term:** If the function is deployed, extract its configuration (RBAC assignments, trigger type, output bindings) from Azure Portal and document it as compensating controls until source code is available.
3. **Short-term:** Verify the managed identity RBAC scope for blob tag write permissions — it should be scoped to the specific storage account containers, not subscription-wide.
4. **Medium-term:** Once source code is restored, run CodeQL, OWASP Dependency-Check, and CycloneDX SBOM generation and remediate any findings before the next production deployment.
