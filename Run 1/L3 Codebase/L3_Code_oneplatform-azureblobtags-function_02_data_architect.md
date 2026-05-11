# Data Architect Report — oneplatform-azureblobtags-function

## Source Availability Note

No source files are available in this repository clone. Analysis is based on the repository name and inferred purpose within the Onbe Gen-3 OnePlatform architecture. All data architecture observations are inferred; they should be validated against the actual source code when access is restored.

## Inferred Data Models

Azure Blob Index Tags are key-value string pairs (max 10 tags per blob, key ≤128 chars, value ≤256 chars). The function likely works with a tagging schema such as:

| Tag Key | Example Value | Purpose |
|---|---|---|
| `data-classification` | `sensitive`, `public` | PCI DSS / GLBA data classification |
| `contains-pii` | `true`, `false` | GDPR/CCPA applicability indicator |
| `contains-chd` | `true`, `false` | PCI DSS CDE scope indicator |
| `retention-category` | `7y`, `3y`, `1y`, `90d` | Lifecycle management policy target |
| `document-type` | `statement`, `disbursement-confirmation`, `audit-log` | Business document classification |
| `processing-status` | `pending`, `processed`, `archived` | Workflow state |
| `owner-service` | `oneplatform`, `disbursements` | Originating service |

The exact tag schema is unknown without source code access.

## Sensitive Data Handling

Blob tags themselves in Azure are metadata — they do not contain the blob content. However:
- Tags may contain metadata values that are themselves sensitive, e.g., a cardholder ID, account number (last 4), or program identifier used as a tag value. These would be visible in Azure Portal and Azure Monitor Diagnostic Logs.
- If a tag value contains a full account number, PAN, or SSN, this would constitute a PCI DSS / GDPR violation, as Azure Blob tags are stored in plaintext and indexed by Azure.
- **Risk:** The absence of source code means it is impossible to verify that no sensitive data is being written to blob tags.

## Data Flows (Inferred)

```
[Trigger: Azure Event Grid / Service Bus / HTTP]
    --> [Azure Function: oneplatform-azureblobtags-function]
        --> [Azure Blob Storage SDK]
            --> [Azure Blob Storage (blob container)]
                --> [Tag: key=value applied to blob]
```

Inbound trigger payload likely contains:
- Blob URI or container + blob name
- Tag key-value pairs to apply
- Optional: conditional tagging based on existing blob properties

## Encryption and Data Protection

Azure Blob Storage encrypts all data at rest using Azure Storage Service Encryption (SSE) by default (AES-256). Blob tags are encrypted as part of the blob metadata. No additional encryption is applied to tags by the function (tagging is a metadata operation, not a data encryption operation).

Transport: All Azure SDK calls use HTTPS/TLS 1.2+. No plaintext blob tag operations are possible via the standard Azure SDK.

## Retention Concerns

This function exists precisely to manage retention classification — it is the upstream control for Azure Blob Lifecycle Management policies. Its correct operation is therefore critical to:
- PCI DSS Req 10.3 (audit log retention ≥ 12 months)
- PCI DSS Req 9.4 (media retention and secure disposal)
- GDPR Article 5(1)(e) (data minimization / storage limitation)
- GLBA Safeguards Rule (6-year record retention for financial data)

If this function fails or applies incorrect tags, lifecycle policies will be misconfigured, potentially causing either premature deletion (compliance violation) or indefinite retention (GDPR violation).

## PCI DSS Compliance Assessment

- Req 9.4 (Media Classification): This function is a primary control for classifying electronic media containing CHD. Critical function.
- Req 3.1 (CHD Minimization): If tags identify CHD-containing blobs, lifecycle policies triggered by those tags must enforce deletion after the retention period — alignment depends on correct tag values.
- Gap (Unverifiable): Without source code, it is impossible to confirm that no CHD or PII values are written as blob tag values. This must be audited when source access is available.
- Gap (Unverifiable): Error handling and retry logic for failed tag operations is unverifiable. Silent failures would leave blobs without classification tags.
- **Recommended action:** Restore source code access and conduct a targeted audit of tag value construction logic and error handling.
