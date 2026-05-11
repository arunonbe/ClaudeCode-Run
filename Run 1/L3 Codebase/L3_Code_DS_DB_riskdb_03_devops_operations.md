# DS_DB_riskdb — DevOps and Operations Assessment

## 1. Build and Deployment Pipeline

### 1.1 Project Type
Standard SSDT project targeting SQL Server 2016. A compiled DACPAC (`RiskDBv1.0.0.0.dacpac`) is committed to the repository root. The DACPAC version `v1.0.0.0` suggests versioning was started but may not be actively maintained (the version may not have incremented).

### 1.2 CI/CD
**No CI/CD pipeline configuration is present.** The `_archived` folder structure with individual employee subdirectories (`_archived/NAM_Byron.Young/`, `_archived/NAM_Michael.Gevaryahu/`, `_archived/NAM_mg97007/`) strongly suggests that historically, individual developers committed tables and procedures directly to the database without a gated deployment process. This is a significant DevOps maturity gap for a compliance-critical database.

### 1.3 Archived Objects
The `_archived/` folder contains subdirectories for multiple named employees, each containing tables and stored procedures. This pattern indicates:
- Individual ad-hoc work was committed to the repository rather than to personal branches
- These objects may still exist in production if they were deployed before archival
- The archived procedures (`_archived/mantas/`, `_archived/Old Procedures/`) suggest legacy Mantas AML system integration was retired at some point

### 1.4 _config and _QRY_Reports Folders
- `_config/` — contains base insert scripts for DMT application installation
- `_QRY_Reports/` — contains reporting scripts and supporting objects

---

## 2. Operational Characteristics

### 2.1 Daily Batch Job
`DailyRiskReports` is the core operational procedure, designed to run once per day. It:
1. Truncates all 8 monitoring tables
2. Repopulates them with previous-day data
3. Takes approximately 50 minutes to run (per the comment on line 10: `--50 mins`)

This long runtime means:
- The monitoring tables are unavailable for reporting during the 50-minute run window
- If the job fails mid-run, monitoring tables are empty (truncated but not repopulated)
- There is no transactional wrapper — a partial failure leaves inconsistent state

### 2.2 Scheduled Procedures
Multiple `Analytics_sp_DMT_*` procedures are scheduled jobs:
- AML Case Module — appears to run on a schedule (inserts cases with `'SQL Job' [UpdatedBy]`)
- `Analytics_sp_DB_Space_Report` / `Analytics_sp_DB_Space_Report2` — monitor database space
- `Analytics_sp_LowSpace_Notification` — space monitoring with email notification
- ATM Cash Order Email, Hold Reports — scheduled operational notifications

### 2.3 Email Notifications
Multiple procedures send email notifications:
- `Analytics_sp_DMT_ATM_CashOrderEmail`
- `Analytics_sp_DMT_HoldReport_1stAlert`, `1stEmail`, `2ndAlert`, `2ndEmail`
- `Analytics_sp_DMT_IssueTrackerInternal_Email`
- `Analytics_sp_DMT_Entitlements_ServiceDesk_Email`
- `Analytics_sp_Surcharge_Results_email`
- `EUC_DMT_SP_SendEmail`

These procedures use SQL Server Database Mail (`sp_send_dbmail`). Operational email delivery is a dependency — if the mail profile or SMTP relay fails, operational alerts are silently lost.

---

## 3. Change Management Challenges

### 3.1 Scale of Database
The riskdb has hundreds of tables spread across three sub-folders, plus an archive folder. It is one of the largest databases in the Onbe portfolio based on object count. Any change to the EAV case model (adding a new field type) affects all `EUC_DMT_*_DATA` tables simultaneously.

### 3.2 Hardcoded Business Logic
Several business logic elements are hardcoded in stored procedures rather than managed through configuration tables:
- AML threshold: `@Threshold int = 0` — should be a configurable parameter
- AML monitoring verticals: `('Maritime Payroll','Payroll','Sales Incentive')` — should be in a reference table
- AML target region: `@Region varchar(4) = '0401'` — should be configurable
- AML case owner: `'Nathan.Sandiford'` — a named employee hardcoded in production code

Changes to any of these business rules require code changes and redeployment rather than reference data updates.

### 3.3 Monitor Table Truncate Pattern
`DailyRiskReports` truncates all monitoring tables at the start of each run (`TRUNCATE TABLE RiskDB..monitor_*` at lines 24–31). This means:
- No historical trend data is retained in these tables between daily runs
- If the reporting window for a report is missed, the data is gone
- There is no point-in-time recovery for monitoring data

---

## 4. Backup and Recovery

The DACPAC `RiskDBv1.0.0.0.dacpac` committed to the repository provides a schema snapshot. For BSA/AML compliance purposes, AML case records in `EUC_DMT_AMLCase_DATA` must be retained for 5 years. The backup strategy for this database is critical and not visible in the repository. Any backup failure affecting AML case data is a BSA violation.

---

## 5. Security Operations

### 5.1 Access Control
The Security folder defines role memberships for riskdb. Given the nature of this database (fraud cases, AML data, dispute records, subpoena tracking), access should be tightly controlled. Emergency access accounts (`emer_*`) and the breadth of the GERS (internal reporting) role require review.

### 5.2 FortiDB Monitoring
`FortiDBRptRole` confirms database activity monitoring. Given the compliance sensitivity of AML and fraud case data, robust DAM coverage is essential.

### 5.3 Linked Server Queries
`DailyRiskReports` and `Analytics_sp_AML_Case_Module` query `[REPORTINGDBSERVER].ECountcore_ss.*` and `[REPORTINGDBSERVER].Ecountcore_Process_ss.*` via linked server. Compromise of riskdb could expose linked server queries as a lateral movement vector to the core operational database.

---

## 6. Key Operational Risks

1. **50-minute daily job with truncate-and-reload** — monitoring tables are empty and unavailable during the daily run; partial failures leave empty tables
2. **Hardcoded AML case owner** — AML cases auto-created by SQL Job assigned to a named individual; if that person leaves, cases are unassigned
3. **No CI/CD** — compliance-critical database changes can be deployed without review
4. **Ad-hoc tables with client-identifiable names** — production database contains tables named for specific clients with data going back to 2008; these may contain ungoerned cardholder data
5. **EAV case model** — DML on `EUC_DMT_*_DATA` tables is complex and error-prone; data quality issues are difficult to detect
6. **Email dependency** — operational alerts delivered via Database Mail; mail failures result in silent loss of compliance-relevant notifications
