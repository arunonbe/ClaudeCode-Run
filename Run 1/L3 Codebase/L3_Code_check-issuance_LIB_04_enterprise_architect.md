# check-issuance_LIB — Enterprise Architect View

## Platform Generation (Gen-1/Gen-2/Gen-3)

**Classification: Gen-1**

Evidence:
- Parent POM `com.citi.prepaid.service:service-parent:8` — the `citi.prepaid` groupId places this firmly in the original ecount/Citi Prepaid platform generation.
- Spring Framework 2.5.4 (`pom.xml` line 60) — released 2008; Gen-1 Spring XML-driven IoC without annotations or Spring Boot.
- Java 1.6 compile target — aligns with the ecount Gen-1 platform timeframe (pre-2010 architecture).
- All internal APIs (`com.cbase.business.core`, `com.ecount.Core2`, `com.cbase.business.ecount`) are proprietary ecount Core2 platform libraries — the hallmark of Gen-1 ecount services.
- Spring `appContext.xml` uses the DTD-based bean definition format (`http://www.springframework.org/dtd/spring-beans.dtd`) — pre-Spring 3.0 namespace style, typical of Gen-1.
- No REST API, no message queue, no microservice boundaries — monolithic batch process invoked by a Windows VBScript launcher.
- jTDS 1.2.4 JDBC driver (legacy open-source SQL Server driver, succeeded by Microsoft's own JDBC driver circa 2012).
- Sterling Connect:Direct (NDM) file transfer to a Citi MVS mainframe — batch file-based integration typical of Gen-1 financial systems.

## Business Domain

**Disbursements — Physical Check Rail**

This library implements the physical check disbursement rail within the Onbe (formerly ecount/Northlane) payments platform. It is responsible for:
- Deducting funds from a prepaid cardholder's DDA (Demand Deposit Account) device.
- Triggering downstream check printing and mailing via Citi CPS.
- Managing stop payments on refund checks.
- Supporting both auto-generated and CSA-manually-requested checks.
- Supporting re-issuance (source code 255) with fee waiver.
- Supporting enrollment-program-based check issuance (per-payment model).

This sits at the intersection of the **prepaid card** and **physical check** business domains and is relevant to Onbe's healthcare, insurance, auto-finance, and consumer rebate client verticals — wherever a paper check is the preferred or fallback disbursement instrument.

## Role in Platform

The library operates as a **shared batch library** consumed by one or more batch job hosts. Its role in the platform:

```
[Onbe Platform]
     │
     ├─ Card Management (DDA/ecard device lifecycle)
     │       └─► DeviceInfoManager API (ecount Core2)
     │
     ├─ Fund Transfer Engine
     │       └─► TransferManager API (ecount Core2 — transferDDAToOperator)
     │
     ├─ Check Issuance Batch  ◄── THIS LIBRARY
     │       ├─ Reads pending work from SQL Server (EcountCoreDataSource)
     │       ├─ Debits cardholder DDA via TransferManager
     │       ├─ Writes status back to SQL Server
     │       └─ Triggers Citi CPS file generation / stop-refund NDM transfer
     │
     └─ Citi CPS (external — check printing/mailing)
             └─ Receives check issuance file + stop-refund file via NDM
```

The library is **not a service** — it has no inbound API surface (no REST, no SOAP, no messaging consumer). It is a purely outbound batch processor that must be invoked by a scheduler (Windows Task Scheduler or similar).

## Dependencies

### Compile-time / Runtime Dependencies (internal)

| Artefact | GroupId | Version | Notes |
|---|---|---|---|
| `xPlatform` | `com.ecount` | `2013.1.5` | Core ecount platform utilities |
| `director-client` | `com.ecount.service.Core2.director` | `1.0.11` | Director service registry client |
| `ecount-system` | `com.ecount.service.Core2` | `2.0.0` | Core2 system layer |
| `springutils-generic` | `com.ecount.springutils` | `1.0.4` | ecount Spring utilities |
| `spring-dbctx-*` | `com.ecount.spring-dbctx` | `1.0.1`–`1.0.2` | ecount Spring DB context (test scope) |

All internal `com.ecount` and `com.cbase` classes referenced (`TransferManagerImpl`, `DeviceInfoManagerImpl`, `ECoreTransfer`, `AppProfileUserEnrollmentClass`) must be resolved via the internal Maven repository at build time. These artefacts are **not available in Maven Central** — the build is not reproducible outside the Northlane/Onbe internal network.

### External Runtime Dependencies

| Artefact | Version | Status |
|---|---|---|
| `spring` | `2.5.4` | EOL — Spring 2.x unsupported since 2013 |
| `log4j` | `1.2.14` | EOL — Log4j 1.x unsupported since 2015; CVE-2019-17571 |
| `jtds` | `1.2.4` | Deprecated — replaced by `mssql-jdbc` |
| `commons-logging` | `1.1` | Very old; current is 1.3.x |
| `commons-io` | `1.3.2` | Old; current is 2.15.x |
| `ehcache` | `1.2.3` | Old; current is 3.x |
| `commons-pool` | `1.4` | Old; current is 2.12.x |
| `junit` | `3.8.1` | EOL — JUnit 3 released 2002 |

### Downstream / Operational Dependencies

- **Citi CPS / Citi Mainframe** — for check printing and mailing; NDM node `NDMTEST` (possibly a staging reference hardcoded in the CDP script).
- **Sterling Connect:Direct** — for NDM file transmission.
- **Perl runtime with specific CPAN modules** — for report parsing scripts.
- **SQL Server BCP 2008 tools** — for stop-refund file extraction.

## Integration Patterns

1. **Database Polling (Batch Pull):** The library implements a polling loop against a SQL Server stored procedure to retrieve batches of work. This is a classic Gen-1 "polling batch" pattern with no event-driven or message-driven alternative.
2. **Stored Procedure API:** All database interactions are encapsulated behind stored procedures — the library has no direct table-level SQL. This is a characteristic Gen-1 pattern providing a degree of DB schema insulation.
3. **Thread-Pool Parallelism:** Transactions within each batch are processed in a fixed `ExecutorService` thread pool (`Executors.newFixedThreadPool`). This is the only concurrency mechanism.
4. **File-Based Downstream Integration:** Outbound data to Citi CPS is via pipe-delimited flat files transmitted over Sterling Connect:Direct. This is a legacy EDI-style integration with no API equivalent.
5. **RPC via ecount Core2:** Fund transfers and account inquiries are delegated to the `TransferManager` and `DeviceInfoManager` RPC interfaces — synchronous in-process calls backed by `ECoreTransfer` (likely XML-RPC or similar proprietary protocol based on package name `com.ecount.xmlrpc`).
6. **Spring XML IoC (DTD-based):** Bean wiring is entirely via `appContext.xml`. No annotations, no component scanning, no Spring Boot auto-configuration.

## Strategic Status

**Status: Legacy / Retirement Candidate**

- The library carries the `ecount`, `citi`, and `northlane` identities throughout — no rebranding to Onbe.
- It operates on technology that is 10–15+ years past EOL (Java 6, Spring 2.5, Log4j 1.x, jTDS, JUnit 3).
- The integration model (VBScript launcher, Windows-only, Sterling NDM to Citi mainframe) is tied to an infrastructure that is architecturally incompatible with cloud-native Gen-3 patterns.
- The Citi banking relationship embedded in this codebase (Citi CPS, NDM, Citi MVS mainframe) may no longer reflect current Onbe check-issuance partners.
- There is active CodeQL scanning and Dependabot configuration, suggesting the repo is still under minimal maintenance, but development is effectively frozen (version `2.0.1-SNAPSHOT` with all tests disabled).

## Migration Blockers

1. **Dependency on proprietary ecount Core2 APIs:** `TransferManager`, `DeviceInfoManager`, `ECoreTransfer`, `AppProfileUserEnrollmentClass`, `director-client` — none of these have open equivalents. Migration requires reimplementing or wrapping these capabilities in a Gen-3 API-based service.
2. **Citi CPS / NDM integration:** The outbound check issuance and stop-refund file transmission to Citi is a bespoke integration using Sterling Connect:Direct to a Citi MVS mainframe. Re-platforming requires either replicating this file-based integration (new NDM client) or replacing Citi CPS with a different check-printing vendor API.
3. **Windows-only runtime:** The VBScript launcher and BCP tool dependency make the batch non-portable to Linux/container environments without replacing the entire execution wrapper.
4. **No service interface:** The library has no inbound API — it must be wrapped in a scheduler/trigger mechanism before it can participate in an event-driven or orchestration-based architecture.
5. **Shared mutable state in `CheckIssuanceHelper`:** The counter fields are not thread-safe. Before migration, thread safety must be addressed to avoid data integrity issues under concurrent load.
6. **Spring XML wiring with hardcoded paths:** The `appContext.xml` contains hardcoded Windows `D:\` paths for property files. These must be externalised to environment variables or a config server for cloud deployment.
7. **jTDS / SQL Server 2008 BCP:** Requires upgrading to a supported JDBC driver and BCP client before running against modern SQL Server versions (2019/2022) or migrating to a cloud database.
8. **Log4j 1.x CVE exposure:** Cannot be deployed in a PCI DSS-compliant environment with known unpatched CVEs without risk acceptance documentation.
