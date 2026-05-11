# DevOps / Operations View — CONFIG_ci-templates

## Repository Role
Shared GitLab CI/CD template library. All Java/Maven application pipelines in the `northlane/development/application-development/` namespace include these templates via GitLab `include: project:` directives.

## Files and Their Functions

| File | Stage(s) | Purpose |
|------|----------|---------|
| `maven.gitlab-ci.yml` | build, test, release, publish, deploy, verify | Root composite template for single-artifact apps |
| `mavenBuild.gitlab-ci.yml` | build, test, release, publish | Build, test, release, and publish jobs |
| `mavenMulti.gitlab-ci.yml` | build, test, release, publish, deployBridge | Multi-artifact variant using parent-child pipeline bridge |
| `tomcat/deployWar.gitlab-ci.yml` | deploy | Tomcat WAR deployment jobs for DEV and QA (single and parent-child modes) |
| `tomcat/deployBridge.gitlab-ci.yml` | deployBridge | Parent pipeline trigger for child deploy pipelines |
| `tomcat/deployChild.gitlab-ci.yml` | deploy, verify | Child pipeline composed of deployWar + verify |
| `tomcat/deployVerify.gitlab-ci.yml` | deploy, verify | Composite include: deployWar + verify |
| `tomcat/verify.gitlab-ci.yml` | verify | HTTP health check against deployed service endpoint |

## Build System
- **Tool**: Apache Maven 3.6.3
- **Runtime**: JDK 8 (`maven:3.6.3-jdk-8` Docker image)
- **Runner tags**: `nl-ntt` (build/test/release), `dev` (dev healthcheck), `qa` (qa healthcheck)
- **Cache**: `.m2/repository` directory cached per branch/job

## Deployment Pipeline
- **DEV deploy**: Automatic on default branch and feature branches
- **QA deploy**: Manual gate (`when: manual`) on default branch, feature, and Release branches
- **Release deploy**: Release branches trigger `release:prepare/perform` then deploy to DEV/QA
- **Deploy method**: Script `deployFromNexus.sh` pulled from ci-scripts repo at runtime; uses SMB (Samba Docker image `dperson/samba`) to copy artifacts to target Windows Tomcat hosts
- **Deploy targets**: Resolved from CI variables `DEV_SERVICE_HOSTS` / `QA_SERVICE_HOSTS` (per-service host lists)
- **Multi-service support**: `deployBridge.gitlab-ci.yml` supports up to three service slots: MAIN, SECONDARY, SHARED
- **Resource locking**: `resource_group: tomcatDev-$SERVICE_NAME` used for SHARED Tomcat instances to prevent concurrent deploys

## Configuration Management
- Services configured via GitLab CI variables (not in this repo)
- Maven settings optionally injected via base64-encoded `$MVN_SETTINGS` variable
- No Ansible, Puppet, Chef, or Terraform in this repo — infrastructure configuration is out of scope

## Observability
- Health checks run after deploy: `verify.gitlab-ci.yml` calls HTTP endpoint, checks for HTTP 200
- GC logging configured per service in UAT JAVA_OPTIONS files (companion env-config repos)
- No centralized alerting or monitoring configuration in this repo

## Infrastructure Dependencies
- GitLab CI/CD platform (runner infrastructure, protected variables)
- Nexus repository at `http://d-na-stk01.nam.wirecard.sys:8080/nexus/` — **legacy Wirecard infrastructure DNS**
- Internal DNS domain: `nam.wirecard.sys` — legacy naming
- ci-scripts Git repo: `gitlab.com/northlane/infrastructure/scripts/ci-scripts`
- Target app servers must be reachable from GitLab runners via SMB
- Health check targets must be reachable via HTTPS/HTTP from `dev`/`qa` tagged runners

## CI/CD Pipeline Stages (maven.gitlab-ci.yml)
1. build
2. test
3. release
4. publish
5. deploy
6. verify

## Operational Risks
- `deployFromNexus.sh` script is fetched at runtime from an external repo — if that repo is unavailable or changed, all deployments fail
- Nexus URL is hardcoded to legacy `wirecard.sys` internal hostname; DNS dependency on legacy infrastructure
- SSH StrictHostKeyChecking disabled in release jobs — risk of MITM during release commit
- Unit test job commented out — no unit test enforcement
- WhiteSource scan is opt-in (requires `WHITESOURCE=yes`) — not enforced across all pipelines
- Healthcheck uses basic auth; if service requires different auth, check will fail silently (marked `allow_failure: true` for QA)
