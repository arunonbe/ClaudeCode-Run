# Data Architect View — sbom-report

## Data Models

The repository stores and processes data in CycloneDX SBOM JSON format. The data model is defined by the CycloneDX specification (ECMA-424 / CycloneDX standard).

### Per-Repo SBOM Format (CycloneDX 1.7 — .NET)

Each SBOM file follows this schema:
```json
{
  "bomFormat": "CycloneDX",
  "specVersion": "1.7",
  "serialNumber": "urn:uuid:{UUID}",
  "version": 1,
  "metadata": {
    "timestamp": "{ISO8601}",
    "tools": [{ "type": "application", "name": "CycloneDX module for .NET", "version": "6.2.0.0" }],
    "component": { "type": "application", "bom-ref": "{app}@{version}" }
  },
  "components": [
    {
      "bom-ref": "{group}/{name}@{version}",
      "type": "library",
      "group": "{nuget group}",
      "name": "{package name}",
      "version": "{semver}",
      "description": "{package description}",
      "licenses": [{ "license": { "id": "{SPDX-license-id}" } }]
    }
  ]
}
```

### Aggregated Report Format (CycloneDX 1.4 — Python-generated)

The `report_aggregated.py` script produces a downgraded CycloneDX 1.4 output (despite the .NET SBOMs being 1.7). The aggregated report flattens all component entries from all service SBOMs into a single `components` array, deduplicates by `bom-ref`, sorts alphabetically, and outputs to `aggregated-reports/aggregated_report_cyclonedx_{directory}.json`.

## Sensitive Data

SBOM files do not contain cardholder data, PII, credentials, or financial account information. They contain only software component metadata:
- Package/library names, versions, and group IDs
- Publisher names
- License identifiers
- SBOM generation timestamps
- Application component names (which may reveal internal service names)

**Sensitive data concern — internal architecture disclosure**: The SBOM files reveal Onbe's internal service names, application versions, and complete third-party dependency inventories. If these files were exposed externally, an attacker could use the component list to identify which services use known-vulnerable library versions. This is a **secondary sensitivity** — not cardholder data but strategic/security-sensitive information. SBOM files should not be committed to public repositories or exposed via unauthenticated endpoints.

**Credential risk**: The aggregation script reads JSON files from the `dotnet/` directory without authentication or access control. The script itself contains no secrets. However, the GitHub Actions workflow uses `actions/checkout@v4` (public action — appropriate) and `actions/upload-artifact@v4` — no secrets are required for the core aggregation logic.

## Encryption Status

- **At rest**: SBOM JSON files are committed to the git repository in plaintext. No encryption is applied. The repository appears to be private (internal to Onbe), which provides access-control-based protection.
- **In transit**: GitHub provides TLS for repository access and Actions artifact transfer.
- **No secrets or financial data in SBOMs**: Encryption of the SBOM files themselves is not required.

## Database Schemas

No database. All data is stored as JSON files in the git repository and processed in-memory by the Python aggregation script.

## Data Flows

```
[Individual service CI/CD pipeline]
    → Generates CycloneDX SBOM (via CycloneDX .NET module v6.2.0, Maven CycloneDX plugin, or npm CycloneDX plugin)
    → Commits/uploads SBOM JSON to sbom-report repository dotnet/ (or java/, js/ directories)

[Weekly GitHub Actions workflow (Tuesday 19:47 UTC)]
    → Checkout sbom-report repository
    → python3 report_aggregated.py js
    → python3 report_aggregated.py java
    → python3 report_aggregated.py dotnet
    → Outputs: aggregated-reports/aggregated_report_cyclonedx_js.json
               aggregated-reports/aggregated_report_cyclonedx_java.json
               aggregated-reports/aggregated_report_cyclonedx_dotnet.json
    → Upload as GitHub Actions artifacts (90-day retention)

[Security/Compliance Team]
    → Download artifacts
    → Cross-reference with CVE databases (manual step)
    → Remediation planning
```

## Retention Concerns

- **GitHub Actions artifacts**: Default 90-day retention. For PCI DSS and NIST CSF audit purposes, SBOM records should be retained for at least 1 year (aligned with PCI DSS annual assessment cycles) or longer per Onbe's data retention policy. GitHub Actions artifact retention can be extended to 90 days maximum; for longer retention, SBOMs must be published to Azure Blob Storage, GitHub Releases, or another persistent store.
- **Git history**: All committed SBOM files are retained in git history permanently. This provides a long-term record of dependency versions at each point in time, which is valuable for post-incident analysis (determining which version of a library was deployed when a vulnerability was disclosed).
- **SBOM timestamps**: Each SBOM includes a `metadata.timestamp` (e.g., `2026-05-04T07:19:20Z`). These timestamps confirm the SBOM generation date and can be used to determine when a vulnerable dependency was first introduced.

## PCI DSS Compliance Relevance

SBOMs directly support PCI DSS 4.0 compliance:
- **Req 6.3.3**: An accurate SBOM enables systematic identification of components requiring security patches.
- **Req 12.3.4**: Hardware and software inventory must be reviewed at least once every 12 months — SBOM data is the software component inventory for this requirement.
- The aggregated CycloneDX report can be ingested by tools such as Dependency-Track (OWASP) for automated CVE matching against NVD/OSV, which would directly support continuous compliance with Req 6.3.3.
