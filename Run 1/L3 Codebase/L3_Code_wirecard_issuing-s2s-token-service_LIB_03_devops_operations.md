# DevOps / Operations View — wirecard_issuing-s2s-token-service_LIB

## Build System

- **Build tool**: Gradle with Gradle Wrapper (`gradlew`, `gradlew.bat`)
- **Java version**: Java 8 required (`requires('wd-jdk8', '1.8.0_141', GREATER | EQUAL)` in RPM spec) — **EOL for Oracle commercial use**
- **Spring Boot version**: 2.1.5.RELEASE — **EOL** (Spring Boot 2.x support ended November 2023)
- **Spring Cloud**: Greenwich.SR1 — **EOL** (Greenwich release train is no longer supported)
- **Multi-module Gradle project**:
  - `iss-authorization-server` — main Spring Boot application
  - `iss-authorization-server-it` — integration tests (Groovy/Spock)
- **Groovy/Spock tests**: Integration tests use Spock Framework with Spock Spring extension
- **RPM packaging**: `nebula.rpm` Gradle plugin builds a deployable Linux RPM package
- **Maven publishing**: `maven-publish` Gradle plugin for artifact publication to internal Maven repository

## CI/CD Pipeline

- **Jenkins**: `Jenkinsfile` at repository root — Jenkins pipeline for CI/CD (Gen-2/Wirecard era CI tooling)
- **Ansible**: `ansible/` directory with deployment playbooks (`books/deploy.yml`) and environment inventories (`dev`, `qa`, `test`, `prod`) — Ansible-based infrastructure deployment
- **Jenkins job definitions**: `ansible/jenkins-job-defs.json` — Jenkins job configuration as code
- **No GitHub Actions**: This repo uses Jenkins + Ansible (pre-GitHub Actions migration); GitHub Actions CI has not been added for this service
- **Deployment environments**: `ansible/inventories/` — dev, qa, test, prod environments defined

## Deployment Model

- **Artifact type**: RPM package (`wd-app-iss-authorization-server`) containing the Spring Boot fat JAR
- **OS**: Linux x86_64; systemd service unit (`src/rpm/iss-authorization-server.service`)
- **Deployment path**: `/usr/share/wd_app/iss-authorization-server/lib/` — Wirecard application directory convention
- **Service account**: `wd_app` user/group (created by RPM pre-install script if not present)
- **Configuration**: External configuration at `/etc/wd_app/iss-authorization-server/iss-authorization-server.conf` (symlinked; managed by Puppet)
- **No container**: RPM-based bare-metal or VM deployment; no Docker/Kubernetes
- **Version**: Inferred from Gradle `version` variable; RPM release `1`

## Runtime

- **Java 8** (JDK 1.8.0_141+)
- **Spring Boot 2.1.5** (EOL)
- **Oracle Database** via `ojdbc8:12.2.0.1.0`; DBCP2 connection pool
- **BouncyCastle**: `bcprov-jdk15on:1.56`, `bcpkix-jdk15on` (version resolved via dependency substitution)
- **Horus crypto**: `com.wirecard.horus:horus-crypto:8.35.0.RC3_20170904163352_8786975238bd` — Wirecard proprietary cryptography; 2017 release candidate
- **Logstash Logback encoder**: `net.logstash.logback:logstash-logback-encoder:5.0` — JSON structured logging to Logstash/ELK

## Secrets Management

- **Puppet**: Application configuration (including database credentials, signing keys) managed by Puppet at `/etc/wd_app/iss-authorization-server/` — Puppet-based secrets management (Wirecard infrastructure pattern)
- **No Azure Key Vault or HashiCorp Vault integration**: Gen-2 era uses Puppet/Ansible for secret distribution
- **Maven repository credentials**: Referenced via Gradle property (`project.property('mavenPublishRepo')`) — credentials externalized to Gradle properties file (not in source)
- **Private key storage**: JWT signing keys loaded from application configuration managed by Puppet; if not stored in an HSM, private key material is in Puppet-managed config files — must be reviewed for PCI DSS Requirement 3.6 compliance

## Observability

- **Structured JSON logging**: `logstash-logback-encoder:5.0` outputs JSON-formatted logs suitable for ELK stack (Elasticsearch/Logstash/Kibana) — Wirecard standard observability stack
- **Spring Boot Actuator**: Health endpoint via `spring-boot-starter-actuator` + `issuing-boot-actuator-utils`
- **JaCoCo**: Code coverage configured in Gradle build (`apply plugin: 'jacoco'`)
- **Monitoring integration**: Likely monitored via ELK stack with Logstash ingestion (standard Gen-2 Wirecard observability)

## Known EOL Runtimes and CVEs

- **Spring Boot 2.1.5.RELEASE**: EOL since 2021; no security patches. This is a security-critical service (OAuth 2.0 authorization server) running on an EOL framework — **critical risk**.
- **Spring Security OAuth 2.0**: The `spring-security-oauth2-autoconfigure` and `spring-security-oauth2` libraries are the legacy OAuth 2.0 implementation; replaced by Spring Authorization Server. EOL; no security patches.
- **Spring Cloud Greenwich.SR1**: EOL (December 2020).
- **Java 8**: Oracle Java 8 commercial support ended January 2019 (extended support available with subscription). OpenJDK 8 continues community support but LTS support is limited.
- **BouncyCastle 1.56**: CVE vulnerabilities present in 1.56 (released 2016). Current is 1.78+. Specific CVEs should be verified.
- **Horus crypto 8.35.0.RC3**: Release candidate from 2017; likely unmaintained post-Wirecard insolvency.
- **Logstash Logback encoder 5.0**: Old version; current is 7.x. Not a critical security risk but should be updated.
- **RPM deployment model**: The Wirecard RPM + Puppet + Ansible deployment model is incompatible with AKS/Gen-3 infrastructure. Migration to a containerized deployment is required for Gen-3 alignment.
- **No GitHub Actions**: The Jenkins + Ansible CI/CD pipeline is not integrated with the GitHub Actions standard established for other Onbe repos; migration needed.
