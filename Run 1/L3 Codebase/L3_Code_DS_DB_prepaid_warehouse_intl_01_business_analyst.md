# DS_DB_prepaid_warehouse_intl — Business Analyst Assessment

## 1. Repository Identity

| Attribute | Value |
|---|---|
| Repository name | DS_DB_prepaid_warehouse_intl |
| Project name (sqlproj) | database.Prepaid_Warehouse_Intl |
| Solution file | prepaid_warehouse_intl.sln |
| SQL Server target | SQL Server 2012 (DSP: Sql110DatabaseSchemaProvider) |
| Build tool | Visual Studio SSDT, MSBuild ToolsVersion 4.0, .NET 4.0 |
| Default collation | SQL_Latin1_General_CP1_CI_AS |
| Project GUID | 901cc23d-65da-4b12-b166-12c27fddfb5d |

---

## 2. Business Purpose

The International Prepaid Warehouse is the **non-US international prepaid data warehouse** — the analytical and reporting database for Onbe's prepaid card portfolio operating in markets outside the United States. It mirrors the structural purpose of the US warehouse but serves international programs that may operate under different regulatory regimes (GDPR, PIPEDA, Quebec Law 25, local AML/KYC obligations, and non-US card network rules).

The international warehouse supports:
- Program performance analytics for non-US prepaid card programs
- Cardholder account lifecycle reporting across international markets
- Transaction aggregation and utilisation analytics in local currencies
- Data feeds to TTS (Total Transaction Services) and other third-party partners for international programs
- Claimable payment issuance tracking for international disbursement programs
- Incremental DDA capture for international ACH/direct deposit programs

The presence of `nvarchar` rather than `varchar` for name and address fields (unlike the US warehouse) indicates awareness of multi-byte character set requirements for international cardholder names and addresses (Arabic, Chinese, European extended characters).

---

## 3. Business Processes Supported

### 3.1 Standard International Reporting
Stored procedures `rpt_std_header`, `rpt_std_issuanceaggregate`, and `rpt_claimable_payment` / `rpt_claimable_payment_summary` provide standard reporting consistent with the US warehouse but applied to international program data.

### 3.2 TTS International Data Feed
`rpt_TTS_data_feed` — an international counterpart to the US TTS data feed — produces program-level transaction volume and active card count data broken down by country and currency (`dim.DimCountry`, `dim.DimGLCompany.CurrencyName`). This is used for partner reporting and potentially for regulatory reporting in non-US jurisdictions.

### 3.3 Incremental DDA Capture
`sprocInc_Capture_Incremental_DDAs` captures new and changing DDA numbers from the international operational systems, ensuring the warehouse reflects current account status.

### 3.4 Columnstore Rebuild for OLAP
`sprocInc_Create_ColumnStore_DimAccountHolder` and equivalent procedures rebuild columnstore indexes for OLAP cube consumption — identical in pattern to the US warehouse.

### 3.5 Claimable Payment Lifecycle
`sprocInc_Insert_New_ClaimablePaymentIssuance`, `sprocInc_Insert_ReIssues_Into_FactClaimablePaymentIssuance`, and `sprocInc_Update_Existing_ClaimablePaymentIssuance` manage the full lifecycle of claimable payments in international programs.

---

## 4. Key Differences From US Warehouse

| Dimension | US Warehouse | International Warehouse |
|---|---|---|
| SQL Server target | 2016 (Sql130) | 2012 (Sql110) — older version |
| .NET target framework | 4.6.1 | 4.0 — older |
| Character set | `varchar` for name/address | `nvarchar` for name/address — multi-byte support |
| Country dimension | Not explicit in US schema | `dim.DimCountry` explicitly present |
| Currency | USD implicit | `dim.DimGLCompany.CurrencyName` — multi-currency |
| Org/Logo fields | Not present in US | `dim.DimAccountHolder.Org` (VARCHAR 3), `Logo` (VARCHAR 3) — suggests multi-org structure |
| ANSI_NULLS | Default (True) | `<AnsiNulls>False</AnsiNulls>` in sqlproj — legacy compatibility mode |
| QuotedIdentifier | Default | `<QuotedIdentifier>False</QuotedIdentifier>` — legacy compatibility |
| Page verify | Not specified | `<PageVerify>CHECKSUM</PageVerify>` |
| Snapshot isolation | Default | Explicitly disabled |

---

## 5. Data Stored — Key Subject Areas

| Subject Area | Primary Tables | Sensitivity |
|---|---|---|
| International cardholder identity | `dim.DimAccountHolder` | **HIGH** — FirstName, LastName, Address (nvarchar), HomePhone, HomeEmail, BusinessEmail |
| DDA account numbers | `dim.DimAccountHolder.DDANumber` CHAR(16) | **HIGH** — full account number, plaintext |
| Transaction fact | `fact.FactPaymentTransactions`, `fact.FactUtilizationTransactions` | Moderate — amounts, dates, DDA numbers |
| Country/geography | `dim.DimCountry`, `dim.DimGeography` | Low |
| Program/product | `dim.DimProgram`, `dim.DimProduct` | Low |
| Claimable payments | `fact.FactClaimablePaymentIssuance` | Moderate — payment amounts |

---

## 6. Regulatory Relevance

### 6.1 GDPR (EU Residents)
If the international warehouse serves EU cardholder programs (likely given "international" scope), then `dim.DimAccountHolder` PII fields are subject to GDPR Article 5 (data minimisation), Article 17 (right to erasure), and Article 25 (privacy by design). The schema stores full cardholder names and addresses without encryption or masking. There is no evidence of a data retention or deletion procedure.

### 6.2 PIPEDA / Quebec Law 25 (Canadian Programs)
If Canadian cardholders are included, PIPEDA and Quebec Law 25 impose consent, access, and correction obligations. The warehouse's indefinite retention of cardholder identity data likely conflicts with PIPEDA's accountability and retention principles.

### 6.3 PCI DSS
Same concerns as the US warehouse apply — DDA numbers stored in plaintext in analytical tables.

### 6.4 Local Card Network Rules
International programs may be subject to Mastercard or Visa non-US data localisation requirements, which may prohibit certain cardholder data from being stored in US-based databases. If the international warehouse is hosted in the US, this creates data residency compliance exposure.

### 6.5 AML/CTF
International programs are subject to Financial Action Task Force (FATF) AML/CTF standards, which require transaction monitoring and suspicious activity reporting. The international warehouse provides the data layer for analytical AML monitoring, but the actual AML case management appears to reside in RiskDB.

---

## 7. Operational Business Risks

1. **GDPR right-to-erasure cannot be systematically executed** — cardholder PII in `DimAccountHolder` is stored indefinitely with no deletion mechanism.
2. **Data residency risk** — if EU/Canadian cardholder data is stored in a US-hosted database, this may violate GDPR Article 44 (transfers to third countries) or PIPEDA transfer requirements without appropriate safeguards.
3. **Older SQL Server target (2012)** — targeting SQL 2012 means the project may miss security fixes and features available in later versions. SQL Server 2012 reached end of extended support in July 2022.
4. **`AnsiNulls = False` and `QuotedIdentifier = False`** — legacy T-SQL compatibility settings that can cause subtle query logic bugs with NULL handling and identifier resolution.
5. **Multi-currency data quality** — transaction amounts in different currencies require correct FX conversion for aggregate reporting; any inconsistency in currency handling creates incorrect financial analytics.
