# 03 DevOps / Operations — wirecard_utilities_LIB

## Build
- **Tool**: Maven (Maven Wrapper `mvnw`)
- **Parent POM**: `com.parents:service-parent:9.0.0`
- **Java**: 1.8 (Java 8 source and target)
- **Packaging**: JAR (`com.wirecard.issuing:utilities:1.0.9-SNAPSHOT`)
- Two artifacts produced:
  - `utilities.jar` — production utilities (default)
  - `test-utilities.jar` — test support utilities (test-scope consumers only)
- `maven-jar-plugin 3.3.0` configured with manifest entries: vendor (`Onbe, Inc`), Java version, Maven version, built-by
- No assembly or fat-JAR; pure library JAR

## Deployment
Library JAR only. No standalone deployment. Published to the internal Maven repository (Onbe/Wirecard Nexus or GitHub Packages). Consumed as a compile-time dependency by other Wirecard Issuing services.

## Config Management
- No application configuration files; entirely stateless utility classes with static methods
- `.github/workflows/codeql.yml` — CodeQL static analysis on GitHub
- No CI pipeline beyond CodeQL (no build/publish workflow visible in `.github/workflows/`)
- Parent POM (`service-parent:9.0.0`) likely controls repository configuration and plugin management

## Observability
Not applicable for a library. No HTTP surface, no logging configuration, no metrics. Consumer services are responsible for observability.
- SLF4J (`slf4j-api 1.7.26`) is declared as a dependency; `PGPUtils` uses it for error logging — `LOG.error(exception.getMessage(), exception)` on encrypt/close failures

## Infrastructure Dependencies
- Internal Maven repository for parent POM (`com.parents:service-parent:9.0.0`) and artifact publication
- BouncyCastle (`bcpg-jdk15on:1.48`) for PGP operations — note: `1.48` is from 2012; current BouncyCastle is 1.78+; multiple CVEs in older versions
- Jackson Databind (`2.9.9`) — CVE-affected version; multiple known deserialization vulnerabilities in Jackson 2.9.x
- Hibernate Validator (`6.0.17.Final`) with Javax EL (`3.0.0`)
- Spring Core (`5.1.8.RELEASE`) — EOL; Spring 5 support ended December 2024

## Operational Risks
- **BouncyCastle 1.48** (2012): multiple known CVEs in PGP and cryptographic operations; this is the version used for `PGPUtils` encrypt/decrypt — **critical risk** for a library handling payment file encryption
- **Jackson 2.9.9**: multiple known deserialization CVEs (CVE-2019-12384, CVE-2019-14379, etc.); `JsonUtils.fromJson()` is a generic deserializer — **high risk** if input is untrusted
- **Spring Core 5.1.8.RELEASE**: EOL; `spring-core` is a transitive dependency in this context but still a version management concern
- **Java 8**: approaching end of commercial support timelines depending on JDK vendor; should be updated to Java 17+ LTS
- Snapshot version (`1.0.9-SNAPSHOT`) in production use is a bad practice; library should be released with a fixed version

## CI/CD
- CodeQL GitHub Actions workflow (`.github/workflows/codeql.yml`) — static analysis only
- No build or publish GitHub Actions workflow visible; publication likely relies on manual Maven command or the parent POM CI
- Dependabot configured (`.github/dependabot.yml`) for dependency alerts
- No automated version bump or release pipeline visible
