# DS_DB_ecountcore_process_archive — DevOps and Operations View

## Build System

- **Repository Type**: Migration script repository — NOT an SSDT project
- **No `.sqlproj` file**: There is no Visual Studio SQL Server Database Project. Scripts are plain `.sql` files organised in dated, numbered folders.
- **Change Set Format**: `YYYYMMDD-StoryID-description/` folders containing numbered `.sql` files executed in filename order
- **Target SQL Server**: SQL Server 2016 (consistent with the rest of the Ecountcore platform)
- **No DACPAC Output**: Because this is not an SSDT project, there is no DACPAC artifact. Deployment is entirely manual — a DBA runs the numbered scripts in sequence.

---

## CI/CD Pipeline

**No CI/CD pipeline is configured.** No `.gitlab-ci.yml` is present in the repository. All deployments are manual script executions by a DBA. This is a higher risk than the SSDT-based repositories because:

1. There is no schema validation before deployment
2. There is no pre-deployment diff review
3. There is no automated rollback mechanism
4. Script execution order is enforced by convention (numbered filenames) rather than tooling
5. No automated testing verifies that the archive partition maintenance procedure executes correctly after deployment

For a database holding years of archived financial records (NACHA, FDR settlement data, cardholder data), the absence of CI/CD represents an operational risk.

---

## Change Set Structure

### Deployed Change Sets

| Change Set | Date | Story | Description |
|---|---|---|---|
| `20210823-Initial-Base` | 2021-08-23 | US565 (implied) | Full initial schema deployment |
| `20210824-US565-Fix-monthly-database-archive` | 2021-08-24 | US565 | Bug fix — PK restructure and data cleanup for `fdr_process_dcaf_auth_data` |

The one-day gap between initial deployment and the bug fix is notable: it suggests the initial deployment was found to have an incorrect primary key structure on `fdr_process_dcaf_auth_data`, requiring a manual data deletion and PK alter in production within 24 hours. This kind of rapid emergency patch is a symptom of inadequate pre-deployment testing.

### 20210824-US565 Execution Sequence

The bug fix change set must be executed in strict file order:

1. `001_create_nci_fdr_process_dcaf_auth.sql` — Create temporary NCI to support the DML delete
2. `002_dml_manual_delete_dcaf_auth_data.sql` — Delete excess/duplicate rows that would block the PK change
3. `003_drop_nci_fdr_process_dcaf_auth.sql` — Drop the temporary NCI
4. `004_drop_pk_alter_batch_spa_create_pk.sql` — Drop old PK, alter table, create new PK with correct `batch_spa`/`batch_date`/`batch_record_id` structure
5. `005_dml_archive_retention_online_months.sql` — Set retention period values in `ecountcore_process_archive_partition_control`

Executing these out of order (e.g., step 4 before step 2) would fail due to uniqueness violations or index conflicts.

---

## Partition Maintenance Operations

The `ecountcore_process_archive_partition_maintain` stored procedure performs:

1. **Split**: Creates new monthly partitions as needed for current and next month
2. **Archive Expiry**: For each table in `ecountcore_process_archive_partition_control`, partition-switches data older than `online_months` to the `*_switch` table, then truncates (final deletion — data is not moved further)
3. **Merge**: Cleans up empty historical partitions beyond the maximum retention period

Unlike the `Ecountcore_Process` database where archived data is moved to the archive DB, in the archive database the expiry step is **final deletion**. Data aged out of the archive database is gone. This makes the `online_months` values in `ecountcore_process_archive_partition_control` critically important for regulatory compliance — setting them too short could cause premature deletion of records needed for NACHA (2-year minimum), Reg E (24 months), or state law (up to 7 years) requirements.

The procedure should be scheduled to run monthly via SQL Server Agent, consistent with the source `Ecountcore_Process` maintenance job.

---

## Environments

No explicit environment-tagged service accounts are visible in the archive database security scripts (unlike the process DB which has `NAM\PPA_PRD_*SVC`, `NAM\UAT`, etc.). The archive database security roles are:

| Role | Purpose |
|---|---|
| `ecountcore_process_archive_Delete` | Grants DELETE on archive tables — needed for partition switch/truncate operations |
| `ecountcore_process_archive_Execute` | Grants EXECUTE on stored procedures |
| `ecountcore_process_archive_Select` | Grants SELECT — used by reporting, AML feeds |
| `ecountcore_process_archive_Update` | Grants UPDATE |
| `FortiDBRptRole` | FortiDB database activity monitoring reporting role |
| `gers_role` | GERS (Governance, Enterprise Risk, and Security) monitoring role |

The `ecountcore_process_archive_Delete` role is particularly sensitive — it grants delete access to tables containing archived cardholder data, NACHA records, and potentially CVV data.

---

## Storage Configuration

The archive database uses the `[PRIMARY]` filegroup for all partitioned data. This is a key operational difference from the source `Ecountcore_Process` database, which uses a dedicated `ECP_FG1` filegroup.

**Operational implications**:
- All archive data competes with system objects for space on `[PRIMARY]`
- Cannot independently back up or restore partition data by filegroup
- Cannot move cold partitions to cheaper/slower storage tiers
- SQL Server backup of `[PRIMARY]` includes all archive data — no granular backup possible

For a database that may hold 5-7 years of financial data, the `[PRIMARY]`-only design limits operational storage management.

---

## Backup and Recovery

### Recovery Characteristics

The archive database has distinct recovery requirements:
- **RPO**: Can tolerate some data loss (archived data exists in `Ecountcore_Process` for `online_months` before being moved here)
- **RTO**: Moderate — if the archive is lost, regulatory compliance gaps open immediately for any data that had already been deleted from `Ecountcore_Process`
- **Critical window**: Once data has been partition-switched out of `Ecountcore_Process` and into the archive, it only exists in the archive database. Loss of the archive DB at this point means permanent data loss.

### Recovery Scenario: Archive DB Lost After Partition Switch

If `Ecountcore_Process_Archive` is lost after `ecountcore_process_partition_maintain` has completed its archive step (data is in the archive DB, switch table in the process DB has been truncated):
- The archived partition data **cannot be recovered** from the source unless the source DB has a pre-switch backup
- This represents a potential regulatory compliance breach (NACHA 2-year, Reg E 24-month)
- QSA, Legal, and Compliance must be notified immediately

**Recommendation**: Ensure SQL Server Agent backups for the archive database run on the same schedule (or more frequently) as the `ecountcore_process_partition_maintain` job. Consider log-shipped replicas for the archive database.

---

## Operational Risks

| Risk | Severity | Detail |
|---|---|---|
| `cvv_in` column in `fdr_process_dcaf_auth_data` | Critical | CVV from FDR DCAF auth data is archived here indefinitely — PCI DSS Req 3.3.1 violation |
| `online_months` set too short | Critical | Premature deletion of NACHA/Reg E required records — regulatory violation |
| No CI/CD pipeline | High | Manual script execution — no validation, no diff review, no automated rollback |
| Archive on [PRIMARY] filegroup | Medium | Storage management limitations; no filegroup-level backup isolation |
| Dynamic SQL in partition maintain procedure | Medium | SQL injection risk via table name values from `ecountcore_process_archive_partition_control` — same risk as source DB procedure |
| No documented rollback for migration scripts | Medium | Once `002_dml_manual_delete_dcaf_auth_data.sql` is run, deleted rows cannot be recovered without a pre-execution backup |
| Single-region deployment (implied) | Medium | No evidence of geo-redundant replica or Azure Site Recovery for disaster recovery |
