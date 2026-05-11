# ci-scripts_INFRA — DevOps & Operations View

## Build & Packaging

This repository is a shared script library, not a built artifact. There is no build pipeline that produces a binary from this repo. However:

- **Node.js dependency**: `package.json` declares one runtime dependency: `properties-reader ^2.2.0`. This npm package must be installed (`npm install`) in the CI runner context before the dormant Node.js scripts can execute. The current locked version targets Node.js `14.5.0-r0` (per README).
- **Shell scripts**: Require `bash`, `curl`, `smbclient`, `net` (Samba), and `find` to be present on the CI runner. These are not declared anywhere; they are implicit Linux environment dependencies.
- **No Makefile, Dockerfile, or build manifest** is present. No containerisation of the scripts is defined in this repository.
- **GitHub Actions CodeQL**: The `.github/workflows/codeql.yml` workflow triggers on manual dispatch and weekly (Friday at 21:46 UTC), running a shared reusable CodeQL analysis workflow from `Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main` using a self-hosted Linux/X64 runner labelled `ubuntu-docker`. This scans JavaScript code (the only language detected by CodeQL in this repository).

## Deployment

The scripts in this repository **are the deployment mechanism** for other services. Deployment of the scripts themselves is done by reference within GitLab CI pipeline definitions (`.gitlab-ci.yml` files in other repositories, specifically the `ci-templates` project). The referencing mechanism is a GitLab `include` or script `curl`/`source` that pulls from a specific Git ref of this repository.

### How external pipelines use this repository (based on README and code)
- The `ci-templates` GitLab project references scripts from this repository. The active reference is to the `master` branch for `deployFromNexus.sh`.
- The dormant properties deployment stage referenced a branch `SQ-4057-deploy-configuration-files` in `ci-templates`.
- No Jenkinsfile or Groovy pipeline definition is present in this repository.

### Deployment Orchestration (what the scripts deploy)
```
Supported application server type:  Apache Tomcat on Windows
Target OS:                           Windows (SMB-accessible, domain-joined: nam.wirecard.sys)
Artifact format deployed:            Java .war
Config format deployed:              .properties, .xml (config files)
Service manager:                     Windows Service Control Manager via Apache Procrun (prunsrv)
Registry key read:                   HKLM\Software\Wow6432Node\Apache Software Foundation\Procrun 2.0\<service>\Parameters\Java\Options
Webapps target path:                 <catalina.home>\<serviceName>\webapps\
Transfer protocol:                   SMB (smbclient), D: administrative share (D$)
```

### Deployment Sequence (Active — `deployFromNexus.sh`)
1. For each `ARTIFACT_PATH` in `$ARTIFACT_MODULES`: read `$ARTIFACT_INFO` properties file, call `download_artifact` to fetch `.war` from Nexus into `$DOWNLOAD_DIR`. Fallback to local artifact copy if no properties file.
2. Verify `$DOWNLOAD_DIR` is non-empty; exit 1 if not.
3. For each `$SERVICE_HOST` in `$SERVICE_HOSTS`:
   - Append `$HOST_SUFFIX` (`.nam.wirecard.sys`) to construct FQDN.
   - Query service status via `net rpc service`.
   - Query `catalina.home` path via `net rpc registry` (Windows Registry).
   - If service is `running`: issue stop command, poll until `stopped` (15-second interval, no timeout limit).
   - Call `transfer_artifact`: delete `temp/` and `work/` directories, delete old `.war` and exploded directory from `webapps/`, copy new `.war` to `webapps/`.
   - Issue start command.

## Configuration Management

### Runtime Configuration (Environment Variables consumed)
All configuration is passed via environment variables injected by the CI system:

| Variable | Used In | Purpose |
|---|---|---|
| `DEPLOY_DEBUG` | All `.sh` | Enables `set -x` bash debug tracing |
| `SERVICE_HOSTS` | `deploy.sh`, `deployFromNexus.sh` | Space-separated list of short hostnames |
| `SERVICE_NAME` | `deploy.sh`, `deployFromNexus.sh` | Windows Tomcat service name |
| `ARTIFACT_PATH` | `deploy.sh` | Local path to built `.war` files (legacy) |
| `ARTIFACT_MODULES` | `deployFromNexus.sh` | Space-separated list of artifact module directories |
| `ARTIFACT_INFO` | `deployFromNexus.sh` | Filename of the properties file inside each module dir |
| `DOWNLOAD_DIR` | `deployFromNexus.sh` | Temporary directory for downloaded artifacts |
| `RELEASES_REPO` | `deployFromNexus.sh`, `nexusFunctions.sh` | Base URL of Nexus releases repository |
| `SNAPSHOTS_REPO` | `deployFromNexus.sh`, `nexusFunctions.sh` | Base URL of Nexus snapshots repository |
| `GL_NAM_USER` | All service/server scripts | AD domain user in `domain/username` format |
| `GL_NAM_PASSWORD` | All service/server scripts | AD domain password |
| `HOST_SUFFIX` | `deploy.sh`, `deployFromNexus.sh` | Hard-coded as `.nam.wirecard.sys` (not a variable) |

### No Configuration Files
There are no YAML, TOML, INI, or `.env` configuration files in this repository. All runtime configuration comes from CI environment variables.

### Mapping Files (Dormant)
For the dormant `deployFilesFromMappings.js` path, additional JSON mapping files are expected in a `mappingsDirectory` passed as a CLI argument:
- `gitlabMetadata.json`: Maps project aliases to GitLab project IDs.
- `environment.<name>.json`: Describes which files go where for a given environment.

## Observability

- **Logging**: All scripts emit coloured ANSI terminal output (`\e[32m\e[1mINFO\e[0m`, `\e[31m\e[1mERROR\e[0m`, `\e[33m\e[1mINFO\e[0m`) to stdout/stderr. Captured by the CI system's job log.
- **Debug mode**: Setting `DEPLOY_DEBUG=true` enables `set -x` in all shell scripts, producing a full command-level trace.
- **No structured logging**: No JSON log format, no log shipping, no centralised log aggregation from within these scripts.
- **No metrics or tracing**: No deployment duration metrics, no APM integration, no Prometheus/Datadog instrumentation.
- **No notifications**: Scripts do not send Slack, email, or webhook notifications upon deployment success or failure.
- **No health checks**: After starting a Tomcat service, the scripts do not verify that the service is actually healthy (no HTTP check, no log scan). Start is fire-and-forget.

## Infrastructure Dependencies

| Dependency | Type | Required By | Notes |
|---|---|---|---|
| Nexus Repository Manager | External service | `deployFromNexus.sh`, `nexusFunctions.sh` | URL from env vars `RELEASES_REPO`/`SNAPSHOTS_REPO` |
| GitLab (gitlab.com) | External SaaS | `deployFilesFromMappings.js`, `gitFunctions.sh` | REST API for config file fetch; project IDs in mapping files |
| SMB network access to target servers | Network | All server/tomcatServices scripts | Requires SMB port (445) open from CI runner to app servers |
| Windows AD Domain (`nam.wirecard.sys`) | Identity | `smbclient`, `net rpc` | `GL_NAM_USER` / `GL_NAM_PASSWORD` must be valid domain credentials |
| `smbclient` binary | CI runner tooling | `serverFunctions.sh`, `deployFromNexus.sh`, `deploy.sh` | Part of Samba client package |
| `net` (Samba) binary | CI runner tooling | `deploy.sh`, `deployFromNexus.sh`, `serviceControlFunctions.sh` | For RPC service control |
| `curl` binary | CI runner tooling | `nexusFunctions.sh`, `gitFunctions.sh`, `deployFromNexus.sh` | HTTP/HTTPS file downloads |
| Node.js v14 | CI runner tooling | `deployFilesFromMappings.js` | Only for dormant path |
| `properties-reader` npm package | npm | `deployFilesFromMappings.js` | Only for dormant path |
| GitHub Actions self-hosted runner | CI infrastructure | `.github/workflows/codeql.yml` | Labels: `self-hosted`, `X64`, `Linux`, `ubuntu-docker` |
| `om-ci-setup` GitHub repo | Shared workflow | `.github/workflows/codeql.yml` | Reusable workflow at `Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main` |

## Operational Risks

1. **Infinite stop-wait loop**: `stop_service_with_wait` and the inline stop loops in `deploy.sh`/`deployFromNexus.sh` have no timeout. If a Tomcat service hangs and never transitions to `stopped`, the CI job will run forever (or until a CI system timeout kills it).
2. **Hard-coded domain suffix**: `HOST_SUFFIX=".nam.wirecard.sys"` is hard-coded in two scripts. A domain rename or DNS change silently breaks all deployments.
3. **No rollback**: If the new `.war` causes an application error, there is no automated mechanism to redeploy the previous version. Manual intervention is required.
4. **No post-deployment health verification**: Service start is issued but correctness is not validated. A Tomcat that starts but immediately crashes will not be detected by these scripts.
5. **SMB dependency**: All file transfers depend on SMB connectivity from the CI runner. Network segmentation changes or firewall rule changes will silently fail deployments.
6. **Credential exposure in logs**: The `serverFunctions.sh` logging statement prints the `password` variable. Any CI log retention policy that stores plain-text job logs is therefore storing credentials.
7. **Samba tooling version sensitivity**: `net rpc registry getvalue` and Windows Registry key path (`HKLM/Software/Wow6432Node/Apache Software Foundation/Procrun 2.0/...`) are sensitive to Samba version compatibility and the specific Procrun installation path on the target server.
8. **Single-threaded sequential deployment**: Hosts are deployed to one at a time in a `for` loop. For large numbers of hosts, this is slow. There is no parallel deployment.

## CI/CD (This IS the CI Infrastructure — Detailed)

### Repository Role in the CI/CD Ecosystem

`ci-scripts_INFRA` is a **shared CI/CD script library** consumed by application pipeline definitions in other GitLab repositories. It is not a pipeline itself but the reusable executable layer that pipeline stages call.

### Active CI/CD Operations Supported

**`deployFromNexus.sh`** — The only actively used script. Called from a GitLab CI pipeline stage to deploy Java `.war` files to on-premises Windows Tomcat servers. It performs:
- Artifact resolution and download from Nexus (release or snapshot)
- Remote service stop via Windows RPC
- File deployment via SMB
- Remote service start via Windows RPC

### Dormant CI/CD Operations (Built, Preserved, Not Active)

**`deployFilesFromMappings.js`** — Node.js orchestration script intended to replace the fragmented shell scripts with a data-driven, mapping-file-based approach. Supports both config file and `.war` deployments driven by JSON descriptors. Not referenced by any active pipeline.

**`git/` module** — Reusable shell functions for fetching files from GitLab via REST API with Bearer token auth. Intended for use in config-file deployment pipelines.

**`nexus/` module** — Standalone wrapper around the Nexus download logic (same function as embedded in `deployFromNexus.sh`). Refactored for reuse.

**`servers/` module** — Standalone wrapper for SMB file transfer. Calls `serverFunctions.sh:transfer_file_to_server`.

**`tomcatServices/` module** — Standalone wrappers for individual Tomcat lifecycle operations (start, stop, bounce). Each script sources `serviceControlFunctions.sh` and delegates to its functions.

**`deploy.sh`** — Predecessor to `deployFromNexus.sh`. Deploys from a locally-built artifact path rather than downloading from Nexus. No longer in active use.

### GitHub Actions Workflow

**`.github/workflows/codeql.yml`** — A security scanning workflow only. It does NOT deploy anything. It:
- Triggers on `workflow_dispatch` (manual) and weekly cron (Fridays 21:46 UTC)
- Delegates entirely to the reusable workflow at `Onbe/om-ci-setup` (inheriting its secrets)
- Runs on a self-hosted runner (`self-hosted`, `X64`, `Linux`, `ubuntu-docker`)
- Scans JavaScript code in this repository for security vulnerabilities

### CI/CD Integration Architecture

```
[GitLab CI — Application Repository Pipeline]
  stage: deploy
    script:
      - source ci-scripts_INFRA/deployFromNexus.sh    (referenced via ci-templates include)
  variables:
      SERVICE_HOSTS, SERVICE_NAME, ARTIFACT_MODULES,
      ARTIFACT_INFO, DOWNLOAD_DIR, RELEASES_REPO,
      SNAPSHOTS_REPO, GL_NAM_USER, GL_NAM_PASSWORD

[GitHub Actions — Security Scanning]
  .github/workflows/codeql.yml
    → Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main
      → CodeQL analysis of JavaScript
```

### Lifecycle State Summary

| Script | CI/CD Role | Status |
|---|---|---|
| `deployFromNexus.sh` | Primary deployment executor for .war releases | Active, tested |
| `deploy.sh` | Legacy deployment executor (local artifact path) | Inactive (deprecated predecessor) |
| `deployFilesFromMappings.js` | Data-driven multi-file deployment orchestrator | Dormant (untested, needs hardening) |
| `deployFileFunctions.js` | Support library for mappings orchestrator | Dormant |
| `nexus/downloadArtifact.sh` | Standalone Nexus download wrapper | Dormant |
| `nexus/nexusFunctions.sh` | Nexus download function library | Dormant |
| `servers/deployFile.sh` | Standalone SMB file deploy wrapper | Dormant |
| `servers/serverFunctions.sh` | SMB transfer function library | Dormant |
| `tomcatServices/bounceTomcatService.sh` | Service restart wrapper | Dormant |
| `tomcatServices/startTomcatService.sh` | Service start wrapper | Dormant |
| `tomcatServices/stopTomcatService.sh` | Service stop wrapper | Dormant |
| `tomcatServices/getRemoteTomcatDirectory.sh` | Registry path query wrapper | Dormant |
| `tomcatServices/serviceControlFunctions.sh` | Service control function library | Dormant |
| `git/fetchFileUsingRestUrl.sh` | GitLab file fetch wrapper | Dormant |
| `git/gitFunctions.sh` | GitLab REST function library | Dormant |
| `experimental/experimentalFunctions.js` | Empty placeholder | Dormant (empty) |
