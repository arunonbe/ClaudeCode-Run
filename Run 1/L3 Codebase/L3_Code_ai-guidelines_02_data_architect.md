# ai-guidelines — Data Architect View

## Data Stores

None. This repository contains no application code, no database schemas, no migrations, and no data persistence layer. There are no data stores of any kind.

## Schema & Tables

Not applicable. No schemas, tables, entities, or ORM mappings are defined in this repository.

## Sensitive Data Handling

The repository does not handle or store any data. However, the guideline files it contains prescribe sensitive data handling rules for the projects that consume them:

- `security-standards.md` mandates encryption of sensitive data at rest and in transit.
- `java-standards.md` (section 8 — Logging) explicitly states: "Don't log sensitive information."
- `java-standards.md` (section 9 — Security) states: "Don't expose sensitive information in logs or exceptions."
- `security-standards.md` requires compliance with GDPR and CCPA for data privacy.
- `security-standards.md` prohibits hardcoding credentials, API keys, passwords, or tokens in any file.

These are prescriptive rules for consuming projects; they are not implemented or enforced within this repository itself.

## Encryption & Protection

No encryption is implemented in this repository. The `security-standards.md` guideline mandates:

- Encrypt sensitive data at rest and in transit.
- Use HTTPS for all network communication.
- Use environment variables or secure configuration management instead of hardcoded secrets.
- Reference `${SECRET_NAME}` style placeholders for any configuration that would contain secrets.

No specific encryption algorithms, key management approach, or vault/secrets-manager integration is prescribed in the guidelines.

## Data Flow

Not applicable. There is no data flow within this repository.

## Data Quality & Retention

Not applicable. No data is produced, consumed, or retained by this repository.

## Compliance Gaps

From a data governance perspective, the following gaps are present in the guideline content:

- No mention of cardholder data environment (CDE) controls, PAN masking, or PCI DSS tokenization requirements — significant for Onbe's payments context.
- No mention of NACHA data handling requirements for ACH records.
- No data retention or data destruction policies are defined.
- No data classification scheme (public, internal, confidential, restricted) is specified.
- No guidance on handling or masking PII beyond the general GDPR/CCPA reference.
- No guidance on audit logging requirements (e.g., what events must be logged, log immutability, retention period).
- No reference to database-level security controls (e.g., column-level encryption, row-level security, least-privilege database accounts).
