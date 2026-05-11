# ci-scripts_INFRA — Enterprise Architect View

## Platform Generation (Gen-1/Gen-2/Gen-3)

**This repository is firmly Gen-1/Gen-2 infrastructure.** The evidence is conclusive:

- Targets **Windows-hosted Apache Tomcat** services managed via Apache Procrun (a Gen-1/Gen-2 Windows-service wrapper for Java applications), not containerised or cloud-native deployments.
- Uses **SMB (samba/smbclient)** to transfer files to servers over the `nam.wirecard.sys` domain — an on-premises Windows Active Directory topology.
- Reads Tomcat paths from the **Windows Registry** (`HKLM\Software\Wow6432Node\Apache Software Foundation\Procrun 2.0\...`), which is characteristic of Apache Tomcat installed as a Windows NT service.
- The README explicitly states: *"New Onbe platform is to be started in the near future"* and *"Work is wrapping up on our last iteration of CI/CD"* — written in July 2021. The "new Onbe platform" is the Gen-3 initiative. This repository represents the deployment toolchain for the platform it is replacing.
- The domain suffix `nam.wirecard.sys` references the Wirecard / Northlane legacy network, predating the Onbe rebrand.

**Gen-3 relevance**: None of the deployment mechanisms (SMB, Windows service RPC, Procrun registry) apply to a cloud-native or container-based platform. The entire script library would be retired, not migrated, in a Gen-3 transition.

## Business Domain

- **Domain**: Internal Platform Engineering / CI/CD Infrastructure
- **Sub-domain**: Application Deployment Automation
- **Business context**: Payments processing platform operations (Onbe delivers B2C disbursements, prepaid card, ACH, and multi-rail payouts; the Tomcat services being deployed are the backend application tier of that payment platform)

## Role in Platform

`ci-scripts_INFRA` occupies the **Continuous Delivery execution layer** in the Gen-1/Gen-2 platform architecture:

```
[Source Code] → [GitLab CI Build Pipeline] → [Nexus Artifact Repository]
                                                         |
                                           ci-scripts_INFRA (deployFromNexus.sh)
                                                         |
                                    [Windows Tomcat App Servers (nam.wirecard.sys)]
                                    [Payment Processing Backend Services]
```

It is a **cross-cutting infrastructure capability** — not owned by any single application domain team. It is referenced by multiple application repositories through the `ci-templates` GitLab project abstraction layer.

Within the CI/CD chain:
- **Upstream**: GitLab CI build stages (Maven build, artifact publish to Nexus)
- **Peer**: `ci-templates` GitLab project (pipeline template definitions that reference these scripts)
- **Downstream**: Running application services on Windows Tomcat servers

## Dependencies

### Inbound Dependencies (Who depends on ci-scripts_INFRA)
- `ci-templates` GitLab project — pipeline templates for application repositories include/call these scripts
- All application GitLab repositories whose `.gitlab-ci.yml` includes the relevant `ci-templates` pipeline that invokes `deployFromNexus.sh`

### Outbound Dependencies (What ci-scripts_INFRA depends on)
- **Nexus**: Maven artifact repository (RELEASES_REPO, SNAPSHOTS_REPO) — must be reachable from CI runner
- **GitLab REST API** (dormant path): `gitlab.com` HTTPS endpoint for config file retrieval
- **Windows Active Directory** (`nam.wirecard.sys`): Domain authentication for SMB and RPC calls
- **Samba tooling on CI runner**: `smbclient`, `net` (rpc)
- **curl**: HTTP client for Nexus downloads and GitLab API calls
- **om-ci-setup GitHub repository**: Provides the shared CodeQL reusable workflow
- **Self-hosted GitHub Actions runner**: For CodeQL scanning (labels: `self-hosted`, `X64`, `Linux`, `ubuntu-docker`)

### Key Versioning Constraint
- Node.js `14.5.0-r0` — explicitly noted in README for the dormant Node.js scripts. This is an old Alpine-flavoured Node.js version (the `-r0` suffix is Alpine package versioning) and would need updating before any re-activation.

## Integration Patterns

| Pattern | Implementation | Location |
|---|---|---|
| **Script library / function sourcing** | Shell scripts source function files using `source $(dirname $0)/...Functions.sh` | All shell scripts |
| **Environment variable injection** | CI system injects all runtime config as env vars; no config files | All scripts |
| **Pull-based artifact deployment** | Scripts pull artifacts from Nexus rather than artifacts being pushed to servers | `deployFromNexus.sh`, `nexusFunctions.sh` |
| **SMB file push** | Files are pushed to servers via SMB administrative shares (`//$host/d$`) | `serverFunctions.sh`, `deployFromNexus.sh` |
| **RPC-based service control** | Windows services are started/stopped via Samba `net rpc service` | `serviceControlFunctions.sh`, deploy scripts |
| **REST API pull (dormant)** | Config files are fetched from GitLab via HTTPS REST before being pushed to servers | `gitFunctions.sh`, `deployFilesFromMappings.js` |
| **Data-driven deployment (dormant)** | JSON mapping files describe deployments declaratively; Node.js orchestrates execution | `deployFilesFromMappings.js` |
| **Reusable workflow delegation** | GitHub Actions CodeQL uses `uses:` to delegate to a shared workflow in another repo | `.github/workflows/codeql.yml` |
| **Stop-deploy-start lifecycle** | All deployment operations stop services, transfer files, then start services | All deploy scripts |

## Strategic Status

**Strategic status: End-of-Life / Maintenance-only**

- The README (July 2021) explicitly frames the repository as being preserved to avoid code loss as the team transitions to a new platform.
- Only one of fourteen scripts/modules is actively used (`deployFromNexus.sh`).
- The dormant majority was never formally tested and is explicitly flagged as needing *"fine polishing, more error handling, and hardening/formal testing"* before use.
- The target infrastructure (Windows Tomcat on `nam.wirecard.sys`) represents the Gen-1/Gen-2 on-premises platform that is being replaced.
- No evidence of active investment or enhancement since the README was written.
- A hard-coded credential exists in dormant committed code, indicating no security review was performed before the code was checked into master.

**Recommendation from architecture standpoint**: This repository should be formally archived once the last active pipeline using `deployFromNexus.sh` is decommissioned or migrated to Gen-3. The dormant code should not be reactivated without a full security and quality review.

## Migration Blockers

The following items must be resolved before any migration or re-activation effort:

1. **Hard-coded credential in `deployFilesFromMappings.js`**: A bearer token is committed to source code in `master`. This must be rotated, removed from history (git history rewrite or repo migration), and replaced with a secrets management solution before the dormant code can be re-activated or migrated.

2. **Windows/Samba-only toolchain**: The entire deployment mechanism depends on Windows SMB and Windows RPC protocols. This is incompatible with cloud-native targets (Kubernetes, ECS, etc.). For Gen-3, a replacement mechanism (Helm, ArgoCD, Spinnaker, AWS CodeDeploy, etc.) is required.

3. **Hard-coded legacy domain**: `HOST_SUFFIX=".nam.wirecard.sys"` would need to be replaced or parameterised for any non-legacy environment.

4. **No approval/gate mechanism**: Gen-3 deployment pipelines at Onbe's compliance posture (PCI DSS Level 1) will require change management gates. These scripts have none.

5. **Credential management model**: Credentials injected as plain-text CI environment variables is insufficient for a PCI DSS compliant deployment pipeline. Vault integration (HashiCorp Vault, AWS Secrets Manager) would be required.

6. **Node.js 14 EOL**: Node.js 14 reached end-of-life in April 2023. Any re-activation of the Node.js scripts requires a Node.js upgrade and dependency re-validation.

7. **No idempotency guarantee**: Scripts are not designed to be safely re-run (idempotent). Partial failures leave servers in intermediate states with no recovery logic.
