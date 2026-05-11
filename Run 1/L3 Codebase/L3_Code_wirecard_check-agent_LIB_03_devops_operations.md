# DevOps / Operations — wirecard_check-agent_LIB

## Build System
- **Tool**: Gradle 4.x via Gradle Wrapper (`gradlew` / `gradlew.bat`)
- **Gradle plugins**:
  - `io.spring.dependency-management:1.0.7.RELEASE`
  - `org.springframework.boot:1.5.13.RELEASE` (Spring Boot 1.5.13 — EOL as of August 2019)
  - `org.unbroken-dome.gitversion:0.9.10` — version from Git tags
  - `org.unbroken-dome.test-sets:1.2.0`
  - `nebula.rpm:4.2.0` — RPM packaging
  - `jacoco`, `org.sonarqube:2.7.1`
- **Multi-module**: `settings.gradle` defines submodules: `check-agent-batch`, `check-agent-config`, `check-agent-core`, `check-agent-data`, `check-agent-db-app`, `check-agent-db-scripts`, `check-agent-documentation`, `check-agent-event-consumer`, `check-agent-performance`, `check-agent-persistence`, `check-agent-qa`, `check-agent-rest-controller`
- **Java version**: `jdk8` (GitLab CI image `gradle:4.8-jdk8`)
- **Maven repository**: Internal Wirecard Nexus `http://d-issrepo-app01.wirecard.sys:8081/nexus/content/groups/public` (HTTP, not HTTPS)
- **Artefact publication**: RPM (via `nebula.rpm`) uploaded to AWS (`uploadRpmToAWS` task via `curl`)

## CI/CD Pipeline
- **Platform**: GitLab CI (`gitlab-ci.yml`)
- **Stages**: `checkoutBranch` → `build` → `checkstyle` → `test` → `publish` → `update-release-bundle` → `merge-request-checks` → `tag-release`
- **Docker image**: `gradle:4.8-jdk8`
- **Publish**: `./gradlew check-agent-db-app:publish -Papp.mavenPublishRepo=aws buildRpm uploadRpmToAWS`
- **Quality gates**: Checkstyle (`checkstyleMain`, `checkstyleTest`) and JaCoCo coverage verification (`jacocoTestCoverageVerification`; minimum 90% line coverage)
- **SonarQube**: `sonarqube` plugin configured; project key `com.wirecard.issuing:check-agent`
- **Tag release**: Runs `./gradlew tagRelease` on `master` branch only
- **Merge request checks**: `./gradlew checkIfArtifactExists` — verifies artefact version does not already exist before merge

## Configuration Management
- `check-agent-config/src/main/resources/application.yml` — base configuration (H2/in-memory defaults for local dev)
- Spring profiles: `wiremock` (uses WireMock for CCP/Brand server), `eventhubmock` (in-memory EventHub)
- Production configuration is expected to be injected via environment-specific config files or a Spring Cloud Config Server (not defined in this repo)
- **Hardcoded QA credentials** in `application.yml`: `ccp.client.password: aaaa1111`, `iss-auth-server.url` pointing to `wirecard.sys` domain — these are QA defaults that MUST be overridden in production

## Observability
- **Logging**: SLF4J + Logback (standard Spring Boot); logstash-logback-encoder (`net.logstash.logback:logstash-logback-encoder`) is a runtime dependency — structured JSON logging for ELK stack integration.
- **Actuator**: Spring Boot Actuator enabled; management endpoints exposed on `/monitoring/*` with `show-details: ALWAYS` — exposes full health detail including database status.
- **JaCoCo**: Code coverage reporting (HTML + XML); minimum 90% threshold.
- **SonarQube**: Configured for quality analysis.
- **JMeter performance tests**: `check-agent-performance/src/test/resources/*.jmx` — JMeter test plans for `CheckAgent_APIs` and `CheckAgent_CheckStatusUpdatedEvent`.
- **Email alerts**: `EmailServiceImpl` sends operational alerts to `emails.job-executions.send-to` addresses.
- **EhCache**: `ehcache3.xml` configuration for in-process caching.

## Infrastructure Dependencies
| Dependency | Usage | Notes |
|---|---|---|
| Oracle DB | Primary persistence | OJDBC8 driver required at runtime |
| H2 (in-memory) | Dev/test only | Included as `runtime` dependency |
| ActiveMQ | EventHub messaging | `tcp://localhost:61616` in dev; SSL URL expected in production |
| Wirecard CCP (`q-horust-app02.wirecard.sys`) | Fund reservation API | HTTP (not HTTPS) in QA config |
| Wirecard Brand Server (`q-brands-app01.wirecard.sys`) | Check template config | HTTP in QA config |
| Wirecard ISS Auth Server (`q-s2sauth-app02.wirecard.sys`) | JWT key set | HTTP in QA config |
| Wirecard Nexus (`d-issrepo-app01.wirecard.sys:8081`) | Maven/Gradle dependency resolution | **HTTP (not HTTPS)** — supply chain risk |
| SMTP server (`localhost:4025`) | Email notifications | Dev/test stub; must be overridden in production |

## Operational Risks
1. **Spring Boot 1.5.13 (EOL August 2019)**: This is a critically outdated framework version with unpatched CVEs. This is the highest-priority risk in this repository.
2. **Nexus over HTTP**: `http://d-issrepo-app01.wirecard.sys:8081/nexus` — dependency resolution over HTTP is a supply-chain attack vector (PCI DSS Req 6.3.3).
3. **CCP/Brand/Auth server calls over HTTP in QA config**: If QA config leaks to production, cardholder fund operations would traverse unencrypted HTTP.
4. **`management.endpoint.health.show-details: ALWAYS`**: Exposes full health details including database connection status to anyone who can reach the `/monitoring/health` endpoint. This could reveal internal infrastructure details.
5. **Hardcoded QA password `aaaa1111`** in `application.yml` — must be overridden via secure config injection in all non-dev environments.
6. **No deployment manifests in this repo**: Deployment topology, Ansible/Kubernetes configs, and environment-specific application configs are not in this repository, making it difficult to audit the production configuration.
