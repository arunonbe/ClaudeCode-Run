# Solution Architect View — drawdown-data-manager_LIB

## Architecture Summary
Single-process Java CLI application. No network-exposed interface. Reads a local CSV file, calls an internal XMLRPC vault service (StrongBox via Director), and writes a stored-procedure result to a SQL Server database. Spring 2.5 is used purely for IoC bean wiring (no web layer). The main class is the sole entry point.

## API / Integration Surface
| Interface | Protocol | Direction | Notes |
|-----------|----------|-----------|-------|
| StrongBox XMLRPC | HTTP XMLRPC | Outbound | Via `IStrongBoxClient`; URI from properties |
| Director Config Service | HTTP | Outbound | Provides datasource/agent lookup |
| GreatPlains SQL Server | JDBC (DBCP) | Outbound | `DrawdownReferenceUpdateSP` stored proc |
| CSV file | Local file I/O | Inbound | No format version or schema validation beyond field-level |

## Security Assessment
| Area | Finding | Severity |
|------|---------|---------|
| Plaintext account numbers in CSV | Input file contains unmasked account numbers at rest | High |
| Spring 2.5.4 | No security patches since 2010; known deserialization and SPEL vulnerabilities | Critical |
| Log4j 1.2.15 | CVE-2019-17571 (SocketServer remote code execution); multiple others | Critical |
| commons-collections 3.2.1 | Apache deserialization gadget chain CVE-2015-6420 | High |
| StrongBox client SNAPSHOT | Non-deterministic build artifact in production path | Medium |
| No TLS validation visible | XMLRPC connection security depends on server config | Medium |
| Hardcoded config path | Path `D:\c-base\config` may expose credentials if read permissions are broad | Medium |

## Technical Debt
1. **Framework vintage** — Spring 2.5, Log4j 1.x, and commons-collections 3.x are decade-old EOL artifacts. A full framework upgrade is required before any further development.
2. **No unit tests** — refactoring confidence is zero without a test suite.
3. **God-class `main()`** — validation, vault write, DB write, and file parsing are all in a single static method; should be decomposed.
4. **Caught-and-suppressed exceptions** — `e.printStackTrace()` used throughout; no structured error propagation.
5. **Hardcoded Windows paths** — prevents containerisation, Linux deployment, or multi-environment use.

## Gen-3 Migration Recommendations
1. Replace StrongBox with Onbe's Gen-3 secret/token vault (e.g., HashiCorp Vault or AWS Secrets Manager).
2. Replace Director-managed datasource with standard Spring Boot / environment-variable-driven datasource configuration.
3. Replace CSV file input with an API call (REST) or managed event queue to eliminate plaintext-file risk.
4. Package as a Spring Boot application (Java 17+) with proper structured logging (SLF4J + Logback).
5. Add idempotency key (e.g., hash of ProgramID + PromotionID) to prevent duplicate vault entries on re-run.
6. Add integration tests against a mock StrongBox and an in-memory DB (H2) before any migration.

## Code Risks Summary
- Three critical CVE-bearing dependencies in the runtime classpath.
- Zero test coverage.
- Plaintext financial data on disk before it reaches the vault.
