# DevOps / Operations — wirecard_nam-bank-agent_LIB

## Build System
- **Tool**: Gradle 4.8 (wrapper), Java 8 (`gradle:4.8-jdk8` CI image)
- **Spring Boot**: 1.5.13.RELEASE (declared in plugins block)
- **Modules**: nam-bank-agent-batch, -config, -data, -db-app, -docs, -event-consumer, -event-persistence, -event-service, -event-utility, jenkins-plugins (ansible sub-project)
- **RPM packaging**: nebula.rpm; `wd-app-nam-bank-agent-batch` and related packages; deployed to `/usr/share/wd_app/`
- **Artifact repository**: Nexus (`d-issrepo-app01.wirecard.sys:8081`); also AWS S3 for db-app artifacts

## CI/CD Pipeline (GitLab CI — .gitlab-ci.yml)
| Stage | Description |
|---|---|
| checkoutBranch | Git checkout |
| build | `./gradlew clean cleanVersion assemble` |
| checkstyle | `./gradlew checkstyleMain checkstyleTest` |
| test | `./gradlew test jacocoTestCoverageVerification` (90% minimum) |
| publish | `./gradlew nam-bank-agent-db-app:publish -Papp.mavenPublishRepo=aws buildRpm uploadRpmToAWS` |
| update-release-bundle | master/development branches |
| merge-request-checks | Pre-merge artifact check |
| tag-release | master branch |

## Deployment (Ansible)
Two Ansible deployment playbooks found:

### deploy-batch.yml
- Target: `batchserver` host group
- Rolling update with Ansible `rolling_update` role
- Service: `wire-transfer-agent-batch` (NOTE: this playbook uses the wire-transfer-agent service name — may be copy/paste from sibling repo or deliberate reuse)
- Health check: `/wire-transfer-agent/monitoring/health`
- Port: 9000

### deploy-consumer.yml
- Target: `batchserver` host group (consumer application)
- Spring Boot app (`nam-bank-agent-event-consumer`)

## Configuration Management
- Spring profiles: default (H2/dev), environment-specific overlays via Puppet
- Batch job directory paths configured via `@ConfigurationProperties` bound at startup
- SFTP credentials (host, port, username, private key) injected via environment properties
- Gradle properties file (not in source) for Nexus credentials
- `NAM_BANK_AGENT_DIR` environment variable required at runtime (documented in README)

## Observability
- **Spring Boot Actuator**: Health endpoint at `/nam-bank-agent/monitoring/health` (assumed; consistent with platform pattern)
- **Logging**: SLF4J/Logback; structured JSON via logstash-logback-encoder (declared in sibling dependency management)
- **Email alerting**: `StepExceptionEmailListener` sends emails on batch step failure
- **SonarQube**: project key `com.wirecard.issuing:nam-bank-agent`; Jacoco integration
- No distributed tracing observed

## Infrastructure Dependencies
| Dependency | Purpose | Notes |
|---|---|---|
| Oracle DB | Primary data store | ojdbc8; two-schema pattern |
| ActiveMQ (EventHub) | Inbound/outbound events with CCP/platform | Same EventHub pattern as FTC |
| Sunrise Bank SFTP | ACH/wire/check file exchange | Config prefix `sftp.srb`; private-key auth |
| PDS SFTP | Check file exchange | `PdsSftpConfig`; separate credentials |
| Local filesystem | Batch staging directories | Input/processed/failed/archive/output |
| SMTP | Batch failure emails | Environment-specific |
| Nexus | Artifact repo | `d-issrepo-app01.wirecard.sys:8081` |
| AWS S3 | Release artifact storage | For db-app artifacts |
| Jenkins | CI/CD orchestration | `jenkins-plugins` sub-module with `Jenkinsfile` and `plugins.txt` |

## Operational Risks
1. Spring Boot 1.5.13 — older than FTC sibling; EOL since Aug 2019; significant CVE exposure
2. Ansible deploy playbook uses `wire-transfer-agent-batch` service name for NAM bank agent — possible copy/paste error causing health checks to target wrong service
3. `setAllowUnknownKeys(true)` in SFTP factory — no SFTP host verification in production
4. Batch staging directories on local filesystem — if disk fills or permissions change, all batch jobs fail silently or accumulate in failed directory
5. Private key for Sunrise SFTP loaded from application property — rotation requires application restart
6. 90% test coverage requirement may mask edge-case failures in complex NACHA file processing
7. Partial clone limitation — operational scripts and configuration may be incomplete in this analysis
8. Jenkins plugins managed in source via `jenkins-plugins/plugins.txt` — plugin versions must be actively managed for CVE remediation
