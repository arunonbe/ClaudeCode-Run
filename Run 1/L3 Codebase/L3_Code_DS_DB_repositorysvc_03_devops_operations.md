# DS_DB_repositorysvc — DevOps and Operations Assessment

## 1. Build and Deployment Pipeline

### 1.1 Project Structure
Standard SSDT project (`RepositorySvc.sqlproj`, `RepositorySvc.sln`). No CI/CD pipeline files are present in the repository. Deployment is presumed manual (DACPAC or script-based).

### 1.2 Change Management Practices
The `dbo.ddl_log` table provides a database-level audit of DDL changes (`CREATE`, `ALTER`, `DROP` statements). This is a positive change management control — it records schema changes made directly against the database outside of the deployment process. However, it does not replace proper version-controlled deployments.

The `dbo.CodeArchive` table is a legacy pattern of versioning SQL scripts as database records. This is superseded by the Git repository and should be treated as dead data.

### 1.3 Security Role Management
The `Security/` folder contains 50+ files defining security principals and role memberships. The naming convention `NAM_PPA_PRD_*SVC` follows the broader Onbe pattern. The breadth of service accounts granted access (15+ named services) reflects the repository service's central role in the platform. Role files include:
- `repositorysvc_Delete.sql` — DELETE permission role
- `repositorysvc_execute.sql` — EXECUTE permission role
- `repositorysvc_Select.sql` — SELECT permission role
- `repositorysvc_Update.sql` — UPDATE permission role
- `RoleMemberships.sql` — maps principals to roles

---

## 2. Operational Characteristics

### 2.1 Audit Table Growth
`repo_file_audit` records every file access event — every stage, create, retrieve, and delete operation. As the platform's file repository, this table accumulates one row per file operation. If the platform processes tens of thousands of files per day, this table grows at a high rate. Without a retention or archival procedure, it will become a performance and storage concern.

**No archival or partition procedure** is defined in the repository for `repo_file_audit`.

### 2.2 Error Log Monitoring
`repo_error_log` captures repository service errors. Without a monitoring procedure or alerting mechanism, errors in this log may go undetected. There is no evidence of an alerting stored procedure or job watching this table.

### 2.3 File Attribute Change Audit
`repo_file_attributes_log` maintains a change history for file attributes. This is a good audit control but similarly has no visible archival mechanism.

---

## 3. Backup and Recovery

No backup configuration in the repository. Recovery of lost file metadata is critical because the mapping between file names and archived storage names is held only in this database. If the database is lost without backup, all stored files become orphaned (the physical files remain on disk but their metadata — including encryption codes and program associations — is lost, making decryption or correct retrieval impossible).

**Risk:** Loss of `repo_file` records for encrypted files means those files cannot be decrypted (assuming decryption requires the encryption code stored in this database).

---

## 4. Service Dependencies

The Repository Service database has a filesystem dependency (physical files are stored on disk at paths defined by `repo_file_type.relative_path`). Operational consistency requires:
- The filesystem paths must be accessible to all services that call `repo_retrieve_file`
- If the filesystem is migrated or remounted, all `relative_path` values in `repo_file_type` must be updated
- File permissions on the filesystem must align with the service accounts that have database access

---

## 5. Latent Bugs and Operational Risks

### 5.1 Transaction Management Bug in `repo_retrieve_file`
File: `dbo/Stored Procedures/repo_retrieve_file.sql`, lines 30–32:
```sql
declare @trancount int
...
if @trancount = 0
    begin transaction
```
`@trancount` is declared but **never assigned a value**. It remains `NULL` throughout. `IF NULL = 0` evaluates to `NULL` (not true or false), so the `BEGIN TRANSACTION` is never executed. This means `repo_retrieve_file` never opens an explicit transaction, and the `ROLLBACK TRANSACTION` on error (line 66) and `COMMIT TRANSACTION` on success (line 73) will attempt to commit or roll back a transaction that was never opened. In most cases, SQL Server will handle this gracefully (the `COMMIT` is a no-op if there is no active transaction), but `ROLLBACK` on an uncommitted transaction may raise an error. This is a pre-existing bug that has likely existed unnoticed because the procedure's primary operation (a `SELECT`) does not modify data.

### 5.2 GOTO-based Error Handling
`repo_create_file.sql` (line 36) uses `GOTO cancel`. This is a pre-`TRY...CATCH` error handling pattern. It cannot catch errors raised in called stored procedures or SET operations. Any uncaught exception in `repo_create_file` that is not surfaced via `@@ERROR` will not trigger the GOTO cancel path.

### 5.3 `encryption_code` Nullable
Files can be registered in the repository without an encryption code. If any service registers unencrypted files containing sensitive data, there is no database-level enforcement to prevent plaintext sensitive file storage.

---

## 6. Security Operations

### 6.1 FortiDB Monitoring
`FortiDBRptRole` is defined in `Security/`, confirming this database is monitored by FortiDB database activity monitoring. This is consistent with the database's role as a shared infrastructure component.

### 6.2 Emergency Access
Multiple `emer_*` accounts are defined (emergency access). Same concern applies as in the warehouse databases.

### 6.3 `vascan` and `ifs_infosec`
Vulnerability scanning and InfoSec monitoring accounts are granted access, consistent with PCI DSS Requirement 11 (security testing).
