# actimize-kyc_LIB — DevOps & Operations View

## Build & Packaging

### Build Tool: Apache Ant + Apache XmlBeans 2.5.0
The sole build file is `build.xml` (repository root). It contains a single Ant target named `compile`:

```xml
<!-- build.xml, lines 5–19 -->
<target name="compile">
  <taskdef name="xmlbean"
    classname="org.apache.xmlbeans.impl.tool.XMLBean"
    classpath="D:\c-base\src\services\core\actimizeKYC\xmlbeans\xmlbeans-2.5.0\lib\xbean.jar"/>
  <xmlbean
    schema="D:\c-base\src\services\core\actimizeKYC\KycCheckService.xsd"
    destfile="KycCheckServiceXmlBeans.jar"
    classpath=".../xbean.jar:.../jsr173_1.0_api.jar"/>
</target>
```

Key observations:
- **Hardcoded absolute Windows paths** (`D:\c-base\...`): The build is not portable. It will only work on the exact developer workstation where `D:\c-base\src\services\core\actimizeKYC\` exists.
- **No parameterisation**: No property files, no environment variables, no path abstraction.
- **XmlBeans version**: 2.5.0, released circa 2008. This version is EOL and not maintained.
- **Output**: A single JAR file `KycCheckServiceXmlBeans.jar` produced in the project root.
- **No test target**: There are no unit tests, no test compile target, no validation target.
- **No clean target**: No `clean` target to remove stale outputs.

### XmlBeans Toolchain
The XmlBeans 2.5.0 distribution is vendored in-repository at `xmlbeans/xmlbeans-2.5.0/`. This is a full local copy including binaries (`bin/scomp`, `bin/scomp.cmd`), documentation, and library JARs. The JARs themselves are not tracked in source — only the scripts and docs are visible in the glob (the `.jar` files in `lib/` are part of the pack file). The vendored distribution is used only to compile the XSD into Java types.

### Maven Distribution
Post-build, the JAR is manually deployed to an internal Maven repository via commands documented in `deploy kycbean jar to repository.txt`:

```
mvn deploy:deploy-file \
  -Durl=http://ecsvn.office.ecount.com:8080/mvn/release \
  -DrepositoryId=ecount.release \
  -Dfile=KycCheckServiceXmlBeans.jar \
  -DgroupId=com.ecount.actimizekyc \
  -DartifactId=actimizekyc \
  -Dversion=1.0 \
  -Dpackaging=jar
```

Maven repo URL: `http://ecsvn.office.ecount.com:8080/mvn/release` (plain HTTP — no TLS on the artifact repository). Consuming projects reference the artifact as:

```xml
<dependency>
  <groupId>actimizekyc</groupId>
  <artifactId>actimizekyc</artifactId>
  <version>1.0</version>
</dependency>
```

Note: The `groupId` in the dependency snippet (`actimizekyc`) differs from the one in the `deploy` command (`com.ecount.actimizekyc`) — this is an inconsistency in the documented deployment instructions.

### Compiled Artifact in Repository
Both `KycCheckServiceXmlBeans.jar` (root) and `artifacts/KycCheckServiceXmlBeans.jar` are binary JARs committed directly to Git. This is a deviation from standard source-control practices and makes it impossible to audit the compiled code without decompiling.

## Deployment

The library is not independently deployed as a service. Deployment consists of:

1. **Build**: Run `ant compile` on the developer workstation with the hardcoded `D:\c-base\...` path available.
2. **Publish to Maven repo**: Run `mvn deploy:deploy-file` as documented in `deploy kycbean jar to repository.txt` (lines 2–9).
3. **Certificate registration**: For each environment, import `artifacts/<ENV> certificate/servercert.bin` into the JVM `cacerts` truststore using `keytool -import` (documented in `artifacts/keytool security cer add.txt`).
4. **Database seed**: Execute the appropriate `kyc_profile_<ENV>_NA.sql` against the `ecountcore` SQL Server database to register the KYC endpoint URL and credentials.
5. **Consuming application**: The consuming application includes the Maven dependency and calls the service via the compiled XmlBeans types.

There is no automated deployment pipeline, no containerisation, no infrastructure-as-code, and no configuration management tooling.

### Environment Matrix

| Environment | KYC Endpoint | DB Script |
|---|---|---|
| SIT | `isgswcse46i.nam.nsroot.net:8181` | `kyc_profile_SIT_NA.sql` |
| UAT | `icgmwcos1u.nam.nsroot.net:8181` | `kyc_profile_UAT_NA.sql` |
| PROD | `icgmwcos1p.nam.nsroot.net:8181` | `kyc_profile_PROD_NA.sql` |

## Configuration Management

All configuration is manual and environment-specific. No configuration management system (Chef, Ansible, Terraform, Kubernetes ConfigMaps) is present.

**Configuration surface:**
1. `ecountcore.kyc_profile` database table — holds endpoint URL and credentials per country profile.
2. JVM `cacerts` truststore — holds server certificates for TLS validation.
3. Maven `settings.xml` (not in repo) — required for `repositoryId=ecount.release` credential resolution.

**Problems identified:**
- No templating or environment-variable substitution for the SQL scripts.
- `secure_code` is a hardcoded plaintext string in all SQL files (`Prepaid1`).
- JVM path (`D:\c-base\opt\jdk1.6.0_16\jre\lib\security`) is hardcoded in the keytool instructions.
- Default truststore password (`changeit`) is used — standard but well-known.
- Maven repo URL uses plain HTTP (`http://ecsvn.office.ecount.com:8080/mvn/release`).

## Observability

**Logging**: None. The repository contains no logging framework configuration, no log4j/SLF4J setup, no metrics instrumentation, and no tracing identifiers.

**Monitoring**: No health checks, no alerts, no dashboards.

**Alerting**: None.

The library provides only compiled data types. All observability responsibility falls on the consuming application. There is no contract for structured logging of KYC check outcomes, failure counts, or latency.

**Operational gaps for compliance:**
- No audit log of which `checkReference` values were submitted or completed.
- No metrics on CIP pass/fail rates.
- No alerting on `AUTHENTICATION_FAILURE` or `PERMISSION_DENIED` error types returned by the service.

## Infrastructure Dependencies

| Component | Detail | Version / Notes |
|---|---|---|
| JDK | `D:\c-base\opt\jdk1.6.0_16` | Java 6 — EOL since 2013; TLS 1.0/1.1 only |
| Apache Ant | Build execution | Version unspecified |
| Apache XmlBeans | `xmlbeans-2.5.0` (vendored) | EOL; Apache project archived |
| Maven | JAR deployment to Nexus | Version unspecified |
| SQL Server | `ecountcore` database | Version unspecified; `use ecountcore; go` syntax |
| Internal Maven repo | `ecsvn.office.ecount.com:8080/mvn/release` | Plain HTTP; availability unknown |
| Actimize KYC Server | `*.nam.nsroot.net:8181` | Fortent/NICE Actimize; internal network only |
| JAX-WS RI | `2.1.2-hudson-182-RC1` (from WSDL comment) | Very old; bundled with Java 6 |

All infrastructure is on-premises and internal-network only (`.nam.nsroot.net` domain). No cloud or container dependencies exist.

## Operational Risks

1. **Java 6 EOL**: JDK 1.6.0_16 is referenced in tooling instructions. This version has been EOL since February 2013. It does not support TLS 1.2 without patches, violating PCI DSS v4.0 Requirement 4.2.1.
2. **No automated build**: The Ant build requires a specific filesystem layout (`D:\c-base\...`). Rebuilding the JAR is a manual, workstation-specific operation. If the developer who set up this path leaves, the build breaks.
3. **Compiled binary in Git**: Two copies of `KycCheckServiceXmlBeans.jar` are tracked in Git. Without source (.java files in a separate project), there is no way to audit what is in the JAR. The JAR may not correspond to the current XSD.
4. **No versioning after 1.0**: Any changes to the Actimize XSD/WSDL contract require a manual rebuild and re-deployment with no version bump strategy.
5. **Plain HTTP Maven repo**: The artifact is deployed to and fetched from a plain HTTP Maven repository, enabling man-in-the-middle substitution of the library.
6. **Single point of failure — no load balancing**: Each `kyc_profile` entry has a single `webservice_url`. No failover URL or retry configuration is present in the library.
7. **Certificate expiry risk**: Server certs are manually imported binary files (`servercert.bin`). There is no automated certificate rotation or expiry alerting. The `cacertslist.txt` shows certs with expiry dates — some now past (e.g., TC TrustCenter Class 2 CA II expired Dec 31, 2025).
8. **Internal hostname dependency**: All three endpoint hostnames are private `.nam.nsroot.net` addresses. The library will not function outside the corporate network without VPN or equivalent access.

## CI/CD

**No CI/CD pipeline exists** in this repository. There is no:
- Jenkinsfile, `.github/workflows`, `.gitlab-ci.yml`, Azure Pipelines YAML, or any pipeline definition.
- Automated test execution.
- Automated build trigger on commit.
- Automated deployment to any environment.
- Code quality gates or static analysis.
- Dependency vulnerability scanning.
- Secret scanning (credentials are present in the repository undetected).

All build, test (none), and deploy steps are fully manual, performed by a developer following the text instructions in `deploy kycbean jar to repository.txt` and `artifacts/keytool security cer add.txt`.
