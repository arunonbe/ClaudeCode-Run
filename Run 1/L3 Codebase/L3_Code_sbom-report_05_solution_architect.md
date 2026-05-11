# Solution Architect View — sbom-report

## API Surface

The repository does not expose an API. The only programmatic interface is the Python aggregation script `report_aggregated.py`, invoked as a command-line tool:

```bash
python3 ./report_aggregated.py {directory}
```

Where `{directory}` is one of `dotnet`, `java`, or `js`. The script outputs a CycloneDX JSON file to `./aggregated-reports/aggregated_report_cyclonedx_{directory}.json`.

## Security Posture

The security posture of this repository is appropriate for an internal tooling repository. Key characteristics:

- **No authentication**: The repository is a GitHub private repo; access is controlled by GitHub team/organization permissions.
- **No secrets**: The workflow and script use no credentials.
- **Read-only processing**: The Python script only reads input files and writes output — no network calls, no external API access.
- **No execution of untrusted content**: The script uses `json.load()` (Python's safe JSON parser) on SBOM files. Python's `json.load()` does not evaluate arbitrary code, unlike XML parsers that may be vulnerable to XXE. Risk of SBOM poisoning via malformed JSON is limited to crashing the script (unhandled exception on malformed JSON), not code execution.

## Code-Level Findings

### Finding 1: CycloneDX Version Downgrade Without Validation

**File**: `report_aggregated.py`, line 65

```python
"specVersion": "1.4",
```

Input .NET SBOMs are CycloneDX 1.7. The aggregated output is hardcoded to CycloneDX 1.4. The script does not validate that input components are 1.4-compatible before inclusion. CycloneDX 1.7 introduced new fields (e.g., `manufacturer`, `authors`, enhanced `externalReferences` with `hashes`). These fields are silently dropped in the 1.4 output.

This is a data integrity concern: consumers of the aggregated report who rely on 1.7-specific fields will not find them.

**Remediation**: Update the output to CycloneDX 1.5 or 1.6 (current stable spec versions) and validate that the script correctly handles all relevant component fields from the input format.

### Finding 2: `security-events: write` Permission With No Corresponding Upload

**File**: `.github/workflows/aggregated_report.yml`, line 17

```yaml
security-events: write
```

The workflow requests `security-events: write` permission — this is the permission required to upload SARIF security scan results to GitHub Security tab via `github/codeql-action/upload-sarif`. However, no such upload step is present in the workflow. The permission is unnecessary and follows the principle of least privilege — it should be removed.

**Remediation**: Remove `security-events: write` from the workflow permissions block.

### Finding 3: Incorrect Timeout Configuration (Matrix Variable Without Matrix)

**File**: `.github/workflows/aggregated_report.yml`, line 17

```yaml
timeout-minutes: ${{ (matrix.language == 'swift' && 120) || 360 }}
```

The `matrix.language` variable is undefined in this workflow (there is no `strategy.matrix` block). The expression evaluates to `360` minutes (6 hours) because `matrix.language` is null, making the condition false. For a Python script that processes JSON files, 6 hours is an extreme timeout. If the script hangs due to malformed input or infinite loop, the runner would remain occupied for 6 hours before being killed.

**Remediation**: Replace with `timeout-minutes: 30` (sufficient for JSON file processing).

### Finding 4: No Error Handling for Missing Directories

**File**: `report_aggregated.py`, lines 49–56

```python
for filename in os.listdir(directory):
    if filename.endswith('.json'):
```

If the specified directory does not exist (e.g., `python3 ./report_aggregated.py java` when no `java/` directory has been created), `os.listdir()` will raise `FileNotFoundError`, aborting the workflow step. While the workflow uses `run: |` with multiple Python invocations in a single step, the `set -e` default in GitHub Actions `shell: bash` means the first failure (`java` or `js` directory missing) will abort the entire step before `dotnet` is processed.

**Remediation**: Add a directory existence check:
```python
if not os.path.isdir(directory):
    print(f"Directory {directory} not found, skipping.")
    exit(0)
```

Or use separate workflow steps with `continue-on-error: true` for each directory.

### Finding 5: Aggregated Reports Not Persisted Beyond 90 Days

**File**: `.github/workflows/aggregated_report.yml` — `upload-artifact` step with default retention

GitHub Actions artifacts have a default retention of 90 days. The aggregated SBOM reports are the primary evidence artifact for PCI DSS Req 6.3.3 compliance. If the reports are needed during an annual QSA assessment that occurs after the 90-day window, the artifacts will not be available.

**Remediation**: Add an additional workflow step to upload aggregated reports to Azure Blob Storage with a lifecycle policy setting retention to 2+ years, or tag a GitHub Release with the aggregated reports for permanent retention.

## Technical Debt Summary

| Finding | File | Severity |
|---|---|---|
| CycloneDX spec version downgrade (1.7 → 1.4) | `report_aggregated.py:65` | Medium |
| `security-events: write` permission unused | `aggregated_report.yml:17` | Low |
| Timeout uses undefined `matrix.language` variable | `aggregated_report.yml:17` | Low |
| Missing directory causes step abort | `report_aggregated.py:49` | Medium |
| Artifact retention < audit requirements | `aggregated_report.yml` (upload step) | High |
| Java and JS SBOMs not yet collected | Repository structure | High |
| No CVE correlation in aggregation step | `report_aggregated.py` (absent) | High |
