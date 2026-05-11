# DevOps / Operations View — crypto-service_SVC

## 1. Build System

| Property | Value |
|---|---|
| Build tool | Apache Maven 3.9.5 (Maven Wrapper via `mvnw`/`mvnw.cmd`) |
| Java source/target | 21 (`pom.xml` lines 26–27) |
| Packaging | Multi-module: `common` (JAR) + `impl` (JAR) + `service` (WAR → `cryptokeysvc.war`) |
| Parent BOM | `com.parents:prepaid-parent:6.0.12` (sourced from `github-releases` at `maven.pkg.github.com/onbe/onbe_maven_releases`) |
| Version | `3.0.1-SNAPSHOT` |
| Skip tests | All CI pipelines pass `-Dmaven.test.skip` or `-DskipTests`; tests are never run in automated pipelines |
| Enforcer | `banTransitiveDependencies` is active in all three sub-modules; Spring and Jackson are whitelisted |

Maven settings authenticate to GitHub Packages using `${env.GITHUB_TOKEN}` (`.mvn/wrapper/settings.xml`, line 6).

## 2. Deployment Targets

The service supports two distinct deployment tracks:

### Track A: Containerised (AKS — current/preferred)
- **Image base**: `bellsoft/liberica-openjre-alpine:21` (`Dockerfile` line 1)
- **Application server**: Apache Tomcat 10.1.28 downloaded at image build time (`Dockerfile` line 8)
- **Port**: Container listens on 80; host mapping is `9315:80` in `docker-compose.yaml`
- **Environment variable**: `CBASE_HOME_URL=file:///cbase` (`Dockerfile` line 24); config mounted at `/cbase/config` from host volume
- **QA cert**: `certfile_qa.crt` imported into the JRE cacerts at image build time (`Dockerfile` lines 19–20); keystore password is the JDK default `changeit` — this is a well-known default and should be rotated
- **Networks**: Uses externally defined Docker network `my-network`
- **Extra hosts**: Hard-coded IP mappings for `qa.nam.wirecard.sys` (10.91.22.253) and `ppnaut.nam.wirecard.sys` (10.91.22.254) in `docker-compose.yaml` — these reference old Wirecard infrastructure hostnames; their continued necessity should be reviewed
- **Deployment workflow**: `deployment.yml` calls shared `Onbe/om-ci-setup/.github/workflows/java-workflow.yml@main`; on-demand redeploy via `redeploy.yaml` (AKS QA)

### Track B: Bare-Metal Windows VM (legacy)
- **Target host**: `azureuser@d-app02.nam.wirecard.sys` (`vm-deployment.yml` line 16)
- **Destination**: `C:/Users/azureuser/Documents/cryptokeysvc.war`
- **Mechanism**: `scp` copy of WAR file; no Tomcat restart or verification step is scripted
- **GitLab CI** (`.gitlab-ci.yml`): Separate legacy pipeline still references `d-na-app03` (dev) and `q-na-app03`, `q-na-app04` (QA) Windows hosts on port 9315

**Critical contradiction**: The Docker image uses Alpine Linux, but the application's `ExecuteCommands.java` calls `cmd /c start/min` (Windows CMD). The containerised deployment path cannot work as-is for the add-key operation.

## 3. Configuration

All runtime configuration is externalised via `${CBASE_HOME_URL}/config/service/httpCryptoService/httpCryptoService.properties`. This file is **not in the repository**. Known keys:

| Property Key | Purpose |
|---|---|
| `httpCryptoService.batAddCommandFile` | Absolute path to Windows .bat file that wraps `pgp --key-add` |
| `httpCryptoService.pgpFilesFolderName` | Temp folder for add-key command output files |
| `httpCryptoService.cluster.node.*` | Host:port entries for multi-node client-side URL list |

Log4j2 configuration is also externalised: `${CBASE_HOME_URL}/config/service/httpCryptoService/log4j2.xml` (`web.xml` line 28).

Docker secrets/env are loaded via `.env` file (`docker-compose.yaml` line 10); the `.env` file is not in the repository (correctly excluded by `.gitignore`).

## 4. Observability

### Logging
- **Framework**: SLF4J + Log4j2 (API: `log4j-api`, implementation: `log4j-core`, legacy bridge: `log4j-1.2-api`)
- **Annotation**: `@Slf4j` (Lombok) used on all service classes
- **Level distribution**:
  - `INFO`: All key operation entry points, key names, key IDs, command output
  - `ERROR`: All caught exceptions plus redundant test calls in constructor (`CryptoServiceImpl` lines 35–36)
  - `DEBUG`: Key paths and constructed command strings (gated behind `log.isDebugEnabled()` check only in one place: `KeyManipulationHelper.java` line 179)
- **Concern**: Full raw PGP command output is logged at INFO level including key names and IDs. Log destination and retention period are not controlled by this repository.

### Health Check
- Endpoint: GET `/cryptokeysvc/hc` → returns string `"OK"` (`HealthCheck.java`)
- Implemented as a Spring `@RestController` in a separate servlet context (`HTTPCryptoService-hc-servlet.xml`)
- No dependency checks (keyring reachability, PGP binary presence) — purely a JVM liveness signal

### Metrics / Tracing
- **None present**. No Micrometer, Prometheus, or distributed tracing instrumentation exists.

### Access Logs
- Tomcat `AccessLogValve` is configured in `server.xml` (line 182) with common log format to `logs/localhost_access_log*.txt`. This is inside the container and will not survive pod restarts unless a persistent volume is mounted.

## 5. Infrastructure Dependencies

| Dependency | Type | Notes |
|---|---|---|
| PGP binary on host | Runtime executable | Must be on `PATH` or hardcoded in `.bat` file; not managed by this service |
| Windows CMD shell | OS requirement | `cmd /c` hardcoded in `ExecuteCommands.java` line 38; incompatible with Alpine Linux container |
| `${CBASE_HOME_URL}` volume | Filesystem mount | Config, log config, and key file staging all rooted here |
| Spring HttpInvoker transport | Network | Plain HTTP; no TLS at application layer |
| Wirecard DNS entries | Network | `qa.nam.wirecard.sys` and `ppnaut.nam.wirecard.sys` hostnames hardcoded in `docker-compose.yaml` |
| GitHub Packages registry | Build | Dependency resolution and artifact publishing |

## 6. CI/CD Pipeline Summary

| Workflow | Trigger | Action |
|---|---|---|
| `deployment.yml` | Push/PR to `main` | Calls shared `java-workflow.yml`; builds, tests (skipped), publishes, deploys to AKS |
| `github-package-publish.yml` | Push to `main`, workflow_dispatch | Publishes JAR/WAR to GitHub Packages |
| `codeql.yml` | Weekly (Friday 17:53 UTC), workflow_dispatch | Runs CodeQL SAST via shared `codeql-auto.yml` |
| `redeploy.yaml` | workflow_dispatch | Redeploys existing image to QA AKS |
| `vm-deployment.yml` | workflow_dispatch (requires `version-tag` input) | Downloads WAR from GitHub Packages, SCP to Windows VM |
| `.gitlab-ci.yml` | GitLab triggers | Legacy pipeline for Windows VM deployment (still present, may be stale) |

Dependabot is configured for Maven with weekly schedule (`dependabot.yml`).

`PUBLISH_TO_APIM: true` is set in `deployment.yml` but `INTERNAL_APIM: false` and `EXTERNAL_APIM: false` — indicating the APIM publish step is configured but no gateway exposure is active.

`EXCLUDE_STAGE: true` — the staging environment is skipped; changes go directly from build to production equivalent.

## 7. Ignored CVEs (Active Risk Acceptance)

The following CVEs are suppressed in both `.trivyignore` and `.github/containerscan/allowedlist.yaml`:

| CVE | Component | Notes |
|---|---|---|
| CVE-2018-1000632 | dom4j | XML injection |
| CVE-2020-10683 | dom4j | XXE |
| CVE-2024-22262 | Spring Framework | URL parsing / open redirect |
| CVE-2024-52316 | Apache Tomcat | Authentication bypass |
| CVE-2024-38816 | Spring Web | Path traversal |
| CVE-2024-50379 | Apache Tomcat | Race condition / RCE |
| CVE-2024-56337 | Apache Tomcat | (Trivy only) Case-sensitive bypass |
| CVE-2024-38819 | Spring Web | (Trivy only) Path traversal |

**CVE-2024-52316** (Tomcat authentication bypass) and **CVE-2024-50379** (Tomcat RCE race condition) are particularly concerning for a key-management service and have been explicitly whitelisted. These must be reviewed for applicability and formally risk-accepted with Security sign-off, not simply suppressed.

## 8. Operational Risks

| Risk | Severity | Detail |
|---|---|---|
| Tests skipped in all CI pipelines | High | `-Dmaven.test.skip=true` in every pipeline definition; the sole test class also has all test bodies commented out |
| No staging gate | High | `EXCLUDE_STAGE: true` means no pre-production verification step |
| 5-second hardcoded sleep | Medium | Race condition on slow hosts; no retry or file-existence polling loop |
| Container image downloads Tomcat at build time | Medium | `curl -O https://archive.apache.org/dist/tomcat/...` in Dockerfile — build fails if archive.apache.org is unreachable; also foregoes image layer caching for Tomcat |
| Temp file not deleted on exception paths | Medium | `file.delete()` at `ExecuteCommands.java` line 86 is inside a try block; if an exception is thrown before that line the temp file is not cleaned up |
| GitLab CI pipeline still present alongside GitHub Actions | Low | Two parallel CD configurations exist; operational state of GitLab pipeline is unknown |
| `NAVIN\` sentinel in output data | Low | Developer debug artifact (`ExecuteCommands.java` lines 77, 127, 132, 171, 176) shipped to production |
