# Enterprise Architect View — sbom-report

## Platform Generation

**Cross-generation — Generation-agnostic tooling.** The `sbom-report` repository spans all three platform generations:
- It currently contains `.NET` SBOMs for Gen-2 (Wirecard/Northlane) and Gen-3 (NexPay/Onbe) .NET services
- The aggregation script references `js` and `java` directories, intended to cover Gen-1 (Java), Gen-2 (Java/Spring Boot), and Gen-3 (Java 21+, JavaScript/Node.js) services
- The filtering logic in `report_aggregated.py` excludes `com.citi.*`, `com.ecount.*`, `com.onbe.*` group IDs, indicating that Gen-1 Java SBOMs were either contemplated or partially implemented

The repository serves as an enterprise-wide horizontal capability, not aligned to any single generation.

## Integration Patterns

The current integration model is **pull-based file aggregation**:
1. Individual service CI pipelines are expected to generate SBOM files and commit or upload them to this repository
2. The weekly workflow reads from the committed files
3. Reports are uploaded as GitHub Actions artifacts for manual consumption

This is a **collect-and-batch** pattern rather than a **push-and-alert** pattern. The architecture does not support real-time CVE alerting when a new vulnerability is disclosed.

A more mature architecture would use **push-based integration** with an SBOM management platform:
- Each service CI pipeline posts its SBOM to OWASP Dependency-Track (or Snyk/Anchore) via API
- The platform continuously re-evaluates SBOMs against updated CVE databases
- Security teams receive automated alerts when a vulnerability is newly disclosed against a deployed component

## External Dependencies

- **GitHub Actions** — pipeline execution platform
- **CycloneDX .NET module** (`cyclonedx-dotnet v6.2.0`) — SBOM generator used by .NET service pipelines
- **No external SBOM management platform** — this is the key architectural gap

## Position in the Broader Platform

`sbom-report` sits at the **enterprise risk management layer**:

```
[Gen-1/2/3 Service CI/CD Pipelines]
    → Generate CycloneDX SBOMs
    → Commit to sbom-report repository

[sbom-report repository]
    → Weekly aggregation (Python script)
    → GitHub Actions artifacts (90-day retention)

[Security/Compliance Team]
    → Manual download and analysis
    → [Manual CVE cross-reference with NVD/OSV]
    → Remediation ticketing (Jira/ServiceNow)
```

This repository is Onbe's primary (and possibly only) software supply chain inventory mechanism. It is therefore a critical compliance control for PCI DSS Req 6.3.3 and NIST CSF ID.AM-2 (Software platforms and applications within the organization are inventoried).

## Observed Coverage Gaps

Based on the repository's file structure:
1. **Only .NET SBOMs are present**: The `java/` and `js/` directories referenced in the aggregation script are not present in the checked-out working tree. Java services (Gen-1 eCount, Gen-2 Spring Boot, Gen-3 Spring Boot 3.x) may not be contributing SBOMs to this repository.
2. **Not all .NET services visible**: The SBOM files visible represent a subset of Onbe's .NET portfolio. The aggregation workflow processes whatever is committed; if some services are not generating or committing SBOMs, they are absent from the inventory.
3. **Onbe-internal filtering**: The Python script filters out Onbe-internal group IDs. This is correct for the purpose of third-party dependency reporting, but means no SBOM data is collected for Onbe's own libraries (like `request-context_LIB`, `request-file_LIB`), which also carry dependency risk.

## Migration Blockers

No migration blockers per se — this is a tooling/reporting repository. However, the following improvements are needed to make it production-grade:

1. **Missing Java SBOM collection**: Java service CI pipelines (Maven-based) should add the `cyclonedx-maven-plugin` and commit or upload SBOMs.
2. **Missing JS SBOM collection**: Node.js service CI pipelines should add `@cyclonedx/cyclonedx-npm` and commit or upload SBOMs.
3. **Platform integration gap**: Connection to OWASP Dependency-Track or similar for automated CVE correlation.
4. **Artifact retention gap**: Move from GitHub Actions artifacts (90-day limit) to persistent storage.

## Strategic Status

**Active, growing, strategically important but immature.** The repository establishes the right pattern (CycloneDX SBOMs, centralized aggregation) but lacks:
- Complete coverage across all three platform generations and technology stacks
- Automated CVE correlation (converting SBOM inventory to actionable vulnerability findings)
- Real-time alerting (weekly batch is too slow for critical CVE response)
- Persistent artifact retention for audit purposes

Investment priority: medium-high. This repository is a PCI DSS Req 6.3.3 control evidence point, and strengthening it directly improves Onbe's security posture and audit readiness. The recommended evolution is integration with OWASP Dependency-Track as a persistent SBOM management platform, with this repository serving as the SBOM source and git-based audit trail.
