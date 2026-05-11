# stip-models — Solution Architect View

## Technical Architecture
The repository contains only a `.git/` directory with standard git hook sample files. There is no implemented technical architecture.

## API Surface
None.

## Security Posture
Not applicable — no code present.

## Technical Debt
The entire deliverable is absent. As the upstream model source for a tier-1 payments resilience capability, this represents the highest-priority implementation gap in the analysed set of repositories.

## Gen-3 Migration Requirements
This is the starting point for a Gen-3 STIP implementation. Recommended technical approach:

### Schema Format Decision
Choose one of the following, aligned with Onbe's Gen-3 platform standards:
| Format | Use Case | Tooling |
|---|---|---|
| OpenAPI 3.x | REST API contracts (request/response DTOs) | OpenAPI Generator |
| AsyncAPI 2.x | Event-driven contracts (Kafka/Service Bus messages) | AsyncAPI Generator |
| Protocol Buffers | High-performance binary serialisation | protoc + grpc-java |
| JSON Schema | Standalone data model definitions | jsonschema2pojo |

### Security Requirements for Model Definitions
1. **No full PAN fields**: Card identifiers must be defined as opaque token types (`string`, pattern `^[A-Z0-9]{16}$` for a token, not `^\d{16}$` for a PAN).
2. **No CVV/PIN fields**: SAD must not appear in any model definition.
3. **Field-level sensitivity annotations**: Use schema extensions to classify sensitive fields (e.g., `x-pci-field: true`).
4. **Input validation constraints**: Define `maxLength`, `pattern`, `minimum`, `maximum` for all fields to enforce data quality at contract level.
5. **Enum safety**: Use closed enums for status codes, response codes, and decision outcomes — no free-text for structured decisions.

### STIP Entity Model (Recommended Minimum)
```
StipAuthRequest
  - cardToken: string (tokenised card reference, not PAN)
  - transactionAmount: decimal
  - currencyCode: string (ISO 4217)
  - merchantId: string
  - merchantCategoryCode: string (MCC)
  - posEntryMode: enum
  - transactionTimestamp: datetime

StipAuthResponse
  - authorizationCode: string
  - responseCode: enum (APPROVED / DECLINED / REFERRAL)
  - reasonCode: enum
  - stanInIndicator: boolean
  - processingTimestamp: datetime

StipDecisionRecord
  - requestId: UUID
  - cardToken: string
  - decision: enum
  - ruleApplied: string
  - timestamp: datetime
  [for audit log persistence — PCI DSS Req 10]

StipRuleSet
  - programId: string
  - effectiveDate: date
  - velocityLimits: VelocityLimit[]
  - merchantRestrictions: MerchantRestriction[]
  - approvalCriteria: ApprovalCriteria
```

### Code Generation Pipeline Design
```
stip-models/
├── api/
│   └── stip-auth-api.yaml          (OpenAPI 3.x)
├── events/
│   └── stip-decision-event.yaml    (AsyncAPI 2.x)
├── .github/workflows/
│   ├── validate.yml                 (schema validation on PR)
│   └── generate-and-publish.yml    (code gen on merge to main)
└── pom.xml or package.json         (generator tooling config)
```

## Code-Level Risks
| Risk | File | Notes |
|---|---|---|
| Repository is entirely empty | — | No models = no generated code = no STIP capability |
| git hooks are samples only | `.git/hooks/*.sample` | Default git samples; no custom hooks |

## Summary
`stip-models` is an initialised but empty repository. It is the foundational dependency for the entire STIP implementation chain. Its absence, combined with the equally empty `stip-generated` repository, means that Stand-In Processing — a mandatory payments resilience capability — is either implemented entirely elsewhere (and these repositories are stale/unused) or is not implemented at all. The enterprise architecture and payments platform teams should treat this as a critical finding requiring immediate clarification and remediation.
