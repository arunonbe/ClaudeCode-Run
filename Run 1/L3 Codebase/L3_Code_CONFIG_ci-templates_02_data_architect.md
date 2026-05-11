# Data Architect View — CONFIG_ci-templates

## Data Stores
- **Nexus Repository Manager** — artifact repository at `http://d-na-stk01.nam.wirecard.sys:8080/nexus/` (two repos: snapshots and releases). All built JARs and WARs are published here.
- **GitLab CI artifact store** — ephemeral job artifacts (WAR files, artifactInfo.properties, JUnit reports, service_hosts/deploy_job temp files) retained for 1 month.
- **Maven local cache** — `.m2/repository` cached between pipeline runs within the same branch.
- **WhiteSource/Mend cloud** — SCA scan results published to external Mend SaaS.
- **ci-scripts Git repository** — cloned at runtime from `$SCRIPTS_REPO` for deployment helper scripts.

## Schema
- `artifactInfo.properties` — artifact coordinate metadata file located at `target/classes/artifactInfo.properties`; consumed downstream by deploy and verify stages
- `tmp/service_hosts` — text file listing target deployment hosts; passed between jobs as artifact
- `tmp/deploy_job` — text file recording the CI job name that performed the deploy; passed between jobs

## Sensitive Data Handling
- **`$NORTHLANE_CI_RO_USER` / `$NORTHLANE_CI_RO_PASS`** — read-only Git credentials for the ci-scripts repo are embedded in the SCRIPTS_REPO URL variable in `maven.gitlab-ci.yml` and `mavenMulti.gitlab-ci.yml`. This URL pattern (`https://user:pass@gitlab.com/...`) means credentials are visible in the pipeline variable if it is not masked in GitLab. This is a credential-exposure risk.
- **`$GL_NAM_USER` / `$GL_NAM_PASSWORD`** — deployment credentials passed to `deployFromNexus.sh`; must be protected CI variables.
- **`$CICD_RELEASE_KEY`** — SSH private key for release commits; injected via CI variable.
- **`$MVN_SETTINGS`** — base64-encoded Maven settings.xml (may contain repository credentials); decoded at runtime to `~/.m2/settings.xml`.

## Encryption
- TLSv1.2 enforced for all Maven artifact downloads
- SSH StrictHostKeyChecking disabled for release SSH operations (security gap)
- No at-rest encryption controls within the templates themselves

## Data Flow
```
Developer push
  → GitLab CI triggers pipeline
  → build-app: mvn package → WAR artifact stored in GitLab
  → mvndeploy: mvn deploy → WAR published to Nexus
  → deployFromNexus.sh: WAR pulled from Nexus → copied to Tomcat hosts via SMB (dperson/samba Docker image used)
  → verify: HTTP GET to health endpoint → 200 OK expected
```

## Quality
- JUnit XML reports published from failsafe/surefire; available in GitLab test reports
- Artifact expiry set to 1 month for all pipeline artifacts
- No data validation or schema checks on configuration files

## Compliance Gaps
- `$NORTHLANE_CI_RO_USER:$NORTHLANE_CI_RO_PASS` embedded in a URL variable is a PCI DSS credential-management concern (credentials should not appear in variable values visible in logs)
- SSH StrictHostKeyChecking disabled for release jobs violates secure-communication best practices
- No secrets scanning step in the pipeline to catch hardcoded credentials in application code being built
