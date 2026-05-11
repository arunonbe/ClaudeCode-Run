# DevOps / Operations — wirecard_funds-transfer-coordinator_LIB

## Build System
- **Tool**: Gradle 4.8 (wrapper), Java 8
- **Spring Boot**: 2.0.7.RELEASE (via dependency-management BOM)
- **Spring Cloud**: Finchley.RELEASE
- **Modules**: funds-transfer-coordinator-config, -data, -service, -batch, -rest, -qa, -db-scripts, -db-app, -check-agent-client, -documentation
- **RPM packaging**: nebula.rpm plugin; `wd-app-funds-transfer-coordinator-batch` package name; deployed to `/usr/share/wd_app/`
- **Artifact repository**: Nexus (`d-issrepo-app01.wirecard.sys:8081`); AWS S3 bucket (`poc-wd-artefacts.s3-eu-central-1.amazonaws.com`) for AWS publish

## CI/CD Pipeline (GitLab CI)
| Stage | Description |
|---|---|
| checkoutBranch | Git checkout to correct branch ref |
| build | `./gradlew clean cleanVersion assemble` |
| checkstyle | `./gradlew checkstyleMain checkstyleTest` |
| test | `./gradlew test jacocoTestCoverageVerification` (90% minimum coverage enforced) |
| publish | Publishes db-app jar and documentation to AWS; builds and uploads RPM |
| update-release-bundle | Runs `updateReleaseBundle` on master/development branches |
| merge-request-checks | Checks artifact does not already exist before publishing |
| tag-release | Tags release on master |

- CI runner image: `gradle:4.8-jdk8`
- Jacoco test reports: `funds-transfer-coordinator-qa/build/test-results/test/TEST-*.xml`

## Deployment
- **Method**: RPM package deployed via rolling update Ansible playbook (pattern consistent with NAM/wire-transfer-agent siblings)
- **Target**: `batchserver` host group
- **Service name**: `wire-transfer-agent-batch` (referenced in sibling ansible playbooks; FTC follows same pattern)
- **Health check**: `/funds-transfer-coordinator/monitoring/health`
- **Port**: 9000

## Configuration Management
- Spring profiles: default (H2/dev), `wiremock` (WireMock stubs), `eventhubmock` (no EventHub)
- All sensitive values (DB credentials, ActiveMQ credentials, CCP password) use placeholder values in source YAML — must be supplied at runtime via environment variables or Puppet
- `global.datasource.truststore.content` holds Base64-encoded JKS at runtime
- Nexus credentials passed via Gradle properties file (not in source)

## Observability
- **Health endpoint**: `/funds-transfer-coordinator/monitoring/health` — `ALWAYS` show details
- **Actuator**: all endpoints exposed at `/monitoring/*`
- **Logging**: SLF4J/Logback; structured JSON via `logstash-logback-encoder:5.0`
- **SonarQube**: project key `com.wirecard.issuing:funds-transfer-coordinator`; Jacoco integration
- **Circuit-breaker health**: Resilience4j registers circuit-breaker state in Spring Boot Actuator health endpoint
- **No distributed tracing** observed (performance-tracing-library not in dependency list)

## Infrastructure Dependencies
| Dependency | Purpose | Notes |
|---|---|---|
| Oracle DB | Primary data store | ojdbc8; two-schema; TLS |
| ActiveMQ (EventHub) | Inbound events and outbound event publishing | `tcp://localhost:61616` dev default |
| Quartz (JDBC) | Clustered job scheduling | Uses same Oracle DB |
| CCP API | Reserve/confirm/cancel money; A2A transfers | `q-horust-app02.wirecard.sys` |
| Check-Agent API | Cheque issuance | `d-chkagt-app01.wirecard.sys` |
| Brand-Server API | Financial institution lookup | `q-brands-app01.wirecard.sys` |
| ISS Auth Server (OAuth2) | JWT key set for resource-server token validation | `q-s2sauth-app02.wirecard.sys` |
| SMTP | Past-due invoice emails | `localhost:4025` dev default |
| Nexus | Artifact repository | `d-issrepo-app01.wirecard.sys:8081` |
| AWS S3 | Release artifact storage | `poc-wd-artefacts.s3-eu-central-1.amazonaws.com` |

## Operational Risks
1. Spring Boot 2.0.7 is end-of-life; no longer receives security patches
2. Gradle 4.8 / `gradle:4.8-jdk8` CI image is significantly outdated
3. `h2-console` enabled in base application.yml — accidental production exposure risk
4. ActiveMQ credentials `local/local` and CCP password `[REDACTED — rotate immediately]` in source YAML — require positive proof of environment-specific override
5. Quartz cluster check-in interval 10 s with misfire threshold 60 s — misconfigured cluster node could fire duplicate transfers
6. No dead-letter queue configuration observed for failed EventHub messages — silent event loss on processing failure
7. REQUEST/RESPONSE columns in TRANSFER_REQUEST_LOG are VARCHAR(2048) — truncation risk for large API responses
