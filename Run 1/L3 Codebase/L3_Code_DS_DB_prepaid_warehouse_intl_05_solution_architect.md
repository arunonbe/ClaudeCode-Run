# DS_DB_prepaid_warehouse_intl — Solution Architect Assessment

## 1. Critical Security and Compliance Findings

### 1.1 CRITICAL: GDPR-Regulated PII in Unprotected Analytical Table
**Finding:** `dim.DimAccountHolder` (`dim/Tables/DimAccountHolder.sql`, lines 24–35) stores `FirstName`, `LastName`, `MiddleName`, `SuffixName`, `Address1`, `Address2`, `ZipCode`, `City`, `State`, `Country`, `HomePhone`, `BusinessPhone`, `HomeEmail`, and `BusinessEmail` in plaintext NVARCHAR columns. For EU residents, this data is subject to GDPR.

**Criticality:** The international warehouse, by definition, is likely to contain records for EU-resident cardholders. GDPR Article 25 (privacy by design and by default) requires that technical measures limit access to personal data to the minimum necessary. An unprotected analytical table accessible to reporting users fails this requirement.

**Remediation (Priority: P1):**
- Upgrade to SQL Server 2016+ to enable Dynamic Data Masking
- Apply masking on all PII columns for non-privileged roles
- Implement a GDPR deletion/anonymisation procedure for inactive accounts

### 1.2 CRITICAL: SQL Server 2012 End-of-Life — No Modern Data Protection Controls
**Finding:** The project targets SQL Server 2012 (DSP `Sql110DatabaseSchemaProvider`, sqlproj line 11). SQL Server 2012 end of extended support was July 12, 2022.

**Impact:**
- **No security patches** from Microsoft since July 2022
- **Dynamic Data Masking** (SQL 2016) — unavailable
- **Row-Level Security** (SQL 2016) — unavailable
- **Always Encrypted** (SQL 2016) — unavailable
- Known CVEs in SQL Server 2012 engine are unpatched

This is a **PCI DSS Requirement 6.3** (protecting system components from vulnerabilities) and GDPR Article 32 (appropriate technical security measures) failure if the database is deployed on an unpatched SQL Server 2012 instance.

**Remediation (Priority: P0 — Immediate):**
- Verify current deployment target SQL Server version
- If running on SQL Server 2012 or 2014, plan emergency upgrade to SQL Server 2019 or migration to Azure SQL Database
- Assess applicable CVEs and apply available patches for current version

### 1.3 HIGH: No Data Residency Controls for International PII
**Finding:** `dim.DimAccountHolder.Country` (NVARCHAR 50) stores country data but there is no mechanism to restrict data access or storage by jurisdiction. EU cardholder records are stored alongside records from other jurisdictions with no separation.

**Remediation (Priority: P1):**
- Add a `JurisdictionCode` column to `DimAccountHolder` to identify the regulatory jurisdiction
- Implement Row-Level Security (after SQL Server upgrade) to restrict EU records to GDPR-authorised roles
- Evaluate data residency requirements — may require separate EU-hosted database instance

### 1.4 HIGH: Legacy Compatibility Settings Create Query Correctness Risk
**Finding:** `database.Prepaid_Warehouse_Intl.sqlproj` lines 28–29 set `AnsiNulls = False` and `QuotedIdentifier = False`.

**Impact:**
- Queries using `WHERE column = NULL` instead of `WHERE column IS NULL` will return different results depending on session settings
- Single-quoted identifiers will be treated as string literals, not object names, in some contexts
- Portability to modern SQL Server environments is compromised

**Remediation (Priority: P2):**
- Audit all stored procedures for NULL comparison patterns
- Fix procedures to use `IS NULL` / `IS NOT NULL` consistently
- Set `AnsiNulls = True` and `QuotedIdentifier = True` in sqlproj

---

## 2. All Database Objects with Purpose

### 2.1 Stored Procedures

| Procedure | Purpose |
|---|---|
| `rpt_claimable_payment` | International claimable payment detail report |
| `rpt_claimable_payment_summary` | International claimable payment summary |
| `rpt_std_header` | Standard report header for international programs |
| `rpt_std_issuanceaggregate` | Standard issuance aggregate for international programs |
| `rpt_TTS_data_feed` | International TTS partner data feed — multi-currency, country-dimensional |
| `sprocInc_Capture_Incremental_DDAs` | Capture incremental DDA changes from international operational systems |
| `sprocInc_Create_ColumnStore_DimAccountHolder` | Rebuild columnstore index for OLAP |
| Additional `sprocInc_*` ETL procedures | Mirror of US warehouse incremental patterns |

### 2.2 Key Tables

| Table | Purpose | Sensitive |
|---|---|---|
| `dim.DimAccountHolder` | International cardholder identity dimension | Yes — full PII |
| `dim.DimProgram` | International program metadata | No |
| `dim.DimProduct` | International product/brand metadata | No |
| `dim.DimBIN` | BIN range dimension | BIN prefix |
| `dim.DimCountry` | Country reference dimension (intl-only) | No |
| `dim.DimGLCompany` | GL Company + currency dimension | No |
| `fact.FactPaymentTransactions` | International payment transaction history | DDA number |
| `fact.FactUtilizationTransactions` | International spend/utilisation history | DDA number |
| `fact.FactCardAccountDetail` | Card account to DDA linkage | DDA number |
| `fact.FactClaimablePaymentIssuance` | Claimable payment lifecycle | Amounts |
| `fact.FactAccountSnapshot` | Daily balance snapshot | Amounts |

---

## 3. Technical Debt Remediation Priority

| Priority | Item | Effort | Risk |
|---|---|---|---|
| P0 — Immediate | Verify SQL Server version — if 2012, plan emergency upgrade | High (months for full migration) | Security patching, GDPR |
| P1 — Immediate | Apply GDPR data governance controls (jurisdiction flagging, RLS) | High | GDPR Article 25 |
| P1 — Immediate | Implement PII masking / access restriction | Medium | GDPR, CCPA |
| P1 — Immediate | Implement deletion/anonymisation procedure for inactive EU accounts | Medium | GDPR Article 17 |
| P2 — Short term | Fix AnsiNulls/QuotedIdentifier settings | Medium | Query correctness |
| P2 — Short term | Establish CI/CD pipeline | Medium | Deployment quality |
| P2 — Short term | Document data residency hosting location | Low | GDPR Article 44 |
| P3 — Medium term | Unify US/International warehouse schemas | Very High | Maintainability |

---

## 4. Compliance Gap Summary

| Regulation | Gap | Severity |
|---|---|---|
| GDPR Article 25 | No privacy by design — PII unprotected in analytical table | Critical |
| GDPR Article 17 | No right-to-erasure procedure | Critical |
| GDPR Article 44 | Data residency hosting not documented/controlled | High |
| PCI DSS Req 6.3 | SQL Server 2012 EOL — no security patches | Critical |
| PIPEDA | No consent/purpose limitation controls in schema | High |
| Quebec Law 25 | No data governance metadata for Quebec residents | High |
| NIST CSF | SQL 2012 EOL, no CI/CD, no masking | High |
