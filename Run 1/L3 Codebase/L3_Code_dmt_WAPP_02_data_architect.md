# Data Architect Report — dmt_WAPP

## Data Stores
| Store | Type | Location | Purpose |
|---|---|---|---|
| RiskDB | SQL Server (inferred) | On-premises / internal network | Primary operational data store; hosts DMT data and distributes the `.xlsm` files |
| Excel workbook (in-memory) | In-process Excel | User desktop | Runtime display only; no persistence of fetched data |
| Git repository | Binary blob store | Version control | Stores `.xlsm` binaries for distribution and history only |

## Schema
No schema artefacts are present in this repository. The entire relational schema is encapsulated within RiskDB. Key inferences:
- Access is partitioned by user identity / firewall role, implying row- or view-level security at the SQL layer.
- The VBA macro layer constructs SQL queries dynamically (code not available in this repo).

## Sensitive Data Assessment
- The repository itself contains **no raw data** — all `.xlsm` files are stateless front-end shells.
- The `Data Management Tool - Production.xlsm` binary (2.88 MB) and `OPTIC - Production.xlsm` (1.35 MB) are large enough to embed macros that could contain hardcoded connection strings, credentials, or data caches. **These should be opened and inspected for embedded secrets before any deployment or distribution.**
- RiskDB is implied to contain internal operational/risk data; classification is unknown from this repo alone.

## Encryption
- **In transit**: Not specified in this repository. Depends on SQL Server configuration on RiskDB.
- **At rest**: Not specified. Dependent on RiskDB host OS/disk encryption.
- **Excel files**: Not password-protected as far as can be determined from the repo; `.xlsm` files are ZIP-format Office Open XML containers and could be inspected with any zip tool.

## Data Flow
```
[RiskDB SQL Server]
  ├─ Stores production .xlsm file
  ├─ Serves file download to DMT Production Copy Link.xlsm (user desktop)
  └─ Answers SQL queries from opened DMT application
         └─ Result sets → Excel in-memory display (no write-back visible in repo)
```

## Data Quality
- No data validation rules, ETL pipelines, or quality checks are present in this repository.
- Entirely dependent on RiskDB SQL layer constraints.

## Compliance Gaps
| Gap | Standard | Recommendation |
|---|---|---|
| Embedded macro code not reviewable | PCI DSS Req 6.3, SOC 2 CC8 | Extract VBA into a diff-able text format (e.g. VBA project export) and store in Git alongside the binary. |
| No data classification visible | PCI DSS Req 9.9 / GLBA | Formally classify data accessed by DMT; determine CDE scope. |
| No encryption controls defined in repo | PCI DSS Req 4 | Document and enforce TLS for RiskDB connections from Excel macros. |
| No DLP controls on Excel output | GLBA / CCPA | Users can copy fetched data to clipboard/local files; no DLP enforcement visible. |
| Binary files in Git | SOC 2 CC8.1 | Move to an artefact store (e.g. Nexus, S3) with integrity checksums. |
