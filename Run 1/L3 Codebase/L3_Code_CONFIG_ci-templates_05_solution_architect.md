# Solution Architect View — CONFIG_ci-templates

## Technical Architecture
The repository implements a YAML-based GitLab CI/CD template library using GitLab's template composition features:
- **YAML anchors** (`&build_config`, `<<: *build_config`) for job-level DRY configuration
- **`include: local:`** directives for file-level composition
- **`include: project:`** for cross-project template reuse
- **Parent-child pipeline triggers** (`trigger:` + `strategy: depend`) for parallel multi-service deploys
- All build/test jobs run in the `maven:3.6.3-jdk-8` Docker image; deploy jobs run in `dperson/samba`; verify jobs run in `alpine`

## Pipeline Structure
```
mavenBuild.gitlab-ci.yml    ← build, test, release, publish jobs
tomcat/deployWar.gitlab-ci.yml  ← deploy jobs (direct + parent-child + shared variants)
tomcat/verify.gitlab-ci.yml     ← healthcheck jobs
tomcat/deployBridge.gitlab-ci.yml ← trigger wrapper for parent-child pattern
tomcat/deployChild.gitlab-ci.yml  ← child pipeline that includes deployWar + verify
tomcat/deployVerify.gitlab-ci.yml ← includes deployWar + verify (non-bridge mode)
maven.gitlab-ci.yml         ← root: includes mavenBuild + deployVerify
mavenMulti.gitlab-ci.yml    ← root for multi-service: includes mavenBuild + deployBridge
```

## API Surface
No API is exposed. This is purely a CI/CD configuration library.

## Security Posture

### Credential Handling (no values reproduced)
- `$NORTHLANE_CI_RO_USER` and `$NORTHLANE_CI_RO_PASS` are interpolated directly into the `SCRIPTS_REPO` URL in `maven.gitlab-ci.yml` and `mavenMulti.gitlab-ci.yml`. URL-embedded credentials may appear in GitLab job logs if the variable is not masked. **This is a hardcoded-pattern credential risk.**
- `$GL_NAM_USER` / `$GL_NAM_PASSWORD` — passed as positional arguments to `deployFromNexus.sh`; may appear in process lists.
- `$CICD_RELEASE_KEY` — SSH private key added to agent via `ssh-add <(echo "$CICD_RELEASE_KEY")`.
- `$MVN_SETTINGS` — base64-encoded settings.xml decoded to `~/.m2/settings.xml` at runtime; may contain repository credentials.

### Other Security Issues
- `StrictHostKeyChecking no` set globally for release SSH operations — disables host key verification
- `dperson/samba` Docker image used for deployment — public image, no digest pinning (supply chain risk)
- `maven:3.6.3-jdk-8` — public image, no digest pinning
- Health check allows `allow_failure: true` for QA — a failed deployment to QA will not block the pipeline

## Technical Debt
- Unit tests commented out (`#test-app-unit:` block) — zero unit test enforcement at CI level
- JDK 8 (`maven:3.6.3-jdk-8`) — EOL JDK version, Java 8 extended support only
- Nexus URL hardcoded to `wirecard.sys` legacy internal domain
- `git checkout -B "$CI_BUILD_REF_NAME"` — uses deprecated `CI_BUILD_REF_NAME` variable (replaced by `CI_COMMIT_REF_NAME` in modern GitLab)
- No SAST, DAST, or container scanning jobs defined
- No secrets detection job

## Gen-3 Migration Requirements
1. Replace `maven:3.6.3-jdk-8` with JDK 17/21 image
2. Add Docker build + push stage for container registry
3. Replace `deployFromNexus.sh` + SMB deploy with `kubectl apply` or Helm upgrade
4. Pin all Docker image references to digests
5. Move credentials out of URL variables into GitLab masked variables or vault integration
6. Add SAST and secrets detection jobs
7. Replace deprecated `CI_BUILD_REF_NAME` with `CI_COMMIT_REF_NAME`
8. Enforce unit tests (uncomment `test-app-unit` job)
9. Migrate Nexus from `wirecard.sys` to new artifact registry

## Code-Level Risks
- `healthcheck` for QA has `allow_failure: true` — a broken QA deployment produces a green pipeline
- `start_in: 1 minute` delayed healthchecks assume 60 seconds is sufficient for Tomcat startup — may produce false-positive health checks on slow starts
- `git fetch --all --tags` in release job with `StrictHostKeyChecking no` — all remote Git hosts trusted unconditionally
