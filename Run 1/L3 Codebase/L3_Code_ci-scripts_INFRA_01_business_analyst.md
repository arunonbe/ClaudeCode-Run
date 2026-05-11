# ci-scripts_INFRA — Business Analyst View

## Business Purpose

`ci-scripts_INFRA` is a shared CI/CD utility library whose sole business purpose is to automate the deployment of application artifacts (Java `.war` files) and configuration/properties files to on-premises Windows application servers running Apache Tomcat. It acts as the deployment execution layer within the organisation's Continuous Delivery pipeline, bridging artifact repositories (Nexus) and source-controlled configuration (GitLab) with live server environments.

The repository originated during the Wirecard-to-Northlane-to-Onbe transition and represents the final iteration of legacy deployment automation for the Gen-1/Gen-2 on-premises platform. As of the last committed README (July 2021), only one script (`deployFromNexus.sh`) is in active use; the remainder is preserved dormant code retained to prevent branch-divergence loss.

## Business Capabilities

| Capability | Status | Delivery Mechanism |
|---|---|---|
| Download release `.war` artifacts from Nexus | Active | `deployFromNexus.sh` / `nexusFunctions.sh` |
| Download SNAPSHOT `.war` artifacts from Nexus | Active (in `deployFromNexus.sh`) | Maven metadata XML parsing via `curl` |
| Stop remote Windows Tomcat services before deployment | Active (via active script) | `samba`/`net rpc service` over SMB |
| Transfer `.war` to remote server webapps directory | Active | `smbclient` SMB file transfer |
| Start remote Windows Tomcat services after deployment | Active | `samba`/`net rpc service` over SMB |
| Deploy configuration/properties files from GitLab to servers | Dormant | `deployFilesFromMappings.js` + GitLab REST API |
| Deploy `.war` files driven by JSON mapping files | Dormant | `deployFilesFromMappings.js` |
| Fetch files from GitLab via REST API | Dormant | `git/gitFunctions.sh`, `git/fetchFileUsingRestUrl.sh` |
| Remote Tomcat path discovery via Windows Registry | Both | `getRemoteTomcatDirectory.sh` / `serviceControlFunctions.sh` |
| Service bounce (stop + start) | Dormant | `bounceTomcatService.sh` |

## Business Entities

- **Artifact**: A compiled Java `.war` file identified by Maven GAV coordinates (`groupId`, `artifactId`, `version`, `packaging`). Can be a RELEASE or SNAPSHOT build.
- **Service**: A named Windows service wrapping an Apache Tomcat instance on a target server (e.g., `TomcatServiceName`).
- **Host/Server**: A Windows application server in the `nam.wirecard.sys` domain, addressed by short hostname with domain suffix appended at runtime.
- **Component**: A logical application component described in JSON mapping files; maps to one or more servers and one or more Tomcat services.
- **Environment**: A named deployment target (dev, test, prod, etc.) represented by a JSON mapping file (`environment.<name>.json`).
- **Mapping File**: A JSON file describing which files go to which servers for a given component and environment.
- **Configuration File**: A `.properties` or `.xml` file (e.g., `log4j.xml`, `ecountcore.properties`) sourced from a GitLab repository and deployed to a server path.
- **Nexus Repository**: The Maven artifact repository hosting both RELEASE and SNAPSHOT builds (referenced via `$RELEASES_REPO` and `$SNAPSHOTS_REPO` environment variables).

## Business Rules & Validations

1. **Artifact must exist before deployment proceeds.** Both `deploy.sh` and `deployFromNexus.sh` terminate with an error if the download directory or artifact path is empty after the fetch attempt.
2. **Tomcat service must be gracefully stopped before file transfer.** The stop-then-deploy-then-start pattern is enforced by all active and dormant deployment routines. Deployment is skipped for a host if the stop operation fails.
3. **Service status polling enforces stop completion.** A `while` loop polls `get_status` every 15 seconds until the service reports `stopped` before proceeding.
4. **SNAPSHOT versions require a metadata lookup.** The script fetches `maven-metadata.xml` from Nexus to resolve the concrete timestamped build identifier before constructing the download URL.
5. **Backward compatibility is maintained** via a `get_local_artifact` fallback in `deployFromNexus.sh` when no `artifactInfo` file is found; this copies `.war` files from a local path rather than downloading from Nexus.
6. **Deployment can be skipped per file** via a `skip: "true"` flag in mapping JSON entries (dormant path).
7. **Domain/user credentials are parsed from a slash-delimited format** (`domain/user`), implying a specific credential formatting convention (e.g., `NAM/cicd.nonprod`).
8. **Host suffix `.nam.wirecard.sys` is hard-coded** in both `deploy.sh` and `deployFromNexus.sh`, tying the scripts to the legacy Wirecard/Northlane network domain.

## Business Flows

### Active Flow: WAR Deployment from Nexus

```
CI Pipeline Trigger
  → Set environment variables (SERVICE_HOSTS, ARTIFACT_MODULES, SERVICE_NAME, etc.)
  → deployFromNexus.sh
      → For each ARTIFACT_MODULE:
          Read artifactInfo file (group, artifactId, version, packaging)
          → download_artifact() → Nexus RELEASES_REPO or SNAPSHOTS_REPO → curl download to DOWNLOAD_DIR
      → Verify DOWNLOAD_DIR is non-empty
      → For each SERVICE_HOST:
          get_status() → net rpc service (SMB) → running/stopped/ERROR
          get_path()   → net rpc registry (Windows Registry query) → catalina.home path
          If running: control_service(stop) → poll until stopped
          transfer_artifact() → smbclient → delete old webapps, copy new .war
          control_service(start)
```

### Dormant Flow: Configuration and WAR Deployment from Mappings

```
CI Pipeline Trigger
  → node deployFilesFromMappings.js [environment] [componentName] [mappingsDir] [downloadDir] [deployProjectDir] [nam_user] [nam_password] [git_token]
      → Load gitlabMetadata.json, environment.<env>.json
      → Filter component by name
      → organizeComponentByServer() → group deployments by target server
      → For each server:
          stopServicesForServer() → tomcatServices/stopTomcatService.sh (per service)
          For each componentDeployment:
              if fileType == "config":
                  buildGitRestUrlForFile() → GitLab REST API → fetch file content → write to downloadDir
                  deployFile.sh → smbclient → transfer to server path
              if fileType == "war":
                  getRemoteTomcatDirectory.sh → Windows Registry → catalina.home
                  nexus/downloadArtifact.sh → Nexus download
                  servers/deployFile.sh → smbclient transfer
          startServicesForServer() → tomcatServices/startTomcatService.sh
```

## Compliance & Regulatory Concerns

- **Credential exposure in logs**: `serverFunctions.sh` logs the password variable in clear text via `echo "transfer_file_to_server, ... password($password)"`. This would expose domain credentials (e.g., AD service account passwords) in CI pipeline logs. This is a material security concern in a PCI DSS environment.
- **Credential passed as command-line arguments**: `deployFilesFromMappings.js` receives `nam_user` and `nam_password` as positional command-line arguments (visible in process tables). Similarly, GitLab tokens are passed on the command line.
- **Hard-coded credential present**: A bearer token value is present in `deployFilesFromMappings.js` within the HTTPS request options. See Security Posture section. Location noted; value not reproduced here per policy.
- **Domain**: Operations target the `nam.wirecard.sys` internal network domain, which is the legacy Wirecard/Northlane/Onbe on-premises AD domain. Any audit trail for deployments is solely the CI system logs; there is no deployment audit log independent of the pipeline.
- **No approval gate**: The scripts contain no built-in change-approval workflow, separation-of-duties enforcement, or deployment authorisation check. Any access control must be enforced upstream by the CI system (GitLab).
- **PCI DSS relevance**: If any of the Tomcat services being deployed handle cardholder data (card processing, transaction routing), then the deployment pipeline itself is within or adjacent to the Cardholder Data Environment (CDE) and would fall under PCI DSS requirements for change management (Requirement 6.5) and access control (Requirement 7/8).

## Business Risks

1. **Single active script with no formal QA**: Only `deployFromNexus.sh` is actively used and tested. All other capabilities are unfinished and untested.
2. **Hard-coded legacy domain name**: `HOST_SUFFIX=".nam.wirecard.sys"` hard-coded in two scripts. Any DNS or domain name change breaks deployments without code change.
3. **No deployment rollback mechanism**: Scripts deploy forward only; there is no automated rollback if the post-deployment service fails to start.
4. **No deployment record**: There is no audit log, database entry, or notification generated by these scripts upon completion.
5. **Credential handling risk**: Passwords logged in plain text and passed as CLI arguments (see Compliance section).
6. **Infinite loop risk**: `stop_service_with_wait` polls indefinitely if a service never reaches `stopped` state. No timeout or maximum retry limit is implemented.
7. **Dormant code maintenance burden**: The majority of the repository is untested dormant code. If reactivated without hardening, it presents operational and security risk.
