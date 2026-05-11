# DS_DB_repositorysvc — Enterprise Architect Assessment

## 1. Platform Role

The Repository Service database is a **shared infrastructure service** that decouples file storage from file metadata management. It serves as the metadata registry for the Onbe file repository service (`repository-service_SVC` and `repository_LIB` repositories visible in the broader repo listing).

In the platform architecture, it sits between the application services layer and the filesystem/object storage layer:

```
Application Layer             Repository Service           Storage Layer
─────────────────             ──────────────────           ─────────────
APISVC                  -->   DS_DB_repositorysvc    -->   Filesystem
ECORESVC                -->   (metadata only)              (physical files)
CSASVC                  -->
ORDERSVC                -->
ENROLLMENTSVC           -->
IVR                     -->
12+ other services      -->
```

---

## 2. Dependencies

### 2.1 Services Consuming This Database
Based on the Security folder, the following production service accounts have access, implying these services depend on this database:
- `NAM_PPA_PRD_APISVC` — main API platform
- `NAM_PPA_PRD_ECORESVC` — ECount Core (core transaction engine)
- `NAM_PPA_PRD_CSASVC` — Customer Service API
- `NAM_PPA_PRD_CSWSVC` — Customer Service Web
- `NAM_PPA_PRD_CZSVC` — Client Zone
- `NAM_PPA_PRD_ORDERSVC` — Order management
- `NAM_PPA_PRD_BMCSVC` — BMC monitoring/batch
- `NAM_PPA_PRD_SCHSVC` — Scheduler
- `NAM_PPA_PRD_IVRWSVC` — IVR web service
- `NAM_PPA_PRD_NROLLSVC` — Enrollment
- `NAM_PPA_PRD_OPSVC` — Operations
- `NAM_PPA_PRD_ECAPSVC` — ECAP

A database unavailability event would impact all 12+ dependent services.

### 2.2 Filesystem Dependency
The physical files are stored at filesystem paths defined in `repo_file_type.relative_path`. The database and the filesystem must be co-located or accessible from the same infrastructure. This creates a tight operational coupling between the database server and the file storage infrastructure.

---

## 3. Enterprise Architecture Assessment

### 3.1 Generation Assessment
The Repository Service is a **first-generation internal file management service** built using SQL Server SSDT with legacy T-SQL patterns (GOTO error handling, double-quoted string literals, unset `@@TRANCOUNT`). The file creation date of the `repo_create_file` procedure change log entry (June 25, 2003 — documented in the procedure comment) confirms this service is over 20 years old.

### 3.2 Modern Architecture Equivalent
In a modern cloud-native architecture, this service would be implemented using:
- Azure Blob Storage or AWS S3 (object storage)
- Azure SQL Database or Cosmos DB (metadata registry)
- Service Bus or Event Grid (lifecycle event notifications)
- Azure Key Vault (encryption key management rather than nullable encryption code lookup)

The current design couples metadata management (SQL Server) with filesystem storage in a way that creates migration complexity and operational fragility.

### 3.3 Encryption Architecture Gap
The `repo_file_encryption_type` table stores encryption scheme descriptions but the **actual encryption/decryption logic resides outside this database** (in the consuming application services). The database only stores a code indicating which encryption was used. This means:
- If an application service changes its encryption library, the `repo_file_encryption_type` reference data must be updated separately
- There is no cryptographic key management in this database — keys are managed by the calling services
- The nullable `encryption_code` in `repo_file` creates a gap where unencrypted files can be registered

### 3.4 Shared Infrastructure Risk
Because 12+ services depend on this single database:
- A performance degradation in `repo_file_audit` inserts (which happen on every operation) could degrade all dependent services
- A schema change requires coordinated testing across all dependent services
- The database is a **single point of failure** for all file operations across the platform

---

## 4. Migration Complexity

### 4.1 Object Storage Migration
Migrating to a cloud object storage service (Azure Blob Storage) would require:
1. Migrating physical files to blob containers
2. Updating `repo_file_type.relative_path` to blob container paths (or replacing with blob URLs)
3. Updating the `archived_name` column to blob object keys
4. Maintaining backward compatibility for the 12 dependent services during migration

Estimated complexity: **Medium** (3–6 months with careful service-by-service migration)

### 4.2 Dependency on Service Integration Pattern
The repository service is accessed via stored procedures, not a REST API. The `repository-service_SVC` and `repository_LIB` repos (visible in the broader listing) likely wrap these database calls. Migration of the database layer does not require changing the API surface, but it requires changes to the library/service layer.

---

## 5. Technical Debt

| Item | Location | Risk |
|---|---|---|
| GOTO-based error handling | All stored procedures | Medium — brittle error recovery |
| `@trancount` never assigned | `repo_retrieve_file.sql` line 31 | High — latent transaction bug |
| `encryption_code` nullable | `repo_file.sql` line 12 | Medium — unencrypted file registration possible |
| `dbo.CodeArchive` live table | `dbo/Tables/CodeArchive.sql` | Low — dead data accumulation |
| 20+ year old design | All procedures | High — migration urgency |
| No audit table archival | `repo_file_audit` | Medium — unbounded growth |
| Filesystem path hardcoded in DB | `repo_file_type` | Medium — operational brittleness |
| No CI/CD | Repo root | High |
