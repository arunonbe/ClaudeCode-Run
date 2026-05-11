# jobservice-integration_LIB — DevOps / Operations View

## Summary

The build, CI/CD, and operational profile of `jobservice-integration_LIB` is **identical to `jobserviceintegration_LIB`**. Both use:
- Maven Wrapper with Java 1.6 target
- `maven-compiler-plugin` 2.0.2
- `maven-source-plugin` 2.0.3
- `commons-logging` 1.1.1
- No publish workflow; CodeQL only
- Self-hosted runner (`ubuntu-docker`) for CodeQL

See `E:\OnbeEast363\analysis\per-repo\jobserviceintegration_LIB\03_devops_operations.md` for full details.

## CI/CD Workflows (confirmed present)

| Workflow | File | Schedule |
|---|---|---|
| CodeQL | `.github/workflows/codeql.yml` | Wednesday 17:03 UTC, `workflow_dispatch` |
| Dependabot | `.github/dependabot.yml` | Automated dependency PRs |

## Key Delta from jobserviceintegration_LIB

The `codeql.yml` in both repositories delegates to `Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main` using a self-hosted runner. No difference detected in CI configuration.

## Duplicate Artifact Build Risk

Both repos produce `com.ecount.service:jobserviceintegration:1.0.1-SNAPSHOT`. If a consumer pulls from a repository that has builds from both, the result is non-deterministic. This must be resolved before either repo can be safely published.

## Operational Risks

Same as `jobserviceintegration_LIB`:
1. Java 1.6 target — EOL 2013
2. Binary JARs including Log4j 1.2.15 (CVE-2019-17571)
3. Windows-only VBScript / WSF automation scripts
4. No unit tests
5. In-memory `Hashtable`-based processing — OOM risk on large files
6. `System.exit()` calls in library code
7. No publish pipeline — manual artefact distribution

## Recommendation

Consolidate or clearly differentiate these two repositories. Until then, treat both as identical from an operational standpoint and apply all mitigations described for `jobserviceintegration_LIB`.
