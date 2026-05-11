# runner-test — DevOps / Operations View

## Build System
- Maven 3.9.1 (via Maven Wrapper, `distributionUrl` points to repo.maven.apache.org).
- Java 8 (compiler source/target `1.8`).
- Plugin: `maven-shade-plugin` 3.2.4 creates a fat JAR with main class `hello.HelloWorld`.
- No test scope dependencies; no Surefire or Failsafe configuration.

## CI/CD Pipelines
| Workflow | Trigger | Runner | Purpose |
|---|---|---|---|
| `marven.yml` | Push (any branch) | `self-hosted, windows, X64` | Build validation |
| `codeql-java.yml` | Push/PR to main/master; workflow_dispatch | `self-hosted, X64, Linux, ubuntu-docker` | SAST scanning |
| `codeql.yml` | Weekly Tue 12:30 UTC; workflow_dispatch | Delegated to `om-ci-setup` reusable workflow | Centralised CodeQL |

## Config Management
- Maven settings (`settings.xml`) committed to `.mvn/wrapper/` — contains hardcoded credentials (see data architect view).
- Mirror points to legacy `d-na-stk01.nam.wirecard.sys:8081` Nexus and `https://maven.pkg.github.com/onbe/onbe_maven_releases` GitHub Packages.
- Dependabot: weekly Maven ecosystem scan configured.

## Observability
No runtime observability. CI log output only.

## Infrastructure Dependencies
- Self-hosted GitHub Actions runner (Windows X64) for build jobs.
- Self-hosted GitHub Actions runner (Linux ubuntu-docker) for CodeQL.
- Nexus at `d-na-stk01.nam.wirecard.sys:8081` (legacy Wirecard hostname — may be decommissioned).
- GitHub Packages Maven registry (`onbe/onbe_maven_releases`).
- Centralised `Onbe/om-ci-setup` repository for reusable CodeQL workflow.

## Operational Risks
- Misspelled workflow filename (`marven.yml`) is cosmetic but signals low quality gate on CI config changes.
- TLS disabled (`aether.connector.https.securityMode=insecure`) in CodeQL and Nexus deploy workflows — allows MITM on artifact resolution.
- Credentials in settings.xml must be rotated immediately if the Nexus instances are still reachable.
- No deployment step — this repo only validates the runner, it does not ship anything.

## Deployment
No deployment artefact produced for any environment. The JAR is build-and-discard.
