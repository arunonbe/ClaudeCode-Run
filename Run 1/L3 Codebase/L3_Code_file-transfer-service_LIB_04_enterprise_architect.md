# Enterprise Architect Report — file-transfer-service_LIB

## 1. Platform Generation Assessment

The `file-transfer-service_LIB` is a **first-generation, pre-cloud, on-premises batch service** from the Citi Prepaid era (pre-Onbe rebranding). Key indicators:

| Indicator | Evidence |
|---|---|
| Java 1.6 source/target | `pom.xml` lines 30–33: `<source>1.6</source><target>1.6</target>` |
| Spring 2.5.6 | `pom.xml` line 111 — Spring Framework from 2008 |
| log4j 1.2.12 | `pom.xml` line 99 — end-of-life since 2015 |
| JScape 9.3.21 | Commercial SFTP library with binary license ZIP in repo |
| Hardcoded `D:\c-base\` paths | Windows-only, single-server deployment model |
| No Spring Boot | Uses raw Spring XML IoC (`spring.xml`) |
| `com.citiprepaid` package namespace | Predates Northlane / Onbe branding |
| JUnit 3.8.1 | Test framework from 2002 |

This places the codebase as approximately **15–20 years old** in design generation, written during the Citi Prepaid period and inherited through the Wirecard and Northlane acquisitions into Onbe.

---

## 2. Role in Enterprise Architecture

### 2.1 Integration Tier Function

`file-transfer-service_LIB` occupies the **integration / data-exchange tier** of Onbe's card processing architecture. It is the primary mechanism for exchanging structured data files with external card bureau partners and processors via SFTP.

```
[Card Bureau / Processor (External)]
          |
          | SFTP (SSH-2, JScape)
          v
[file-transfer-service_LIB]  <-- This service
          |
          | File system operations
          v
[Internal Onbe Processing Systems (jobsvc, ecount-system)]
          |
          | Director-configured JDBC
          v
[jobsvc_database (SQL Server)]
```

### 2.2 Upstream Dependencies

| Dependency | Type | Version | Risk Level |
|---|---|---|---|
| `director-client` | Internal library | 1.0.11 | MEDIUM — internal versioned dependency |
| `ecount-system` | Internal library | 2.0.0 | MEDIUM — core Onbe platform library |
| `jscape:jscape` | Commercial 3rd party | 9.3.21 | HIGH — commercial license, bundled binary |
| `spring` | Framework | 2.5.6 | CRITICAL — EOL, no security patches |
| `log4j` | Logging | 1.2.12 | CRITICAL — EOL, CVE exposure |
| External SFTP Server | Infrastructure | N/A | HIGH — single point of failure at `169.171.30.166` |
| Director service | Onbe platform | N/A | MEDIUM — handles DB connection pooling |
| `jobsvc_database` | SQL Server | N/A | HIGH — shared database with job service |

### 2.3 Downstream Consumers

Files downloaded from the SFTP server are placed on the local file share (`c:/temp/b2c/`), where downstream Onbe processing services consume them. Files uploaded to SFTP are consumed by external processors/card bureaus.

---

## 3. Architecture Patterns

### 3.1 Batch Processing Pattern

The service implements a **fixed-schedule batch sweep** pattern:
1. Connect to SFTP
2. Enumerate all program directories
3. For each folder type, spawn a worker thread pool
4. Each thread processes a batch ("thread load") of folder items
5. Disconnect and exit

This pattern is functionally similar to a Spring Batch architecture but predates it — it is hand-rolled using raw `java.util.concurrent.ExecutorService`.

### 3.2 Thread-Per-Folder-Type Pattern

`FileTransferProcessMain.java` (lines 181–296) processes each of the 9 folder types sequentially as separate thread-pool submissions, waiting for each to complete before starting the next. This is serialized at the folder-type level but parallelized within each folder type via the thread pool.

### 3.3 Singleton Configuration Pattern

`Configuration.java` uses a classic double-checked non-synchronized singleton (`if (instance == null)`, line 77). This is not thread-safe in Java 1.4 memory model but Java 5+ memory model makes it functionally safe due to JVM initialization guarantees in practice.

---

## 4. Fit / Gap Analysis Against Onbe Target Architecture

| Dimension | Current State | Target State Gap |
|---|---|---|
| Deployment | Windows batch JAR on bare metal | Containerized (Docker/K8s) or Azure Functions |
| Configuration | Hardcoded filesystem paths | Azure App Configuration / Key Vault |
| Secrets | Plaintext properties file | Azure Key Vault with Managed Identity |
| Observability | log4j 1.x file logs | Structured JSON logging → Azure Monitor |
| File Transfer Protocol | JScape SFTP library | Azure Blob / SFTP for Storage or Azure Data Factory |
| CI/CD | GitLab CI with test skip | GitHub Actions with full test execution |
| Error Handling | Exit code 1 | Dead-letter queue / alerting |
| Resilience | Single SFTP endpoint | Multi-region SFTP with automatic failover |

---

## 5. Migration Complexity Assessment

Migration complexity is rated **HIGH** for the following reasons:

1. **Commercial JScape Library**: The `jscape:jscape` 9.3.21 dependency is a commercial product with a license ZIP bundled in the repository (`jscapeLicense/sftp.zip`). Migration requires either license renewal/upgrade or replacement with an open-source SSH library (Apache MINA SSHD, JSch/SSHJ).

2. **Spring 2.5.6 XML Configuration**: The Spring XML-based IoC (`spring.xml`) and Spring 2.5.x API would need to be completely rewritten to Spring Boot 3.x. The `Director-configured DBCP datasource` pattern is specific to the Onbe internal Director service.

3. **Java 1.6 Binary Compatibility**: Upgrading to Java 17 or 21 would require audit of all deprecated/removed APIs used across the dependency tree.

4. **Database Coupling**: The service depends on the `jobsvc_database.sftp_process_status` table which is shared with other services. Schema migrations must be coordinated.

5. **No Unit Tests**: The CI pipeline explicitly skips tests. There is only one test class (`SFtpExample.java`) and it appears to be a placeholder. Any refactoring has zero automated test coverage for regression detection.

6. **Thread Safety Issues**: The `Utility` class uses static mutable shared state (`setSFtpConnection`, `setRemoteDirList`) accessed from multiple threads. This pattern is fragile and would need to be refactored to thread-local or connection-scoped state management.

---

## 6. Integration with Onbe Ecosystem

The service integrates with the `xPlatform` content management system (via the xContent flow) and the `jobsvc` job service infrastructure. It is a foundational component in the legacy `ecount` platform stack which includes:
- `ecount-system_LIB`
- `director-client_LIB`
- `jobservice_SVC`
- `xplatform_LIB`

This tightly couples `file-transfer-service_LIB` to the Onbe legacy stack. Any modernization must account for these dependencies.

---

## 7. Lifecycle Recommendation

Given the platform generation assessment, this service is a candidate for **Phase 2 modernization** — meaning it should be replaced rather than upgraded. The recommended target state is:

- Replace with an Azure Logic App or Azure Data Factory pipeline for SFTP-to-Blob file ingestion
- Use Azure Blob Storage as the intermediate file exchange layer
- Integrate with Azure Key Vault for SFTP credential management
- Retire the `sftp_process_status` table in favor of Azure Table Storage or Cosmos DB audit logging

However, due to the card-bureau SFTP dependencies and the lack of tests, migration risk is high and requires dedicated effort to map all external partner SFTP contracts before decommissioning.
