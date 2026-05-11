# DS_ETL_warehouse — Enterprise Architect Perspective

## Strategic Position

`DS_ETL_warehouse` is the most architecturally significant repository in the six reviewed. It implements the single source of analytical truth for Onbe's prepaid card business — the `Prepaid_Warehouse` — which is consumed by executive dashboards, client reporting, financial reconciliation, compliance reporting, and SSAS cubes. All downstream analytical capability depends on the correct and timely execution of this ETL pipeline.

## Architecture Tier Model

```
[Operational Tier]
  Ecountcore_SS (p-db06\db06)   <- eCount legacy card management
  cf_report (p-db06\db06)       <- reporting support DB
  Jobsvc_SS                     <- job/workflow service
  FDR/Fiserv CDC feeds          <- fdr_dda_account_detail (CDC)

           |  SSIS ETL (DS_ETL_warehouse)
           v

[Analytical Tier]
  Prepaid_Warehouse (p-db07\db07)  <- dimensional warehouse (star schema)

           |  Process_Cubes.dtsx
           v

[OLAP Tier]
  Prepaid_DW_OLAP (SSAS cube)   <- referenced in Warehouse.dtproj

           |  DS_RPT_ecount-report-services
           v

[Reporting Tier]
  SSRS reports  <- cf_report + Prepaid_Warehouse sources
```

## Domestic / International / Multi-Tenant Architecture

The parallel package families reveal a multi-environment warehouse design:

| Prefix | Scope | Example Package |
|---|---|---|
| (none) | Domestic US | `DimAccountHolder_Incremental.dtsx` |
| `Intl_` | International programmes | `Intl_DimAccountHolder_Incremental.dtsx` |
| `MT_` | Multi-tenant | `MT_DimAccountHolder_Incremental.dtsx` |

This triplication suggests the warehouse either maintains separate schema areas (schemas or databases) for each line, or runs the same logical loads against separate source instances. The `MT_DW_Incremental_ETL_Master.dtsx` (297 KB) being a distinct master orchestrator for multi-tenant confirms these are separate execution paths, not just parameter variations.

**Enterprise risk**: Maintaining three parallel codebases for the same logical operation creates significant maintenance overhead and increases the risk of divergence between domestic and international data model parity.

## Legacy Platform Dependency — Critical Enterprise Risk

The entire warehouse ETL is coupled to `Ecountcore_SS` — the legacy eCount platform. The `Ecountcore` name, the `fdr_` prefixed CDC tables, and the historical package dates (2012 origin) collectively indicate this warehouse was built contemporaneously with Wirecard North America's eCount platform and has been maintained in-place for over a decade.

**Strategic risk**: Any initiative to migrate from eCount to a modern card management platform (or to Onbe's newer systems) must include a warehouse migration workstream. The warehouse is not merely a reporting artefact — it is the integration point for the EWRA (Enterprise-Wide Risk Assessment) which has regulatory implications.

## EWRA — Regulatory Context

`EnterpriseWideRA.dtsx` processes Enterprise-Wide Risk Assessment data in ICG/CTS/TTS format. The path `\\ppinmwpdetl1\c-base\runtime\ndmroot\svc-cdwinnt\upload\EWARA\` and filenames like `_ICG_CTS_TTS_PREPAIDGTPLAINS_012019.cntl` indicate:

- **ICG** = Integrated Card Group (a Fiserv/First Data construct)
- **CTS** = Card Transaction System
- **TTS** = Transaction and Transfer System
- **PREPAIDGTPLAINS** = programme identifier (Great Plains region prepaid)

This suggests the EWRA extract feeds a risk reporting process that may interface with Fiserv/First Data systems. Given FFIEC guidance on enterprise risk management for financial institutions and PCI DSS Requirement 12.3 (risk assessment), this ETL package has direct regulatory significance. Failure or inaccuracy in the EWRA extract could constitute a compliance reporting failure.

## PCI DSS Cardholder Data Environment Assessment

The warehouse ETL sits within or adjacent to the PCI DSS Cardholder Data Environment (CDE) by virtue of:

1. **CDC from `fdr_dda_account_detail`** (`CDC_stagingdata.dtsx` line 69): The `dda_account_detail` table almost certainly contains DDA (Demand Deposit Account — bank account) numbers. DDA numbers are not PAN but are payment account data subject to NACHA data security rules and potentially within the scope of PCI DSS Requirement 3 (protection of stored data) if associated with card accounts.

2. **`DimAccountHolder`** dimension: Account holder demographic data including address fields. While not PAN, this is personal data subject to GLBA and potentially CCPA/GDPR for international cardholders.

3. **`CardDetail`** tables: Card lifecycle history. May include card numbers in masked or encrypted form. The presence of a `Masked_card_number` field is confirmed in SSRS reports from `DS_RPT_ecount-report-services` (e.g., `Cardholder Archived Transactions.rdl` line 12). The warehouse must store this in a tokenised or masked form to comply with PCI DSS Requirement 3.4.

4. **Direct production database connections**: `p-db06` and `p-db07` are production systems. Any compromise of the SSIS execution environment would give an attacker read access to production cardholder data.

## Flag: Production Database Direct Connect in CDE Context

Given the above, the following connection strings represent a PCI DSS scope consideration:

- `Data Source=p-db06\db06;Initial Catalog=Ecountcore_SS` — production card management ODS
- `Data Source=p-db07\db07;Initial Catalog=Prepaid_Warehouse` — production warehouse

The SSIS execution server is within the CDE if it processes or has access to PAN or account data. The SSIS service account used for `Integrated Security=SSPI` must be treated as a privileged CDE account and subject to PCI DSS Requirement 8 (identification and authentication) and Requirement 7 (access control).

## Architectural Modernisation Roadmap

| Priority | Recommendation |
|---|---|
| P1 | Assess production server access scope; confirm CDE boundary for SSIS execution server |
| P1 | Migrate protection level to `DontSaveSensitive`; implement SSIS Catalog with environment variables |
| P1 | Version-control the `.dtsConfig` files or migrate to Catalog-based configuration |
| P2 | Consolidate domestic/international/multi-tenant into parameterised packages |
| P2 | Migrate from SSIS 2012 to Azure Data Factory or SSIS 2019 |
| P2 | Replace direct production reads with read-replicas or API-based data access |
| P3 | Implement data lineage tracking (column-level) for PCI DSS audit support |
| P3 | Document warehouse schema in a data dictionary and link to this repository |
