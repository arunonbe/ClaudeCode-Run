# auto-card-batch_LIB — Enterprise Architect View

## Platform Generation (Gen-1/Gen-2/Gen-3)

**Classification: Gen-1**

Evidence:
- Spring Framework 2.5.6 (released November 2008) and Spring Batch 2.1.1 (released 2010).
- Java compiler target `1.5` (`pom.xml` lines 192–195) — Java 5, EOL since October 2009.
- Log4j 1.2.15 — replaced by Log4j 2.x and then by SLF4J/Logback in Gen-2+ systems.
- XML-heavy Spring configuration (no annotations, no Spring Boot).
- Command-line `CommandLineJobRunner` entry point invoked via Windows `.bat` scripts.
- Group ID `com.ecount.batch.autoCardBatch` — uses the legacy `ecount` namespace predating the Northlane and Onbe rebrands.
- SCM URL references `northlane/development/application-development/libraries` (GitLab), indicating a library that originated in the Northlane era of the platform.
- Parent POM `com.citi.prepaid.service:service-parent:8` — references the Citi Prepaid lineage, the earliest generation of the platform.
- Dependency on `com.ecount.service.Core2.director:director-client:1.0.11` and `com.ecount.service.Core2:ecount-system:2.0.0` — Core2 designation is a Gen-1 internal platform layer.
- `com.cbase.*` imports (`CardCreateService.java`) reference the `cbase` domain layer, consistent with the oldest platform generation.

## Business Domain

**Domain**: Prepaid Card Provisioning / Cardholder Onboarding

This library sits within the **Card Lifecycle Management** subdomain of the prepaid platform. It handles the automated, batch-driven phase of card issuance for members who have been flagged for automatic card creation (as opposed to self-service or agent-initiated card creation). It bridges the member management layer (upstream — population of `autocard_creation_transaction_journal`) and the card issuance infrastructure (downstream — `IDeviceManager` / eCore / FDR).

Secondary subdomain: **Program Management** — the threshold-based plastic issuance logic (`ThresholdProgramVirtualCardSP`) introduces program-level configuration that governs whether a virtual card holder is also issued a physical card, tying card provisioning to program/BIN configuration.

## Role in Platform

This is a **shared library** (packaging `jar`, artifact `autocard-batch`), not a standalone microservice. It is designed to be consumed by batch execution environments that invoke it via `CommandLineJobRunner`. Its role in the broader platform:

1. **Batch card provisioner**: The only system in the legacy platform that performs automated bulk card issuance. Interactive/real-time card issuance occurs via separate channels (the xPlatform dependency suggests integration with the Ecount xPlatform portal layer).

2. **Enrollment gate**: Combined with `AppProfileUserEnrollmentClass`, it is the system of record for confirming that a member has been enrolled into the `card` option (system-enroll event).

3. **Status machine for the transaction journal**: Acts as the state machine controller for `autocard_creation_transaction_journal`, transitioning records through N → P → C/I/F/R states.

4. **Load job companion**: The two-job architecture (`autoCardLoadRecordsJob` + `autoCardProcessJob`) implies a coordinated scheduling arrangement. Job1 populates the journal from upstream sources; Job2 processes it. This separation allows retry-only scenarios (re-running Job2 without re-loading).

## Dependencies

### Upstream (this system consumes)
| Dependency | Type | Coupling |
|---|---|---|
| `autocard_creation_transaction_journal` (populated by external process or `autoCardLoadRecordsJob`) | SQL Server table | Tight — reads and writes directly |
| Director service | Runtime config service | Tight — no DB connections without Director |
| eCore / FDR system (`IDeviceManager`) | Internal card issuance API | Tight — synchronous call within batch step; failure marks member FAILED/INVALID |
| eCount Profile System (`AppProfileUserEnrollmentClass`) | Internal enrollment API | Tight — synchronous call; failure marks member INVALID |
| `com.ecount.service.Core2:ecount-system:2.0.0` | Internal library | Tight — runtime classpath |
| `com.ecount.service.Core2.director:director-client:1.0.11` | Internal library | Tight — runtime classpath |
| `com.ecount:xPlatform:2.5.44` | Internal library (with Spring exclusion) | Build-time |

### Downstream (consumers of this system's output)
| Consumer | What It Consumes |
|---|---|
| Downstream cardholder systems | Updated status in `autocard_creation_transaction_journal` |
| Card fulfilment / delivery system | Physical card orders triggered via `IDeviceManager.issuePlastic()` with delivery codes |
| Spring Batch job repository | `BATCH_*` tables — consumed by monitoring/operations tooling |

## Integration Patterns

| Pattern | Implementation |
|---|---|
| Stored-procedure-based data access | All DB reads use `StoredProcedureItemReader` (Spring Batch) against SQL Server SPs; no direct SQL SELECT in readers |
| Synchronous service call within batch writer | `CardCreateService` makes synchronous calls to `IDeviceManager` and `AppProfileUserEnrollment` within the Spring Batch writer (`AutoCardCreateWriter`) — no async, no queue |
| Spring Batch partitioned processing | `autoCardProcessStep` uses `SimplePartitioner` with `SimpleAsyncTaskExecutor` at grid-size 5 — parallel in-process thread partitioning, not distributed |
| Exit-code-driven flow control | Custom exit codes (`RECORDS FOUND`, `NO RECORDS FOUND`, `EXCEPTION THRESHOLD`, `RECORDS FOUND:INFINITELOOP`) drive job flow decisions via `next/end` elements in the job XML |
| Director-pattern data source resolution | Connection parameters resolved at runtime from a central Director service rather than static JDBC URLs — a proprietary service-locator pattern |
| Pass-through processing | All three item processor beans are `PassThroughItemProcessor` — no item transformation occurs; all logic is in writers |

## Strategic Status

**Status: Legacy / End-of-Life Candidate**

- All core technology dependencies (Spring 2.5, Spring Batch 2.1, Log4j 1.x, Java 5) have been EOL for 10–15 years.
- The parent POM ancestry (`com.citi.prepaid.service`) and company namespace trail (`ecount` → `northlane` → `onbe`) confirm this is a first-generation artifact from the original Ecount/Citi Prepaid platform that has survived multiple corporate transitions without significant modernisation.
- The dual GitLab/GitHub CI posture and the `refactor` branch reference in GitLab CI suggest there is an ongoing but incomplete modernisation effort.
- The library is classified as `_LIB` in the repository name convention, indicating it is a shared component. Any modernisation must account for downstream consumers.
- **Recommended status**: Prioritise for Gen-3 rewrite or retirement. If automated card provisioning remains a required capability, it should be re-implemented as a cloud-native batch microservice (e.g., Spring Batch 5.x on Spring Boot 3.x, containerised, with event-driven triggering via message queue).

## Migration Blockers

| Blocker | Severity | Detail |
|---|---|---|
| `com.cbase.*` API dependency | Critical | `IDeviceManager`, `ECoreDevice`, `AccountDefinitionECard`, `Funds`, `Member`, `Account` — all from the legacy `cbase` domain. No modern equivalent identified in this repo. Migration requires the eCore/cbase layer to expose a modern API (REST/gRPC) or for those interfaces to be reimplemented. |
| `AppProfileUserEnrollment` / `AppProfileUserEnrollmentClass` | High | Proprietary profile enrollment API from `com.cbase.business.ecount.profile`. Must be replaced or wrapped. |
| Director service coupling | High | All DB connections depend on the Director service for runtime configuration. No standard connection string or secret-manager integration. |
| Hard-coded `D:\c-base\` filesystem paths | High | `AutoCardBatch.xml` (line 23) and `log4j.properties` (line 9) use absolute Windows paths. Containerisation or cloud deployment is blocked without externalising these. |
| XML-only Spring configuration | Medium | No Spring Boot autoconfiguration. All bean wiring is in legacy Spring XML. Migration to Spring Boot requires full rewrite of configuration layer. |
| Java 5 target | Medium | `pom.xml` `maven-compiler-plugin` source/target `1.5`. Upgrade to at least Java 17+ required for Gen-3 compatibility. |
| Missing `autocard.threshold.issue.plastic` property | Medium | Referenced in XML but absent from committed properties file. Indicates environment-specific configuration drift that must be resolved and documented before any migration. |
| `autocard.sp.autocard_order_load` key mismatch | Medium | Property key in `AutoCardLoadRecordsJob.xml` does not match the key in `autocardbatch.properties`. Must be corrected and SPs rewritten or replaced with API calls in Gen-3. |
| Stateful job context (transaction counts) | Low-Medium | Count promotion across steps (`AutoCardCountSavingListener.promoteCount()`) uses Spring Batch `ExecutionContext` as a mutable state store. This pattern is incompatible with stateless/serverless execution models. |
