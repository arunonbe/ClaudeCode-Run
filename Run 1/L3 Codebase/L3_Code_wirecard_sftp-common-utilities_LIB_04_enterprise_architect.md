# Enterprise Architect — wirecard_sftp-common-utilities_LIB

## Platform Generation
**Transitional — Gen-2 to Gen-3 boundary**. This library is unusual within this repo set:
- Uses Maven (not Gradle) — different from all other repos in this batch
- Compiled for Java 21 — significantly ahead of the Java 8 used by FTC, NAM-bank-agent, wire-transfer-agent
- Published to GitHub Packages (not internal Nexus) — aligns with Gen-3 cloud-native tooling
- Parent POM `prepaid-parent:6.0.12` — connects it to the modern Onbe prepaid platform parent
- Version 2.0.0 — the "2.0" designation and Java 21 target suggest a deliberate platform modernisation step
- GitHub Actions CI (not GitLab CI) — different from all other repos in this batch

This places sftp-common-utilities in a **modernised shared library** position: it is being used by Gen-2 services (NAM-bank-agent) but is itself implemented with Gen-3 tooling.

## Business Domain
**Infrastructure / Integration Utilities** — SFTP file transfer capability shared across all batch services that exchange payment files with bank partners.

## Role in the Wirecard/Onbe Platform
- Consumed by NAM-bank-agent for all Sunrise Bank and PDS file exchanges
- Potentially consumed by other batch services (check-agent, wire-transfer-agent) for similar SFTP patterns
- Provides the only observable reuse of SFTP logic — without it each service would independently implement SFTP, creating N copies of the same vulnerability (`setAllowUnknownKeys`)

## System Dependencies
None at runtime — pure library.

## Integration Patterns
- **Tasklet pattern**: Spring Batch `Tasklet` implementations — pluggable into any Spring Batch step
- **Configuration by injection**: `BatchCommonConfig`, `BatchPathImportConfig`, `BatchPathPublishConfig` injected by consuming service
- **Retry**: Spring Retry `@Retryable` for transient SFTP failures
- **Session factory**: Spring Integration `DefaultSftpSessionFactory` — Apache MINA SSHD under the hood (replaces older JSch)

## Strategic Status
- **Current**: Active library at v2.0.0; published to GitHub Packages; compiled for Java 21
- **Strategic position**: This is already a transitional Gen-3 library — use of Apache MINA SSHD (replacing JSch) and Java 21 are forward-looking choices
- **Key risk**: `setAllowUnknownKeys(true)` is a security defect embedded in the shared library — ALL consumers inherit this vulnerability
- **Remediation path**: Fix `setAllowUnknownKeys` to `false` and provide a mechanism for consuming services to supply known-host verification data

## Migration Blockers
1. `setAllowUnknownKeys(true)` must be fixed before any Gen-3 migration — it is a compliance blocker
2. Parent POM `prepaid-parent` must resolve in cloud-native CI environments
3. `@ToString` on `BatchCommonConfig` must have `@ToString.Exclude` on password/privateKey fields before any log-aggregation migration
4. SFTP retry behaviour should be made explicitly configurable (not default Spring Retry) for cloud-native resilience patterns
