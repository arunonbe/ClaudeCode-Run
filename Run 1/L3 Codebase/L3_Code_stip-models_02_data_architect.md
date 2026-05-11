# stip-models — Data Architect View

## Data Stores
None. The repository is empty of source files.

## Schema / Tables
None defined. This repository is intended to be the source of schema definitions.

## Sensitive Data Elements (Intended scope)
When implemented, STIP model definitions would need to define or reference:

| Data Element | PCI DSS Classification | Handling Requirement |
|---|---|---|
| Card identifier / token | Account Data | Must use tokenised reference — not full PAN in models |
| Transaction amount | Non-PCI, but financially sensitive | Standard protection |
| Merchant Category Code | Non-PCI | Standard |
| Account status flags | Account Data | PCI Req 3 — restrict access |
| Available balance / limit | Financially sensitive | GLBA, Reg E |
| Stand-in decision result | Audit data | PCI Req 10 — retain for 12 months |

## Encryption
Not applicable — no content present. When implemented, any model fields that represent PANs or SAD must be explicitly typed as opaque/tokenised — the schema itself should not permit plain PAN values.

## Data Flow (Intended)
```
stip-models schema definitions (OpenAPI/XSD/Protobuf)
    |
    v (code generation pipeline)
    |
stip-generated (Java DTOs / stubs)
    |
    v
STIP runtime services:
    stand-in-processing-api
    stand-in-recovery-service
    |
    v (at runtime)
    |
STIP decision engine ←→ Card account data store
    |
    v
Authorisation response → Network (Visa/Mastercard)
    |
    v
Audit log (PCI DSS Req 10)
```

## Data Quality / Retention
Not applicable — no content.

## Compliance Gaps
| Gap | Standard | Notes |
|---|---|---|
| No model definitions | PCI DSS, FFIEC | STIP domain model is absent — all downstream compliance requirements are unmet |
| No data classification in models | PCI DSS Req 3 | Models must classify fields by data sensitivity when defined |
| No schema validation rules | GDPR / CCPA | Input validation constraints should be embedded in model definitions |

## Recommendations
When implementing:
1. Use a schema format that supports documentation/annotation of field sensitivity (OpenAPI `x-pci-classification` extension, for example).
2. Define card identifiers as token/masked types — never as a plain 16-digit numeric string.
3. Include model-level validation constraints (maxLength, pattern, required) to enforce data quality at the contract layer.
4. Apply semantic versioning to model releases so consuming services can pin to a specific schema version.
