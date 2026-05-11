# ci-scripts_INFRA — Solution Architect View

## Technical Architecture

The repository is a flat collection of loosely coupled shell scripts and Node.js modules. There is no formal framework, service mesh, or build system. The architecture pattern is a **shell function library with a thin Node.js orchestration layer** (dormant).

### Directory Structure and Module Map

```
ci-scripts_INFRA/
├── deploy.sh                          # Legacy WAR deploy (local artifact, active but deprecated)
├── deployFromNexus.sh                 # Active WAR deploy from Nexus (all logic inline)
├── deployFileFunctions.js             # Node.js helpers: shell exec, service start/stop wrappers
├── deployFilesFromMappings.js         # Node.js orchestrator: config + WAR deploy from JSON mappings
├── package.json                       # npm: properties-reader ^2.2.0 only
├── experimental/
│   └── experimentalFunctions.js       # Empty placeholder module
├── git/
│   ├── gitFunctions.sh                # Library: fetch_git_file_using_rest_url()
│   └── fetchFileUsingRestUrl.sh       # Entry point: calls gitFunctions.sh
├── nexus/
│   ├── nexusFunctions.sh              # Library: download_artifact()
│   └── downloadArtifact.sh            # Entry point: calls nexusFunctions.sh
├── servers/
│   ├── serverFunctions.sh             # Library: transfer_file_to_server()
│   └── deployFile.sh                  # Entry point: calls serverFunctions.sh
└── tomcatServices/
    ├── serviceControlFunctions.sh     # Library: get_status(), control_service(), get_path(),
    │                                  #          stop_service_with_wait(), start_service_without_wait()
    ├── bounceTomcatService.sh         # Entry point: stop + start
    ├── startTomcatService.sh          # Entry point: start_service_without_wait()
    ├── stopTomcatService.sh           # Entry point: stop_service_with_wait()
    └── getRemoteTomcatDirectory.sh    # Entry point: get_path() (Windows Registry query)
```

### Key Function Inventory

| Function | File | Purpose |
|---|---|---|
| `download_artifact` | `nexusFunctions.sh`, `deployFromNexus.sh` | Resolve SNAPSHOT/RELEASE URL, curl download from Nexus |
| `get_status` | `serviceControlFunctions.sh`, `deployFromNexus.sh`, `deploy.sh` | Query Windows service state via `net rpc service status` |
| `control_service` | `serviceControlFunctions.sh`, `deployFromNexus.sh`, `deploy.sh` | Start/stop Windows service via `net rpc service` |
| `get_path` | `serviceControlFunctions.sh`, `deployFromNexus.sh`, `deploy.sh`, `getRemoteTomcatDirectory.sh` | Read `catalina.home` from Windows Registry via `net rpc registry getvalue` |
| `transfer_artifact` | `deployFromNexus.sh`, `deploy.sh` | SMB: delete old webapps content, copy new `.war` via smbclient |
| `transfer_file_to_server` | `serverFunctions.sh` | SMB: copy single file to a specific server path |
| `stop_service_with_wait` | `serviceControlFunctions.sh` | Stop + poll until service reaches `stopped` state |
| `start_service_without_wait` | `serviceControlFunctions.sh` | Issue start command without polling for confirmation |
| `fetch_git_file_using_rest_url` | `gitFunctions.sh` | curl GET with Bearer auth to GitLab REST URL |
| `get_local_artifact` | `deployFromNexus.sh` | Fallback: find and copy `.war` from local path |
| `organizeComponentByServer` | `deployFilesFromMappings.js` | Group deployment spec by target server (Map) |
| `buildGitRestUrlForFile` | `deployFilesFromMappings.js` | Construct GitLab REST URL for a file by alias lookup |
| `deployWar` | `deployFilesFromMappings.js` | Read GAV from properties, download from Nexus, deploy via SMB |
| `deployConfigFile` | `deployFilesFromMappings.js` | Fetch from GitLab REST, write local, deploy via SMB (async/Promise) |
| `deployFilesByServer` | `deployFilesFromMappings.js` | Async orchestrator: stop services, deploy files, start services |
| `executeShellCommand` | `deployFileFunctions.js` | Node.js `execSync` wrapper for shelling out |
| `stopServicesForServer` | `deployFileFunctions.js` | Iterate services, call `stopTomcatService.sh` for each |
| `startServicesForServer` | `deployFileFunctions.js` | Iterate services, call `startTomcatService.sh` for each |

### Code Duplication

`get_status`, `control_service`, and `get_path` are duplicated verbatim across `serviceControlFunctions.sh`, `deployFromNexus.sh`, and `deploy.sh`. The refactored versions in `serviceControlFunctions.sh` exist but the active scripts embed their own copies. This is a maintenance liability — a bug fix in one location will not propagate to others.

Similarly, the `download_artifact` function body is duplicated verbatim between `deployFromNexus.sh` and `nexusFunctions.sh`.

## API Surface

This repository exposes no network API. Its "API" is its shell script entry points, invoked by CI pipelines:

### Shell Entry Points (CLI interface)

| Script | Arguments (positional) | Environment Variables Required |
|---|---|---|
| `deployFromNexus.sh` | None (all via env vars) | `SERVICE_HOSTS`, `SERVICE_NAME`, `ARTIFACT_MODULES`, `ARTIFACT_INFO`, `DOWNLOAD_DIR`, `RELEASES_REPO`, `SNAPSHOTS_REPO`, `GL_NAM_USER`, `GL_NAM_PASSWORD`, optionally `DEPLOY_DEBUG` |
| `deploy.sh` | None (all via env vars) | `SERVICE_HOSTS`, `SERVICE_NAME`, `ARTIFACT_PATH`, `GL_NAM_USER`, `GL_NAM_PASSWORD`, optionally `DEPLOY_DEBUG` |
| `bounceTomcatService.sh` | `$1`=service, `$2`=host | `GL_NAM_USER`, `GL_NAM_PASSWORD` |
| `startTomcatService.sh` | `$1`=service, `$2`=host | `GL_NAM_USER`, `GL_NAM_PASSWORD` |
| `stopTomcatService.sh` | `$1`=service, `$2`=host | `GL_NAM_USER`, `GL_NAM_PASSWORD` |
| `getRemoteTomcatDirectory.sh` | `$1`=service, `$2`=host, `$3`=user, `$4`=password | None (args explicit but also falls back to env vars) |
| `servers/deployFile.sh` | `$1`=host, `$2`=full_user, `$3`=password, `$4`=local_filename, `$5`=server_full_filename | `GL_NAM_USER`, `GL_NAM_PASSWORD` (used instead of $2/$3 in function call — bug noted below) |
| `nexus/downloadArtifact.sh` | `$1`=group, `$2`=artifact, `$3`=version, `$4`=packaging, `$5`=outputPath, `$6`=outputName | `RELEASES_REPO`, `SNAPSHOTS_REPO` |
| `git/fetchFileUsingRestUrl.sh` | `$1`=git_file_url, `$2`=bearer_token | None |

### Node.js Entry Point (dormant)

```
node deployFilesFromMappings.js [environment] [componentName] [mappingsDirectory] [downloadDirectory] [deployProjectDirectory] [nam_user] [nam_password] [git_token]
```
8 positional arguments required. Passing `nam_password` and `git_token` as CLI args is a security concern (visible in process table).

## Security Posture

### Critical Issues

1. **Hard-coded credential in source code (`deployFilesFromMappings.js`, line 187)**
   A literal credential value appears as the `Authorization: Bearer` header value in the HTTPS options object for the GitLab REST API call. This token is committed to the `master` branch and is visible in git history. The value is not reproduced here. This must be treated as a compromised credential and rotated immediately.

2. **Plain-text password logging (`serverFunctions.sh`, line 13-14)**
   The function `transfer_file_to_server` logs: `echo "transfer_file_to_server, ... password($password)"`. The variable `$password` receives the value of `$GL_NAM_PASSWORD` (the AD domain service account password). This is written to the CI pipeline log in plain text.

3. **Credentials passed as CLI arguments (`deployFilesFromMappings.js`)**
   `nam_password` (arg 7) and `git_token` (arg 8) are passed on the command line. On Linux systems, command-line arguments are visible in `/proc/<pid>/cmdline` to any process running as the same user or as root on the CI runner.

### Elevated Concerns

4. **No TLS enforcement on Nexus downloads**: The `curl` commands use URLs constructed from `$RELEASES_REPO`/`$SNAPSHOTS_REPO` environment variables with no `--ssl-reqd` or equivalent flag. If the environment variables contain `http://` URLs, artifact downloads are unencrypted and unverified.

5. **No certificate pinning or validation flags**: No `curl` calls include `--cacert`, `--cert`, or `--ssl-reqd`. Default system CA bundle is used; any misconfigured `--insecure` flag added by a caller would silently disable TLS verification.

6. **No artifact integrity verification**: Downloaded `.war` files are deployed without checksum verification. A compromised Nexus or a man-in-the-middle on an HTTP download could inject a malicious artifact.

7. **SMB without enforced signing**: `smbclient` invocations do not pass `--signing=required`. SMB signing is enforced at the server/domain level; if domain policy does not require it, transfers are vulnerable to relay attacks.

8. **`eval` usage with user-controlled data (`serviceControlFunctions.sh`, `deploy.sh`, `deployFromNexus.sh`)**: `get_status` and `control_service` use `eval $rpc_list` and `eval $rpc_command` where the command strings are assembled from variables including `$password`. If `$GL_NAM_PASSWORD` contains shell metacharacters, this could result in unintended command execution. This is a shell injection vector in principle, though in practice the password is sourced from a CI secret rather than user input.

9. **`set -x` debug mode expands all variables including secrets**: When `DEPLOY_DEBUG=true`, `set -x` is enabled and every command — including those embedding credentials — is printed to stderr before execution. This amplifies the credential logging risk.

### Mitigating Factors

- Scripts are intended to run only within a controlled GitLab CI environment where pipeline logs are access-controlled.
- `GL_NAM_USER` and `GL_NAM_PASSWORD` are injected as masked CI/CD variables (GitLab has a masking feature for variable values in logs), though `serverFunctions.sh` may still expose them if masking does not cover all log patterns.

## Technical Debt

| Debt Item | Severity | Location | Description |
|---|---|---|---|
| Hard-coded credential | Critical | `deployFilesFromMappings.js:187` | Bearer token committed to master |
| Password in log output | High | `serverFunctions.sh:13-14` | `$password` printed to stdout |
| Function duplication | Medium | `deployFromNexus.sh`, `deploy.sh`, `serviceControlFunctions.sh`, `nexusFunctions.sh` | `get_status`, `control_service`, `get_path`, `download_artifact` duplicated verbatim |
| Hard-coded domain suffix | Medium | `deploy.sh:8`, `deployFromNexus.sh:7` | `HOST_SUFFIX=".nam.wirecard.sys"` — not parameterised |
| Bug: `deployFile.sh` ignores passed args | Medium | `servers/deployFile.sh:17` | Calls `transfer_file_to_server $host $GL_NAM_USER $GL_NAM_PASSWORD $local_filename $server_full_filename` — uses env vars `$GL_NAM_USER`/`$GL_NAM_PASSWORD` instead of the passed `$full_user`/`$password` positional arguments ($2, $3). The positional args are accepted but never used in the function call. |
| Infinite loop (no timeout) | Medium | `deployFromNexus.sh:237-243`, `deploy.sh:127-132`, `serviceControlFunctions.sh:67-73` | Stop-wait polls indefinitely; no max iteration guard |
| `eval` with credential variables | Medium | `serviceControlFunctions.sh:9-10`, `deployFromNexus.sh:71`, `deploy.sh:19` | Shell injection surface; `eval` of dynamically assembled commands containing password |
| No artifact integrity check | Medium | `nexusFunctions.sh`, `deployFromNexus.sh` | `.war` deployed without hash verification |
| Node.js 14 (EOL) | Medium | `package.json`, README | Node.js 14 reached EOL April 2023 |
| `byServers` variable name bug | Low | `deployFilesFromMappings.js:220` | `deployFilesByServer` iterates `byServers.entries()` but the outer call passes `byServers` — variable is set as a `const` in the outer scope, not passed into the function; works by closure but is not declared as a parameter, making the function signature misleading |
| No error handling in `deployFileFunctions.js` | Low | `deployFileFunctions.js:10` | `execSync` callback is passed but `execSync` does not use a callback; errors will throw synchronously and are not caught |
| No formal tests | High | Entire repo | README states no formal QA; no test framework, no test files |
| `package.json` name is `"data"` | Low | `package.json:2` | Generic, meaningless package name |
| Empty `experimental` module | Low | `experimental/experimentalFunctions.js` | Committed empty placeholder |

## Gen-3 Migration Requirements

The scripts in this repository are not portable to a Gen-3 cloud-native/container-based platform. The following migrations or replacements are required:

1. **Replace SMB-based file transfer**: No equivalent of `smbclient` applies to Kubernetes, ECS, or cloud VM deployments. Artifact deployment must use container image registry pushes (Docker), Helm chart releases, or cloud-native deployment APIs.

2. **Replace Windows RPC service control**: `net rpc service` and `net rpc registry` are Windows-only constructs. Gen-3 service lifecycle is managed by Kubernetes (Pod restarts), ECS task definitions, or a process supervisor in the container image.

3. **Replace Nexus download scripts**: If Nexus is retained as an artifact store in Gen-3, the download logic can be partially reused, but should be replaced with a dedicated CI/CD step (e.g., Maven deploy plugin, Nexus IQ integration, or direct container image pull from a registry).

4. **Credential management overhaul**: Replace all environment-variable-based credential injection with a secrets management solution (HashiCorp Vault, AWS Secrets Manager, Azure Key Vault). Remove all hard-coded tokens from source code.

5. **Deployment audit trail**: Implement a deployment record mechanism — either via the CI system (pipeline metadata, GitLab Environments) or a deployment tracking service — to satisfy PCI DSS change management requirements.

6. **Health check integration**: Post-deployment health verification must be added (HTTP readiness/liveness probe, smoke test) before any Gen-3 deployment pattern is considered production-ready.

7. **Rollback mechanism**: Gen-3 deployments require a defined rollback strategy (Helm rollback, blue/green switch, previous task definition reactivation).

## Code-Level Risks

### Bug: `servers/deployFile.sh` ignores passed credentials
```bash
# deployFile.sh accepts:
host=$1        full_user=$2    password=$3    local_filename=$4    server_full_filename=$5

# But calls:
transfer_file_to_server $host $GL_NAM_USER $GL_NAM_PASSWORD $local_filename $server_full_filename
#                              ^^^^^^^^^^^^ ^^^^^^^^^^^^^^^^
#                              Uses env vars instead of $full_user ($2) and $password ($3)
```
The positional arguments `$2` and `$3` are accepted and named but never used. The function always reads from the environment. This means the script ignores credentials passed from `deployFilesFromMappings.js` (which passes `server.namUser` and `server.namPassword`) and uses the global env vars instead. In practice, if both are set to the same values this has no effect, but it is a latent correctness bug.

### Bug: `execSync` callback pattern is incorrect
```javascript
// deployFileFunctions.js:10
return execSync(shellCommand, (error, stdout, stderr) => { ... });
```
`execSync` does not accept a callback. The second argument to `execSync` is an options object, not a callback. The callback is silently ignored. Errors from the child process will throw a `ChildProcess` error synchronously, which is not caught by the module. Any caller (`deployFilesFromMappings.js`) that calls `executeShellCommand` has no error handling for command failures.

### Risk: Async/sync mixing in `deployFilesFromMappings.js`
`deployWar` is synchronous (uses `executeShellCommand` / `execSync`). `deployConfigFile` is asynchronous (returns a Promise, uses `https.request`). `deployFilesByServer` uses `await deployConfigFile(...)` but calls `deployWar(...)` without `await` (WAR deployments are synchronous, so `await` is not needed, but the inconsistency could confuse maintainers and lead to future bugs if the pattern is changed).

### Risk: No guard against empty `SERVICE_HOSTS`
If `$SERVICE_HOSTS` is an empty string, the `for host in $(echo $SERVICE_HOSTS)` loop produces no iterations and the script exits with a success exit code (0) having deployed nothing. There is no validation that at least one host was provided.

### Risk: `maven-metadata.xml` parsing fragility
```bash
build=`curl -s $repopath/$version/maven-metadata.xml | grep '<value>' | head -1 | sed "s/.*<value>\([^<]*\)<\/value>.*/\1/"`
```
SNAPSHOT metadata resolution uses a brittle grep/sed pipeline on XML. If the XML format changes (namespace, attribute order, whitespace) or if `curl` returns an error page in XML/HTML format, the `build` variable will silently receive garbage and construct an invalid download URL.
