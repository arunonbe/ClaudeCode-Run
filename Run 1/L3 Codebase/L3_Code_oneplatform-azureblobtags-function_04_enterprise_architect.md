# Enterprise Architect Report — oneplatform-azureblobtags-function

## Source Availability Note

No source files are present in this repository clone. This analysis is based on the repository name, naming conventions observed across the Onbe 363-repo estate, and the broader OnePlatform Gen-3 Azure architecture context.

## Platform Generation

**Gen-3 (NexPay/Onbe) — inferred.** The repository naming convention `oneplatform-*-function` aligns directly with Onbe's Gen-3 Azure Functions pattern. The `onbe-spring-boot-parent` POM's `spring-cloud-azure-function` profile and the presence of `azure-functions-maven-plugin` 1.37.0 in the parent BOM confirm that Azure Functions is a first-class deployment target in the Gen-3 architecture.

## Position in OnePlatform Architecture

The `oneplatform` prefix designates this as a component of Onbe's OnePlatform — the Gen-3 unified payment processing platform. Within the OnePlatform ecosystem, blob tag management serves as an infrastructure cross-cutting concern:

```
[OnePlatform Core Services] 
    --> [Document/Artifact Storage: Azure Blob Storage]
        --> [oneplatform-azureblobtags-function]  (metadata governance)
            --> [Azure Blob Lifecycle Management Policies]
                --> [Retention / Archival / Deletion enforcement]
```

This function occupies a data governance supporting role — it does not directly process payments but governs the lifecycle of data artifacts produced by payment processing.

## Integration Patterns (Inferred)

- **Event-driven:** Most likely triggered by Azure Event Grid blob events or Azure Service Bus messages from other OnePlatform services — consistent with Gen-3 event-driven patterns.
- **Azure SDK direct:** Interacts directly with Azure Blob Storage SDK for tag operations (not via Dapr state store, which does not support blob tag semantics).
- **Azure Managed Identity:** Expected to authenticate to Azure Blob Storage via MSI (no static keys), consistent with Gen-3 security standards.
- **Azure App Configuration:** May receive tagging schema configuration (tag keys, allowed values) from Azure App Configuration for runtime governance without redeployment.

## External Dependencies (Inferred)

| Dependency | Version (Inferred) | Purpose |
|---|---|---|
| Spring Cloud Function | Via parent BOM | Azure Functions handler |
| Azure Functions Maven Plugin | 1.37.0 (from parent) | Packaging and deployment |
| Azure Blob Storage SDK | Via spring-cloud-azure 5.20.0 | Tag read/write operations |
| Azure Identity | 1.15.2 (from parent) | Managed Identity auth |
| Dapr SDK | 1.13.3 (from parent) | Secrets (if needed) |

## Strategic Assessment

**Supporting infrastructure function within OnePlatform Gen-3.** This function serves a governance and compliance role for the broader OnePlatform data estate. Its strategic importance is proportional to how extensively Azure Blob Storage is used for cardholder data artifacts (statements, disbursement records, audit logs). If OnePlatform stores CHD-adjacent documents in Blob Storage, this function is in scope for PCI DSS and must be subject to the same change management and security review processes as payment processing services.

## Migration Considerations

- No Gen-1/Gen-2 equivalent is likely — blob tag management is a cloud-native pattern with no precedent in older on-premises payment systems. This is a net-new Gen-3 capability.
- The function should be integrated with OnePlatform's data classification framework to ensure consistency with other data governance controls (database column-level encryption, field masking, API response filtering).

## Governance Gap

The empty repository represents a governance gap: if this function is deployed in production but has no source code in version control, it cannot be subject to:
- Code review and approval gates
- Static security analysis (CodeQL)
- SBOM generation (CycloneDX)
- Dependency vulnerability scanning

This is a PCI DSS Requirement 6.2 (secure development lifecycle) violation if the function is in production scope. The team should investigate whether source code exists on a non-default branch or has been lost, and take corrective action.
