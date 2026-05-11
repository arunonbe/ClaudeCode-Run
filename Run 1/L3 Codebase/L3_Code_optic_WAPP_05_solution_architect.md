# Solution Architect Report — optic_WAPP

## API Surface

None. OPTIC is a client-side Excel VBA application. It has no HTTP endpoints, no REST API, no SOAP service, no gRPC interface, and no message queue integration. Its sole integration is an outbound SQL connection to the RiskDB SQL Server database, established via ADO/ODBC from VBA code embedded in the `.xlsm` binary file.

## Security Posture

OPTIC has a very poor security posture by modern standards. The following findings are based on observable characteristics of the repository and the Excel VBA application model.

### Critical Finding 1 — VBA Code Is Not Auditable via Source Control

**Severity: Critical**

The `.xlsm` files store VBA code in binary Office Open XML format. Git cannot produce readable diffs for VBA changes. This means:
- Any VBA code change — including the introduction of malicious code — is indistinguishable from a legitimate update in git history.
- Pull request code review, the primary SDLC control for catching security issues, is non-functional for this repository.
- CodeQL, SonarQube, and all standard SAST tools cannot analyze VBA inside `.xlsm` files.

**PCI DSS mapping:** Req 6.2.4 (security testing integrated into SDLC), Req 6.3.1 (security vulnerabilities identified and addressed).

### Critical Finding 2 — Potential Hardcoded Database Credentials in VBA

**Severity: Critical (unconfirmed — requires VBA extraction and review)**

Legacy Excel VBA applications commonly embed database connection strings directly in code, for example:
```vba
conn.Open "Driver={SQL Server};Server=riskdb;Database=RiskDB;Uid=optic_user;Pwd=S3cr3tP@ss;"
```
If OPTIC contains hardcoded credentials:
- All users who can open the file in Excel (Developer → Visual Basic) can read the credentials.
- If the password is in the VBA, it is effectively public to all OPTIC users.
- The database account associated with those credentials has network-level access to RiskDB from any user's workstation.

**PCI DSS mapping:** Req 8.2.1 (unique user IDs), Req 8.6.2 (no hardcoded passwords), Req 8.3 (strong authentication for administrative access).

**Required action:** Extract VBA code using a tool such as `olevba` (part of oletools) or the Excel VBA IDE and audit all `Connection.Open` or `ADODB.Connection` instantiations for embedded credentials.

### High Finding 3 — File Download Mechanism Has No Integrity Verification

**Severity: High**

The `OPTIC Production Copy Link.xlsm` downloads the production `OPTIC - Production.xlsm` from the RiskDB server. This distribution mechanism has no:
- Cryptographic signature verification of the downloaded file
- Hash comparison to detect tampering
- HTTPS/TLS enforcement (if download is via SMB share, it is plaintext over the network)

An attacker with network access or access to the RiskDB server share could replace the production `.xlsm` with a trojaned version containing malicious VBA. The malicious file would be automatically distributed to all OPTIC users on their next launch.

**PCI DSS mapping:** Req 6.3.3 (protection of software components from unauthorized modification), Req 12.3.4 (review of security posture of third-party software).

### High Finding 4 — No Macro Code Signing

**Severity: High**

If the OPTIC `.xlsm` files are not digitally signed with a trusted code-signing certificate, then:
- Enterprise Group Policy may block the macros from running (requiring users to click "Enable Content" — a social engineering prompt)
- There is no mechanism to detect if the VBA code has been tampered with between git commit and server distribution

**Recommended:** Sign the `.xlsm` files with an Onbe-issued code-signing certificate and configure group policy to trust only signed macros from authorized publishers.

### High Finding 5 — SQL Connection Encryption Unknown

**Severity: High**

RiskDB SQL Server connections from VBA/ODBC may not use TLS encryption. SQL Server ODBC connections historically default to unencrypted unless `Encrypt=yes` is specified in the connection string. Unencrypted SQL traffic over a corporate network (or VPN) is susceptible to packet capture. If query results contain financial data, this is a PCI DSS Requirement 4 violation.

### Medium Finding 6 — No Audit Trail for OPTIC User Activity

**Severity: Medium**

OPTIC has no application-layer audit logging. User queries, data viewed, and export activity are not logged by the application. SQL Server's built-in audit logging (if configured on RiskDB) may capture query activity, but this is unverified from the repository. PCI DSS Requirement 10 requires audit logs of access to CHD and systems processing CHD.

## Technical Debt

- Entire application logic is in binary `.xlsm` format — not maintainable using modern development tools or practices.
- No test framework exists for VBA — all testing is manual.
- Distribution mechanism (file copy to server) has no rollback capability beyond restoring the previous `.xlsm` version from git.
- Single-developer knowledge risk — only two named contacts know the VBA codebase.
- The Confluence documentation is on `northlane.atlassian.net` — unclear if Onbe has maintained access to this and whether the documentation is current.

## Recommendations

1. Extract and audit VBA code from both `.xlsm` files using `olevba` or similar tool. Audit specifically for: embedded credentials, SQL query construction (SQL injection risk), and file access paths.
2. If embedded credentials are found, immediately rotate the affected database account password and implement Windows Integrated Security (SSPI) instead.
3. Implement VBA code signing with an Onbe code-signing certificate.
4. Enforce SQL Server connection encryption (`Encrypt=yes;TrustServerCertificate=No`) in the connection string.
5. Enable SQL Server Audit on RiskDB to capture all OPTIC user query activity for PCI DSS Req 10 compliance.
6. Initiate a migration roadmap to retire OPTIC in favor of a modern, auditable, and securely developed replacement.
