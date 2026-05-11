# Auto_CZ — Data Architect View

## Data Stores

None. No database connection strings, ORM entity definitions, SQL scripts, migration files, or data-store configuration files exist anywhere in the repository. The only tracked file is `.gitattributes` (68 bytes, content: `* text=auto` plus a comment line).

## Schema & Tables

None defined. No SQL DDL, Liquibase/Flyway changelogs, JPA/Hibernate entity classes, EF Core DbContext, or NoSQL collection definitions are present.

## Sensitive Data Handling

No code exists that handles any data, sensitive or otherwise. No PII, PAN, or financial data handling patterns can be identified because there is no source to analyse.

**Note:** The git configuration includes `filter.lfs.required=true`, meaning Git LFS is mandatory for this repository. If test artefacts (e.g., screenshots, exported reports containing cardholder data) are later added via LFS, those artefacts would need to comply with PCI DSS v4.0.1 Requirement 3 (protection of stored account data) and should never contain real PANs.

## Encryption & Protection

None implemented. No TLS configuration, secrets vault references, key management files, or encryption libraries are referenced.

## Data Flow

No data flows exist. No API clients, message consumers, ETL pipelines, or file processors are present.

## Data Quality & Retention

Not applicable. No data processing logic exists.

## Compliance Gaps

| Gap | Standard | Detail |
|-----|----------|--------|
| No data classification labelling | PCI DSS v4.0.1 Req 9.4 / SOC 2 | Repository contains no data inventory or classification |
| No secrets management configuration | PCI DSS v4.0.1 Req 8 / NIST CSF 2.0 PR.AC | No `.env.example`, Vault config, or secrets scanning baseline committed |
| No data retention policy | GDPR Art. 5(1)(e) / CCPA | No retention schedule or purge logic defined |
| Repository purpose undocumented | Internal governance | Without a README or architecture decision record, data residency and flow cannot be assessed |
