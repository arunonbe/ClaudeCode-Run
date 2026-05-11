# Data Architect Report — webapp-parent-pom_PARENT

## Data Models

As a parent POM, this repository defines no data models. All data modelling is done in the individual web application modules that inherit this parent.

## Sensitive Data

No sensitive data is stored or processed in this repository. The POM file itself contains:
- An internal Nexus server URL (`http://d-na-stk01.nam.wirecard.sys:8080/nexus/...`).
- A GitLab SCM URL (`ssh://git@gitlab.com/northlane/development/...`).

Neither constitutes cardholder data. However, the Nexus URL is over unencrypted HTTP, which is a dependency supply-chain concern.

## Encryption Status

The POM does not configure encryption for any artifact transport. The Nexus repository URL uses `http://` rather than `https://`, which means dependency resolution from the internal Nexus server is performed over an unencrypted channel. This creates a man-in-the-middle risk for artifact integrity.

## Database Schemas

None. No database configuration is present.

## Data Flows

At build time:
1. Maven resolves the parent POM from the internal Nexus server (or local Maven cache).
2. Dependencies declared here (JUnit, Spring Mock, EasyMock, commons-logging, geronimo specs, Struts, xDoclet) are downloaded from the Nexus repository over HTTP.
3. xDoclet reads Java source annotations and generates Struts configuration XML files at `generate-sources` phase.
4. The WAR is built and may be deployed to the Nexus releases repository.

No runtime data flows are defined by the parent POM itself.

## Retention Concerns

- The parent POM version `10.0.1-SNAPSHOT` is a SNAPSHOT, which in Maven means it can be updated in the Nexus repository without changing the version number. Any inheriting project that re-resolves dependencies could receive a different artifact than what was previously tested. This is a supply-chain integrity concern for regulated environments.
- Released versions of the parent POM should be preserved in Nexus with an immutable release policy.

## PCI DSS Compliance

- **Req. 6.3.3**: All software must be protected from known vulnerabilities. Struts 1.3.8 inheriting into all web applications is a direct violation of this requirement.
- **Req. 12.3.4**: The organization must review hardware and software technologies at least once every 12 months. Java 1.6 and Struts 1.x should have been flagged in any technology review.
- The HTTP-only Nexus URL represents a build-time supply chain risk that could allow injection of malicious artifacts — a risk relevant to PCI DSS Req. 6.3 secure development practices.
