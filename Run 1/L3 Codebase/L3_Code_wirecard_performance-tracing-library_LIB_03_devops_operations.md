# DevOps / Operations — wirecard_performance-tracing-library_LIB

## Build System
- **Tool**: Gradle (wrapper), Java 8
- **Spring Boot BOM**: 2.0.7.RELEASE
- **Dependencies**: `spring-boot-starter-web`, `spring-boot-starter-aop`, `lombok:1.18.4`, `jackson-dataformat-xml:2.9.9`
- **Single module**: flat project (not multi-module)
- **Artifact ID**: `performance-tracing-library`
- **Group**: implicitly `com.wirecard.issuing` (from Nexus publish path and README dependency string)

## CI/CD Pipeline (GitLab CI — .gitlab-ci.yml)
Same GitLab CI template as sibling repos:
| Stage | Description |
|---|---|
| checkoutBranch | Git checkout |
| build | `./gradlew clean cleanVersion assemble` |
| checkstyle | `./gradlew checkstyleMain checkstyleTest` |
| test | `./gradlew test jacocoTestCoverageVerification` |
| publish | Publishes to AWS S3 (`s3://poc-wd-artefacts.s3-eu-central-1.amazonaws.com`) or Nexus |
| update-release-bundle | master/development |
| merge-request-checks | Merge request pre-check |
| tag-release | master |

## Publishing
- **Nexus** (non-AWS): `project.property("app.mavenPublishRepo.${profile}.url")` — dev/qa Nexus
- **AWS S3**: `s3://poc-wd-artefacts.s3-eu-central-1.amazonaws.com` using `AwsImAuthentication` (IAM instance role)
- Versioning: `versioning.gradle` / `release.gradle` scripts; latest tag `performance-tracing-library-1.6.0`

## Configuration Management
- Properties prefix `performance.tracing.*` consumed by applications
- No environment-specific configuration for the library itself
- `lombok.config` present (suppresses Lombok warnings)

## Observability
- Library is itself an observability tool — no additional monitoring of the library itself
- Published as a JAR; no runtime health endpoint
- SonarQube integration assumed via GitLab CI but not explicitly configured in `build.gradle` (unlike FTC/wire-transfer-agent)

## Infrastructure Dependencies
| Dependency | Purpose | Notes |
|---|---|---|
| Nexus `d-issrepo-app01.wirecard.sys` | Artifact publication/consumption | HTTP (not HTTPS) |
| AWS S3 `poc-wd-artefacts` | Release artifact storage | IAM authentication |

## Release Management
- `release-and-publish.sh` shell script for manual release publishing
- `versioning.gradle` + `release.gradle` for version management
- Latest released version: `1.6.0` (from git tag `performance-tracing-library-1.6.0`)

## Operational Risks
1. Spring Boot BOM 2.0.7 — EOL; inherited by all consumers
2. HTTP Nexus URL — artifact download integrity not protected by TLS
3. `release-and-publish.sh` shell script for publishing — manual process prone to human error
4. No explicit checkstyle configuration file found (unlike FTC which has `checkstyle.xml`) — code style enforcement may be weaker
5. `configurations.all` block validates no project-to-project dependencies — good guard against accidental coupling; no operational risk
