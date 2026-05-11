# DevOps / Operations — wirecard_wire-transfer-agen_LIB

## Build System
- **Tool**: Gradle 4.8 (wrapper), Java 8
- **Spring Boot**: 1.5.13.RELEASE (declared in plugins block — same as NAM-bank-agent, oldest version across this repo set)
- **Modules**: wire-transfer-agent-batch, -config, -data, -service, jenkins-plugins (ansible sub-project)
- **RPM packaging**: nebula.rpm; `wd-app-wire-transfer-agent-batch` package; deployed to `/usr/share/wd_app/wire-transfer-agent-batch/`
- **Artifact repository**: Nexus (`d-issrepo-app01.wirecard.sys:8081`); AWS S3 for RPM upload

## CI/CD Pipeline (Jenkins — Jenkinsfile)
| Stage | Description |
|---|---|
| Checkout | Git clone |
| Build | Gradle assemble |
| Checkstyle | Gradle checkstyle |
| Test | Gradle test + Jacoco coverage (90% minimum) |
| Publish | Build RPM, upload to AWS S3 |

Branches:
- `master` → production release
- `development` → dev release

## Deployment (Ansible)
Two Ansible deployment playbooks:

### deploy-batch.yml
- Target: `batchserver` host group
- Rolling update (serial: 1)
- Package: `wd-app-wire-transfer-agent-batch`
- Service name: `wire-transfer-agent-batch`
- Health check URI: `/wire-transfer-agent/monitoring/health` → expects `"UP"`
- Port: 9000

### deploy-service.yml
- Similar pattern for the service (event-consumer/REST) component

## Configuration Management
- Spring profiles: default, `h2` (dev/test), batch-job-specific active profiles
- Batch job input/output directory paths via `@ConfigurationProperties`
- EventHub ActiveMQ credentials injected via environment
- SMTP configuration for email service
- Gradle `mavenPublishRepo.*` properties for Nexus credentials (not in source)

## Observability
- **Health endpoint**: `/wire-transfer-agent/monitoring/health`
- **Actuator**: all endpoints at `/wire-transfer-agent/monitoring/*`
- **Logging**: SLF4J/Logback; logstash-logback-encoder for structured JSON
- **SonarQube**: project key `com.wirecard.issuing:wire-transfer-agent`; Jacoco integration
- **Email alerting**: Email service for operational notifications on wire transfer events

## Infrastructure Dependencies
| Dependency | Purpose | Notes |
|---|---|---|
| Oracle DB | Primary data store | ojdbc8; two-schema |
| ActiveMQ (EventHub) | Inbound consumer + outbound producer | Wire transfer events |
| Local filesystem | Batch file staging | JSON files from NAM bank agent |
| NAM Bank Agent | Upstream file provider | Deposits JSON files to shared filesystem |
| CCP API | Reserve/confirm money operations | Via EventHub events |
| SMTP | Operational email notifications | Email service |
| Nexus | Artifact repo | Internal |
| AWS S3 | RPM artifact storage | |
| Jenkins | CI/CD | jenkins-plugins sub-module |

## Operational Risks
1. Spring Boot 1.5.13 — EOL Aug 2019; same risk level as NAM-bank-agent
2. Shared filesystem coupling with NAM-bank-agent — if the shared mount is unavailable, all file-based batch jobs fail
3. No deduplication: if a JSON file is processed twice (e.g., due to replay), duplicate wire transfers could be sent
4. JSON batch files with bank account/routing numbers stored in plaintext on shared filesystem — if filesystem is compromised, financial data exposed
5. `suppressions.xml` present — some Checkstyle violations are deliberately suppressed; may hide code quality issues
6. Gradle 4.8 / Java 8 / deprecated `compile` scope — same tech debt profile as NAM-bank-agent
7. jenkins-plugins embedded in repo — CI/CD coupled to repo lifecycle
8. No circuit-breaker observed for EventHub or Oracle operations in batch jobs
