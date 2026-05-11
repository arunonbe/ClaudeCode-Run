# om-east-deploy — Business Analyst View

## Executive Summary

`om-east-deploy` is the central deployment orchestrator for all East-region Onboarding Manager (OM) services. It owns the declarative mapping of every deployable OM service to its target servers, artifact coordinates, and environment-specific configuration. Its business purpose is to provide a single, auditable, human-readable source of truth for what version of which service runs in which environment, replacing ad-hoc per-service deployment scripts with a governed, repeatable process.

## Business Context

The Onboarding Manager platform processes payment operations (card issuance, ACH, check disbursements) for Onbe's East-region B2C clients. In a PCI DSS Level 1 environment, every deployment must be traceable, approvals must be captured, and production changes must be gated by authorized personnel. `om-east-deploy` fulfills these requirements by wrapping the deployment lifecycle inside GitHub Actions workflows with environment-gated approvals.

### Business Stakeholders

- **East Deploy Team** — acts as required reviewer for every environment deployment (named in the `uat`, `qa`, and `prod` GitHub Environments as required reviewers per `README.md` lines 74-78).
- **Service Owners** — register new services by creating a `services/<name>.yml` config file, making the service onboarding process self-service while keeping operational ownership with the deploy team.
- **Audit and Compliance** — every triggered deployment produces a workflow run with an immutable Deploy Summary (`.github/workflows/deploy.yml` lines 185-198) listing service, version, environment, target servers, and job status, satisfying change-management evidence requirements.

## Business Capabilities Delivered

### 1. Centralised Service Registry
The `services/` directory is the human-readable inventory of all deployable OM services. Each YAML file (`services/<name>.yml`) declares Maven coordinates, per-environment server lists, Windows service names, and filesystem paths. This registry replaces tribal knowledge and makes the deployment topology inspectable by any stakeholder.

### 2. Controlled Environment Promotion
The workflow (`deploy.yml`) accepts three inputs — `service`, `version`, and `environment`. The environment choices are currently `uat` only (line 20), reflecting Phase 1 scope. Future phases (noted in `README.md` lines 95-97) will add `qa` and `prod` with corresponding approval gates, providing a formal promotion path from development through production.

### 3. Break-Glass Continuity
The `README.md` (lines 87-89) explicitly documents a break-glass path: if the orchestrator is unavailable, services can still be deployed via the deprecated `cicd-deployment.yml` workflow inside each service repo. This continuity provision mitigates single-point-of-failure risk during a migration window.

## Service Configuration Schema — Business Impact

The `services/test-east-deploy.yml` canonical example shows:

- **artifact**: Maven group, artifact ID, and packaging type — links every deployment to an auditable artifact version in GitHub Packages.
- **environments.uat.servers**: `u-app01.nam.wirecard.sys`, `u-app02.nam.wirecard.sys` — two-node cluster, indicating baseline redundancy.
- **deploy_user**: `NAM\qa_east_deploy` — a domain service account, not a personal account, satisfying PCI DSS requirement for shared-service credentials.
- **clean_targets** / **backup_path**: Backup before deploy and working-directory cleanup are modelled as first-class config fields, reducing human error during deployments.

## Roadmap Phases — Business Significance

| Phase | Business Value |
|---|---|
| 1 (current) | Validates orchestrator pattern end-to-end; no traffic risk (no rolling) |
| 2 | Rolling deploy with Azure Application Gateway drain — zero-downtime deployments for production traffic |
| 3 | Rollback/recovery semantics — reduces MTTR for failed deployments |
| 4 | Auto-deploy SNAPSHOT to QA — accelerates release cycle; reduces manual intervention |
| 5 | Migration of all services — eliminates per-repo deployment scripts, full governance coverage |

Phase 2 is partially pre-configured: the `test-east-deploy.yml` contains commented-out `rolling:` block referencing a real Azure subscription ID (`f409c36e-affb-495d-93fd-e2cfab1a7faf`), resource group (`rg-az1-uat-ecount-001`), and App Gateway (`agw-az1-uat-ecount-002`), indicating Azure infrastructure is already provisioned.

## Compliance Observations

- Deployments are triggered manually (`workflow_dispatch`), satisfying the PCI DSS 6.5 requirement that production changes undergo authorization before implementation.
- Credential separation exists: QA/UAT uses `QA_EAST_DEPLOY_PASSWORD`; production uses `PROD_EAST_DEPLOY_PASSWORD` — preventing UAT credentials from accessing production systems.
- The use of a PAT (`PAT_TOKEN_PACKAGE`) scoped to `read:packages` restricts the workflow to artifact consumption only, following least-privilege principles.
- Current scope is limited to UAT environment; production deployment gating (`prod` required reviewers) is listed as future configuration, which should be treated as a **compliance gap** until implemented.

## Key Business Risks

1. **Single environment in scope**: Only `uat` is currently in the workflow options. Until `prod` is added with proper approval gates, the organization lacks automated governance for production deployments through this orchestrator.
2. **Phase 5 migration pending**: While the orchestrator exists, services not yet migrated from per-repo `cicd-deployment.yml` workflows operate outside centralized governance.
3. **Commented-out rolling config contains real resource identifiers**: The Azure subscription ID and resource group names visible in `test-east-deploy.yml` lines 24-35 should be treated as potentially sensitive infrastructure metadata.
