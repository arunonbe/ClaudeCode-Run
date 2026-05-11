# prepaid-batch-framework_LIB — Enterprise Architect View

## 1. Architectural Classification

`prepaid-batch-framework_LIB` is a **shared infrastructure library** in the enterprise architecture tier classification. It provides the execution container for all batch workloads across the prepaid platform. As such, it is an architectural **bottleneck** — any defects in the framework affect all batch jobs that depend on it.

The framework architecture follows a classic **plugin-based batch processing pattern**:
- The core engine (impl) is generic and knows nothing about specific business logic
- Business logic is injected via module plugins loaded from an external registry
- Infrastructure services (FTP, DB, security, profile) are abstracted behind service library interfaces

## 2. Enterprise Context Placement

```
[ActiveBatch Scheduler]
        |
        | (CLI invocation)
        v
[prepaid-batch-framework_LIB]
        |
        |-- Module Registry (XML) -- D:\c-base\config\...
        |
        |-- Plugin Modules (CMFA-*, submithierarchy, submitinquiry)
        |
        |-- Service Layer
             |-- Profile Service (XML-RPC)  --> [profile_SVC]
             |-- Repository Service (XML-RPC)
             |-- Job Service (XML-RPC)
             |-- Security Service (XML-RPC)
             |-- Director Service (config discovery)
        |
        |-- Database Layer
             |-- ecountcore (SQL Server via Director/DBCP)
             |-- ecountcore_process (SQL Server via Director/DBCP)
        |
        |-- FTP Layer --> [Banking Partners / CMFA host]
```

## 3. Module Architecture

The framework implements a **Strategy pattern** for module execution via `ModuleProcessorContext.java`, which holds references to three concrete processors:

| Processor | Strategy | Use Case |
|---|---|---|
| `JavaModuleProcessorImpl` | Direct Java invocation | Custom Java batch logic |
| `SpringBatchModuleProcessorImpl` | Spring Batch job execution | ETL-style multi-step batch jobs |
| `BcpDataOperationsModuleProcessorImpl` | SQL Server BCP | High-volume bulk data import/export |

The `FTP-Library` bean (`applicationContext.xml` lines 62–67) provides all modules with a single FTP abstraction backed by four underlying service clients. This centralizes FTP behaviour, which is good for maintainability but creates a single point of failure.

## 4. Technology Debt and Modernization Assessment

### 4.1 Framework Technology Stack Age
The framework is built on a 2014-era technology stack (commit message: `@author TCS`, `PrepaidBatchMain.java` line 36; creation dates in Javadoc headers). It predates Spring Boot by several years.

| Component | Current | Modern Equivalent |
|---|---|---|
| Spring Framework | 2.5.6 | Spring Batch 5.x on Spring Boot 3.x |
| Job orchestration | ActiveBatch (external) | AWS Batch / Azure Batch / Kubernetes Jobs |
| FTP | Apache Commons Net (via `IBatchFTPLibrary`) | SFTP via Apache MINA SSHD (`prepaid-parent_PARENT` has `sshd-sftp` 2.13.0) |
| Config discovery | Director Service (XML-RPC) | Spring Cloud Config / Azure App Configuration |
| Service calls | XML-RPC | REST (Feign client, as available in `prepaid-parent_PARENT`) |

### 4.2 Architectural Coupling Issues
- **Hardcoded Windows paths**: `MODULE_REGISTRY_PATH = "D:\\c-base\\config\\..."` and log4j path in `processBatch.bat` create tight coupling to the on-premises Windows deployment model. This prevents containerization without significant refactoring.
- **XML-RPC service communication**: All inter-service calls use XML-RPC, a protocol from 1998. Modern Onbe services use REST. This creates an integration protocol impedance mismatch that will grow worse as new services migrate to REST.

## 5. PCI DSS Compliance Architecture

The batch framework processes settlement data (CMFA files, BCP operations on `ecs_encashment_settlement_file` table) that may contain cardholder data. Architectural compliance considerations:

| Requirement | Status | Detail |
|---|---|---|
| Req 1.3 — Network isolation | Unknown | No network topology data in repo; CDE boundary for batch server must be verified |
| Req 3.4 — Render PAN unreadable | Risk | BCP import files at `bcpInputFilePath` may contain PAN data; encryption at rest must be verified |
| Req 6.3.3 — Patch vulnerabilities | Fail | Spring 2.5.6, Log4j 1.2.15, Commons-beanutils 1.7.0 all have critical CVEs |
| Req 7 — Restrict access | Partial | Security service integration present, but no evidence of file-level access control |
| Req 10 — Logging | Partial | Log4j present but config not in repo; log integrity controls unknown |

## 6. NACHA / Reg E Compliance Considerations

The CMFA batch modules are part of the ACH/settlement file exchange pathway. Relevant compliance requirements:
- **NACHA Rule R10/R29**: Return files processed by inquiry modules must be processed within defined windows (2 business days for unauthorized returns). The framework provides no built-in deadline enforcement — this is fully delegated to the scheduler.
- **Reg E Section 1005.11**: Error resolution time limits (10/45 business days). Settlement file processing timeliness feeds directly into Reg E compliance.

## 7. Strategic Recommendations

1. **Migrate to Spring Batch 5.x on Spring Boot 3.x**: Aligns with `prepaid-parent_PARENT` standards; enables containerization.
2. **Replace FTP with SFTP**: Use Apache MINA SSHD (already managed in `prepaid-parent_PARENT`) for secure file transfer compliance with PCI DSS Requirement 4.2.
3. **Replace XML-RPC with REST**: Align inter-service communication with modern Onbe platform conventions.
4. **Externalize config**: Replace hardcoded Windows paths with Spring Boot external configuration management.
5. **Enable CI tests**: Remove `-Dmaven.test.skip=true` from `.gitlab-ci.yml` and implement at minimum smoke tests for the core `BatchProcessorImpl` logic.
