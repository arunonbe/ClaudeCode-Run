# scripts — Data Architect View

## Data Stores
None present. No scripts, configurations, or data files have been committed.

## Schema / Tables
Not applicable.

## Sensitive Data
No sensitive data found in committed content. The `.gitignore` excludes binary artefacts but does not include secrets-specific exclusions (e.g., `*.env`, `*.key`, `*.pem`, `credentials*`).

## Encryption
Not applicable — no code or configuration committed.

## Data Flow
Not applicable.

## Data Quality / Retention
Not applicable.

## Compliance Gaps
- No `.gitignore` entries for credential files (`.env`, `*.key`, `*.pem`, `*credentials*`, `*.pfx`). If scripts with embedded secrets are added in future, there is no gitignore safety net.
- No secrets scanning (e.g., GitHub secret scanning, truffleHog) pipeline configured.
