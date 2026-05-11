# DevOps & Operations — ieft-cp2e_LIB

## CI/CD Pipeline

The repository uses GitHub Actions for CI with a single workflow file.

### CodeQL Workflow (`.github/workflows/codeql.yml`)

- **Trigger**: Manual dispatch (`workflow_dispatch`) and weekly scheduled scan (Wednesdays at 10:27 UTC, line 5: `cron: 27 10 * * 3`).
- **Runner**: Self-hosted Linux x64 Ubuntu Docker runner (`java-runner: "['self-hosted', 'X64', 'Linux', 'ubuntu-docker']"`).
- **Reusable workflow**: Delegates to `Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main` with `secrets: inherit`.
- **Purpose**: Static Application Security Testing (SAST) — CodeQL scans Java source for security vulnerabilities.

### Dependabot (`.github/dependabot.yml`)

Automated dependency version monitoring is configured but the specific configuration was not visible in full. This enables automated PRs for outdated dependencies.

**Gap**: There is no build-on-push CI workflow, no unit-test execution in CI, no artifact publishing pipeline, and no deployment workflow. The library relies on manual Maven builds.

## Build System

- **Build tool**: Apache Maven with Maven Wrapper (`mvnw`, `mvnw.cmd`).
- **Maven settings**: `.mvn/wrapper/settings.xml` — likely configures internal Nexus/Artifactory.
- **Packaging**: `maven-assembly-plugin` creates a fat JAR (`jar-with-dependencies`), bound to the `package` phase (pom.xml lines 75–90).
- **Java source/target**: 1.6 (pom.xml lines 70–71) — **critically outdated**.

## Runtime Deployment

The library is deployed as a standalone batch JAR invoked by a scheduler (e.g., Active Batch, Windows Task Scheduler, or a Unix cron job). Entry point: `com.ecount.process.cp2eExtractFile.Cp2eExtractFile.main()`.

**Invocation pattern:**
```
java -jar IEFT_CP2E-2019.4.5-jar-with-dependencies.jar <output_file_path> [request_file_id=<id>] [wl_transfer_type=<0|1>]
```

**Runtime configuration** (`cp2eExtract.properties`):

| Property | Value | Purpose |
|----------|-------|---------|
| `director.address` | `http://ppamwdcddcor1:80/service/dispatch.asp` | Director service URL for datasource resolution (plain HTTP, not HTTPS) |
| `agent` | `b2ctest` | eCount agent identifier |
| `database` | `ecountcore` | Target database |
| `XMLFilePath` | `D:/c-base/runtime/ndmroot/cititest/program/ieft_cp2e/` | Path for CP2E template XML and output files |
| `threadpoolsize` | `20` | Worker threads for StrongBox lookups |
| `strongbox.retries` | `30` | Retry count per StrongBox call |

**Exit codes:**

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General failure |
| 777 | Invalid `request_file_id` passed when OTT status is clean |
| 888 | Previous OTT extraction failed — `request_file_id` required to recover |

## Operational Monitoring

- Logging via `log4j` (commons-logging facade), configured in `src/main/resources/log4j.properties`.
- No metrics, health endpoints, or alerting integrations are present in this library.
- Operations teams monitor output file presence and batch scheduler exit codes.

## Security Concerns in Operations

1. **Director URL uses plain HTTP** (`http://ppamwdcddcor1:80`): database credentials are transmitted unencrypted between the batch host and the Director service. This violates PCI DSS Requirement 4.2.1 (strong cryptography for transmission of sensitive data).

2. **Hardcoded agent identifier** `b2ctest` in `cp2eExtract.properties` (line 2) suggests the properties file was committed with a test/QA value. If used in production, this value needs verification.

3. **Output file path** `D:/c-base/runtime/ndmroot/cititest/` — the `cititest` substring in a production path is a naming anomaly that should be confirmed. Access to this directory must be restricted to the NDM/MFT service account only.

4. **No log sanitization**: StrongBox `putDataIntoRecord()` logs all key-value pairs at DEBUG level (line 105: `log.debug("Putting " + prefix + (String)a.getKey() + " = " + a.getValue() + " into map")`). If DEBUG logging is enabled in production, bank account numbers and routing numbers will appear in plaintext in log files, violating PCI DSS Requirement 3.3.1.

## Environment Separation

No evidence of environment-specific configuration profiles (dev/QA/prod). A single `cp2eExtract.properties` file controls all configuration. Environment promotion requires manual file replacement, which is an operational risk.

## Recommendations

| Priority | Action |
|----------|--------|
| Critical | Upgrade Java from 1.6 to a supported LTS (Java 17 or 21) |
| Critical | Switch Director URL from HTTP to HTTPS |
| High | Disable DEBUG logging of StrongBox data in production |
| High | Parameterize stored procedure calls to eliminate SQL injection risk |
| High | Add build-on-push CI workflow with unit test execution |
| Medium | Implement environment-specific configuration management |
| Medium | Add artifact publishing pipeline to internal Nexus/Artifactory |
