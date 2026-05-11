# DS_ETL_great-plains — Solution Architect Report

## 1. Technical Architecture

| Attribute | Value |
|-----------|-------|
| Technology | SSIS Package Deployment Model — SQL Server 2008 R2 |
| Project format | Legacy `.dtproj` (pre-Project Deployment Model) |
| Package format version | FormatVersion 3 (SSIS 2008 R2) |
| Package count | 34 `.dtsx` files |
| Deployment mode | Package Deployment (MSDB or file system; no SSISDB catalog) |
| Configuration method | `.dtsConfig` files (not present in repo) or package-embedded configs |
| Source control integration | Disabled (`<Enabled>false</Enabled>` in project state) |
| No `.ispac` output | Package Deployment Model produces no deployment archive |

---

## 2. API Surface

Batch ETL pipeline — no HTTP API. External interfaces:

1. **SQL Server OLE DB connections** (multiple, embedded in `.dtsx` packages): Reads from `ecountcore`, `ordersvc`, `jobsvc`, prepaid warehouse databases; writes to Microsoft Dynamics GP SQL Server.
2. **Flat file input**: FDR and Visa VSS settlement files — file system reads.
3. **Flat file output**: NACHA ACH files for CitiDirect bank, GP import files.
4. **SQL Server Agent**: Package execution scheduler.
5. **`dtexec.exe` / MSDB**: Package runtime.

---

## 3. Security Posture

### 3.1 Authentication and Credential Storage

- Package Deployment Model packages can use one of three protection levels:
  - `DontSaveSensitive` — credentials removed; must be supplied at runtime
  - `EncryptSensitiveWithUserKey` — sensitive data encrypted with current Windows user key
  - `EncryptAllWithUserKey` — all package data encrypted with user key
  - `EncryptSensitiveWithPassword` — sensitive data encrypted with a password
  - `EncryptAllWithPassword` — all data encrypted with a password

- Without inspecting the `.dtsx` XML content (binary-encoded within the project), the protection level cannot be determined from the project artefacts in this repo.
- **Risk**: `EncryptSensitiveWithUserKey` is common in legacy SSIS projects and ties the package to a specific Windows service account — packages become unusable if the service account is changed.

### 3.2 PCI DSS Scope

- `SSIS_VSS.dtsx` processes **Visa Settlement Services** data — Visa transaction-level settlement records. This places the SSIS server and any storage it writes to in **PCI DSS scope**.
- `SSIS_FDR.dtsx` processes **First Data Resources** settlement data — PCI DSS scope.
- Running these packages on a SQL Server 2008 R2 SSIS infrastructure (EOL) is a likely **PCI DSS compensating control** that requires QSA documentation and may not be acceptable in the next PCI DSS assessment.

### 3.3 ACH Data Security

- `CitiDirectACH.dtsx` and `CACitidirectACH.dtsx` generate NACHA ACH files containing bank routing and account numbers.
- These files must be protected at rest and in transit. No evidence of file encryption or access control beyond OS-level file permissions in the project artefacts.
- NACHA Operating Rules require controls over ACH file security; unprotected files are a NACHA compliance risk.

---

## 4. Technical Debt

| Issue | Severity | Detail |
|-------|---------|--------|
| SSIS 2008 R2 — EOL July 2019 | CRITICAL | 6+ years without security patches; running PCI-scope data on unsupported platform |
| Three `SOJobsvc` versions | CRITICAL | Active SOX change management risk; canonical version unknown |
| `CDW_P-DB06_DB06_P-DB08_DB08_0.dtsx` | HIGH | One-time migration package in active project; should be removed or tagged as inactive |
| Source control integration disabled | HIGH | No SSIS-level source control hooks; package changes may bypass git |
| No `.dtsConfig` in repository | HIGH | Configuration not version-controlled; environment-specific settings exist only in deployed binaries or undocumented config files |
| Package protection level unknown | HIGH | Cannot assess credential exposure without inspecting package XML |
| ACH files unencrypted | HIGH | NACHA files likely written as plaintext to file system |
| No CI/CD | HIGH | Manual deployment; no validation pipeline |
| 34 packages in flat directory | MEDIUM | No sub-folder organisation; difficult to navigate and maintain |
| Binary project state encoded (base64) | MEDIUM | Project metadata is base64-encoded; source control history for project-level changes is not human-readable |

---

## 5. Gen-3 Migration Assessment

**Migration complexity**: VERY HIGH — but the path is clear if the GP ERP replacement is also planned.

### Per-package migration approach

| Package Category | Gen-3 Replacement Pattern |
|---|---|
| NACHA ACH generation (`CitiDirectACH`, `CACitidirectACH`, `FeeInvoicingACH`) | Spring Batch + NACHA library (e.g., `nacha4j` or custom formatter) + SFTP delivery |
| GL export to GP (`SSIS_GLBatch*`, `SSIS_GLExport*`, `SSIS_GLTx*`) | If GP is replaced: REST API to successor ERP. If GP remains: custom GP eConnect API or GP Web Services integration |
| Visa VSS (`SSIS_VSS`) | Spring Batch + Visa VSS file parser + SQL Server JDBC |
| FDR reconciliation (`SSIS_FDR`) | Spring Batch + FDR file parser + SQL Server JDBC |
| Sales Order invoicing (`SOFee*`, `SO*`) | Spring Boot REST service calling GP eConnect or successor ERP API |
| Client refunds (`ClientRefund`, `RSCheck`) | Spring Batch item writer with GP API or successor ERP REST endpoint |
| Cube reconciliation (`SSIS_CubeReconcile*`) | Spring Batch + SQL aggregation queries + reconciliation report service |

### Migration prerequisites
1. **Determine canonical `SOJobsvc` version** — audit GP production to identify which package version is deployed; retire the others.
2. **Remove `CDW_P-DB06_DB06_P-DB08_DB08_0.dtsx`** — confirm migration is complete; remove from project.
3. **Externalise all connection strings** — audit each `.dtsx` for embedded credentials before migration.
4. **PCI DSS scoping** — formal QSA scoping of `SSIS_VSS` and `SSIS_FDR` data flows in the Gen-3 architecture.
5. **GP ERP roadmap decision** — if GP is being replaced (e.g., with SAP, NetSuite, or another ERP), the GL/invoicing migration must be co-ordinated with that programme.

---

## 6. Code-Level Risks

| Risk | File | Detail |
|------|------|--------|
| Canonical version unknown | `SOJobsvc.dtsx` / `_Orig` / `_recompile` | Three versions of same package; incorrect production deployment = SOX-reportable financial misstatement risk |
| Live migration package | `CDW_P-DB06_DB06_P-DB08_DB08_0.dtsx` | Production server names in package name; accidental execution re-runs a historical migration |
| PCI data on EOL infrastructure | `SSIS_VSS.dtsx`, `SSIS_FDR.dtsx` | Visa and FDR settlement data on SSIS 2008 R2 (EOL) |
| Package protection level unknown | All packages | Cannot determine if credentials are exposed without reading `.dtsx` XML |
| No execution isolation | Flat package directory | No mechanism to prevent deploying `CDW_*` or `SOJobsvc_Orig*` packages accidentally |
