# DS_Gitlab-Demo-Branching — DevOps and Operations Perspective

## Repository Infrastructure Assessment

`DS_Gitlab-Demo-Branching` is a placeholder repository with no operational significance. From a DevOps perspective, there are no build pipelines, no deployment configurations, no infrastructure-as-code artefacts, and no CI/CD definitions. All eight files are either empty or contain trivial placeholder text.

## GitLab Configuration Observations

No `.gitlab-ci.yml` file is present. This means no CI/CD pipeline is configured for this repository. While expected for a demo repository, it is worth noting that none of the six repositories reviewed in this analysis set contain a `.gitlab-ci.yml` or any CI/CD pipeline definition. This is a systemic gap: the Data Services team is using GitLab for source control but has not yet implemented automated build, test, or deployment pipelines for any of its repositories.

## Branching Model Demonstrated

Based on the file-naming evidence, the demo walked through a typical GitLab flow:

### Inferred Branch Structure Used in Demo

```
main (or master)
  ├── feature/dev-work         <- "this is my dev work.txt" committed here
  │     └── fix/moar-work      <- "this is moar work.txt" committed here
  └── incremental changes      <- change2.txt through change101.txt
```

The gap from `change5` to `change101` is notable — it may indicate the demo was extended at a later date, or a branch was created with a different numbering sequence that was merged back.

### GitLab Merge Request Workflow

The demo likely covered:
1. Creating a branch from `main`
2. Committing changes to the branch
3. Pushing the branch to GitLab
4. Opening a Merge Request (MR)
5. Reviewing and approving the MR
6. Merging to `main`
7. Deleting the feature branch

This is the canonical GitLab Feature Branch Workflow and is the appropriate baseline for Data Services teams managing SSIS, SQL, and report artefacts.

## Recommended GitLab Branch Strategy for Onbe Data Services

Based on the branching demo patterns and the operational context of the production repositories in this review set, the following branch strategy is recommended:

### Branch Naming Convention

| Branch Type | Pattern | Purpose |
|---|---|---|
| Main | `main` | Production-ready code only |
| Development | `develop` | Integration branch for QA testing |
| Feature | `feature/<ticket-id>-<short-desc>` | New functionality |
| Bugfix | `fix/<ticket-id>-<short-desc>` | Bug corrections |
| Release | `release/<version>` | Release candidate preparation |
| Hotfix | `hotfix/<ticket-id>-<short-desc>` | Emergency production fixes |

### Branch Protection Rules

- `main`: Protected; requires MR with at least 1 approver; no direct pushes; pipeline must pass.
- `develop`: Protected; requires MR; direct pushes by owners only.
- `feature/*` and `fix/*`: Unprotected; developer freedom.

### Merge Request Template

A `.gitlab/merge_request_templates/default.md` file should be added to all production repositories, containing:
```markdown
## Summary of changes
## Packages/reports modified
## Database objects changed
## Testing performed
## Rollback plan
```

## CI/CD Pipeline Recommendation

Although this demo repository has no pipeline, the analysis of `DS_ETL_sykes` and `DS_ETL_warehouse` indicates the need for CI/CD pipelines across all Data Services repositories. A GitLab CI pipeline for SSIS projects would include:

```yaml
stages:
  - validate
  - build
  - deploy-dev
  - deploy-qa
  - deploy-prod

validate:
  stage: validate
  script:
    - powershell.exe -File scripts/Validate-SSIS.ps1
  only:
    - merge_requests

build:
  stage: build
  script:
    - msbuild Sykes.sln /p:Configuration=Release
  artifacts:
    paths:
      - bin/Release/*.ispac

deploy-dev:
  stage: deploy-dev
  script:
    - powershell.exe -File scripts/Deploy-SSIS.ps1 -Environment dev
  only:
    - develop
```

## Operations Checklist for Repository Cleanup

- [ ] Archive `DS_Gitlab-Demo-Branching` in GitLab (Settings > General > Archive project)
- [ ] Remove from any automated scanning pipelines (dependency checks, secret scanning, SAST)
- [ ] Document official branching strategy in the Data Services GitLab wiki
- [ ] Add `.gitlab-ci.yml` templates to all production Data Services repositories
- [ ] Implement branch protection rules on `main` and `develop` branches in production repos

## Conclusion

This repository demonstrates the DevOps maturity baseline of the Onbe Data Services team at the time of its creation: awareness of the need for source control discipline, but not yet implementation of automated pipelines or formal governance. The recommended next step is to build on this foundation by implementing GitLab CI/CD pipelines for the production `DS_ETL_*` and `DS_RPT_*` repositories.
