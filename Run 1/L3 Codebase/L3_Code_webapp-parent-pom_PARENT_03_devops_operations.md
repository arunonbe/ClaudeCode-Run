# DevOps / Operations Report — webapp-parent-pom_PARENT

## Build System

**Maven 3.x** via Maven Wrapper. The POM itself is a pure parent POM (`<packaging>pom</packaging>`), so it produces no JAR or WAR artifact. Its build role is entirely to provide inherited configuration to child modules.

Build plugins configured:
- `maven-jetty-plugin:6.1.3` — for local development server (Mortbay Jetty, not Eclipse Jetty).
- `maven-antrun-plugin` — for xDoclet code generation via Ant tasks.
- `jspc-maven-plugin` (Codehaus) — for JSP pre-compilation (activated by `jspc` Maven property).
- `maven-war-plugin` — for WAR assembly with JSPC output.

## CI/CD Pipeline

Two CI configurations are present:

1. **`.gitlab-ci.yml`**: References a shared CI template from `northlane/development/application-development/configuration/ci-templates` on the `refactor` branch using `include`. All Maven phases (build, test, deploy) have `maven.test.skip=true` set, meaning **tests are never run in CI**. This is a significant quality control gap.

2. **`.github/workflows/codeql-java.yml`**: GitHub CodeQL analysis workflow — suggests migration toward GitHub Actions. This is a positive security control addition.

3. **`.github/dependabot.yml`**: Dependabot configuration — automated dependency update PRs.

## Deployment Model

The parent POM is published to the internal Nexus repository at `http://d-na-stk01.nam.wirecard.sys:8080/nexus/`. Web applications that inherit it are deployed as WARs to application servers (likely Tomcat or JBoss/WildFly in the Gen-1 era).

## Runtime

- **Java 1.6** — Extremely EOL (EOL: February 2013, over 12 years past end of support). Any JVM running code compiled to this target should be a remediation priority.
- **Struts 1.3.8** — EOL, no vendor patches since 2013.
- **Jetty 6.1.3** — EOL (Mortbay Jetty, superseded by Eclipse Jetty 9+).
- **xDoclet 1.2.3** — Abandoned since ~2008.
- **Spring Mock 1.2.7 / EasyMock 2.0** — Ancient test dependencies, no known critical CVEs in test scope but reflect extreme age of the stack.

## Secrets Management

No secrets present. The Nexus URL is hardcoded in the POM as a plain HTTP URL (not HTTPS), which is a transport security gap but not a secret exposure.

## Observability

Not applicable to a parent POM. Runtime observability is configured in individual application modules.

## EOL Runtimes / CVEs

| Component | Version | EOL Since | Critical CVEs |
|-----------|---------|-----------|--------------|
| Java | 1.6 | Feb 2013 | Multiple JVM CVEs |
| Struts | 1.3.8 | 2013 | S2-001 through S2-016+, including RCE |
| Jetty | 6.1.3 | 2009 | Multiple |
| xDoclet | 1.2.3 | ~2008 | N/A (code gen tool) |

**Struts 1.x CVEs** are particularly severe in the context of a PCI DSS cardholder data environment. Known critical issues include OGNL injection leading to remote code execution. Since Struts 1.x is entirely EOL, there are no patches; the only remediation is framework migration.

## Operational Risks

1. **Tests are skipped in CI**: `MAVEN_TEST_OPTS: "-Dmaven.test.skip=true"` in `.gitlab-ci.yml` means no automated tests run in the CI pipeline for this parent or any child project using the same template.
2. **SNAPSHOT parent versioning**: Child projects that use `webapp-parent:10.0.1-SNAPSHOT` may unexpectedly pick up changes to the parent without a version bump, causing non-deterministic builds.
3. **HTTP Nexus URL**: Dependency resolution over HTTP risks artifact substitution attacks.
