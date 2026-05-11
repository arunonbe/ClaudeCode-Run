# DS_Gitlab-Demo-Branching — Enterprise Architect Perspective

## Enterprise Architecture Assessment

`DS_Gitlab-Demo-Branching` has no enterprise architecture significance in terms of systems, integrations, or data flows. It is a demonstration repository. However, its existence provides useful signal about the state of source control governance, tooling adoption, and DevOps maturity within the Onbe Data Services team at the time of its creation.

## Organisational Context

The repository was created under the `DS_` (Data Services) prefix namespace, confirming it was created by or for the Data Services team. The GitLab branching demonstration indicates that:

1. The team was transitioning to GitLab as its primary source control platform — likely as part of a broader Wirecard-to-Onbe/NorthLane infrastructure migration.
2. The team recognised a need for formal branching discipline, implying prior practices (possibly direct commits to a single branch, or manual file-copy based change management) were being replaced.
3. Training was occurring informally (ad-hoc demo repo) rather than through a structured DevOps enablement programme.

## Enterprise Source Control Strategy

From an enterprise architecture perspective, the co-existence of demo and production repositories in the same GitLab namespace reflects a source control governance gap. In a mature enterprise:

| Repository Category | Namespace / Group | Access Control |
|---|---|---|
| Production ETL | `data-services/etl/` | Engineering team + release managers |
| Production Reports | `data-services/reports/` | Engineering + BI team |
| Training / Demo | `data-services/training/` | All staff; read-only from CI |
| Infrastructure | `platform/infra/` | Platform Engineering only |

The current state, where `DS_Gitlab-Demo-Branching` sits alongside `DS_ETL_warehouse` in the same namespace, does not meet this standard.

## GitLab as Enterprise Platform

GitLab provides enterprise capabilities beyond simple source control that the Data Services team is not yet utilising based on the evidence in these repositories:

| Capability | Current State | Recommended State |
|---|---|---|
| CI/CD Pipelines | Not implemented in any DS repo | SSIS build + deploy pipelines per repo |
| Branch Protection | Not visible in repository content | Enforce on `main` + `develop` for all DS repos |
| Merge Request Approvals | Not configured (no CODEOWNERS file) | Require 1 approver for all production merges |
| Secret Detection | Not configured | Enable GitLab Secret Detection scanner |
| Container Registry | Not used | N/A for current SSIS stack |
| GitLab Environments | Not configured | Map to dev/QA/prod SSIS Catalog environments |

## Change Management and Audit Trail

For a PCI DSS Level 1 service provider, change management is a specific compliance requirement. PCI DSS Requirement 6.4 (change management) requires that:
- All changes to system components are documented
- Changes are approved before implementation
- Testing is performed and documented
- Rollback procedures exist for each change

GitLab's merge request workflow, when properly configured with approvals, protected branches, and linked issue tracking (Jira/Asana), provides a full audit trail for PCI DSS Requirement 6.4 compliance. The demo repository shows the team is aware of the workflow but has not yet formalised it for production repositories.

## Recommendation: Enterprise DevOps Governance Framework

The Data Services team should implement the following enterprise-level controls, with this demo repository serving as the historical reference point for where the journey began:

1. **Repository Classification Policy**: All repositories must be tagged with a `classification` tag: `PRODUCTION`, `QA`, `DEVELOPMENT`, `TRAINING`, or `DEPRECATED`.

2. **Naming Convention Standard**: Adopt a consistent prefix convention:
   - `DS_ETL_` for ETL pipelines
   - `DS_RPT_` for reporting
   - `DS_DB_` for database schema projects
   - `DS_TRAINING_` for training repositories

3. **Lifecycle Management**: Define a repository lifecycle with automated archival triggers:
   - No commits in 180 days → alert to team
   - No commits in 365 days → auto-archive proposal
   - `README.md` contains "Delete me" → flag for immediate review

4. **GitLab Group Structure**:
   ```
   Onbe / Data-Services /
     ├── ETL /          <- DS_ETL_* repos
     ├── Reports /      <- DS_RPT_* repos
     ├── Training /     <- DS_*_TRAINING_* repos (this repo should be here)
     └── Archive /      <- Decommissioned repos
   ```

5. **PCI DSS Change Management Integration**: Link GitLab MRs to the change management ticketing system. All production deployments require an approved change ticket reference in the MR description.

## Conclusion

This repository is architecturally trivial but organisationally informative. It marks the starting point of the Onbe Data Services team's GitLab adoption journey. The recommended enterprise action is to archive this repository, use it as a before-state reference in the DevOps maturity assessment, and implement the governance framework described above across all active Data Services repositories.
