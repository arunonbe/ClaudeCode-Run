# maven-packaging-poc — Data Architect View

## Data Stores

**None.** This repository contains no application code, no database connections, and no data storage of any kind. It is a build-system POC consisting entirely of POM files and GitHub Actions workflow YAML.

## Schema / Tables

Not applicable.

## Sensitive Data

No application data. The GitHub Actions workflow references one secret:

| Secret | Name in Workflow | Notes |
|---|---|---|
| GitHub PAT token | `secrets.PAT_TOEKN_PACKAGE` | **Typo** — `TOEKN` instead of `TOKEN`. Used to authenticate Maven deploy to GitHub Packages. |

This PAT token grants write access to GitHub Packages. It should be stored in GitHub Actions Secrets and never committed to source. Confirmed: it is referenced only as a secret reference, not hardcoded.

## Encryption

Not applicable — no data at rest or in transit beyond build artefacts.

## Data Flow

```
[Developer / GitHub Actions trigger]
        |
        v
[mvn deploy]
        |
        v
[GitHub Packages: maven.pkg.github.com/onbe/onbe_maven_releases]
```

The only "data" in this repository is the published Maven POM artefact itself (empty module POMs with no compiled code).

## Compliance Gaps

None directly applicable. However:

1. **Legacy Nexus URL in POM**: `distributionManagement` still references `d-na-stk01.nam.wirecard.sys:8080/nexus` — a Wirecard on-premise server. This URL should be verified as decommissioned or removed. If still active, it represents an uncontrolled artefact endpoint.
2. **Secret name typo**: `PAT_TOEKN_PACKAGE` — if the actual GitHub secret is named differently (`PAT_TOKEN_PACKAGE`), deployments silently fail, creating a gap in the CI/CD supply chain.
