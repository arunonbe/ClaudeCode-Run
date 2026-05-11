# DS_DB_prepaid_warehouse_intl — Data Architect Assessment

## 1. Schema Architecture

The international warehouse uses the same **star schema** structure as the US warehouse (`dbo`, `dim`, `fact`, `stagingdata`, `Storage`, `Security` schemas). Key architectural differences are documented below.

---

## 2. Dimension Tables

### dim.DimAccountHolder (International)
File: `dim/Tables/DimAccountHolder.sql`

The international variant of `DimAccountHolder` is structurally nearly identical to the US version with these differences:

| Difference | US Warehouse | International Warehouse |
|---|---|---|
| Name columns | `VARCHAR(50)` | `NVARCHAR(50)` — Unicode support for international characters |
| Address columns | `VARCHAR(50)` | `NVARCHAR(50)` — Unicode |
| City column | `VARCHAR(50)` | `NVARCHAR(50)` — Unicode |
| Country column | `VARCHAR(50)` | `NVARCHAR(50)` — Unicode |
| HomeEmail, BusinessEmail | `VARCHAR(50)` | `NVARCHAR(50)` — Unicode |
| Org field | Not present | `[Org] VARCHAR(3)` — organisational unit code |
| Logo field | Not present | `[Logo] VARCHAR(3)` — brand logo identifier |
| PartnerUserID index | `NDX_PUID_DDA` | Not present |

**Sensitive fields (same as US):**
- `DDANumber` CHAR(16) — full DDA account number, plaintext
- `FirstName`, `MiddleName`, `LastName`, `SuffixName` — NVARCHAR, PII
- `Address1`, `Address2`, `City`, `State`, `Country`, `ZipCode` — NVARCHAR, PII
- `HomePhone`, `BusinessPhone` — VARCHAR(16), PII
- `HomeEmail`, `BusinessEmail` — NVARCHAR(50), PII

The `NVARCHAR` usage is a positive design decision for international support but does not address the data protection concern — the PII remains unmasked and unencrypted.

---

## 3. Additional Dimension: DimCountry

The international warehouse has an additional dimension table `dim.DimCountry` (referenced in `rpt_TTS_data_feed.sql` line 61 as `[dim].[DimCountry]`) that does not exist in the US warehouse. This dimension maps `CountryKey` to `CountryName` and is joined through `dim.DimGLCompany`, enabling country-level transaction aggregation in the TTS data feed.

---

## 4. Fact Tables

The fact table structure mirrors the US warehouse:
- `fact.FactPaymentTransactions` — payment transactions (partitioned)
- `fact.FactUtilizationTransactions` — utilisation/spend transactions (partitioned)
- `fact.FactOtherTransactions` — other transaction types
- `fact.FactCardAccountDetail` — card account dimension link
- `fact.FactCardEmbossDetail` — emboss/fulfillment detail
- `fact.FactClaimablePaymentIssuance` — claimable payment lifecycle
- `fact.FactJobSvcActions` — job service events
- `fact.FactAccountSnapshot` — daily account balance snapshot (partitioned)
- `fact.FactAllotmentToCard`, `fact.FactAllotmentToWorldLink` — allotment tracking

All `_OLAPInc`, `_Stg`, `_Work`, `_Hold`, `_Dups`, and `_Rollback` variants follow the same pattern as the US warehouse.

---

## 5. Stored Procedures (Complete List)

| Procedure | File | Purpose |
|---|---|---|
| `rpt_claimable_payment` | `dbo/Stored Procedures/` | Claimable payment detail report |
| `rpt_claimable_payment_summary` | `dbo/Stored Procedures/` | Claimable payment summary |
| `rpt_std_header` | `dbo/Stored Procedures/` | Standard report header |
| `rpt_std_issuanceaggregate` | `dbo/Stored Procedures/` | Standard issuance aggregate |
| `rpt_TTS_data_feed` | `dbo/Stored Procedures/` | TTS partner data feed (international) — queries `dim.DimCountry`, `dim.DimGLCompany.CurrencyName` |
| `sprocInc_Capture_Incremental_DDAs` | `dbo/Stored Procedures/` | Incremental DDA capture from operational systems |
| `sprocInc_Create_ColumnStore_DimAccountHolder` | `dbo/Stored Procedures/` | Rebuild columnstore index on DimAccountHolder |
| Additional `sprocInc_*` procedures | `dbo/Stored Procedures/` | Mirror of US warehouse incremental ETL procedures |

---

## 6. Sensitive Data Field Catalogue

| Table | Field | Type | Classification |
|---|---|---|---|
| `dim.DimAccountHolder` | `DDANumber` | CHAR(16) | Account number — plaintext |
| `dim.DimAccountHolder` | `FirstName` | NVARCHAR(50) | PII — GDPR/CCPA |
| `dim.DimAccountHolder` | `LastName` | NVARCHAR(50) | PII — GDPR/CCPA |
| `dim.DimAccountHolder` | `MiddleName` | NVARCHAR(50) | PII |
| `dim.DimAccountHolder` | `Address1` | NVARCHAR(50) | PII — GDPR |
| `dim.DimAccountHolder` | `Address2` | NVARCHAR(50) | PII |
| `dim.DimAccountHolder` | `City` | NVARCHAR(50) | PII |
| `dim.DimAccountHolder` | `State` | NVARCHAR(50) | PII |
| `dim.DimAccountHolder` | `Country` | NVARCHAR(50) | PII — data residency implications |
| `dim.DimAccountHolder` | `ZipCode` | VARCHAR(50) | PII |
| `dim.DimAccountHolder` | `HomePhone` | VARCHAR(16) | PII |
| `dim.DimAccountHolder` | `BusinessPhone` | VARCHAR(16) | PII |
| `dim.DimAccountHolder` | `HomeEmail` | NVARCHAR(50) | PII — GDPR Article 6 |
| `dim.DimAccountHolder` | `BusinessEmail` | NVARCHAR(50) | PII |
| `fact.*` | `DDANumber` | CHAR/VARCHAR(16) | Account number |

---

## 7. Data Architecture Risks

### 7.1 SQL Server 2012 Target
The project targets SQL Server 2012 (`Sql110DatabaseSchemaProvider`). SQL Server 2012 has been out of extended support since July 2022. This means:
- No security patches from Microsoft for the database engine
- Missing features: Row-Level Security (SQL 2016+), Dynamic Data Masking (SQL 2016+), Always Encrypted (SQL 2016+)
- If this project is deployed to a SQL Server 2012 instance, the database cannot leverage modern data protection controls

### 7.2 Legacy Compatibility Settings
The sqlproj (`database.Prepaid_Warehouse_Intl.sqlproj`) sets:
- `<AnsiNulls>False</AnsiNulls>` — disables ANSI null behaviour; affects how `= NULL` comparisons behave vs `IS NULL`
- `<QuotedIdentifier>False</QuotedIdentifier>` — allows single-quoted string literals that are normally identifier delimiters

These settings indicate the database was built on very old SQL Server conventions and stored procedures may not behave correctly if migrated to a modern server with default settings.

### 7.3 No CDC Tables in Scope
Unlike the US warehouse which has `stagingdata.cdc_*` tables explicitly defined, the international warehouse's staging structure is less visible in the repository file listing. If CDC is not used for international ETL, the data freshness mechanism is unclear.

### 7.4 Multi-Currency Amount Handling
The TTS data feed procedure (`rpt_TTS_data_feed`) joins to `dim.DimGLCompany.CurrencyName` for currency labeling, but amounts in `FactPaymentTransactions` are stored as MONEY type without explicit currency codes at the fact row level. Currency context is resolved only through the GL Company dimension. This creates a risk of incorrect currency aggregation if two programs share a GL Company but operate in different currencies.
