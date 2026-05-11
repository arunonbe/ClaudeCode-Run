# DS_DB_vendor — DevOps and Operations Assessment

## 1. Build and Deployment Pipeline

### 1.1 Project Type
Standard SSDT project targeting **SQL Server 2016** (`DSP: Microsoft.Data.Tools.Schema.Sql.Sql130DatabaseSchemaProvider`). This is a more recent SQL Server target than the international warehouse or StrongBox. SQL Server 2016 reached end of mainstream support in July 2021 and end of extended support in July 2026 — still within the extended support window as of 2026.

Key project settings from `Vendor.sqlproj`:
- `TargetFrameworkVersion = v4.5` — .NET 4.5
- `SqlServerVerification = False` — SSDT does not validate SQL syntax during build
- `ModelCollation = 1033, CI` — case-insensitive collation

### 1.2 CI/CD
**No CI/CD pipeline is present.** The repository contains no `.yml`, `.json`, or pipeline configuration files. For a database that stores full card numbers (PAN), plaintext Social Security Numbers, and OFAC screening results, the absence of a gated deployment pipeline with security review requirements is a significant compliance gap.

PCI DSS Requirement 6.2.4 states: "All software-development practices prevent common vulnerabilities." Requirement 6.3.2 requires: "An inventory of bespoke and custom software is maintained to facilitate vulnerability and patch management." Without CI/CD, neither requirement can be enforced through automated process.

### 1.3 No DACPAC Committed
No pre-built DACPAC artifact is present in the repository. Deployments depend on SSDT project build output.

---

## 2. Security Role Architecture

### 2.1 Defined Custom Roles

| Role | File | Members |
|---|---|---|
| `Vendor_Select` | `Security/Vendor_Select.sql` | 20+ accounts including all production service accounts |
| `Vendor_execute` | `Security/Vendor_execute.sql` | Subset of production accounts |
| `Vendor_Update` | `Security/Vendor_Update.sql` | Subset |
| `Vendor_Delete` | `Security/Vendor_Delete.sql` | Subset |
| `Vendor_Schema_View` | `Security/Vendor_Schema_View.sql` | Subset |
| `GBBase` | `Security/GBBase.sql` | Schema-level role for GBBase |
| `GBLoads` | `Security/GBLoads.sql` | Schema-level role for GBLoads |
| `GBMap` | `Security/GBMap.sql` | Schema-level role for GBMap |
| `FortiDBRptRole` | `Security/FortiDBRptRole.sql` | FortiDB monitoring integration |
| `gers_role` / `gers_read` | `Security/gers_role.sql`, `gers_read.sql` | GERS (Global Export Reporting System?) |
| `abat_vendor` | `Security/abat_vendor.sql` | ABAT integration role |
| `report` / `report_full` / `report_readonly` | Multiple files | Reporting access tiers |

### 2.2 `db_owner` Memberships — Critical
`Security/RoleMemberships.sql` (lines 1–10) grants `db_owner` to:
- `vendor` — application login
- `nam\jd62380` — named individual account
- `NAM\PPA_PRD_ABAT` — production ABAT service account

`db_owner` grants unrestricted access to all tables, stored procedures, and schema objects. For a database containing plaintext SSN and PAN data, `db_owner` membership for service accounts violates PCI DSS Requirement 7.2 (least privilege). The presence of a named individual (`jd62380`) in `db_owner` is particularly concerning — if this individual has left Onbe, the account may still have unrestricted database access.

### 2.3 `db_datareader` Memberships
`db_datareader` grants SELECT on ALL tables, including `GBBase.CustomerMaster.SSN` and `dbo.fdr_cardholder_master.card_number`. Members include:
- `CB_OFFICE\SQLDBUsers_Read` — broad office user group
- `NAM\PPA_DB_ACCESS` — general DB access group
- `NAM\UAT` — UAT environment account (potentially accessing production data)
- `NAM\PPA_PRD_ABAT` — also a `db_owner` member
- `NAM\PROD_ITOPS` — IT operations account
- `NAM\PROD` — general production account
- `report_readonly` — reporting read-only role

The `NAM\UAT` membership in a production database's `db_datareader` role is an environment segregation failure — UAT credentials with production data access directly violates PCI DSS Requirement 6 (separation of environments).

### 2.4 FortiDB Integration
The `FortiDBRptRole` security role indicates FortiDB database activity monitoring is deployed for the Vendor database. This is a positive security control providing database query auditing. However, the value of FortiDB monitoring is limited if `db_owner` accounts can create and drop their own audit traces.

---

## 3. Operational Dependencies

### 3.1 FDR File Feed Dependency
The database is critically dependent on daily FDR file feeds. The `GBLoads.Files` table tracks these feeds — if an FDR file fails to load, the `GBBase.CustomerMaster` data becomes stale, affecting NESS screening extracts (which would miss newly enrolled cardholders) and reporting views.

The `GBLoads.uspRollBack` procedure provides a rollback capability for failed file loads — rolling back records associated with a specific `fkFileID`. This is a positive operational design.

### 3.2 NESS Screening Engine Dependency
The `uspNESSDailyExtract` and `uspNESSWeeklyExtract` procedures assume an external NESS engine receives the extract and returns results via the `dbo.ness_hits` table. There is no in-database mechanism to verify that the NESS engine has processed the extract and returned results within an expected window. A silent failure in the NESS pipeline could result in unscreened cardholders going undetected.

### 3.3 `uspNESSDailyExtract` Date Range Bug
`GBLoads/Stored Procedures/uspNESSDailyExtract.sql`, line 43:
```sql
WHERE PICreated > @startdate AND PICreated > @enddate
```
Both conditions use `>` (greater than). The intended logic was almost certainly `PICreated > @startdate AND PICreated <= @enddate` (i.e., records within the date range). As written, both conditions filter for records after the start date and after the end date — since `@enddate = GETDATE()` (today), the second condition `PICreated > GETDATE()` would exclude all records (no records created in the future). **This means the NESS daily extract produces an empty result set and no cardholders are screened.** This is a critical operational and OFAC compliance failure.

### 3.4 GoogleBinKey Expiry
The `GoogleBinKey` symmetric key is encrypted by `GoogleBinCert`, which expired October 2012. Any stored procedure or application that attempts to `OPEN SYMMETRIC KEY GoogleBinKey DECRYPTION BY CERTIFICATE GoogleBinCert` will fail if certificate expiry is enforced. This may silently cause failures in any Google BIN lookup functionality.

---

## 4. Key Operational Risks

### 4.1 `fdr_cardholder_master` — No Indexes, No PK
`dbo/Tables/fdr_cardholder_master.sql` has no primary key and no indexes. Queries against this table (e.g., card number lookups) will always perform full table scans. For a table that may contain millions of rows of FDR cardholder data, this creates performance risk for any downstream process that queries it.

### 4.2 IVR Call Log Cleanup
`usp_IVR_CallLog_Cleanup` exists to purge old IVR call records, but there is no visible scheduled job or retention policy definition in this repository. If `usp_IVR_CallLog_Cleanup` is not called on a regular schedule, `IVR_CallLog` will accumulate cardholder DOB and phone number records indefinitely — violating data minimisation principles under GDPR (Art 5(1)(e)) and CCPA.

### 4.3 Dated DCAF Tables
Tables `fdr_process_dcaf_chd_data_20061223` and `fdr_process_dcaf_chd_data_20090519`, and `fdr_process_dcaf_auth_data_20061223` and `fdr_process_dcaf_auth_data_20090519` have dates embedded in their names (December 2006, May 2009). These appear to be point-in-time schema snapshots or historical data tables retained past their operational use. They should be audited for active data and archived or dropped if no longer required.

### 4.4 `september.sql` and `sep_quality.sql` — Ad-hoc Tables
`dbo/Tables/september.sql` and `dbo/Tables/sep_quality.sql` are named after a month — consistent with ad-hoc analysis tables created for one-off reports and never cleaned up. These should be audited for any cardholder or transaction data and dropped.

---

## 5. Change Management Gaps

1. **No peer review requirement** visible in CI/CD configuration.
2. **No security review gate** for changes affecting `GBBase.CustomerMaster` (SSN, PAN storage).
3. **Named individual** `nam\jd62380` has `db_owner` — may be a former employee with active privileged access.
4. **`NAM\UAT` in production** `db_datareader` — UAT environment credential with production PII access.
5. **Multiple archived stored procedure variants** (`thankyou_get_shipping_report_old_04242009.sql`) remain in production schema — dead code that could be exploited or cause confusion during incident response.

---

## 6. Backup and Recovery

Loss of the Vendor database would mean loss of:
- All FDR-sourced cardholder master records (`GBBase.CustomerMaster`)
- All authorized and posted transaction history (`GBBase.AuthorizedTransactions`, `GBBase.PostedTransactions`)
- OFAC hit records (`dbo.ness_hits`) — a BSA compliance record
- IVR call logs — potential fraud investigation evidence
- Chargeback queue — active dispute processing would be interrupted

The CDC journal view (`GBBase.CustomerMaster_CDC_Journal`) implies CDC is enabled on the Vendor database — CDC change tables must also be backed up as they contain the full change history for the most sensitive table in the database.

Backup strategy must ensure:
- Backups of `CustomerMaster` are themselves encrypted (they contain plaintext SSN)
- Backup encryption keys are managed independently of the database
- Backup retention aligns with BSA 5-year retention for `ness_hits`
