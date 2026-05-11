# DevOps / Operations View — j-integra-j2com_LIB

## Build
- **Build system**: Maven, single-module JAR.
- **Maven wrapper**: `mvnw` / `mvnw.cmd` present.
- **Parent POM**: `com.citi.prepaid.service:service-parent:8`.
- **Java compiler**: source/target 1.6 — Java 6.
- **Artifact name**: `scriptmigration` (misleading name vs repo name `j-integra-j2com`). Version: `1.0.3-SNAPSHOT`.
- **Build output**: `j2com-service/` directory with `jars/`, `bin/`, `conf/` subdirectories assembled by maven-antrun-plugin.
- **Assembly**: All dependency JARs copied to `target/j2com-service/jars/`; `src/bin/` and `src/conf/` copied alongside.
- **GitLab CI**: `.gitlab-ci.yml` present; Jenkinsfile present.
- **SCM**: `gitlab.com/northlane/development/application-development/libraries/j-integra-j2com.git`.

## Deployment
- **Deployment model**: The assembled `j2com-service/` directory is deployed to a Windows server.
- **Windows service**: `src/bin/jIntegraService.exe` registers and runs the Java J2COM bridge as a Windows NT service via `service.bat`.
- **Service configuration**: `src/conf/log4j.xml` and `src/conf/timesync.properties` are deployed to `conf/`.
- Requires `D:/c-base/config/` directory structure for ELF certificates and properties.
- Requires TIBCO JMS (tibjms.jar, tibcrypt.jar) connectivity to ELF servers.

## Configuration Management
- `DirectorySettings.xml` loaded from classpath at JVM startup (`JavaCOMConfiguration` static initialiser) — configures Director service registry client and DBCP factory.
- `src/conf/timesync.properties` — lists ELF time server hostnames.
- `src/conf/log4j.xml` — logging configuration including ELF JMS endpoint, SSL cert paths, and email address.
- All configuration files must be present at runtime in the `conf/` directory relative to the service working directory.
- No secrets manager or externalised configuration.

## Observability
- Log4j 1.2.15 with a DatedFileAppender (5-minute cycle rolling).
- ELF JMS async appender with SSL, buffer of 2500 messages.
- File fallback appender if ELF JMS is unavailable.
- Console (stdout) appender at DEBUG level.
- Log path set via system property `${log_path}`.
- No metrics, health endpoint, or APM integration.

## Infrastructure Dependencies
| Dependency | Type | Notes |
|-----------|------|-------|
| Director service registry | Service discovery | Resolves all XML-RPC service endpoints |
| ecount XML-RPC services | HTTP services | All platform services (crypto, profile, member, etc.) |
| TIBCO JMS ELF server | JMS / SSL | `csdesbdev.nam.nsroot.net:7243` (dev); prod server TBD |
| ELF time servers | NTP | `cccaelm10p.nam.nsroot.net` etc. |
| Windows NT service host | OS | Windows only (jIntegraService.exe) |
| Filesystem (`d:\c-base\`) | Configuration | ELF certs, properties |
| jintegra.jar 2.12 | COM bridge | Commercial JAR in `src/lib/` |

## Operational Risks
1. Windows-only deployment (`jIntegraService.exe`) — cannot be containerised or run on Linux.
2. Java 6 compiler target — severely EOL; limited security patches available.
3. jintegra.jar 2.12 is a commercial binary in `src/lib/` — unknown license status post-acquisition; updates not possible without vendor engagement.
4. Static initialiser in `JavaCOMConfiguration` loads Spring context at class-load time — a failure in `DirectorySettings.xml` loading will crash the entire JVM with no recovery path.
5. ELF logging configuration references Citi-era email (`shomit.sahdev@citi.com`) and Citi internal hostnames — these are broken post-acquisition and must be updated.
6. `testJ2COM-Service.vbs` in `src/bin/` is a VBScript test file committed to source — its content and any embedded credentials should be audited.

## CI/CD
- **Jenkinsfile**: Simple pipeline — feature branch builds (`mvnw clean install`), master branch deploys (`mvnw clean deploy`). Tests are skipped (`-Dmaven.test.skip=true`). Runs on Windows agent (`bat` commands).
- **GitHub Actions**: `.github/workflows/codeql.yml` — CodeQL.
- **Dependabot**: `.github/dependabot.yml`.
- **GitLab CI**: `.gitlab-ci.yml` present.
- Default branch: `master`.
- Tests are always skipped in CI — no automated test execution.
