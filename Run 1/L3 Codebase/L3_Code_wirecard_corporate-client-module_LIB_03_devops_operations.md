# DevOps / Operations — wirecard_corporate-client-module_LIB

## Build System
- **Tool**: Gradle 4.x via Gradle Wrapper (`gradlew` / `gradlew.bat`)
- **Gradle plugins** (same set as `check-agent`):
  - `io.spring.dependency-management:1.0.7.RELEASE`
  - `org.springframework.boot:1.5.13.RELEASE` (Spring Boot 1.5 — EOL)
  - `org.unbroken-dome.gitversion:0.9.10`
  - `org.unbroken-dome.test-sets:1.2.0`
  - `nebula.rpm:4.2.0`
  - `org.asciidoctor.convert:1.5.9.2`
  - `jacoco`, `org.sonarqube:2.7.1`
- **Multi-module**: `settings.gradle` defines: `corporate-client-module-auth-server-client`, `corporate-client-module-cmm-client`, `corporate-client-module-config`, `corporate-client-module-data`, `corporate-client-module-db-app`, `corporate-client-module-db-scripts`, `corporate-client-module-documentation`, `corporate-client-module-event-consumer`, `corporate-client-module-persistence`, `corporate-client-module-qa`, `corporate-client-module-rest-controller`, `corporate-client-module-service`
- **Nexus**: Internal Wirecard Nexus `http://d-issrepo-app01.wirecard.sys:8081/nexus` (**HTTP**)
- **Artefact**: RPM `wd-app-corporate-client-module`, deployed to AWS RPM repository

## CI/CD Pipeline
- **Platform**: GitLab CI (`gitlab-ci.yml`)
- **Stages**: `checkoutBranch` → `buildAndCheck` → `publish` → `update-release-bundle` → `merge-request-checks` → `tag-release`
- **Combined build**: `./gradlew clean assemble check sonarqube jacocoTestCoverageVerification` (build + checkstyle + tests + SonarQube in one stage)
- **Publish**: `./gradlew corporate-client-module-db-app:publish -Papp.mavenPublishRepo=aws buildRpm uploadRpmToAWS`
- **JaCoCo**: Minimum 90% line coverage enforced
- **SonarQube**: Project key `com.wirecard.issuing:corporate-client-module`

## Configuration Management
- `corporate-client-module-config/src/main/resources/application.yml` — base configuration
- Spring profiles: `wiremock` (WireMock for CCP/Brand Server/CMM), `global` (TLS truststore block for local builds)
- Production config injected via environment-specific overrides (not in this repo)
- **Hardcoded QA credentials**:
  - `ccp.client.password: aaaa1111`
  - `cmm.client.password: aaaa1111`
  - `iss-auth.client.password: aaaa1111`
  - Usernames: `callcenter_QA`, `callcenter_DEV`

## Deployment
- **Deployment target**: `d-ccm-app01.wirecard.sys` (Ansible inventory: DEV)
- **Deployment tool**: Ansible playbooks (`ansible/books/deploy.yml`)
- **Strategy**: Rolling update via `rolling_update` Ansible role (serial 1 — one-at-a-time)
- **Health check**: `GET /corporate-client-module/monitoring/health` → response `"UP"`
- **DB migration**: Run as separate step via `liquibase_migration` Ansible role on `dbupdater` host
- **Init.d service**: RPM installs a SysV init.d script; service name `corporate-client-module`
- **User**: `wd_app` (dedicated OS user/group)

## Observability
- Spring Boot Actuator on `/monitoring/*` (all endpoints exposed)
- Logstash JSON encoder for ELK integration (`net.logstash.logback:logstash-logback-encoder` runtime dependency)
- JaCoCo coverage reports
- SonarQube code quality analysis
- No distributed tracing configured

## Infrastructure Dependencies
| Dependency | Usage | Protocol | Notes |
|---|---|---|---|
| Oracle DB | Primary persistence | JDBC/TLS | |
| H2 (dev/test) | In-memory DB | JDBC | |
| ActiveMQ | EventHub | `tcp://localhost:61616` | No TLS in committed config |
| CCP (`q-horust-app02.wirecard.sys:9000`) | Fund reservation, virtual clients | HTTP | Not HTTPS in QA config |
| CMM (`d-cmm-app01:9000`) | Card creation | HTTP | Not HTTPS in committed config |
| Brand Server (`q-brands-app01.wirecard.sys:9000`) | Brand/card program data | HTTP | Not HTTPS |
| ISS Auth Server (`q-s2sauth-app02.wirecard.sys:9000`) | JWT key set + tech user mgmt | HTTP | Not HTTPS |
| Wirecard Nexus (`d-issrepo-app01.wirecard.sys:8081`) | Build dependencies | **HTTP** | Plaintext — supply chain risk |
| SMTP (`localhost:3025`) | Email | None/plaintext | Dev stub |

## Operational Risks
1. **Spring Boot 1.5.13 (EOL)** — same as `check-agent`. Highest severity risk.
2. **All upstream service calls over HTTP** (CCP, CMM, Brand Server, ISS Auth Server): Financial operations (fund reservation, card creation) may traverse unencrypted HTTP in QA environments that use default config. Must verify production overrides.
3. **Ansible inventories committed in repo** (`ansible/inventories/dev`, `prod`, `qa`, `test`): Hostnames are exposed. The `prod` inventory was not read — must verify it contains only hostnames, not credentials.
4. **`management.endpoint.health.show-details` not explicitly set** in this `application.yml` (defaults to `NEVER` in Spring Boot 1.5 Actuator) — but all endpoints are exposed, including `/info`, `/trace`, `/env`, which may reveal sensitive config.
5. **Rolling update with Ansible serial 1** — during deployment, at least one instance is down. For a financial system, this window requires careful scheduling.
6. **Jenkins job definitions committed**: `ansible/jenkins-job-defs.json` — contains Jenkins CI job definitions. These may include hardcoded paths, credentials, or environment details.
