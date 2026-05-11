# Solution Architect Report — onbe-spring-boot-parent_PARENT

## API Surface

This repository has no executable code and no HTTP API surface. Its interface is the Maven POM contract: the `<dependencyManagement>` section defines available libraries and their versions, and the `<pluginManagement>` section defines available build plugins. Consuming services reference this parent via:

```xml
<parent>
  <groupId>com.onbe.spring.boot</groupId>
  <artifactId>onbe-spring-boot-parent</artifactId>
  <version>0.0.22-SNAPSHOT</version>
</parent>
```

## Security Posture

### Strengths
- GPL/AGPL license exclusion enforced via `maven-license-plugin` — prevents copyleft contamination.
- Pre-release version exclusions in `maven-versions-plugin` — prevents accidental use of alpha/beta/RC/Dev artifacts in production BOM.
- `maven-enforcer-plugin` enforces Java ≥ 21 and Maven ≥ 3.9 — no EOL runtime builds.
- CycloneDX SBOM generated at every package phase — enables downstream vulnerability scanning (OWASP Dependency-Check, Dependency-Track, Grype).
- `depclean-maven-plugin` included — detects and flags unused declared dependencies, reducing attack surface from unnecessary transitive dependencies.
- OWASP Encoder 1.3.1 managed — provides output encoding for XSS prevention in consuming services.
- Resilience4j 2.3.0 managed — circuit breaker and rate limiting for downstream API calls.
- Image pull policy is `ALWAYS` — ensures container builds use the latest patched base images.

### Weaknesses / Findings

**Finding 1 — QueryDSL Plugin Template Contains `encrypt=false` and Hardcoded Credentials Template**
File: `pom.xml`, line 721
```xml
<jdbcUrl>jdbc:sqlserver://localhost:1433;databaseName=AdventureWorks;user=MyUserName;password=*****;encrypt=false;</jdbcUrl>
```
The `encrypt=false` parameter disables TLS for the SQL Server connection. While this appears to be a development template, its presence in the parent POM normalizes insecure connection patterns. Any developer who copies this template without changing `encrypt=false` will create an unencrypted database connection. In a PCI CDE context this violates Requirement 4 (encryption of CHD in transit). The template should be replaced with `encrypt=true;trustServerCertificate=false` and the JDBC URL should reference a Maven property.

**Finding 2 — OpenTelemetry Alpha Dependency in Production BOM**
File: `pom.xml`, line 133
`<opentelemetry-instrumentation.version>2.13.1-alpha</opentelemetry-instrumentation.version>`
Alpha-versioned software in an enterprise production BOM is problematic. Alpha artifacts may capture or log unexpected data (including request/response payloads containing CHD), have breaking API changes without notice, and lack commercial support. This should be evaluated for upgrade to a stable release.

**Finding 3 — Azure Functions Maven Plugin with Commented-Out Docker Runtime**
File: `pom.xml`, lines 893–897
A Docker-based runtime configuration is commented out in the Azure Functions plugin:
```xml
<!--<runtime>-->
<!--  <os>docker</os>-->
<!--  <image>${spring-boot.build-image.name}</image>-->
```
This indicates an incomplete or abandoned container deployment path for Azure Functions. Commented-out configuration in a foundational POM creates confusion and should be removed or documented with a decision record.

**Finding 4 — `spring-boot-thin-layout` from Experimental Spring Group**
File: `pom.xml`, line 864
`<artifactId>spring-boot-thin-layout</artifactId>` from `org.springframework.boot.experimental` is a non-production Spring artifact. The `experimental` group ID explicitly indicates this is not covered by Spring commercial support. Using it in production Azure Functions deployments is a supportability risk.

**Finding 5 — SNAPSHOT Version as Enterprise BOM**
File: `pom.xml`, line 16
Version `0.0.22-SNAPSHOT` is the published parent for all Gen-3 services. SNAPSHOT Maven artifacts are mutable — a republished SNAPSHOT with the same version number can change build behavior without any change in consuming service POMs. This is particularly risky in a payments context where build reproducibility is a security control. PCI DSS Requirement 6 (secure development) implies build reproducibility; SNAPSHOT dependencies undermine this.

## Technical Debt

- The `swagger-codegen-maven-plugin` (3.0.58) is managed alongside `openapi-generator-maven-plugin` (7.11.0). Having two competing OpenAPI code generation tools managed simultaneously creates confusion about which one to use. The swagger-codegen plugin appears to be a legacy artifact that should be deprecated.
- The `querydsl-maven-plugin` is managed with a SQL Server-specific configuration that hard-codes `localhost:1433/AdventureWorks` — this is clearly a development convenience that has leaked into the enterprise BOM.
- No explicit `maven-dependency-check-plugin` execution is defined in the POM (the version is managed at 9.0.10), meaning OWASP vulnerability scanning must be explicitly configured in each consuming service — a weak default that may result in services skipping CVE scanning.
- `structurizr` dependencies (3.2.1) are managed, indicating architecture documentation tooling is included in the BOM. This is appropriate but should be marked as `<scope>provided</scope>` or `<optional>true</optional>` to prevent inclusion in production artifacts.

## Recommendations

1. Replace the QueryDSL JDBC URL template with `encrypt=true;trustServerCertificate=false` and a property reference for credentials.
2. Replace `opentelemetry-instrumentation:2.13.1-alpha` with the latest stable release.
3. Remove or archive the commented-out Docker runtime configuration from the Azure Functions profile.
4. Establish a release cadence and publish release (non-SNAPSHOT) versions for production service consumption.
5. Enable OWASP Dependency-Check plugin execution by default in the BOM (not just version management) so all consuming services get vulnerability scanning without explicit opt-in.
6. Deprecate `swagger-codegen-maven-plugin` management in favor of `openapi-generator-maven-plugin` exclusively.
