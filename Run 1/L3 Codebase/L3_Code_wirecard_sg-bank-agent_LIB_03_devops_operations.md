# DevOps / Operations Report — wirecard_sg-bank-agent_LIB

## Build System

**Gradle** with Spring Boot 1.5.13.RELEASE and a multi-module project structure:
- `sg-bank-agent-config`: Application configuration and YAML.
- `sg-bank-agent-data`: Domain model and data transfer objects.
- `sg-bank-agent-persistence`: JPA repositories and database access.
- `sg-bank-agent-service`: Business services and validators.
- `sg-bank-agent-batch`: Spring Batch job configuration and processors.
- `sg-bank-agent-event-consumer`: ActiveMQ event consumer.
- `sg-bank-agent-db-app`: Database migration application.
- `sg-bank-agent-db-scripts`: Liquibase migration scripts.
- `sg-bank-agent-qa`: Integration test module.

## CI/CD Pipeline

**Jenkins** via `Jenkinsfile` with Gradle-based build and Ansible-based deployment.

Pipeline stages:
1. **Build**: `./gradlew cleanVersion clean assemble` — creates JAR artifacts.
2. **PrepareVersion**: Reads version from `build/version.properties`.
3. **Checkstyle**: `./gradlew checkstyleMain checkstyleTest`.
4. **Test**: `./gradlew test jacocoTestCoverageVerification` — enforces 90% code coverage minimum.
5. **Package** (master/release only): `./gradlew buildRpm` — creates RPM packages.
6. **Publish** (master/release only): Publishes RPM to Nexus and Maven artifacts to Nexus.
7. **Deploy** (master/release only): Ansible playbooks to deploy batch and consumer services.

Target environments: `dev` (master branch) and `qa` (release branches).

## Deployment Model

**RPM deployment to on-premises Linux servers** via Ansible playbooks. Two deployable components:
- `deploy-consumer.yml`: The event consumer (ActiveMQ message listener).
- `deploy-batch.yml`: The Spring Batch job runner.

Ansible inventory for `dev`, `qa`, `prod`, and `test` environments.

## Runtime

- **Java**: Not explicitly set in `build.gradle`; likely Java 8 given Spring Boot 1.5.13.RELEASE.
- **Spring Boot 1.5.13.RELEASE**: EOL — reached end of open-source support in August 2019.
- **Spring Cloud Finchley.RELEASE**: EOL — reached end of support in 2020.
- **Spring Integration SFTP 5.1.4**: Relatively modern.
- **ActiveMQ (version from Spring Cloud Finchley BOM)**: Older version.
- **Oracle OJDBC6 (11.2.0.2.0)**: Oracle JDBC driver for Oracle 11g — EOL.
- **H2 1.4.192**: EOL — current H2 is 2.x.
- **Hibernate 5.3.7.Final**: Relatively stable version.
- **BouncyCastle bcpg-jdk15on:1.48**: EOL — current is 1.78+. Multiple CVEs in old BouncyCastle.
- **jcraft/jsch:0.1.55**: Old JSch SFTP library — known CVEs in older versions.

## Secrets Management

**CRITICAL: Secrets hardcoded in repository files.**

| Secret | File | Line |
|--------|------|------|
| CIMB SFTP RSA private key (full key material) | `sg-bank-agent-config/src/main/resources/application.yml` | 34–61 |
| PGP passphrase `wirecard` | `sg-bank-agent-config/src/main/resources/application.yml` | 154 |
| Nexus DEV password `acmng` | `gradle.properties` | 10, 14 |
| Nexus QA password `acmng` | `gradle.properties` | 17, 21 |
| Nexus release password `dwil15?` | `gradle.properties` | 22, 26 |
| AWS DEV password `admin123` | `gradle.properties` | 13 |
| AWS access key `[REDACTED — rotate immediately]` | `gradle.properties` | 31 |
| AWS secret key `[REDACTED — rotate immediately]` | `gradle.properties` | 32 |
| Sonar admin password `admin` | `gradle.properties` | 35 |

## Observability

- Logstash Logback encoder (`net.logstash.logback:logstash-logback-encoder:5.0`) for structured JSON logging.
- Spring Boot Actuator health endpoint exposed at `/sg-bank-agent/monitoring` with **all endpoints exposed** (`exposure.include: '*'`) and **health details always shown** (`show-details: ALWAYS`) — without any authentication.
- JaCoCo coverage reporting with 90% minimum threshold.

## EOL Runtimes

Spring Boot 1.5.x, Spring Cloud Finchley, Oracle OJDBC6, H2 1.4.x, BouncyCastle 1.48, JSch 0.1.55 — all EOL with known CVEs. This service is significantly behind on dependency maintenance.
