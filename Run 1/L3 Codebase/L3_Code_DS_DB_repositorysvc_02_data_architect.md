# DS_DB_repositorysvc — Data Architect Assessment

## 1. Schema Design

The Repository Service database uses a single `dbo` schema. The design is a **metadata registry** (not a content store). It follows a file lifecycle state machine pattern backed by relational tables.

---

## 2. Complete Table Inventory

### 2.1 Core File Registry

#### `dbo.repo_file`
File: `dbo/Tables/repo_file.sql`

| Column | Type | Purpose | Notes |
|---|---|---|---|
| `file_id` | UNIQUEIDENTIFIER PK | Globally unique file identity | Non-clustered PK |
| `file_name` | VARCHAR(100) NOT NULL | Original user-facing file name | |
| `file_version_number` | INT | File version counter | Nullable |
| `file_type_id` | INT NOT NULL | FK to `repo_file_type` | Determines storage path |
| `created` | DATETIME | Record creation timestamp | Default getdate() |
| `program_id` | VARCHAR(8) NOT NULL | Program context for the file | Indexed |
| `archived_name` | VARCHAR(100) NOT NULL | Name used for physical storage on disk | |
| `submission_channel_id` | INT NOT NULL | FK to `repo_submission_channel` | |
| `encryption_code` | INT | FK to `repo_file_encryption_type` | Nullable — files may be unencrypted |

**Clustered index:** `IX_repo_file__program_id_created` on (`program_id`, `created`)
**Non-clustered index:** `IX_repo_file__program_id_program_id` on (`program_id`, `file_type_id`) INCLUDE (`file_id`)

**Key observations:**
- `encryption_code` is nullable — this means some files may be stored with no encryption
- The clustered index on `(program_id, created)` optimises program-scoped file queries
- `archived_name` is the physical storage name — the mapping between `file_name` (user-visible) and `archived_name` (storage) is a security control that prevents directory traversal attacks

#### `dbo.repo_file_audit`
File: `dbo/Tables/repo_file_audit.sql`

| Column | Type | Purpose |
|---|---|---|
| `file_audit_id` | INT IDENTITY PK | Audit record identity |
| `file_id` | UNIQUEIDENTIFIER FK | File reference |
| `member` | UNIQUEIDENTIFIER NOT NULL | User/service identity (FK to application user system) |
| `action_code` | INT FK | Action performed (from `repo_file_action`) |
| `date` | DATETIME | Timestamp of action |
| `host` | VARCHAR(100) NOT NULL | Hostname that performed the action |
| `host_relative_path` | VARCHAR(256) | Host filesystem path |

**Clustered index:** `IX_repo_file_audit__file_id` on `file_id`

This table is the **primary audit trail** for file access. Every stage, create, retrieve, and delete event is recorded here with the performing service's member GUID and host IP/name.

#### `dbo.repo_file_attributes`
File: `dbo/Tables/repo_file_attributes.sql`

| Column | Type | Purpose |
|---|---|---|
| `file_id` | UNIQUEIDENTIFIER PK (composite) | File reference |
| `attribute_id` | INT PK (composite) | Attribute type FK |
| `attribute_value` | VARCHAR(512) NOT NULL | Attribute value |

**Sensitive data risk:** The `attribute_value` column (VARCHAR 512) can store arbitrary metadata associated with a file. Depending on the attributes defined in `repo_attribute_control`, this could include cardholder names, SSNs, or other PII as file metadata tags. This column warrants a data classification review.

#### `dbo.repo_file_attributes_log`
Audit log of attribute changes — same schema as `repo_file_attributes` with additional timestamp/change tracking columns.

#### `dbo.repo_file_association`
Stores file-to-file relationship pairs. Used for grouping related files (e.g., a batch file and its reconciliation file).

#### `dbo.repo_file_action`
Lookup table for action codes (staged=99, created=100, retrieved=120, etc.).

#### `dbo.repo_file_type`
| Column | Type | Purpose | Sensitivity |
|---|---|---|---|
| `file_type_id` | INT PK | Type identifier | None |
| `file_description` | VARCHAR(50) | Human-readable type name | None |
| `relative_path` | VARCHAR(50) | Filesystem relative path for this file type | **Medium** — reveals storage topology |

The `relative_path` column exposes the filesystem path structure of the file repository. If disclosed to an attacker, it reduces the effort needed to locate files on disk.

#### `dbo.repo_file_encryption_type`
| Column | Type | Purpose |
|---|---|---|
| `encryption_code` | INT PK | Encryption scheme identifier |
| `description` | VARCHAR(50) | Encryption scheme name |

This table defines the enumeration of encryption schemes. The actual values are not in the source repository (reference data is inserted separately). The `encryption_code` being nullable in `repo_file` implies a gap: files can be registered without an encryption code, meaning no encryption is required.

#### `dbo.repo_submission_channel`
Lookup table for how files were submitted (API, SFTP, manual upload, etc.).

#### `dbo.repo_attribute_control`
Defines allowed attribute types and validation rules for file attributes.

#### `dbo.repo_error_log`
Error log table for repository service failures.

#### `dbo.ddl_log`
DDL change history — records `ALTER TABLE`, `CREATE TABLE`, etc. executed against this database.

#### `dbo.CodeArchive`
Historical SQL code archive — legacy pattern of storing SQL scripts as table records.

---

## 3. Complete Stored Procedure Inventory

| Procedure | File | Purpose |
|---|---|---|
| `repo_stage_file` | `dbo/Stored Procedures/repo_stage_file.sql` | Stage a file with action_code=99 (initiates lifecycle) |
| `repo_create_file` | `dbo/Stored Procedures/repo_create_file.sql` | Commit staged file to created (action_code=100) |
| `repo_retrieve_file` | `dbo/Stored Procedures/repo_retrieve_file.sql` | Retrieve file metadata + create audit record (action_code=120) |
| `repo_delete_file` | `dbo/Stored Procedures/repo_delete_file.sql` | Delete file metadata record |
| `repo_check_file_existence` | `dbo/Stored Procedures/repo_check_file_existence.sql` | Check if a file exists by ID |
| `repo_get_file_definition` | `dbo/Stored Procedures/repo_get_file_definition.sql` | Get file definition metadata |
| `repo_get_file_type_path` | `dbo/Stored Procedures/repo_get_file_type_path.sql` | Get filesystem path for a file type |
| `repo_get_file_attributes` | `dbo/Stored Procedures/repo_get_file_attributes.sql` | Get all attributes for a file |
| `repo_get_latest_file_version` | `dbo/Stored Procedures/repo_get_latest_file_version.sql` | Get latest version of a named file |
| `repo_set_file_attribute` | `dbo/Stored Procedures/repo_set_file_attribute.sql` | Set a single file attribute |
| `repo_begin_set_file_attributes` | `dbo/Stored Procedures/repo_begin_set_file_attributes.sql` | Begin attribute update transaction |
| `repo_commit_set_file_attributes` | `dbo/Stored Procedures/repo_commit_set_file_attributes.sql` | Commit attribute update transaction |
| `repo_create_file_audit` | `dbo/Stored Procedures/repo_create_file_audit.sql` | Write an audit record |
| `repo_create_file_association` | `dbo/Stored Procedures/repo_create_file_association.sql` | Create file-to-file association |
| `repo_remove_file_association` | `dbo/Stored Procedures/repo_remove_file_association.sql` | Remove file association |
| `repo_get_associated_file_definitions` | `dbo/Stored Procedures/repo_get_associated_file_definitions.sql` | Get files associated with a file |
| `repo_file_inquiry_get_criteria` | `dbo/Stored Procedures/repo_file_inquiry_get_criteria.sql` | Build inquiry filter criteria |
| `repo_file_inquiry_get_param_list` | `dbo/Stored Procedures/repo_file_inquiry_get_param_list.sql` | Get inquiry parameter list |
| `repo_file_inquiry_get_sort_order` | `dbo/Stored Procedures/repo_file_inquiry_get_sort_order.sql` | Get inquiry sort order |
| `repo_log_error` | `dbo/Stored Procedures/repo_log_error.sql` | Log error to `repo_error_log` |

### Functions
| Function | Purpose |
|---|---|
| `dbo.SplitString` | Split a delimited string into rows (used for attribute/parameter parsing) |

---

## 4. File Lifecycle State Machine

```
[File submitted]
       |
       v
  action_code = 99 (STAGED) -- repo_stage_file
       |
       v (physical write to disk succeeds)
  action_code = 100 (CREATED) -- repo_create_file
       |
       v (file requested)
  action_code = 120 (RETRIEVED) -- repo_retrieve_file (also logs audit)
       |
       v (optional)
  action_code = [DELETE] -- repo_delete_file
```

---

## 5. Key Architectural Observations

1. **No content storage** — The database is purely metadata. Physical files are on a filesystem. This is a correct separation of concerns for a file repository metadata service.
2. **GOTO-based error handling** — `repo_create_file.sql` (lines 36–47) and `repo_retrieve_file.sql` use `GOTO cancel` / `GOTO done` patterns. This is a legacy SQL Server error handling style predating `TRY...CATCH` (SQL Server 2005+). It is functional but not idiomatic for modern SQL Server development.
3. **Transaction management inconsistency** — `repo_retrieve_file` checks `IF @trancount = 0` before beginning and committing a transaction, but `@trancount` is declared but never set (lines 31–32). This means `@trancount` will always be `NULL`, and `IF @trancount = 0` will never be true (NULL != 0). The transaction begin and commit are therefore never executed as intended. This is a latent bug.
4. **String literal as error message** — `repo_create_file.sql`, line 43: `exec repo_log_error @result_code, "Error updating data into table repo_create_file", "repo_create_file"` uses double-quoted string literals. This only works if `QUOTED_IDENTIFIER` is OFF, consistent with the legacy SQL Server convention.
5. **`encryption_code` nullable** — Allows file registration without encryption scheme, meaning not all files are required to be encrypted.
