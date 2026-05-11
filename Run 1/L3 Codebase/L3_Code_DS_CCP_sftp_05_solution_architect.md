# Solution Architect Report — DS_CCP_sftp

## Technical Debt Inventory

| Item | Severity | Location |
|---|---|---|
| Default `GP_SFTP_HostName` points to QA endpoint | HIGH | `Project.params` line 82 — `sftp-qa.nam.wirecard.com` |
| All Wirecard-branded SFTP hostnames — post-acquisition validity unknown | HIGH | `Project.params` and DS_CCP_db09 configs |
| No CI/CD pipeline | MEDIUM | Entire repo |
| No file count or integrity validation in packages | MEDIUM | `Receive.dtsx`, `Send.dtsx` |
| No host key verification evidence in SSIS SFTP tasks | MEDIUM | `Receive.dtsx`, `Send.dtsx` (binary content not fully parsed) |
| ETL server local paths as defaults (`C:\ETL\`) | MEDIUM | `Project.params` lines 19 and 40 |
| No retry / resume logic in SSIS SFTP transfers | LOW-MEDIUM | SSIS native SFTP limitation |
| No formal version numbering for the SSIS project | LOW | `SFTP.dtproj` — `VersionMajor=0, VersionMinor=0, VersionBuild=0` |
| SSISDB `wdnam-ccp-etl` folder name is Wirecard-branded | LOW | Cosmetic/naming debt |

## Security Vulnerabilities Found

### 1. Default QA SFTP Hostname (HIGH — Data Exposure Risk)
`Project.params`, line 82: `GP_SFTP_HostName` has a default value of `sftp-qa.nam.wirecard.com`. If this project is deployed to a new SSISDB instance without configuring the production environment variable override, file operations will target the QA SFTP server. For outbound operations (Send.dtsx), this means production data files could be delivered to a QA environment — a data breach scenario. For inbound operations (Receive.dtsx), production processing would attempt to pick up QA test files.

**Remediation**: Change the default value to an empty string or a clearly invalid sentinel value (e.g., `REQUIRES-CONFIGURATION`) to force explicit configuration before use.

### 2. SSH Key File on Server Filesystem (MEDIUM — Secret Management)
`GP_SFTP_SSHKey` parameter stores a path to an SSH private key file on the ETL server. This key is not managed by any secrets vault. If the ETL server is compromised or a DBA has direct file system access, the private key can be extracted and used to authenticate as the service account to the SFTP server.

**Remediation**: Use Azure Key Vault (or equivalent) to store SSH private key material directly, eliminating the need for a key file on the server filesystem. Alternatively, use certificates managed by a hardware security module (HSM) for SFTP key authentication in PCI CDE environments.

### 3. Password Authentication Support (MEDIUM — PCI DSS Req 8)
The project supports password-based SFTP authentication (`GP_SFTP_Password` sensitive parameter). Password-based authentication is weaker than SSH key authentication. PCI DSS Requirement 8.3.9 requires that passwords for non-consumer user accounts are changed at least every 90 days. Managing SFTP password rotation in SSISDB environment variables requires a manual update process each rotation cycle.

**Remediation**: Enforce SSH key-only authentication. Remove password parameter from the project or implement a process to detect and alert when password rotation is due.

### 4. No SFTP Host Key Pinning Evidence (MEDIUM — PCI DSS Req 4.2 / MITM Risk)
SSIS SFTP tasks (depending on the SFTP component library used — native WinSCP-based or third-party) may not verify the remote server's SSH host key fingerprint by default. Without host key verification, a man-in-the-middle (MITM) attack could present a different server's certificate and intercept file transfers. For inbound FIS files containing PANs, this represents a data interception risk.

**Remediation**: Verify that the SFTP task component enforces host key checking. Configure known host key fingerprints for all production SFTP endpoints in the SSIS connection manager or configuration.

### 5. No Input Validation on File Paths (LOW — Path Traversal)
The `SourceFolder`, `ArchivedFolder`, and remote path parameters accept arbitrary string values. If these values were sourced from a user-controlled input, path traversal attacks could be possible. However, given these are SSISDB environment variables managed by administrators, the practical risk is low.

## Package / Component Inventory

This project contains two executable SSIS packages:

| Package | SSIS DTSID | Purpose | Parameters Used |
|---|---|---|---|
| `Send.dtsx` | `{643ED6F6-1166-493C-AEC2-647FE43E7E15}` | Upload files from local path to remote SFTP | `archivepath`, `filepattern`, `hostname`, `port`, `credentials`, `remotepath` (per SFTP.dtproj metadata) |
| `Receive.dtsx` | Separate ID | Download files from remote SFTP to local path | `SourceFolder`, `ArchivedFolder`, `GP_SFTP_*` parameters |

The project also contains a `PackagePart` (`.dtsxp`) file in DS_CCP_wired-caching (`PackagePart1.dtsxp`) — package parts are reusable control flow components that can be shared across packages. The exact content of `Receive.dtsx` (64,994 bytes) and `Send.dtsx` (15,498 bytes) is in SSIS XML format; binary-level analysis would be needed to enumerate all connection managers and data flow components.

## Code Quality Issues

1. **Zero version numbers**: `VersionMajor=0, VersionMinor=0, VersionBuild=0` in project metadata indicates no formal version management has been applied. The project was created and never version-bumped.
2. **No package annotations or documentation** visible in the project metadata — the package description fields are empty.
3. **Single creator identity** (`WIRECARD\van.nguyen2`) across all project assets — no evidence of code review or multiple contributors.
4. The `SFTP.database` file (1,685 bytes) defines the SSISDB database connection but is a minimal configuration file.

## Recommended Remediation Priority

| Priority | Action |
|---|---|
| P1 — Immediate | Change default `GP_SFTP_HostName` from `sftp-qa.nam.wirecard.com` to an empty string or explicit sentinel value |
| P1 — Immediate | Validate all Wirecard SFTP endpoints — confirm which are still operational under Onbe, decommission or remap those that are not |
| P1 — Immediate | Verify SSH host key checking is enabled in SSIS SFTP task component |
| P2 — Short-term | Migrate SSH key files from ETL server filesystem to Azure Key Vault or equivalent secrets management |
| P2 — Short-term | Implement file arrival count validation in Receive.dtsx (alert on zero-file transfers for expected-file schedules) |
| P2 — Short-term | Implement file checksum / size validation for PAN-bearing file types |
| P3 — Medium-term | Add CI/CD pipeline for SSIS project build and `.ispac` deployment |
| P3 — Medium-term | Apply version numbering (increment VersionMajor/Minor/Build on each release) |
| P3 — Medium-term | Evaluate migration of SFTP capability to Azure Data Factory with Key Vault credential integration |
