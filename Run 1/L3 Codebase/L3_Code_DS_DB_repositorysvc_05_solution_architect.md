# DS_DB_repositorysvc — Solution Architect Assessment

## 1. Security Vulnerabilities and Findings

### 1.1 HIGH: Latent Transaction Management Bug
**Finding:** `dbo/Stored Procedures/repo_retrieve_file.sql`, lines 30–32:
```sql
declare @trancount int
...
if @trancount = 0
    begin transaction
```
`@trancount` is declared but never assigned. It is `NULL`. `IF NULL = 0` is always false (ANSI NULL semantics), so `BEGIN TRANSACTION` is never executed. The corresponding `COMMIT TRANSACTION` and `ROLLBACK TRANSACTION` branches (lines 66–73) operate against no active transaction. While this does not cause data corruption for the current `SELECT`-based implementation, any future modification of this procedure to include DML operations would silently omit transaction management.

**Remediation (Priority: P1):**
```sql
-- Replace GOTO pattern with TRY...CATCH and proper transaction management:
BEGIN TRY
    BEGIN TRANSACTION
    -- ... operations ...
    COMMIT TRANSACTION
END TRY
BEGIN CATCH
    ROLLBACK TRANSACTION
    EXEC repo_log_error @@ERROR, 'Error in repo_retrieve_file', 'repo_retrieve_file'
    RETURN 1
END CATCH
```

### 1.2 HIGH: Encryption Not Enforced at Database Level
**Finding:** `dbo/Tables/repo_file.sql`, line 12: `[encryption_code] INT NULL`. The `encryption_code` column is nullable. There is no `CHECK CONSTRAINT` or trigger enforcing that files containing sensitive data must have an encryption code.

**Impact:** Services can register files for sensitive content (KYC documents, dispute evidence, settlement files) without specifying an encryption scheme. The database has no control to prevent unencrypted PII files from entering the repository.

**Remediation (Priority: P1):**
- For file types that are known to contain sensitive data, add a check at the `repo_file_type` level (e.g., a `requires_encryption` flag)
- Add an application-layer enforcement: reject `repo_stage_file` calls with NULL `encryption_code` for sensitive file types
- Consider adding a `CHECK CONSTRAINT` or trigger on `repo_file` to enforce non-null `encryption_code` for specific `file_type_id` values

### 1.3 MEDIUM: `repo_file_type.relative_path` Exposes Filesystem Topology
**Finding:** `dbo/Tables/repo_file_type.sql` stores the relative filesystem path for each file type. Exposure of this table's data to any user who can query `repo_file_type` reveals the internal filesystem directory structure.

**Remediation (Priority: P3):**
- Restrict `SELECT` on `repo_file_type.relative_path` to application service roles only
- Do not expose this information in API responses

### 1.4 LOW: `dbo.CodeArchive` Table Contains Potentially Sensitive SQL
**Finding:** `dbo/Tables/CodeArchive.sql` is a legacy code archive table that may contain historical SQL scripts, including scripts that may reference actual table names, data structures, or even historical data samples. The contents are not visible in the repository (only the DDL), but the existence of this table in a production database is a compliance concern.

**Remediation (Priority: P3):**
- Audit the contents of `dbo.CodeArchive` in production
- If no active use is confirmed, truncate and drop the table
- Ensure no sensitive data (credentials, PII samples) is stored in this table

---

## 2. All Database Objects with Purpose

### 2.1 Tables

| Table | Purpose | Sensitive Fields |
|---|---|---|
| `repo_file` | Core file metadata registry | `archived_name` (reveals storage name), `encryption_code` (nullable) |
| `repo_file_audit` | File access audit trail | `member` GUID, `host`, `host_relative_path` — access metadata |
| `repo_file_attributes` | Key-value file metadata | `attribute_value` VARCHAR(512) — **potentially PII if attributes include cardholder data** |
| `repo_file_attributes_log` | Change history for file attributes | Same as above |
| `repo_file_type` | File type definitions with filesystem paths | `relative_path` — filesystem topology |
| `repo_file_encryption_type` | Encryption scheme reference data | None — reference data only |
| `repo_file_association` | File-to-file relationship pairs | None |
| `repo_file_action` | Action code reference data | None |
| `repo_submission_channel` | Submission channel reference data | None |
| `repo_attribute_control` | Attribute type definitions | None |
| `repo_error_log` | Error log | None |
| `dbo.ddl_log` | DDL change audit log | None |
| `dbo.CodeArchive` | Historical SQL code store | **Potentially sensitive — audit required** |

### 2.2 Stored Procedures

| Procedure | Purpose | Security Notes |
|---|---|---|
| `repo_stage_file` | Stage a file | Entry point — validate encryption code here |
| `repo_create_file` | Commit staged file | Action code 100 |
| `repo_retrieve_file` | Retrieve file metadata + audit | Bug: @trancount never set |
| `repo_delete_file` | Delete file record | No soft-delete / archive pattern |
| `repo_check_file_existence` | Check file exists | None |
| `repo_get_file_definition` | Get file metadata | None |
| `repo_get_file_type_path` | Get storage path | Returns sensitive path info |
| `repo_get_file_attributes` | Get file attribute values | May return PII attribute values |
| `repo_get_latest_file_version` | Get latest file version | None |
| `repo_set_file_attribute` | Set file attribute | No validation of PII in values |
| `repo_begin_set_file_attributes` | Begin attribute transaction | None |
| `repo_commit_set_file_attributes` | Commit attribute transaction | None |
| `repo_create_file_audit` | Write audit record | Core security control |
| `repo_create_file_association` | Create file relationship | None |
| `repo_remove_file_association` | Remove file relationship | None |
| `repo_get_associated_file_definitions` | Get associated files | None |
| `repo_file_inquiry_get_criteria` | Build inquiry filter | Dynamic SQL risk — review for injection |
| `repo_file_inquiry_get_param_list` | Get inquiry parameters | Dynamic SQL risk |
| `repo_file_inquiry_get_sort_order` | Get inquiry sort order | Dynamic SQL risk — sort order injection |
| `repo_log_error` | Log error | None |

### 2.3 Function

| Function | Purpose |
|---|---|
| `dbo.SplitString` | String splitting utility |

---

## 3. Dynamic SQL Risk Flag

The `repo_file_inquiry_get_criteria`, `repo_file_inquiry_get_param_list`, and `repo_file_inquiry_get_sort_order` procedures have names strongly suggesting they build dynamic SQL for file inquiry operations. Dynamic SQL construction with sort order expressions is a classic SQL injection vector if sort column names are not validated against an allowlist. These procedures require a **security review** to confirm they use parameterised queries or validated column name allowlists. The procedure files were not directly read in this analysis — this is flagged for immediate review.

---

## 4. Remediation Priority

| Priority | Item | Effort |
|---|---|---|
| P1 | Fix `@trancount` transaction bug in `repo_retrieve_file` | Low (hours) |
| P1 | Enforce encryption for sensitive file types | Medium (days) |
| P1 | Security review of dynamic SQL in inquiry procedures | Low (days) |
| P2 | Implement audit table archival/partitioning for `repo_file_audit` | Medium |
| P2 | Restrict `repo_file_type.relative_path` access | Low |
| P3 | Audit and clean `dbo.CodeArchive` | Low |
| P3 | Migrate to TRY...CATCH error handling | Medium |
| P3 | Establish CI/CD pipeline | Medium |
