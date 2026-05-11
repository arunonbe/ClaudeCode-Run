# DS_ETL_warehouse — Business Analyst Perspective

## Repository Overview

`DS_ETL_warehouse` is the core data warehouse ETL solution for Onbe's prepaid-card platform. It is a large Microsoft SSIS project (the `Warehouse.dtproj` manifest is 890 KB) containing approximately 100 SSIS packages that collectively load the `Prepaid_Warehouse` dimensional data store from the `Ecountcore_SS` and related operational databases. The project also includes international variants (`Intl_*` packages) and a multi-tenant variant (`MT_*` packages), indicating the warehouse serves domestic US, international, and multi-tenant programme lines.

## Business Purpose

The `Prepaid_Warehouse` is Onbe's central analytical data store for the prepaid card business. It holds:

- **Card and account holder data**: `DimAccountHolder_Incremental.dtsx`, `Intl_DimAccountHolder_Incremental.dtsx`, `MT_DimAccountHolder_Incremental.dtsx` — dimension tables capturing cardholder demographics and account status.
- **Card detail and transaction history**: `CardDetailHistory.dtsx`, `CardDetailIncremental.dtsx`, `Intl_CardDetailHistory.dtsx` — full card lifecycle records.
- **Claimable payment activity**: `ClaimablePaymentHistory.dtsx`, `ClaimablePaymentIncremental.dtsx` — records of claimable disbursements (refunds, incentive payments, insurance proceeds) pending cardholder claim.
- **BIN (Bank Identification Number) data**: `DimBIN_Incremental.dtsx`, `DimBIN_Update.dtsx` — BIN table maintenance for network routing and issuer identification.
- **Geography dimensions**: `DimGeography_Incremental.dtsx`, `DimGeography_Update.dtsx` — address and region data supporting geographic analysis.
- **Merchant data**: `DimMerchant.dtsx`, `DimMerchant_Incremental.dtsx`, `Merchant_Incremental.dtsx` — merchant dimension for spend analytics.
- **Programme and product dimensions**: `DimProgram_Incremental.dtsx`, `DimProduct_Incremental.dtsx`, `DimProgram_DimProduct_Load.dtsx` — the programme/product hierarchy that links each card to its sponsoring client programme.
- **ACH and DDA activity**: `DDAVerification.dtsx`, `Addenda_HistoryLoad.dtsx` — direct deposit and ACH verification records.
- **Enterprise-Wide Risk Assessment (EWRA)**: `EnterpriseWideRA.dtsx` — risk assessment data extract (ICG/CTS/TTS format, `\\ppinmwpdetl1\c-base\runtime\ndmroot\svc-cdwinnt\upload\EWARA\`, line 34).
- **OLAP Cube processing**: `Process_Cubes.dtsx`, `Intl_Process_Cubes.dtsx` — post-load cube refresh for SSAS analytical models.
- **CDC (Change Data Capture) staging**: `CDC_stagingdata.dtsx`, `CDC_stagingdata_jobsvc.dtsx` — captures incremental changes from `fdr_dda_account_detail` and related tables.

## Operational Database Sources

The warehouse draws from three primary source databases:

| Database | Server | Role |
|---|---|---|
| `Ecountcore_SS` | `p-db06\db06` (prod) / `q-db03.nam.wirecard.sys\db03` (QA) | eCount operational platform — card management |
| `cf_report` | `p-db06\db06` | Reporting support database — labels, programme config |
| `Jobsvc_SS` | Referenced in `Warehouse.dtproj` | Job service operational database |
| External EWRA files | `\\ppinmwpdetl1\c-base\runtime\ndmroot\...` | ICG/CTS/TTS risk assessment flat files |

The source database naming convention — `Ecountcore_SS` — indicates the eCount platform with a SQL Server suffix, confirming this is the legacy Wirecard North America prepaid platform that Onbe inherited.

## Claimable Payments — Business Significance

The `ClaimablePaymentHistory.dtsx` package (653 KB — the largest in the project) and its incremental counterpart (`ClaimablePaymentIncremental.dtsx`, 440 KB) process claimable payment data. Claimable payments are a core Onbe business product: funds disbursed by corporate clients (insurance companies, auto dealers, healthcare providers) to recipients who must actively claim them. The warehouse history load extracts "Branded Currency Issuance" and related records from `Ecountcore_SS` and `cf_report` (lines 72–79 of `ClaimablePaymentHistory.dtsx`).

Accurate claimable payment data is critical for:
- Client reconciliation and reporting (how much was disbursed vs. claimed)
- Escheatment compliance (unclaimed funds must be reported to state authorities under unclaimed property laws)
- Reg E dispute resolution
- Revenue recognition (breakage from unclaimed amounts)

## International and Multi-Tenant Programmes

The `Intl_*` package family mirrors the domestic packages for international programmes. The `MT_*` family (`MT_DimAccountHolder_Incremental.dtsx`, `MT_DW_Incremental_ETL_Master.dtsx`) covers multi-tenant environments. This architecture indicates that the `Prepaid_Warehouse` is a single consolidated warehouse supporting multiple operational environments — a design that simplifies cross-programme reporting but increases the blast radius of any ETL failure.

## Email Notification Configuration

`Project.params` defines three notification parameters (lines 5–66):

| Parameter | Value |
|---|---|
| `SuccessEmailTo` | `colin.treat@northlane.com` |
| `FailEmailTo` | `colin.treat@northlane.com` |
| `EmailFrom` | `noreply@northlane.com` |

These are hardcoded to an individual's email address (`colin.treat@northlane.com`). From a business continuity standpoint, operational notifications should go to a team distribution list rather than an individual, ensuring coverage during absence or staff changes.

## Key Business Risks

| Risk | Detail |
|---|---|
| Individual email in notifications | `colin.treat@northlane.com` — single point of failure for ops alerts |
| Largest packages (ClaimablePayment, EWRA, incremental_data) | Complex packages increase risk of partial failure impacting financial reconciliation |
| EWRA flat-file dependency | `EnterpriseWideRA.dtsx` reads from `\\ppinmwpdetl1\c-base\...` — UNC path dependency on a specific server |
| Legacy eCount source | The `Ecountcore_SS` source database is the legacy platform; any decommission without warehouse migration would break all ETL |
| No README content | `README.md` contains only 11 bytes — no operational runbook |
