# DS_WH_ecount-warehouse — Data Architect Report

## Data Architecture Overview

The repository represents a **SQL Server Analysis Services (SSAS) Multidimensional** data warehouse built on top of a star/snowflake schema in the `prepaid_warehouse` SQL Server database (referenced in the Data Source View `Prepaid Warehouse.dsv`). The DSV was created on 2012-08-20 and last updated 2017-06-05, indicating the schema has not evolved since that date.

The SSAS project is named `Domestic_OLAP` (`Prepaid_DW_OLAP/Domestic_OLAP.database`) and contains five cubes, approximately 25 dimensions, and a corresponding set of semantic model files.

---

## Data Source View — Tables and Views

The `Prepaid Warehouse.dsv` references the following named objects (extracted from `<property name="LogicalObject">` elements within the layout annotations):

### Fact Tables
| DSV Table Name | Purpose |
|---|---|
| *(implicit in cubes)* | Transaction fact data sourced from `ecountcore` and `prepaid_warehouse` databases |

### Dimension Views
The DSV references the following dimension views (all prefixed `Dim*_vw`, indicating they are SQL views abstracting the base tables):

| View Name | Dimension | Key Attributes |
|---|---|---|
| `DimPrepaidSettlementDates` | Prepaid Settlement Date | Settlement date hierarchy |
| `DimProcessorSettlementDates` | Processor Settlement Date | Processor-side settlement date |
| `DimTransactionType_vw` | Transaction Type | Transaction classification codes |
| `DimProgram_vw` | Program | Program ID, name, affiliate |
| `DimProduct_vw` | Product | Product type (virtual/physical/DDA) |
| `DimBIN_vw` | BIN | Bank Identification Number — **PCI-sensitive** |
| `DimGeography_vw` | Geography | State, ZIP code, region |
| `DimGLCompany_vw` | GL Company | General ledger company codes |
| `DimMerchant_vw` | Merchant | MCC, merchant name, location |
| `DimAccountStatus_vw` | Account Status | Current account lifecycle state |
| `DimAccountHolder_vw` | Account Holder | **PII** — cardholder name, address, email |
| `DimAccountCreateDates_vw` | Account Create Date | Account open date hierarchy |
| `dimAccountPayments_vw` | Account Payments | Payment summary attributes |
| `DimFirstCardAccountCreateDates_vw` | First Card Create Date | First card issuance date per account |
| `dimAccountUtilization_vw` | Account Utilization | Utilization metrics per account |
| `dimAccountSpend_vw` | Account Spend | Spend aggregation per account |
| `DimFirstUtilizationDates_vw` | First Utilization Date | First spend event date |
| `DimLastSpendDates_vw` | Last Spend Date | Last spend event date |
| `DimFirstPaymentDates_vw` | First Payment Date | First payment/load date |
| `DimLastUtilizationDates_vw` | Last Utilization Date | Most recent utilization date |
| `DimAccessLevel_vw` | Access Level | Multi-tenant access level codes |
| `DimActivationCode_vw` | Activation Code | Card activation method codes |
| `DimCardBlockCode_vw` | Card Block Code | Card blocking/freeze codes |
| `DimCardExpireDate_vw` | Card Expire Date | Card expiry date hierarchy |
| `DimCardType_vw` | Card Type | Virtual vs. physical vs. DDA |
| `DimIssuanceType_vw` | Issuance Type | Bulk, APF, individual issuance |
| `DimPaymentStatus_vw` | Payment Status | Payment lifecycle status |
| `DimPaymentClaimDate_vw` | Payment Claim Date | Date recipient claimed payment |
| `DimPaymentExpirationDate_vw` | Payment Expiration Date | Payment expiry date |
| `DimPaymentIssueDate_vw` | Payment Issue Date | Payment issuance date |

---

## SSAS Cubes — Detailed Structure

### 1. Prepaid Transactions Cube (`Prepaid Transactions.cube`)
This is the primary analytical cube. It covers all prepaid card transaction events. Partitioned (`Prepaid Transactions.partitions` — 356 KB, the largest partition file, indicating high volume / multiple time-period partitions).

**Key measures (inferred from dimension relationships):**
- Transaction amount
- Fee amount
- Settlement amount
- Transaction count

**Dimensions:** BIN, Program, Product, Transaction Type, Geography (merchant state), Merchant, Account, Settlement Dates, Processor Settlement Dates, Card Type

### 2. Prepaid Issuance Cube (`Prepaid Issuance.cube`)
Covers payment issuance and load events. `Prepaid Issuance.partitions` is 159 KB — also partitioned.

**Dimensions:** Program, Product, Issuance Type, Payment Status, Payment Dates (issue, expiration, claim), Account Holder, Geography (cardholder state)

### 3. Account Snapshot Cube (`Account Snapshot.cube`)
Point-in-time balance and account lifecycle snapshot.

**Key measures:** Balance at snapshot, activation status, spend-to-date

**Dimensions:** Account, Account Status, Card Block Code, Card Type, Access Level, Process Date

### 4. Prepaid Card Accounts Cube (`Prepaid Card Accounts.cube`)
Account-level rollup.

**Dimensions:** BIN, Program, Product, Account Create Date, First Card Create Date, First/Last Utilization/Spend/Payment Dates, Account Utilization, Account Spend, Account Payments

### 5. JobSvc Actions Cube (`JobSvc Actions.cube`)
Operational cube tracking job service actions. Uses `JobSvc Action CheckIn Date.dim` and `JobSvc Action Type.dim`.

---

## Semantic Model Files (`.smdl`)

Located in `ecount.warehouse.models/` and duplicated in report project folders:

| File | Purpose |
|---|---|
| `AccountHolder Detail.smdl` (521 KB) | Rich cardholder-level model — **highest PII concentration** |
| `All Transaction Detail.smdl` (375 KB) | Full transaction detail model |
| `Claimable Payment Issuance.smdl` (303 KB) | Outstanding claimable payment view |
| `JobSvc Actions.smdl` (243 KB) | Job service action model |
| `Other Transaction Detail.smdl` (372 KB) | Non-spend transaction model |
| `Payment Transaction Detail.smdl` (375 KB) | Payment-specific transaction model |
| `Utilization Transaction Detail.smdl` (395 KB) | Spend/utilization transaction model |

The `AccountHolder Detail.smdl` at 521 KB is the most PII-dense model and should be subject to the strictest access controls and data classification review.

---

## Sensitive Data Classification

### PII Fields (CCPA / GDPR Scope)
The `DimAccountHolder_vw` dimension maps cardholder attributes from the operational database into the warehouse. Based on operational schema conventions:
- First name, last name
- Mailing address (street, city, state, ZIP)
- Email address
- Account holder ID / member ID

These fields appear in `AccountHolder Detail.smdl` and are surfaced in reports such as `MasterCAM.rdl`, `multiCAM.rdl`, and `Cardholder_Journals.rdl`.

### Financial Sensitive Data
- Card balance (current and historical)
- Transaction amounts
- Load/payment amounts
- Fee amounts

### Payment Rails Data (NACHA-Sensitive)
- DDA (Demand Deposit Account) identifiers in `DDA Rewards Test.rdl` and `DDA-PUID based on Account Created Date Range.rdl`

### BIN Data (PCI DSS Scope)
The `DimBIN_vw` dimension carries Bank Identification Numbers. BINs themselves are not full PANs and are not restricted under PCI DSS, but the combination of BIN + account-level transaction details creates re-identification risk if joined with external data.

---

## Data Lineage

```
ecountcore DB (SQL Server OLTP)
    └─► prepaid_warehouse DB (SQL Server DW)
           └─► Prepaid_DW_OLAP (SSAS Multidimensional)
                  └─► SSRS Reports (.rdl)
                  └─► Report Model Queries (.smdl)
```

The ETL process populating `prepaid_warehouse` is maintained in the separate `DS_ETL_warehouse` repository (not in scope for this analysis). The SSAS cube processing schedule is not visible in this repository.

---

## Data Retention and Access Controls

- The `CubeReader.role` file defines a single SSAS database role with read access to the cubes.
- There is no evidence of row-level security (RLS) at the SSAS layer; access segmentation appears to rely on the application layer report distribution.
- No data masking is applied at the warehouse layer based on the DSV definitions visible in the repository.
- The `Access Level.dim` dimension indicates multi-tenant access tiers exist in the data, but whether SSAS roles enforce these tiers is not determinable from the repository alone.

---

## Risk Assessment for Data Architecture

| Risk | Severity | Notes |
|---|---|---|
| PII in `DimAccountHolder_vw` accessible to all `CubeReader` role members | High | Name, address, email in warehouse |
| No row-level security at SSAS layer visible in repo | High | All `CubeReader` role users may see all programs |
| BIN data in `DimBIN_vw` — if combined with transaction detail creates cardholder profiling risk | Medium | Not a PAN but contextually sensitive |
| Schema not updated since 2017 | Medium | May not reflect current product offerings; stale dimensions |
| Large `.smdl` models (especially `AccountHolder Detail.smdl`) exported to report models | High | Broad PII exposure surface |
