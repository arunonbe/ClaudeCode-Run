# DS_DB_ecountcore — DevOps and Operations View

## Build System

- **Project Type**: SQL Server Database Project (`.sqlproj`)
- **Solution File**: `Ecountcore.sln`
- **Build Tool**: MSBuild / SSDT for Visual Studio
- **Target SQL Server**: SQL Server 2016 (`Sql130DatabaseSchemaProvider`)
- **Target Framework**: .NET 4.6.1
- **Output**: DACPAC artifact
- **Project Name**: `Ecountcore`

The project supports both Debug and Release configurations, producing a `.dacpac` for schema comparison and deployment.

---

## CI/CD Pipeline

**No CI/CD pipeline is configured in this repository.** The GitLab README is the default template. No `.gitlab-ci.yml` exists. Given the criticality of this database (PCI DSS CDE, active production cardholder data), the absence of automated testing, migration validation, or deployment gates is a significant gap.

Manual deployment via SSDT Publish or `sqlpackage.exe` is the presumed approach. Given the database is actively used by multiple production services, deployments must be carefully coordinated.

---

## Database Change Management

The repository uses SSDT object-level scripts — each object is a separate `.sql` file defining `CREATE` or `ALTER` statements. Change management observations:

1. **Branch**: Active branch is `development` (not `main` or `master`), suggesting a branch-based development workflow exists but pipeline automation does not.
2. **Data scripts**: Seed/reference data changes are tracked in `dbo/Data/` folder (e.g., `bin_bank_friendly_config_map_insert_FriendlyConfigId.sql`, `fdr_profile_block_code_insert_BLOCKED_SANCTION.sql`) — these use `MERGE` statements with proper transactions.
3. **No migration tool**: No Flyway, Liquibase, or numbered migration scripts are present. Schema changes are managed as SSDT object replacements.
4. **Rollback separate repo**: A dedicated `DS_DB_ecountcore_rollback` repository maintains rollback scripts and historical backup table definitions, indicating a manual rollback procedure is in use.

---

## Deployment Approach

1. SSDT developer builds the DACPAC on their workstation
2. DBA reviews the generated deployment script (DACPAC diff against target)
3. DBA applies the script during a maintenance window
4. For data changes: manual execution of scripts in `dbo/Data/`
5. Rollback: manual execution of scripts from `DS_DB_ecountcore_rollback`

No blue/green deployment, no zero-downtime migration approach is evident. For a database of this size and complexity, schema changes carry significant risk.

---

## Environments

The `development` branch is the active Git branch. Based on service account names in the security scripts of sibling repos:
- **PROD**: Production environment with `NAM\PPA_PRD_*` service accounts
- **UAT**: `NAM\UAT` environment
- **QA**: Likely exists based on QA SSIS packages referencing `q-db02.nam.wirecard.sys`
- **Development**: Developer local instances

---

## Backup and Recovery

### Criticality
This database contains the primary cardholder data for all active Onbe prepaid programs. Loss of this database without recovery would result in:
- Inability to process card transactions
- Loss of cardholder balance records
- Disruption of ACH payments
- Regulatory reporting gaps
- Potential Reg E violations (failure to process dispute requests timely)

### Backup Requirements
- **Full backup**: Minimum nightly
- **Differential backup**: Every few hours
- **Transaction log backup**: Every 15 minutes minimum (RPO = 15 minutes)
- **Off-site copy**: Required for PCI DSS Requirement 9.4.7 and DR capability

### Recovery Procedures
- Point-in-time recovery capability is essential given the financial nature of the data
- Recovery testing must be performed periodically (PCI DSS Req 12.5.4 recommends regular DR tests)
- Certificate (`card_number_cert`) backup is critical — if lost, encrypted PANs cannot be decrypted. Certificate backup must be stored securely and separately from the database backup.

---

## Monitoring

No monitoring configuration is in this repository. Operational monitoring requirements for this database:

1. **Transaction log growth** — ACH processing generates high write volume; log space monitoring required
2. **Long-running queries** — High-concurrency OLTP workload; query timeout monitoring
3. **Replication lag** (if HA via mirroring/AG) — critical for read-only replicas
4. **Certificate expiry** — `card_number_cert` expiry would break all PAN encryption/decryption — proactive monitoring required
5. **Blocked transactions** — ACH processing uses transactions; blocking chains must be monitored
6. **Dormancy fee processing** — Batch fee posting must complete within SLA windows

---

## Operational Risks

| Risk | Severity | Detail |
|---|---|---|
| Certificate (`card_number_cert`) expiry or loss | Critical | All encrypted PANs become permanently unreadable. Certificate backup and rotation process must be documented and tested. |
| No automated deployment pipeline | High | Manual deployments to a CDE database carry high change risk. Any error could corrupt cardholder records. |
| Dynamic SQL in `app_func_build_achFundSql`, `app_func_build_ccFundSql` | High | These functions build SQL strings dynamically. If caller-supplied values are not parameterised, SQL injection is possible. Code review required. |
| `fdr_card_account_create` accepts plaintext card number | High | The stored procedure signature includes `@card_number char(16)` as a parameter. Any call logs, SQL traces, or query store captures could expose unencrypted PANs. PCI DSS requires PANs to be rendered unreadable wherever transmitted. |
| CVV in `fdr_card_account_detail.cv_code` | Critical | Must be confirmed whether this column holds post-authorisation CVV (PCI violation) or a CV2 verification code only used during card creation (acceptable if purged). |
| SHA-1 card hash | Medium | SHA-1 is considered weak; upgrading to SHA-256 with salt is recommended. |
| `development` branch as primary | Medium | Production deployment from a `development` branch without merge/release gate increases risk of deploying untested changes. |
| No data masking for lower environments | High | QA/UAT environments with real cardholder data from production would be a PCI DSS scope expansion issue. Confirm data masking/synthetic data is used in non-production environments. |
| `monitor_*` procedures in rollback repo | Low | Monitoring query procedures exist in the rollback repo — these should be in the main repo and kept current. |
