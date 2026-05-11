# Data Architect View — RecipientApp

## Source Availability Limitation

The `RecipientApp` repository contains only the `.git` directory with no checked-out source files. No data models, entity definitions, schema migrations, or configuration files are available for direct analysis. This document is based on inferred context from the repository name and the broader NexPay Gen-3 recipient platform context.

## Inferred Data Model

If `RecipientApp` is a recipient management application in the NexPay platform, the expected data model would include:

**Recipient / Person entity**:
- `id` — UUID primary key
- `firstName`, `lastName` — name (PII)
- `email` — contact (PII)
- `phone` — contact (PII)
- `dateOfBirth` — DOB (PII, used for identity verification and sanctions screening)
- `address` — physical address (PII)

**Recipient Payment Method entity**:
- `id` — UUID
- `recipientId` — FK to Recipient
- `ddaNumber` — Demand Deposit Account number (sensitive financial identifier)
- `routingNumber` — ABA routing number (sensitive financial identifier)
- `accountType` — CHECKING / SAVINGS
- `status` — ACTIVE / PENDING / BLOCKED

**Payout / Disbursement entity**:
- `id` — UUID
- `recipientId` — FK
- `amount`, `currency`
- `status` — PENDING / PROCESSING / COMPLETED / FAILED / BLOCKED
- `sanctionStatus` — APPROVED / REFERRED / DECLINED / IN_PROGRESS
- `createdAt`, `updatedAt`

## Sensitive Data Classification

If the inferred model is correct, `RecipientApp` would handle:

| Data Element | Classification |
|---|---|
| `firstName`, `lastName` | PII (GDPR, CCPA, GLBA) |
| `email`, `phone` | PII |
| `dateOfBirth` | PII — sensitive category |
| `address` | PII |
| `ddaNumber` | Financial account number (GLBA, PCI DSS adjacent) |
| `routingNumber` | Financial identifier (GLBA) |

These data elements are the same set forwarded to `recipient-screening-api` for sanctions screening, confirming that `RecipientApp` is likely the upstream source of recipient identity data in the disbursement workflow.

## Encryption Requirements

For a service of this data sensitivity, the following encryption controls are expected:
- **Data at rest**: DDA numbers and routing numbers should be encrypted at the column level (AES-256) or stored as tokens via a vault service.
- **Data in transit**: All API calls must use TLS 1.2 or 1.3 with certificate validation.
- **Secrets**: Database credentials and API keys should be managed via Azure Key Vault, consistent with the Gen-3 pattern established in `recipient-screening-api`.

Without source code, none of these controls can be verified.

## Data Flows

Inferred flow:
```
[Recipient (web/mobile)] 
    → POST recipient registration/DDA enrollment
    → [RecipientApp API]
        → Store in database (recipient + DDA records)
        → Trigger screening → [recipient-screening-api]
            → [om-recipientsanctioning-svc]
        ← Screening status
    → [Payout Orchestrator] (when disbursement is initiated)
```

## Retention Concerns

Recipient PII (name, DOB, address) and financial data (DDA, routing) have specific retention obligations:
- **GLBA**: Financial institutions must retain records for regulatory examination purposes (typically 5–7 years).
- **CCPA/GDPR**: Right to deletion applies — a recipient who requests erasure must have their PII removed, while financial transaction records may be retained for legal/regulatory purposes.
- **OFAC**: Sanctions screening records should be retained for audit trail purposes (typically 5+ years per BSA/AML recordkeeping requirements).

Without source code, it is unknown whether any retention or deletion policies are implemented.

## PCI DSS Compliance

If `RecipientApp` handles prepaid card activation or card-facing operations in addition to DDA enrollment, it may be in scope for PCI DSS. This must be assessed once source code is available. DDA-only operations are not in PCI DSS CDE scope but are subject to GLBA and Reg E data protection requirements.

**Action required**: Obtain full source checkout and assess encryption, retention, and data classification controls against PCI DSS Req 3, GLBA Safeguards Rule, and GDPR Art. 5 (data minimization), Art. 25 (privacy by design), and Art. 32 (security of processing).
