# Business Analyst View — DS_CCP_ccp-export-to-legacy

## Business Purpose
The CCP-Export-to-Legacy project exports CCP (Card/Cardholder Program) data from the modern CCP data store back to the legacy Ecount platform for reconciliation and business-as-usual (BAU) back-office processes. It bridges the new CCP system with the old Ecount infrastructure during the transitional period, ensuring that legacy finance and operations teams continue to receive the data feeds they rely on. The README explicitly states its purpose: "export data from imported for CCP to the legacy Ecount platform for reconciliation and BAU processes."

## Capabilities
| Package | Business Function |
|---------|-----------------|
| `Export_billing_audit.dtsx` | Exports billing audit data (date, program, promotion, access level, billing event) to legacy Ecount in pipe-delimited CSV format |
| `Export_billing_detail.dtsx` | Exports detailed billing line items to legacy |
| `Export_fvd_deferred.dtsx` | Exports FVD (Face Value Discrepancy or Fund Value Distribution — billing category) deferred amounts |
| `Export_fvd_revenue.dtsx` | Exports FVD revenue amounts (revenue date, issuance date, program, amount, financial institution) |
| `Export_fvd_singleload.dtsx` | Exports FVD single-load data |
| `Files_sftp.dtsx` | SFTP file delivery to legacy Ecount platform |
| `Archive_Processed_Files.dtsx` | Archives processed files after successful delivery |

## Key Business Entities
- **Billing Audit Record** — Date, Program, Promotion, Access_Level, Billing_Event (full audit trail of billing actions)
- **Billing Detail** — Line-level billing breakdown
- **FVD Deferred** — Financial values deferred to future periods
- **FVD Revenue** — Revenue recognition entries: Revenue_Date, Issuance_Date, Program, Amount, Financial_Institution
- **FVD Single Load** — Single-load card program financial data
- **Archived File** — Processed files moved to archive location

## Business Rules / Flows
1. Data is extracted from the ODS and/or DWH (Oracle `dwh_dev` in dev environment).
2. Output is formatted as pipe-delimited flat files with date-stamped filenames (e.g., `wdccp_billing_audit_All18991230.csv`, `wdccp_fvd_revenue_All18991230.csv`).
3. Files are delivered to the legacy Ecount platform via SFTP (`Legacy_SFTPHostName` parameter).
4. After successful delivery, files are archived by `Archive_Processed_Files.dtsx`.
5. Email notifications alert on missing files.

## Compliance Relevance
- FVD revenue and billing data support financial reporting obligations (SOC 1 — financial controls).
- Billing audit trail is relevant to dispute resolution and Reg E error-resolution processes.
- The `Financial_Institution` field in FVD revenue links to specific BIN-bank entities, relevant to NACHA/ACH tracking.

## Risks
- **Bridge pattern dependency** — this project exists only because the legacy system cannot directly consume CCP data; it will become redundant once the legacy platform is fully decommissioned.
- **Dual-write risk** — if data is modified in the CCP system between the import step and this export step, the legacy platform may receive stale data.
- **No rollback mechanism** — if archiving succeeds but SFTP delivery fails, the file may be archived without delivery confirmation.
- Legacy SFTP hostname `sftp-qa.nam.wirecard.com` appears to be a QA/Wirecard-branded endpoint; production override required.
