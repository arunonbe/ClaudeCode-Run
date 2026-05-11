# DevOps / Operations Report — windows-scripts

## Build System

None. These are runtime operational scripts (VBScript, Perl) that require no compilation or build process. BCP format files are static configuration files for SQL Server Bulk Copy Program.

## CI/CD Pipeline

None. There is no CI/CD pipeline, no `.github/workflows`, and no Jenkinsfile. Scripts are managed as plain files in Git and deployed manually to production servers.

## Deployment Model

**Manual file copy to production servers.** Scripts are deployed by copying from the Git repository to the following production server paths:
- `bat03`: `D:\c-base\bin\`, `D:\c-base\runtime\`
- `p-az-app12`: `D:\c-base\runtime\`, `D:\c-base\tools\`

The directory structure in the repository mirrors the production server path structure (`PROD\bat03\D\c-base\...`), which suggests the repository is used as a file-synchronization source for production server content.

## Runtime Environment

- **Windows Server** (bat03 and p-az-app12 are Windows batch processing servers).
- **VBScript**: Executed by `wscript.exe` or `cscript.exe` on Windows. VBScript is deprecated by Microsoft as of Windows 11 24H2 and will be removed in future Windows versions.
- **Perl**: Windows Perl runtime (ActivePerl or Strawberry Perl). No version pinning is present.
- **jIntegra J2COM bridge**: COM-to-Java bridge that allows VBScript to call Java objects. This is the `ECountService.Connection` and `ECountService.Connection_j2com` COM server.
- **SQL Server BCP**: Microsoft SQL Server Bulk Copy Program for bulk data import/export.

## Secrets Management

**No formal secrets management.** Key findings:
- The scripts themselves do not contain hardcoded database passwords or network credentials (the J2COM bridge handles connectivity to eCount Core transparently).
- SSN values are passed as command-line arguments: `updateSSN "{memberID}", "SSN"` — plaintext SSN visible in process lists and shell history.
- The Perl scripts do not show embedded database credentials in the reviewed sections, but the FDR report parsers likely connect to SQL Server; their connection strings are not visible without reading the full parser files.
- No secrets vault, environment variable injection, or encrypted credential store is referenced.

## Observability

- `wscript.echo` calls in VBScripts provide console output that can be captured in job scheduler logs.
- SFTP job failure email notifications are sent via `SFTPjobfail_email.vbs`.
- ACH and check control total scripts output totals to console, which are compared to expected values by the calling job scheduler.
- No structured logging, no centralized log aggregation, no metrics.

## EOL Runtimes / CVEs

| Component | Status | Risk |
|-----------|--------|------|
| VBScript (Windows) | Deprecated — scheduled for removal from Windows | All VBScript-based jobs will cease to function as Windows is upgraded |
| jIntegra J2COM | Abandoned commercial product (~2010) | No security patches; COM interop vulnerability surface |
| Perl (unversioned) | Runtime version unknown | If ActivePerl 5.x, some versions have known CVEs |

## Operational Risks

1. **VBScript deprecation**: Microsoft has announced VBScript removal from Windows. All VBScript-based batch jobs must be migrated before the hosting OS is upgraded.
2. **No job orchestration visibility**: Scripts are called by an external job scheduler (ABAT job scheduler, referenced via `ABAT_JOBNAME` environment variable). There is no visibility into job success/failure rates, latency, or error trends.
3. **No automated deployment validation**: Scripts are deployed manually with no smoke test or deployment verification. A syntax error in a production script can cause silent job failures.
4. **Backup files checked into Git**: Multiple `*_bkp07222021.vbs` backup files are present. These are dead code that should be removed to avoid confusion.
5. **Script version fragmentation**: Multiple variants of the same script exist for different environments (e.g., `ach-orig-control-totals-MB.vbs`, `ach-orig-control-totals-Sunrise.vbs`, `ach-orig-control-totals - Copy.vbs`). There is no abstraction layer; logic is duplicated across variants.
