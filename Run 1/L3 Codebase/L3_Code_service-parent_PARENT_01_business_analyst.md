# Business Analyst Report — service-parent_PARENT

## Repository Overview

`service-parent_PARENT` is a Maven Parent POM module that provides a shared build configuration baseline for all service-tier projects within the Onbe/ecount payments platform. It does not contain executable business logic — its purpose is governance of the Maven build process for downstream service modules. The artifact coordinates are `com.parents:service-parent:9.0.1-SNAPSHOT` and it itself inherits from `prepaid-parent:4.0.1`.

## Business Purpose

In a large payments platform like Onbe's, maintaining consistency across dozens of Maven service modules is critical for:

1. **Dependency version governance**: Ensuring all services use the same versions of shared libraries, preventing version drift that causes integration failures in a PCI DSS regulated environment.
2. **Build process standardisation**: All services that inherit this POM get consistent compiler settings, plugin versions, and build lifecycle behaviour.
3. **Documentation infrastructure**: The POM configures `src/site/` with a Maven Site descriptor (`site.xml`), indicating intent to auto-generate service documentation.
4. **Release management**: The version `9.0.1-SNAPSHOT` indicates active development. The SCM configuration (lines 19–24) links to the GitLab repository under the `northlane` organisation.

## Heritage and Migration Context

The POM contains significant evidence of long-term evolution and organisational history:

- The distribution URL (line 16) references `d-na-stk01.nam.wirecard.sys:8080/nexus/` — a Wirecard-era internal Nexus server. Wirecard was the predecessor payments processing infrastructure before the Onbe/Northlane brand consolidation. This URL may be stale or inaccessible.
- Repository entries point to `http://snapshots.repository.codehaus.org/` — the Codehaus project, which shut down in 2015. These repository references are non-functional and introduce unnecessary Maven resolver overhead.
- The SCM URL references `gitlab.com/northlane/` — the current GitLab organisation, confirming ongoing active management.
- The commented-out Hibernate plugin block (lines 41–58) suggests a period when this parent managed ORM schema generation, which has since been decommissioned.

## Organisational Scope

The parent POM defines `ecount.project.type=services` (line 27), which is used by downstream projects to identify their project category in the broader Onbe platform. This type classification feeds into build reporting, artifact categorisation, and potentially compliance traceability (change management requires knowing which category of project was modified).

## Compliance Relevance

As a Maven parent POM, this repository directly influences the security posture of all inheriting service modules. Any dependency version pinned here affects the entire service tier. Failure to update this POM to address CVEs in transitive dependencies results in platform-wide vulnerability exposure. Given Onbe's PCI DSS Level 1 obligations, the parent POM is a critical governance artefact that should be subject to regular security review and dependency scanning.

## Stakeholder Impact

- **Development Teams**: Every service team inheriting this POM is affected by any change here. Version updates require coordinated testing across multiple downstream services.
- **Security Team**: CVE remediation in shared dependencies requires updating this POM, making it a security-critical governance point.
- **Release Management**: Version `9.0.1-SNAPSHOT` indicates the POM is in active development. Snapshot releases should not be referenced by production service POMs.
- **Compliance**: The Nexus server reference to the Wirecard-era host should be updated to reflect current Onbe infrastructure as part of evidence trail accuracy for SOC 2 and PCI DSS assessments.
