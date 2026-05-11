# Business Analyst Report — webapp-parent-pom_PARENT

## Business Purpose

`webapp-parent-pom_PARENT` is a Maven parent POM that governs dependency versions, plugin configuration, and build profiles for all Gen-1 web application modules across the eCount/Citi and Wirecard/Northlane platform lineage. It is a dependency governance artefact, not a deployable service. Any web application that declares this as its `<parent>` inherits its compiler settings, dependency versions, and build profile activations.

The parent chain is: `prepaid-parent:4.0.0` (group `com.citi.prepaid`) → `webapp-parent:10.0.1-SNAPSHOT` (this repo) → individual web applications (ClientZone, CSA, Enrollment, etc.).

## Capabilities

- Sets Java compiler to source/target **1.6** — a critically EOL Java version.
- Provides centralized Struts 1.3.8 dependency management (activated via `struts-xdoclet` profile).
- Manages xDoclet 1.2.3 and xjavadoc 1.5-beta for code-generation from Javadoc annotations.
- Provides a JSPC (JSP pre-compilation) profile for WAR packaging with pre-compiled JSPs.
- Sets up Jetty 6.1.3 for local development server (`maven-jetty-plugin`).
- Nexus repository URL is hardcoded: `http://d-na-stk01.nam.wirecard.sys:8080/nexus/content/repositories/` — an internal Wirecard Nexus server.

## Client and Cardholder Impact

All web applications in the Gen-1 stack that inherit this parent POM are cardholder-facing or client-facing:
- ClientZone: client portal for program management, file upload, inventory, user management.
- CSA (Customer Service Agent): agent tool for account lookup, payments, cardholder profile.
- Enrollment: cardholder enrollment flows.
- Scheduler/Workbench: operational tools for job management.

Dependency version regressions or CVEs introduced through this parent directly affect all of these cardholder-facing surfaces.

## Business Rules Encoded

- Struts 1.x framework version is locked at 1.3.8 — the framework is EOL and has known critical CVEs.
- `commons-fileupload` is explicitly excluded from `struts-core` — indicating awareness of historical file upload CVEs in Struts, though the exclusion alone does not confirm all vectors are closed.
- JSP pre-compilation is optional (activated by the `jspc` Maven property), not enforced — production builds may use interpreted JSPs.
- Tests use Spring Mock 1.2.7 and EasyMock 2.0, both very old versions.

## Regulatory Obligations

- **PCI DSS Req. 6.2 / 6.3**: All components with known vulnerabilities must be remediated. Struts 1.3.8 and Java 1.6 are both substantially past their EOL dates and carry unresolved CVEs. PCI DSS compliance for web applications inheriting this parent is at risk.
- **PCI DSS Req. 6.6**: Web-facing applications must be protected against known web application attacks. Struts 1.x is known for remote code execution vulnerabilities (S2-series).
- **NIST CSF**: Governance of known-vulnerable third-party dependencies is a core supply-chain security control.

## Key Business Risks

1. **Struts 1.3.8 is EOL with no vendor patches**: Any web app inheriting this parent and using the Struts profile is exposed to unpatched CVEs including remote code execution risks that could compromise the CDE.
2. **Java 1.6 compiler target**: Java 6 reached EOL in February 2013. Class files compiled to this target may run on modern JVMs but cannot use security features introduced in Java 7+.
3. **Hardcoded internal Nexus URL**: `http://d-na-stk01.nam.wirecard.sys` is an unencrypted HTTP endpoint on an internal Wirecard network. If this server is reachable from compromised infrastructure, it could serve malicious artifacts.
4. **SNAPSHOT version in production parent**: `webapp-parent:10.0.1-SNAPSHOT` is a snapshot, meaning inheriting projects could pick up unreleased, untested changes at build time.
