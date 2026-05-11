# Enterprise Architect Report — global-deposit-batch_LIB

## 1. Platform Generation Assessment

`global-deposit-batch_LIB` is a **second-generation, cloud-transitional Spring Boot batch library** from the Wirecard era. Key indicators:

| Indicator | Evidence |
|---|---|
| Java 8 | `pom.xml` line 27: `<java.version>1.8</java.version>` |
| Spring Boot 2.3.4.RELEASE | `pom.xml` line 127 — EOL since August 2021 |
| `com.wirecard.globaldepositsbatch` namespace | Wirecard-era package naming |
| Wirecard SCM URL | `pom.xml` line 17: `gitlab.com/northlane/development/...` (Northlane/Wirecard) |
| Wirecard Nexus repository | `pom.xml` line 37: `d-na-stk01.nam.wirecard.sys` |
| CBTS dev URL | `application.yml` line 32: `cbts-dev.amer1.wirecard.com` |
| Lombok | Modern Java pattern |
| Spring Batch | Modern batch framework |
| Dual build system (Maven + Gradle) | Build system transition in progress |

This places the codebase at approximately **5–8 years old** in design generation, written during the Wirecard/Northlane period and inherited into Onbe. It is more modern than `file-transfer-service_LIB` (Gen 1) but older than `functionapptest` (Gen 3).

---

## 2. Role in Enterprise Architecture

### 2.1 Integration Position

`global-deposit-batch_LIB` occupies the **batch processing / fund transfer orchestration tier** of Onbe's cross-border payment architecture:

```
[Onbe Core Platform (iEFT transaction journals)]
    |
    | JDBC (SQL Server)
    v
[global-deposit-batch_LIB] ← This library
    |
    |--→ [Cambridge CBTS API (cross-border transfers)]
    |--→ [xPlatform (iEFT management)]
    |--→ [File system (reject CSV files from Cambridge)]
    v
[Updated transaction journals]
    |
    | NACHA addenda processing
    v
[ACH network / card funding]
```

### 2.2 Relationship to Other Repos

The library depends on:
- `cbts-client_LIB` (referenced as a separate repo in the repo listing) — may be a predecessor to the client modules embedded here
- `wirecard_funds-transfer-coordinator_LIB` — related Wirecard-era fund transfer library
- `ieft-cp2e_LIB` — iEFT cross-platform 2 entity library
- `xplatform_LIB` / `xplatform-library_LIB` — xPlatform foundation libraries

The dependency on `service-parent:9.0.0` (`com.parents`) links this to Onbe's standardized service parent POM.

---

## 3. Architecture Patterns

### 3.1 Spring Batch ETL Pattern

The library implements the classic **Spring Batch Reader-Processor-Writer pattern**:

```
Reader (DB or File) → Processor (CBTS API call / transformation) → Writer (DB update / file move)
```

All three batch jobs follow this pattern:
- `GlobalDepositMigrationReader/Processor/Writer`
- `GlobalDepositRejectsItemReader` → `GlobalDepositRejectsItemProcessor` → `GlobalDepositRejectsJdbcItemWriter`
- `RecurringGlobalDepositServiceReader/Processor/RowMapper`

### 3.2 Chunk-Oriented Processing

All jobs use Spring Batch chunk-oriented processing with configurable chunk sizes (default 10, `application.yml` lines 50, 58, 64). This provides fault tolerance — if a chunk fails, only that chunk is retried, not the entire job.

### 3.3 Multi-Module Library Design

The multi-module structure (6 sub-modules) separates concerns:
- `data` module: pure POJOs, no framework dependencies
- `cbts-client` module: HTTP client, no Spring Batch
- `xplatform-client` module: xPlatform integration
- `batch` module: Spring Batch implementation
- `config` module: Spring Boot application assembly
- `qa` module: integration tests only

This design allows downstream services to include only the modules they need.

---

## 4. Dependencies

### 4.1 External Dependencies

| Dependency | Type | Risk Level |
|---|---|---|
| Cambridge CBTS API | External FX/transfer service | HIGH — Wirecard-branded URL may be offline |
| `core_ieft_transaction_journal` SQL Server | Database | HIGH — shared with other services |
| File system (reject CSV) | Infrastructure | MEDIUM — path must be mounted |
| Spring Batch JobRepository | Database | LOW — standard Spring Batch |

### 4.2 Internal Onbe Dependencies

| Dependency | Risk Level |
|---|---|
| `service-parent:9.0.0` | MEDIUM — parent POM version |
| `xplatform` cross-border transfer service | MEDIUM — library dependency |
| Nexus at `wirecard.sys` | HIGH — may be decommissioned |

---

## 5. Fit / Gap Analysis Against Onbe Target Architecture

| Dimension | Current State | Target State Gap |
|---|---|---|
| Java version | Java 8 | Java 21 LTS |
| Spring Boot | 2.3.4 (EOL) | Spring Boot 3.x |
| Deployment | Library JAR | Azure Container Instance or AKS job |
| Secrets | Hardcoded in `application.yml` | Azure Key Vault |
| Artifact repo | Wirecard Nexus | Azure Artifacts / GitHub Packages |
| CBTS endpoint | Wirecard-branded dev URL | Current Cambridge FX/Onbe production URL |
| Build system | Maven + Gradle (dual) | Maven only (consolidate) |
| CI/CD | GitLab CI (tests skipped) | GitHub Actions (tests enabled) |
| Observability | Spring Batch logs | Azure Application Insights |

---

## 6. Migration Complexity Assessment

Migration complexity is rated **MEDIUM-HIGH** for the following reasons:

1. **Cambridge CBTS Integration**: The CBTS API integration uses Wirecard-era endpoints and credentials. The current production endpoints and credentials must be verified with the Cambridge Global Payments team.

2. **Spring Boot 2.x to 3.x**: Spring Boot 3.x requires Java 17+ and has breaking changes to Spring Batch (Spring Batch 5.x included). The `JobBuilderFactory` and `StepBuilderFactory` APIs used throughout the batch configuration classes were deprecated in Spring Batch 5 and removed.

3. **Java 8 to 17+**: General upgrade path, but the Spring Batch API changes are the key driver.

4. **SQL Schema Dependency**: The `core_ieft_transaction_journal` and `core_ieft_transaction_journal_addenda` tables are shared with other services. Schema changes must be coordinated.

5. **Credential Rotation Urgency**: The hardcoded CBTS credentials require immediate rotation before any other migration activities begin.

6. **Tests Skipped in CI**: Despite having a comprehensive QA test suite, tests have never been run in CI. Before upgrading, tests must be enabled and made to pass to create a regression baseline.

---

## 7. Lifecycle Recommendation

1. **Immediate**: Rotate hardcoded CBTS credentials and move to Azure Key Vault
2. **Short-term**: Enable integration tests in CI (`-Dmaven.test.skip=false`) and fix failing tests
3. **Short-term**: Verify Cambridge CBTS endpoint (`cbts-dev.amer1.wirecard.com`) is still valid; obtain production endpoint
4. **Medium-term**: Upgrade to Java 17 and Spring Boot 3.x; refactor Spring Batch job builders for v5 API
5. **Medium-term**: Migrate artifact publishing from Wirecard Nexus to Azure Artifacts
6. **Long-term**: Containerize batch jobs for Azure Container Jobs / AKS CronJobs
