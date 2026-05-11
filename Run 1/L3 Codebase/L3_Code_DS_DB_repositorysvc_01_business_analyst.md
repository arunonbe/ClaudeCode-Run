# DS_DB_repositorysvc — Business Analyst Assessment

## 1. Repository Identity

| Attribute | Value |
|---|---|
| Repository name | DS_DB_repositorysvc |
| Project name (sqlproj) | RepositorySvc |
| Solution file | RepositorySvc.sln |
| SQL Server target | (from DSP in sqlproj — requires inspection; project structure is standard SSDT) |
| Build tool | Visual Studio SSDT |

---

## 2. Business Purpose

The Repository Service database is the **metadata and audit database for Onbe's file repository service**. It does not store file content; instead, it stores **metadata about files** that have been submitted to, stored in, and retrieved from Onbe's file repository system. The physical files are stored on disk (the `repo_file_type.relative_path` column indicates filesystem paths), and this database tracks:

- File identity (unique ID, name, version, type)
- File lifecycle events (staged, created, retrieved, deleted)
- File attributes (configurable key-value metadata)
- File associations (relationships between files)
- Encryption type applied to each file
- Submission channel (how the file arrived)
- Audit trail (who accessed which file, from which host, at what time)

This service appears to be a shared infrastructure component consumed by multiple Onbe services — the Security folder shows access grants for approximately 15 named production service accounts covering the full breadth of the platform (APISVC, ECORESVC, CSASVC, ORDERSVC, CZSVC, BMCSVC, etc.).

### Inferred Use Cases
Based on the stored procedure names and table design:
- **Enrollment documents** — files uploaded during cardholder enrollment (identity documents, KYC forms)
- **Report files** — generated reports stored for later retrieval
- **Configuration files** — program-specific configuration artefacts
- **Regulatory documents** — compliance filings, audit evidence
- **Transfer files** — SFTP-delivered or API-submitted files awaiting processing
- **KYC/Identity documents** — given the breadth of service account access (enrollment, API, cardholder services), the repository likely stores identity verification documents that may contain PII

---

## 3. Business Processes Supported

### 3.1 File Staging
`repo_stage_file` — initiates a file record with an action_code of 99 (staged, not yet committed). This is the entry point for the file lifecycle workflow. Files are staged before they are confirmed as successfully stored on disk.

### 3.2 File Creation / Commit
`repo_create_file` — transitions a file from staged (action_code 99) to created (action_code 100). Called after successful disk write. This two-phase commit pattern (stage then create) provides transactional consistency between the metadata database and the filesystem.

### 3.3 File Retrieval
`repo_retrieve_file` — records a retrieval audit event (action_code 120) and returns the file's metadata (archived name, file name, type, version, program ID, encryption code). The caller uses the archived name to locate the file on disk.

### 3.4 File Deletion
`repo_delete_file` — removes a file record from the metadata database (presumably after physical deletion from disk).

### 3.5 File Attribute Management
`repo_begin_set_file_attributes`, `repo_commit_set_file_attributes`, `repo_set_file_attribute`, `repo_get_file_attributes` — manage configurable key-value metadata attributes attached to files. The `repo_attribute_control` table defines allowed attribute types. The `repo_file_attributes_log` table provides an audit trail of attribute changes.

### 3.6 File Association
`repo_create_file_association`, `repo_remove_file_association`, `repo_get_associated_file_definitions` — manage relationships between files (e.g., a report file associated with a source data file).

### 3.7 File Inquiry
`repo_file_inquiry_get_criteria`, `repo_file_inquiry_get_param_list`, `repo_file_inquiry_get_sort_order` — support parameterised file search/inquiry operations.

### 3.8 File Definition Lookup
`repo_get_file_definition`, `repo_get_file_type_path`, `repo_get_latest_file_version`, `repo_get_associated_file_definitions` — metadata lookups for file management operations.

### 3.9 Error Logging
`repo_log_error` — logs errors to `repo_error_log`. Error logging is invoked within stored procedure GOTO-based error handling.

### 3.10 Code Archive
`dbo.CodeArchive` table suggests a historical practice of storing SQL code snippets or version-controlled SQL content within the database itself — a legacy pattern.

### 3.11 DDL Change Logging
`dbo.ddl_log` table logs DDL changes, providing a database-level change audit trail.

---

## 4. Data Stored

| Table | Data Stored | Sensitivity |
|---|---|---|
| `repo_file` | File ID (GUID), file name, version, file type, program ID, archived name, submission channel, encryption code | Low-Medium — program IDs and file names may reveal business-sensitive context |
| `repo_file_audit` | Audit log: file ID, member (GUID), action code, date, host, host relative path | Medium — audit trail of file access |
| `repo_file_attributes` | File ID + attribute type + attribute value (VARCHAR 512) | **MEDIUM-HIGH** — attribute values could contain PII if files carry metadata such as cardholder names or SSNs |
| `repo_file_attributes_log` | Change history of file attributes | Same as above |
| `repo_file_type` | File type lookup with relative path | Low — reveals filesystem path structure |
| `repo_file_encryption_type` | Encryption code + description | Low — reveals encryption scheme names |
| `repo_submission_channel` | Submission channel lookup | Low |
| `repo_file_action` | Action code lookup | Low |
| `repo_file_association` | File-to-file relationship pairs | Low |
| `repo_error_log` | Error messages and context | Low |
| `repo_attribute_control` | Attribute type definitions and validation rules | Low |
| `dbo.CodeArchive` | Historical SQL code | Low-Medium |
| `dbo.ddl_log` | DDL change history | Low |

---

## 5. Regulatory Relevance

### 5.1 PCI DSS
If any files stored in the repository contain payment card data (e.g., card issuance files, dispute files, settlement files), the repository service is a component of the Cardholder Data Environment (CDE). The `repo_file_encryption_type` table confirms that encryption types are tracked — this suggests some files are encrypted before storage, which is a positive control. However, the encryption type is stored as a lookup code (integer), and without seeing the reference data, it is unclear which encryption scheme is applied.

### 5.2 GDPR / CCPA
If enrolled document files (KYC, identity verification) are stored via this service, the repository may contain files with PII. The service does not store PII in the relational tables directly (file content is on disk), but file attribute values in `repo_file_attributes` could contain cardholder identifiers.

### 5.3 Reg E / BSA
Dispute files, NOC (Notification of Change) files, and ACH-related files processed through the platform are likely stored via this repository. These have regulatory retention requirements under Reg E (7 years for error resolution records) and BSA (5 years for records related to suspicious activity).

### 5.4 Audit Trail Completeness
`repo_file_audit` captures every retrieval event with host IP and path. This is a strong audit control supporting PCI DSS Requirement 10 (logging and monitoring). Every access to a stored file creates an audit record identifying the accessing host and the member (user/service) GUID.

---

## 6. Named Service Account Access

The Security folder includes grants for an extensive list of production service accounts:
- `NAM_PPA_PRD_APISVC` — API service
- `NAM_PPA_PRD_ECORESVC` — ECount Core service
- `NAM_PPA_PRD_CSASVC` — Customer service API
- `NAM_PPA_PRD_CSWSVC` — Customer service web
- `NAM_PPA_PRD_CZSVC` — Client zone service
- `NAM_PPA_PRD_ORDERSVC` — Order service
- `NAM_PPA_PRD_BMCSVC` — BMC service (batch/monitoring)
- `NAM_PPA_PRD_SCHSVC` — Scheduler service
- `NAM_PPA_PRD_IVRWSVC` — IVR web service
- `NAM_PPA_PRD_NROLLSVC` — Enrollment service
- `NAM_PPA_PRD_OPSVC` — Operations service
- `NAM_PPA_PRD_ECAPSVC` — ECAP service

This broad service account membership reflects the repository's role as a **shared infrastructure service** accessed by virtually every application layer in the platform.
