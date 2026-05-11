# citi-direct-file-process_LIB — Enterprise Architect View

## Platform Generation (Gen-1/Gen-2/Gen-3)

**Classification: Gen-1**

Evidence supporting Gen-1 classification:
- Spring Framework 1.2.7 (circa 2005-2006) as the IoC container.
- jTDS JDBC driver 1.2.2 (unmaintained since ~2013).
- Log4j 1.2.15 (EOL; CVE-laden).
- `junit:3.8.1` (JUnit 3, circa 2002).
- Hardcoded Windows filesystem paths (`d:/c-base/runtime/citidirectfile/`).
- Plain HTTP (non-TLS) for inter-service communication with the Director service.
- `java.util.Hashtable` (synchronised, deprecated in favour of `HashMap` since Java 1.2).
- No dependency injection annotations, no Spring Boot, no containerisation artefacts.
- Comment-dated code (`FDRStringValidator.java` header: "Oct 25, 2006").
- Package root `com.ecount.one.etl` — uses the legacy `ecount` brand, predating the Onbe brand.

The codebase reflects architecture patterns typical of early-2000s Java ETL batch applications and has not been substantively modernised.

## Business Domain

**Domain**: Payment Disbursements — Citibank Integration

**Sub-domain**: File-based payment instruction generation for Citibank's treasury portal (CitiDirect).

This library is a narrow integration adapter: it bridges Onbe's internal account/card data store (EcountCore) and Citibank's batch file ingestion channel. It does not contain core business logic for card issuance, ledger management, or client onboarding. Its domain concerns are:
- Translating internal account records into the CitiDirect fixed-length file format.
- Supporting multi-country disbursement (US, CA, UK as evidenced in code).
- Being configurable per agent/brand (B2C is the default).

## Role in Platform

This library serves as a **batch extraction and file generation component** in the payment rail pipeline. Its role in the broader platform:

```
Onbe Core Platform
  ├─ Card issuance / account creation  [upstream, populates EcountCore]
  │
  ├─ citi-direct-file-process_LIB  ◄── THIS LIBRARY
  │     Reads from EcountCore via stored proc
  │     Generates CitiDirect flat file
  │
  └─ File delivery to Citibank  [downstream, out of scope for this library]
        Presumably SFTP or MFT to Citibank's CitiDirect portal
```

The library is a terminal node in the local processing chain: it consumes data and produces a file. It has no REST/SOAP API surface; it is not called by other services directly.

## Dependencies

### Inbound (what this library consumes)

| Dependency | Type | Notes |
|---|---|---|
| EcountCore SQL Server database | Synchronous JDBC | Via Director-provided DBCP connection pool |
| Director service (`http://ecappdev/...`) | HTTP (plain) | Provides DB connection configuration by agent+database |
| `newAccountFileTemplate.xml` | Filesystem | Must be co-deployed; not bundled in JAR |
| `etlContext.properties` | Classpath | Embedded in JAR or placed on classpath |

### Outbound (what this library produces)

| Output | Type | Destination |
|---|---|---|
| Fixed-length flat file | Filesystem | Local path `d:/c-base/runtime/citidirectfile/`; presumed to be picked up by a downstream file transfer process for delivery to Citibank |

### Library dependencies (from `pom.xml`)

| Artifact | Version | Status |
|---|---|---|
| `spring:1.2.7` | Spring 1.x | EOL ~2007 |
| `log4j:1.2.15` | Log4j 1.x | EOL 2015; multiple CVEs (CVE-2019-17571, etc.) |
| `jtds:1.2.2` | jTDS | Unmaintained; last release 2013 |
| `commons-logging:1.1.1` | Apache Commons | Outdated; current 1.3.x |
| `commons-dbcp:1.2.2` | Apache Commons DBCP | EOL; succeeded by DBCP2 |
| `commons-pool:1.4` | Apache Commons Pool | EOL; succeeded by Pool2 |
| `ecount-system:1.0.10` | Internal Core2 | Internal dependency; version unknown |
| `director-client:1.0.11` | Internal Core2 | Internal dependency; version unknown |

All third-party dependencies are severely outdated. None of the current major-version equivalents are present.

## Integration Patterns

1. **Batch file generation** — the dominant pattern. One SQL query, one output file per invocation. No streaming, no pagination, no checkpoint/restart.
2. **Template-driven layout** — the `newAccountFileTemplate.xml` + XSD pattern is a lightweight meta-model for file formatting without code changes. This is a reasonable abstraction for the era but is not reusable outside this specific file format.
3. **Director-mediated DB connection** — the `DirectorConfiguredDBCPdatasourceCreator` bean pattern provides a level of indirection between the ETL job and the database connection parameters. This is an early predecessor to modern service-mesh or secrets-manager patterns.
4. **Spring XML IoC** — dependency wiring via `etlContext.xml` with `PropertyPlaceholderConfigurer`. This is Spring 1.x XML-only configuration; no annotations or Java config.
5. **RowCallbackHandler pattern** — `CitiDirectDBListProcessor implements RowCallbackHandler` processes result-set rows one at a time without loading all records into memory. This is appropriate for large result sets but the single-threaded, sequential nature limits throughput.

## Strategic Status

**Status: Legacy — Maintenance-only / Retirement Candidate**

Indicators:
- All dependencies are end-of-life or severely outdated (oldest: Spring 1.2.7, ~2005).
- Zero test coverage.
- No evidence of active feature development (version stuck at 1.0.1).
- Hardcoded dev environment values committed to source.
- No containerisation, no cloud-native patterns, no 12-factor compliance.
- The library name ends in `_LIB`, consistent with the Onbe convention for shared/legacy library artefacts.
- The `ecount` package namespace indicates the code predates the Onbe rebrand.

This library should be assessed for:
(a) replacement with a Gen-3 microservice using modern Spring Boot / cloud-native patterns, or
(b) wrapping with a secure adapter layer while it awaits decommission.

## Migration Blockers

| Blocker | Severity | Details |
|---|---|---|
| Stored procedure `core_citi_direct_process_extract` schema unknown | High | No DDL in repo; migrating requires reverse-engineering the SP and its result set |
| `DirectorConfiguredDBCPdatasourceCreator` internal API | High | The Director-based datasource creation is an internal black box; modern replacement requires understanding what Director returns |
| `ecount-system:1.0.10` and `director-client:1.0.11` | High | Internal artefacts not in this repo; their APIs and transitional dependencies are not visible |
| `newAccountFileTemplate.xml` versioning | Medium | The template is co-deployed outside the JAR; migration must account for template lifecycle management |
| Citibank file format contract | Medium | The fixed-length format is driven by an external Citibank specification not present in this repo; any migration must validate against the live Citibank interface spec |
| Windows-only filesystem path | Medium | `d:/c-base/runtime/citidirectfile/` is Windows-specific; containerised or Linux-based Gen-3 deployment requires path reconfiguration |
| `System.exit()` calls | Low | Must be replaced with proper exception propagation before the library can be embedded in a modern orchestration framework |
