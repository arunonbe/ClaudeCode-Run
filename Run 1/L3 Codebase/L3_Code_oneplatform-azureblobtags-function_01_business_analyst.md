# Business Analyst Report — oneplatform-azureblobtags-function

## Source Availability Note

The repository `oneplatform-azureblobtags-function` was cloned as a shallow repository and contains only the `.git` metadata directory with no working tree files (no source code, no build files, no README, no configuration files). The repository HEAD and remote references are present but no content was retrieved in the clone. This analysis is therefore based on the repository name, naming conventions used across the Onbe 363-repo estate, and contextual knowledge of the OneP latform Gen-3 Azure architecture.

## Inferred Business Purpose

Based on the repository name, `oneplatform-azureblobtags-function` is most likely an Azure Functions application (Java or Kotlin, Gen-3) that manages or applies metadata tags to Azure Blob Storage objects within the OnePlatform ecosystem. Blob tagging in a payments context typically serves one or more of the following purposes:

- **Document lifecycle management:** Tagging blob objects (e.g., payment statements, disbursement confirmations, cardholder correspondence) with metadata such as document type, processing status, retention category, and data classification. Azure Blob Index Tags enable server-side filtered queries and lifecycle policy targeting.
- **Compliance and data classification:** Applying PCI DSS data classification tags (e.g., `data-classification=sensitive`, `contains-pii=true`, `retention=7y`) to blobs so that Azure Blob Lifecycle Management policies can enforce retention and deletion schedules required by PCI DSS Requirement 9.4 and GDPR/CCPA right-to-erasure.
- **Event-driven processing:** The function may be triggered by Azure Blob events (via Azure Event Grid or Azure Service Bus) and retroactively apply or update tags as blobs transition through processing states (e.g., `status=uploaded` → `status=processed` → `status=archived`).

## Capabilities (Inferred)

- Read and write Azure Blob Index Tags via the Azure Blob Storage SDK
- Process blob events (EventGrid trigger, HTTP trigger, or Service Bus trigger)
- Apply standardized metadata tagging schema across OnePlatform-managed blob containers
- Potentially enforce retention classification tags required for GDPR/CCPA data lifecycle management

## Client/Cardholder Impact

If this function manages tags on blobs containing cardholder statements, disbursement records, or transaction receipts, its correct operation directly affects:
- Compliance with data retention obligations (PCI DSS, GLBA, state regulations)
- The ability to respond to GDPR/CCPA right-to-erasure requests (deletion lifecycle policies depend on correct tagging)
- Audit trail integrity (improperly tagged audit log blobs could cause premature deletion)

## Regulatory Obligations

- **PCI DSS v4.0.1 Req 9.4:** Media (including electronic media/blobs) containing CHD must be classified and protected. Blob tags are an implementation mechanism for this classification.
- **PCI DSS Req 10.3:** Audit log retention — if audit logs are stored in Blob Storage, retention tags must be set correctly (minimum 12 months retention required).
- **GDPR Article 5(1)(e) / CCPA:** Data minimization and purpose limitation — lifecycle tags enable automated deletion of PII-containing blobs after their retention period expires.
- **GLBA Safeguards Rule:** Retention and disposal requirements for financial records.

## Key Business Risks

- Without source code access, the specific implementation, error handling, and retry logic cannot be assessed. A function that fails silently (swallowing exceptions) would leave blobs untagged, breaking any downstream lifecycle policies.
- Incorrect tagging (e.g., applying `retention=0d` to a blob containing CHD audit records) could cause premature deletion of records required for PCI DSS compliance.
- If the function has broad write access to blob tags across all containers, a misconfiguration could affect all blobs in the storage account.
- **Action required:** The engineering team should ensure this repository's source code is available in the clone for proper analysis, and that the repository is not accidentally empty due to a clone/checkout issue.
