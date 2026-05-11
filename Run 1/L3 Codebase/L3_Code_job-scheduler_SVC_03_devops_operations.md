# DevOps / Operations View — job-scheduler_SVC

## Build System

- **Build tool**: Maven 3.x with wrapper (`mvnw`, `mvnw.cmd`)
- **Maven settings**: `.mvn/wrapper/settings.xml`
- **Java**: 21 (`maven.compiler.source/target = 21`, root `pom.xml` lines 20–21)
- **Packaging**: WAR (`jobscheduler-service.war`)
- **Maven build command**: `mvn -s ./.mvn/wrapper/settings.xml -Dmaven.test.skip clean package` (from `deployment.yml` line 33)
- **Parent**: `com.parents:prepaid-parent:6.0.12`

## CI/CD Pipelines

### GitHub Actions (primary pipeline)

**File**: `.github/workflows/deployment.yml`

This is the primary pipeline triggered on push to `main` or pull requests targeting `main`. It delegates to the centralized Onbe CI workflow (`Onbe/om-ci-setup/.github/workflows/java-workflow.yml@main`):

| Step | Detail |
|---|---|
| App name | `JobSchedulerSVC` |
| PACT participant | `job-scheduler-svc` |
| WSDL publish | `PUBLISH_TO_APIM: true` (APIM publication enabled) |
| Backend suffix | `/services/JobSchedulerWebServices` (XML-RPC service endpoint) |
| Dependency updates | `UPDATE_DEPENDENCIES: true`, `UPDATE_PARENT_VERSION: true` (auto-bump) |
| Tests | Skipped (`-Dmaven.test.skip`) |

**File**: `.github/workflows/redeploy.yaml`
- Manual redeployment without full build cycle

**File**: `.github/workflows/github-package-publish.yml`
- Publishes JAR artifacts to GitHub Packages

### Security Scanning

**File**: `.github/workflows/codeql.yml`
- GitHub CodeQL SAST on push/PR
- Scans Java source

**File**: `.github/containerscan/allowedlist.yaml`
- Container image vulnerability allowlist for Trivy scanner

**File**: `.trivyignore`
- Additional Trivy suppression rules

## Deployment Targets

From `deployment.yml` and GitLab CI references:

| Environment | Servers | Service Name | WAR Path |
|---|---|---|---|
| QA | `q-app09.nam.wirecard.sys` (Java 21) or `q-na-app09.nam.wirecard.sys` (Java 8) | `Apache Tomcat - JobManager` | Embedded in `om-ci-setup` |
| Production | Configured in centralized pipeline | Similar pattern | `D:\c-base\opt\tomcat\servers\...` |

The `jobscheduler-service` WAR is deployed to a Tomcat server. Configuration files (`server.xml`, `certfile_qa.crt`) are in `jobscheduler-service/config/`. The `.env` file in `jobscheduler-service/` contains environment variable defaults for Docker Compose local development.

## Docker Compose (Local Dev)

`jobscheduler-service/docker-compose.yaml` provides a local development environment. The Dockerfile in `jobscheduler-service/Dockerfile` defines the container image. These are not used in production deployments.

## Health Check

`jobscheduler-service/src/main/java/com/ecount/service/jobscheduler/HealthCheck.java` — a lightweight health endpoint. The HTTP endpoint path is likely `/health` or similar, served via the Tomcat deployment. This is the only monitoring surface available.

## Monitoring and Alerting Gaps

There is **no Prometheus/Micrometer metrics integration**, **no distributed tracing** (OpenTelemetry/Zipkin), and **no structured JSON logging** in this codebase. Operational visibility depends on:

1. **Log4j/SLF4J log files** on the application server — searched via Filebeat/ELK (Filebeat configuration is in `CONFIG_filebeat-agent` repo)
2. **Database queries** against `sch_job_actions_log` and `blackout_actions_log`
3. **HTTP health check** endpoint provided by `HealthCheck.java`
4. **Scheduler callback service** (`JobSchedulerCallbackServiceServer.java`) — receives callbacks from the underlying scheduler engine when tasks fire

## Failure Modes and Recovery Procedures

| Failure Mode | Observed Behavior | Recovery |
|---|---|---|
| Tomcat process crash | All in-flight schedule callbacks lost; jobs stuck in `AWAITING_SCHEDULED_EXECUTION` | Restart Tomcat; reapply schedules via ClientZone or `reapplySchedule()` API call |
| Director service unavailable at startup | Datasource beans fail to initialize; WAR does not start | Restore Director connectivity; restart Tomcat |
| `jobsvc` database unavailable | All schedule operations fail with SQLException; logged but not exposed to callers | Restore DB; pending callbacks may need manual reapplication |
| Blackout start/finish callback missed | Blackout stuck in `PROGRESS` state; jobs neither paused nor resumed | Use `overrideBlackout()` API to manually clear; investigate scheduler task delivery |
| Two concurrent blackout `startBlackout()` calls | Race condition — `BlackoutManagerImpl` line 223 sets `PROGRESS` status before iterating jobs; second call re-reads and may double-pause | `startOrFinishBlackout()` uses a do-while retry loop (lines 927–948) with 2-second sleep; not a true lock |
| Schedule time miscalculation | Jobs scheduled for wrong future time; `isSchedulePassed()` check should catch this | `reapplySchedule()` corrects the next execution time |

## Retry Policy

The scheduler does not itself retry failed job executions — that is the responsibility of the Job Service and Autofile workflows. However:
- `BlackoutManagerImpl.startBlackout()` schedules a "retry to stop job" task at `retryIntervalToStopJob` milliseconds after the blackout starts, to catch jobs that were in transition when the blackout began (lines 277–286)
- `startOrFinishBlackout()` has a built-in 3-attempt retry loop with 2-second sleeps when blackout data is not yet available (lines 927–948)

## Secret Management

- No hardcoded credentials observed in source
- Database connection strings are retrieved from Director service at runtime
- TLS certificate for QA is stored in `jobscheduler-service/config/certfile_qa.crt` — a non-secret public certificate
- `secrets.QA_EAST_DEPLOY_PASSWORD` used in deployment workflow is stored in GitHub Actions secrets
- `secrets.PAT_TOKEN_PACKAGE` for package registry access is also in GitHub secrets

## Release Cadence

Version is `3.0.1-SNAPSHOT` — no formal release cycle is enforced by the pipeline configuration. The `deployment.yml` deploys on every push to `main`, making `main` effectively a continuous delivery branch for QA at minimum. Production promotion requires `deploy_to_production: true` input in the `cicd-deployment.yml` workflow (this is the job-service pattern; the scheduler uses the simpler `java-workflow.yml` which includes its own promotion gates).
