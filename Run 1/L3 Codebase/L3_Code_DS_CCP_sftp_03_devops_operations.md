# DevOps & Operations Report — DS_CCP_sftp

## Build System

DS_CCP_sftp uses **Visual Studio Integration Services** tooling. The project file `SFTP.dtproj` is an SSIS project file (Product Version 14.0.3002.113, corresponding to SSDT 17.x for Visual Studio 2017). The solution file is `SFTP.sln`.

The project uses the **Project Deployment Model** (`<DeploymentModel>Project</DeploymentModel>` in `SFTP.dtproj`), which is the modern SSIS deployment model enabling:
- Environment-specific parameter overrides via SSISDB environments
- Centralized package execution monitoring via SSISDB
- SSIS catalog (SSISDB) management

Protection level: `DontSaveSensitive` — sensitive values are not stored in package files.

## CI/CD Pipeline

**No CI/CD pipeline configuration exists in this repository.** No `.gitlab-ci.yml`, Jenkinsfile, or Azure DevOps YAML files are present. SSIS projects can be built and deployed via MSBuild (`/t:build`) and `ISDeploymentWizard.exe` or SqlPackage, but no automation is implemented here.

## Deployment Mechanism

**Manual SSIS project deployment** via Visual Studio SSIS Deployment Wizard or command-line `ISDeploymentWizard.exe`:

1. Build project in Visual Studio → produces `.ispac` file
2. Run deployment wizard → connect to SSISDB on p-db09 → deploy to folder `\SSISDB\wdnam-ccp-etl\SFTP\`
3. Configure SSISDB environment variables for credentials and paths
4. Test package execution via SSISDB catalog or SSMS

No deployment scripts are committed to the repo. All post-deployment environment configuration must be done manually via SSMS or T-SQL (`catalog.create_environment_variable`, `catalog.set_object_parameter_value`).

## Environments

The `SFTP.dtproj` and `SFTP.database` files do not contain environment-specific configurations. Environment management is done entirely via SSISDB:
- Each SSISDB environment (Development, Test, Production) has its own set of parameter values
- The SFTP packages are parameterised to accept hostname, credentials, and paths at runtime
- Default `GP_SFTP_HostName = 'sftp-qa.nam.wirecard.com'` indicates the **default points to QA** — this must be overridden in production SSISDB environment

## Operations — Package Execution

Packages are executed by SQL Agent jobs defined in DS_CCP_db09:
- As sub-packages called from parent SSIS packages (e.g., `Receive_SFTP.dtsx` in DS_CCP_wired-caching calls this project's Receive package)
- As standalone SQL Agent jobs when SFTP transfer is the primary operation

Execution is monitored via SSISDB execution reports in SSMS:
- `[SSISDB].[catalog].[executions]`
- `[SSISDB].[catalog].[operation_messages]`
- `[SSISDB].[catalog].[execution_data_taps]`

## Monitoring and Alerting

- **NotifyEmailAddress parameter**: The project includes a notification email address parameter for operation-level alerts. The email is sent via Database Mail using the `MailServerAccount` parameter value.
- **SQL Agent job-level alerting**: When SFTP packages are executed via SQL Agent, job failure notifications flow through the standard DBA operator email configured in DS_CCP_db09.
- **SSISDB logging**: All package executions are logged to SSISDB with full message detail when logging level is set to `1` (Basic) as specified in job commands.

### Gaps
- **No file count validation**: The SFTP packages transfer files but do not validate that the expected number of files was received. A day with zero files would succeed silently.
- **No SFTP server reachability monitoring**: No proactive health check of SFTP endpoint availability before scheduled transfers.
- **No file integrity check**: No checksum/hash validation of transferred files to detect corruption or truncation.
- **No retry on partial failure**: If an SFTP transfer fails mid-file, there is no partial-transfer resume capability in SSIS native SFTP tasks.

## Backup and Recovery

No backup-relevant content in this repository. The `.dtsx` package files are version-controlled in Git and represent the "backup" of the SSIS logic. The SSISDB catalog on p-db09 should be backed up as part of the system database backup (`SSISDB` database). Recovery of the SFTP capability requires:
1. Restoring/redeploying the `.ispac` to SSISDB
2. Reconfiguring environment variables (credentials)
3. Verifying SSH key files are present on the ETL server

## Operational Risks

1. **Default QA hostname in project parameters**: `GP_SFTP_HostName` defaults to `sftp-qa.nam.wirecard.com`. If the SSISDB environment override is ever dropped or misconfigured, production packages will silently transfer files to the QA endpoint. This would cause a data exposure incident (sending production data to a QA system).

2. **SSH key file on ETL server filesystem**: The `GP_SFTP_SSHKey` parameter value (empty by default, but set to a file path in production) points to an SSH private key on the ETL server's filesystem. If the ETL server is compromised, the SSH private key is at risk. The key file is not protected by a centralised secrets management system.

3. **DontSaveSensitive — deployment gap**: `ProtectionLevel=DontSaveSensitive` means sensitive values are stripped from the `.dtsx` files. If packages are deployed without subsequently configuring SSISDB environment variable values for sensitive parameters, SFTP authentication will fail. The absence of default values means failures are immediate and visible — but the configuration step is easy to miss in a fresh deployment.

4. **Legacy Wirecard SFTP endpoints**: The project references Wirecard SFTP hostnames throughout (defaults and DS_CCP_db09 configuration). These need validation to confirm Onbe has maintained or replaced these endpoints post-acquisition.

5. **No SFTP host key verification evidence**: SSIS SFTP tasks using third-party components (e.g., CozyRoc, WinSCP) may or may not verify the remote server's host key. If host key verification is disabled, the transfer is vulnerable to man-in-the-middle attacks. This cannot be confirmed without reading the full binary DTSX content.

## File System Requirements

The packages expect the following local directories to exist on the ETL server:
- `C:\ETL\In\` — inbound file landing zone
- `C:\ETL\Archived\` — archive for processed inbound files
- `C:\ETL\Out\` — outbound file staging (referenced in DS_CCP_wired-output)

The drive `C:\` default suggests development environment. Production typically uses dedicated data drives (`F:\ETL\` or `R:\ETL\` as seen in DS_CCP_db09 scripts). These paths must be overridden in SSISDB production environment.
