# DevOps / Operations Analysis — ivrintegration_API

## 1. Technology Stack

| Component | Version / Details |
|---|---|
| Language | Java 1.8 (pom.xml line 48: `<java.version>1.8</java.version>`) |
| Framework | Spring 2.5.6 (pom.xml line 69: `spring.version=2.5.6`) |
| Web services | Apache Axis 1.x (SOAP / JAX-RPC via `ServletEndpointSupport`) |
| Build tool | Maven (mvnw wrapper present) |
| Logging | Log4j 1.2.17 (`log4j.version=1.2.15` in pom.xml line 57; `1.2.17` in properties) + JSON event layout |
| Packaging | WAR file deployed to servlet container |
| Parent POM | `ecount-parent` version 6 |

## 2. CI/CD Pipeline

### GitLab CI
File: `.github/workflows/codeql.yml` (CodeQL SAST only):
```yaml
name: "CodeQL"
on:
  workflow_dispatch:
  schedule:
    - cron: ...
jobs:
  analyze:
    uses: Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main
```

### GitLab Pipeline (Legacy)
The Maven POM (`pom.xml`) references GitLab SCM at `gitlab.com/northlane/...` with a Nexus repository (`d-na-stk01.nam.wirecard.sys:8080`) for artifact deployment:
```xml
<url>dav:http://d-na-stk01.nam.wirecard.sys:8080/nexus/content/repositories/releases</url>
```
This uses WebDAV (`wagon-webdav-jackrabbit`) to deploy to an on-premises Nexus. The hostname `d-na-stk01.nam.wirecard.sys` indicates this is a **Northlane/Wirecard legacy on-premises build infrastructure**. CI scripts were templated from `northlane/development/.../ci-templates`.

## 3. Build Configuration

**Root POM** (`pom.xml`) — multi-module Maven build:
- Module: `precheck-impl` — business logic and XML-RPC client layer
- Module: `precheck-ws` — SOAP web service layer (WAR packaging)

Maven build commands:
```bash
mvn clean install -Dmaven.test.skip=true   # build without tests
mvn deploy                                  # deploy to Nexus
```

Maven wrapper (`mvnw` / `mvnw.cmd`) is present. Settings are in `.mvn/wrapper/settings.xml` (internal Nexus mirror configuration).

## 4. Deployment

### Deployment Target
The service is packaged as a WAR (`precheck-ws` module) and deployed to a **servlet container (Tomcat or equivalent)**. The `web.xml` (`precheck-ws/src/main/webapp/WEB-INF/web.xml`) configures Apache Axis servlet. The `server-config.wsdd` (`precheck-ws/src/main/webapp/WEB-INF/server-config.wsdd`) defines SOAP service endpoints.

### Protocol
`.gitlab-ci.yml` (note: this is the legacy GitLab CI config at repo root, not the newer GitHub Actions config) specifies:
```yaml
PROJECT_SERVICE_PROTO: http
PROJECT_SERVICE_DEV_PORT: 9325
PROJECT_SERVICE_QA_PORT: 9325
PROJECT_SERVICE_URI: /ivrws/services/AccountTransactionInquiryServices?wsdl
DEV_SERVICE_HOSTS: d-na-app02
QA_SERVICE_HOSTS: q-na-app01 q-na-app02
```
**Critical Finding**: The service protocol is `http` (not `https`). While TLS termination may occur at a load balancer upstream, the explicit `http` protocol for the health check URI is a red flag. All cardholder data (DDA numbers, authorization codes) transmitted between the IVR system and this service must be over TLS per PCI DSS Requirement 4.2. **This must be verified** — if there is no TLS at the load balancer layer, this is a Critical PCI DSS finding.

### Deployment Hosts
- Dev: `d-na-app02` (on-premises Wirecard/Northlane infrastructure)
- QA: `q-na-app01`, `q-na-app02`
- Prod: Not specified in this repo's CI config — likely in a separate deployment repo.

## 5. Configuration Files

### `ExternalServicesContext.xml` (precheck-ws/src/main/resources/)
Spring context file that wires external service clients (XML-RPC). Loaded at application startup.

### `DirectorySettings.xml` (precheck-ws/src/main/resources/)
Service registry configuration. Points the Director client to the service discovery endpoint.

### `precheck-implContext.xml` (precheck-ws/src/main/resources/)
Spring context for the precheck implementation layer beans.

### `contentValidation.xml` (precheck-ws/src/main/resources/)
Defines validation bean rules for all SOAP input parameters (applicationId allowed values, DDA format, etc.).

### `artifactInfo.properties` (precheck-ws/src/main/resources-filtered/)
Maven-filtered resource file — populated at build time with artifact version info.

## 6. Logging

Log4j 1.2.17 is used (`pom.xml` line 56). Log4j 1.x reached End of Life on August 5, 2015. **Log4j 1.x has multiple known CVEs including CVE-2019-17571 (SocketServer RCE) and CVE-2022-23302 (JMSSink deserialization RCE)**. Additionally, the Log4Shell vulnerability (CVE-2021-44228) affects Log4j 2.x, not 1.x, but Log4j 1.x has its own critical vulnerabilities.

**Recommendation**: Migrate to SLF4J + Logback or Log4j 2.x (with log4j 2.17.2+) immediately.

Every method in `CheckManagementWebServiceImpl.java` logs all input parameters via `logger.info()`:
```java
logger.info("applicationId="+applicationId+",checkId="+checkId+
    ",tellerId="+tellerId+",payeeId="+payeeId+",adminId="+adminId+
    ",assignDDA="+assignDDA+",ani="+ani);
```
This means **DDA numbers, ANI (phone numbers), and authorization codes are written to application logs in plaintext**. If logs are not encrypted at rest and access-controlled, this is a PCI DSS Requirement 3.3 / Requirement 10 violation.

## 7. Artifact Repository

Deployment via WebDAV to Nexus at `d-na-stk01.nam.wirecard.sys`. This is legacy Wirecard/Northlane infrastructure. Dependency on this infrastructure for builds creates a single point of failure and may no longer be operational. The Maven wrapper settings in `.mvn/wrapper/settings.xml` likely configure credentials for this Nexus instance.

## 8. Dependency Versions — Vulnerability Summary

| Dependency | Version | Risk |
|---|---|---|
| Spring | 2.5.6 | **EOL — released 2008, no patches since 2009** |
| Log4j | 1.2.17 | **EOL — CVEs including CVE-2019-17571** |
| Apache Axis | 1.4 | **EOL — multiple CVEs including SSRF** |
| Java | 1.8 | Check JRE version for latest patches |
| commons-lang | 2.1 | Very old — upgrade to commons-lang3 |

The entire stack (Spring 2.5.6, Axis 1.4, Log4j 1.2.x) is critically outdated and EOL. This service represents extreme technical debt from a security standpoint.
