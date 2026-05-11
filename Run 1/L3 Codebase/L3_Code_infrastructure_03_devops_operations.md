# DevOps & Operations — infrastructure

## CI/CD Pipeline

The `infrastructure` repository contains **no CI/CD pipeline configuration**. There are no GitHub Actions workflow files, no GitLab CI/CD `.gitlab-ci.yml`, no Jenkins pipelines, and no Azure DevOps pipeline YAML files anywhere in the repository tree. This is a manual-deployment repository.

### Absence of Automation Findings

| Expected Artifact | Present? | Impact |
|------------------|----------|--------|
| CI workflow (lint, validate) | No | No automated correctness check on configuration changes |
| CD pipeline (deploy to server) | No | All deployments are manual, error-prone, undocumented |
| Secret scanning job | No | Committed private keys are not detected in CI |
| Infrastructure test/diff stage | No | No drift detection between repo state and server state |
| Pull request gating | No | Changes can be merged without review enforcement at pipeline level |

The lack of any pipeline means that configuration changes — including changes to private key files and IIS worker configurations — can be committed and merged with no automated review, no validation, and no audit trail beyond Git commit history.

## Deployment Model

Configurations in this repository map directly to filesystem paths on Azure Windows Server VMs. The folder structure under `webserver-iis-workers/` mirrors the production server layout:

```
webserver-iis-workers/
  PROD/
    p-az-web02/
      D/c-base/opt/iis-proxy/
        clientzone.mypaymentadmin.com/conf/
          isapi_redirect.properties
          workers.properties
          uriworkermap.properties
```

This means deployment consists of manually copying files from the repository to the corresponding paths on each server. There is no configuration management agent (Ansible, Chef, Puppet, DSC) enforcing state, and no deployment record indicating which server version matches which Git commit.

### Server Inventory Requiring Manual Deployment

| Environment | Servers | Sites per Server |
|-------------|---------|-----------------|
| PROD | p-az-web02, p-az-web08, p-az-web09, p-az-web10, p-az-web11, p-az-web13, p-az-web14 | 5–12 site configurations |
| UAT | u-az-web01, u-az-web02 | Subset of PROD sites |
| QA | q-az-web01, q-az-web02 | Subset of PROD sites |

Seven production web servers multiplied by up to 12 site configurations each yields approximately 84 individual configuration triplets (`isapi_redirect.properties`, `workers.properties`, `uriworkermap.properties`) that must be manually synchronized. This is a high-risk operational model; a missed file or a copy to the wrong server creates a service routing failure or security misconfiguration.

## Environment Separation

Environment separation is implemented **by folder name only**:

```
webserver-iis-workers/
  PROD/
  UAT/
  QA/   (inferred; q-az-web servers present)
```

There are no environment-specific variable substitution mechanisms, no deployment profiles, and no template rendering. The actual server hostnames differ between environments, but the AJP cluster backend hostnames (`p-az-app01/02/03.nam.wirecard.sys`) appear in PROD files only; QA and UAT files reference their respective backend servers.

**Risk**: Because there is no automated promotion pipeline, a practitioner deploying to PROD could accidentally copy from the UAT folder or vice versa. There is no safeguard.

## Secrets Management

### Current State — Critical Deficiency

All cryptographic key material is stored directly in the repository with no secrets management integration:

| Material | Location in Repo | Secrets Store | Rotation Mechanism |
|----------|-----------------|---------------|--------------------|
| Harland QA SFTP private key (.ppk, OpenSSH) | `platform-certificates-keys/harland/QA/` | None | None observed |
| Harland QA passphrase | `platform-certificates-keys/harland/QA/key.txt` | None | None observed |
| Titan PROD SFTP private key (.ppk, OpenSSH) | `platform-certificates-keys/titan/PROD/` | None | None observed |
| Titan PROD passphrase | `platform-certificates-keys/titan/PROD/key.txt` | None | None observed |
| Titan QA SFTP private key | `platform-certificates-keys/titan/QA/` | None | None observed |
| Titan QA passphrase | `platform-certificates-keys/titan/QA/key.txt` | None | None observed |

The passphrase `n0ty0u` is identical across all three environments (Harland QA, Titan PROD, Titan QA). This means that compromise of any one key file plus any one `key.txt` unlocks all protected private keys. Under PCI DSS v4.0.1 Requirement 12.3.3, cryptographic key custodians must be identified and documented, and under Requirement 3.5.1 keys must be protected from disclosure. Neither requirement is satisfied.

**Git history is permanent**: Even if the keys are removed from the current branch, the private key bytes and passphrase remain accessible in the Git object store to anyone who clones or has previously cloned the repository. Key rotation (generating new key pairs) is the only effective remediation after a repository exposure event.

### Recommended Secrets Management Target State

1. **Azure Key Vault** (already available in Onbe's Azure tenant per other repos): Store SFTP private key bytes as Key Vault Secrets; retrieve at deployment time via Managed Identity.
2. **SSH Agent / SSH Proxy**: Use an SSH jump host with certificate-based authentication rather than passphrase-protected key files distributed via repository.
3. **Secret Scanning**: Enable GitHub Advanced Security secret scanning to prevent future key commits. Configure push protection.

## Key Rotation Status

No evidence exists in the repository of any key rotation cadence. The `key.txt` passphrase `n0ty0u` appears to have been set at initial configuration and never changed. PCI DSS Requirement 3.7.1 requires that cryptographic key management procedures include key replacement at the end of the defined cryptoperiod. No cryptoperiod is documented.

## Operational Runbooks

No operational runbooks, deployment guides, or change management procedures are present in the repository. The only documentation is the implicit structure of folder names. This creates key-person dependency risk — only team members who have personally performed prior deployments understand the correct procedure.

## Change Management Risk

Because deployments are entirely manual and there is no pipeline:

1. There is no automated rollback capability. Reverting a bad IIS configuration requires a practitioner to manually redeploy the previous version of each affected file.
2. There is no deployment lock or mutex preventing two practitioners from deploying conflicting configurations simultaneously.
3. There is no post-deployment smoke test or health check automation verifying that the new configuration served traffic correctly after deployment.

## Recommendations

| Priority | Action | Effort |
|----------|--------|--------|
| Critical | Rotate all SFTP key pairs (Harland QA, Titan PROD, Titan QA) immediately — git history exposure is permanent | 1–2 days |
| Critical | Remove all private key files and `key.txt` passphrases from the repository; add `.gitignore` entries | 0.5 day |
| Critical | Enable GitHub secret scanning with push protection to prevent future key commits | 0.5 day |
| High | Migrate SFTP key storage to Azure Key Vault with Managed Identity retrieval | 2–3 days |
| High | Implement a configuration deployment pipeline (GitHub Actions + Azure VM Run Command or Ansible) | 3–5 days |
| High | Add distinct passphrases per environment and per key pair | 0.5 day |
| Medium | Introduce Ansible or Azure DSC for idempotent configuration state enforcement | 5–10 days |
| Medium | Document deployment runbooks for PROD, UAT, and QA environments | 2 days |
| Low | Evaluate decommission of legacy wirecard.com domain configurations | 1 day (assessment) |
