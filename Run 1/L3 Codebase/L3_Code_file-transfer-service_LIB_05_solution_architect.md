# Solution Architect Report — file-transfer-service_LIB

## 1. Complete Class and Method Inventory

### Package: `com.citiprepaid.process`

| Class | Key Methods | Purpose |
|---|---|---|
| `FileTransferProcessMain` | `main(String[])`, `xContentFlow(...)`, `callToUtilityClass(...)`, `areDone(List<Future<Controller>>)`, `initialize(boolean)`, `processExceptions()` | Entry point; orchestrates all folder-type processing and xContent flow |
| `SFtpConnection` | `SFtpConnection()`, `SFtpConnection(String, String, String)`, `SFtpConnection(String, String, File)`, `SFtpConnection(String, String, String, File)`, `connectUserPwd()`, `connectUserPwdXContentAutomation()`, `connectPrivateKey()`, `connectPrivateKeyPassphrase()`, `disconnect()`, `createDir(String, String)`, `getFilesListing(String)`, `getDirectoryListing(String)`, `isConnected()`, `connect()`, `isValidRemotePath(String)`, `downloadFile(String, String, String)`, `deleteFile(String, String)`, `uploadDirectory(File, String)`, `uploadDirectory(File, String, int, int)`, `uploadFile(String, String, String)`, `uploadFile(java.io.File, String)`, `uploadFile(java.io.File)`, `connected(SftpConnectedEvent)`, `disconnected(SftpDisconnectedEvent)`, `getFtpHostname()`, `setFtpHostname(String)`, `getFtpUsername()`, `setFtpUsername(String)`, `getFtpPassword()`, `setFtpPassword(String)`, `makeDir(ArrayList)` | SFTP connection and file operation wrapper around JScape |
| `TransferService` | `process(FolderType)`, `areDone(List<Future<RequestProcessorThread>>)`, `load(FolderType)`, `loadPullFolder(String)`, `loadPushFolder(String)` | Thread pool orchestrator for individual folder-type processing |
| `Controller` | `Controller(FolderType)`, `run()`, `runCycle(FolderType)` | Runnable wrapper that invokes `TransferService.process()` |
| `RequestProcessorThread` | (inferred — not read directly) | Worker thread processing a batch load of folder items |
| `Load` | `loadSFTPFolders(String)`, `loadFileServerFolders(String)` | (inferred from usage in `TransferService.java` lines 204, 224) Loads folder records from database |
| `Sync` | (not read) | Synchronization utility |

### Package: `com.citiprepaid.process.config`

| Class | Key Methods | Purpose |
|---|---|---|
| `Configuration` | `getInstance()`, `isLoadedSuccessfully()`, `getProcessType()`, `getMaxThreads(String)`, `getMainThreads()`, `getMaxTries(String)`, `getMaxTriesSleep(String)`, `getThreadLoad(String)`, `getRecordsRetrieve(String)`, `getSimpleTransferRecordsRetrieve()`, `getMaxTriesOnFailure(String)`, `getMaxDaysProcessOnFailure(String)`, `getMaxDBFailureTries(String)`, `getMaxConnectionSFTPServer()`, `getRemoteServer()`, `getRemoteServerUser()`, `getRemoteServerPwd()`, `getRemotePath()`, `getLocalPath()`, `getArchivePath()`, `getSftpServerConnectionTimeout()`, `getFolderName(FolderType)`, `getRequestFolder()`, `getReplyFolder()`, `getErrorFolder()`, `getExceptionFolder()`, `getReportFolder()`, `getFileSeparator()`, `getExcludeFolders()`, `getExcludeReplyFolders()`, `getExcludeErrorFolders()`, `getExcludeExceptionFolders()`, `getExcludeReportFolders()`, `getExcludeBusinessReportFolders()`, `getExcludeBusinessPgmMatFolders()`, `getExcludeStatusFolders()`, `getPrivateKeyFilePath()`, `getPrivateKeyPassphrase()`, `getConnectRemote()`, `getCPSExceptionCodes()` | Singleton properties loader — reads all config from `D:\c-base\config\FileTransferService\configuration.properties` |
| `ConfigurationXContentAutomation` | (inferred from usage) | Configuration loader for xContent flow |
| `FolderType` | (enum) | Enum of folder type codes: REQUEST, HIERARCHYREQUESTS, REPLY, ERROR, EXCEPTION, REPORTS, BUSINESSREPORTS, BUSINESSPGMMAT, STATUS |
| `IProcess` | `process(FolderType)` | Interface for process execution |

### Package: `com.citiprepaid.process.data`

| Class | Key Methods | Purpose |
|---|---|---|
| `Utility` | `getSFtpConnection()`, `setSFtpConnection(SFtpConnection)`, `getRemoteDirList()`, `setRemoteDirList(ArrayList)`, `getLocalDirList()`, `setLocalDirList(ArrayList)`, `isHasErrors()`, `setHasErrors(boolean)`, `getProcessingState()`, `getProcessedState()` | Static shared state holder (thread safety risk) |

### Package: `com.citiprepaid.process.db`

| Class | Key Methods | Purpose |
|---|---|---|
| `SftpProcessStatusDTO` | Getters/setters for: `id`, `hostname`, `filepath`, `filetype`, `filename`, `programid`, `processstatus`, `datecreated` | Data transfer object for `sftp_process_status` table |
| `SftpProcessStatusDao` | `getSftpProcessExceptions(String)`, `insertSftpProcessState(SftpProcessStatusDTO)`, `upateSftpProcessState(SftpProcessStatusDTO)`, `deleteSftpProcessState(SftpProcessStatusDTO)` | DAO interface |
| `SftpProcessStatusDaoImpl` | (implements DAO + inner classes `SftpProcessQuery`, `SftpProcessUpdate`) | Spring JdbcTemplate-based DAO implementation |
| `SftpProcessStatusBO` | `getSftpProcessExceptions(String)`, `updateSftpProcessState(SftpProcessStatusDTO)` | Business object layer wrapping DAO |
| `SpringUtils` | (inferred — loads Spring application context) | Spring context bootstrapper for `spring.xml` |

### Package: `com.citiprepaid.process.Helper`

| Class | Key Methods | Purpose |
|---|---|---|
| `XContentAutomationHelper` | `findSubFolders(File)`, `findTheFiles(String)`, `webBoxFileTransfer(File, String, SFtpConnection)`, `fileTransferForReIndexing(File, ConfigurationXContentAutomation)`, `deleteFiles(File)` | xContent flow helper |

### Package: `com.citiprepaid.process.request`

| Class | Key Methods | Purpose |
|---|---|---|
| `IFolder` | `getType()`, `getDescription()` | Interface representing a folder record |
| `FolderImpl` | (implements IFolder) | Concrete folder record |

### Test Package: `com.ecount.fts`

| Class | Key Methods | Purpose |
|---|---|---|
| `SFtpExample` | (inferred) | Single test class — never executed in CI |

---

## 2. Security Vulnerability Assessment

### VULN-001 — CRITICAL: Plaintext SFTP Password Logged at INFO Level

**Location**: `SFtpConnection.java` lines 83–84, 109–110

```java
LOG.info("... ftpHostname, ftpUsername,ftpPassword" + " - " + ftpHostname + " " + ftpUsername + " " + ftpPassword); // remove
```

**Risk**: SFTP credentials (username + password) are written to log files at INFO level. Log files are often shipped to centralized logging systems (Splunk, Elasticsearch) where they may be accessible by broader teams. This violates PCI DSS Requirement 8.3.1 (individual authentication) and constitutes credential exposure.

**Remediation**: Remove all log statements that include `ftpPassword`. Replace with masked output (e.g., `"password=[REDACTED]"`). Priority: **IMMEDIATE**.

---

### VULN-002 — CRITICAL: SFTP Password Stored in Plaintext Properties File

**Location**: `configuration.properties` line 41 (`remoteServerPwd=` — value absent in repo but loaded from `D:\c-base\config\`)

**Risk**: The password is stored in a plaintext `.properties` file on the filesystem. Any user with filesystem access to the application server can read SFTP credentials. Violates PCI DSS Requirement 8.3.

**Remediation**: Migrate credential retrieval to Azure Key Vault or an equivalent secrets manager. Implement Managed Identity where possible. Priority: **HIGH**.

---

### VULN-003 — CRITICAL: log4j 1.2.12 (End-of-Life, Multiple CVEs)

**Location**: `pom.xml` line 99

**Risk**: log4j 1.x has not received security patches since 2015. Known vulnerabilities include deserialization attacks via JMSAppender (CVE-2019-17571) and SocketAppender. While the infamous Log4Shell (CVE-2021-44228) affects log4j 2.x, the 1.x line has its own separate critical CVEs.

**Remediation**: Replace `log4j:log4j:1.2.12` with `ch.qos.logback:logback-classic` or upgrade to log4j2 with appropriate configuration. Also update `commons-logging:1.0.4` to SLF4J bridge. Priority: **HIGH**.

---

### VULN-004 — HIGH: Spring Framework 2.5.6 (Severely Outdated)

**Location**: `pom.xml` lines 109–113

**Risk**: Spring 2.5.6 (2008) has numerous known CVEs and is completely unsupported. It does not support modern security hardening features such as bean validation improvements, SpEL injection protections, or CSRF protection.

**Remediation**: Upgrade to Spring Boot 3.x (Spring Framework 6.x). This is a significant refactoring effort. Priority: **HIGH** (plan for migration sprint).

---

### VULN-005 — HIGH: JScape Commercial Library Version 9.3.21 (Unknown CVE Exposure)

**Location**: `pom.xml` line 153; `jscapeLicense/sftp.zip`

**Risk**: The JScape SFTP library is a commercial product bundled as a binary ZIP in the repository. Version 9.3.21 may have known vulnerabilities. Since it is a commercial binary, the usual open-source CVE databases may not cover it fully. The bundled ZIP in the repository raises supply chain concerns.

**Remediation**: Evaluate replacement with Apache MINA SSHD or SSHJ (open-source, well-maintained). Remove the commercial binary from the repository. Priority: **MEDIUM** (evaluate licensing cost vs. migration cost).

---

### VULN-006 — HIGH: No Payload-Level Encryption

**Location**: All upload/download methods in `SFtpConnection.java`

**Risk**: Files containing potentially sensitive program data are transferred via SFTP (transport-level encryption only). If files contain PANs or cardholder-adjacent data, PCI DSS Requirement 4.2.1 requires encryption of PAN during transmission. Transport-level encryption alone may not satisfy the requirement if the file content is sensitive and must be encrypted at the payload level.

**Remediation**: Audit the content of files transferred through each folder type. Where PANs are present, implement PGP/GPG payload encryption. Priority: **HIGH** (requires content audit first).

---

### VULN-007 — MEDIUM: Thread-Unsafe Static Shared State in Utility Class

**Location**: `data/Utility.java` — `setSFtpConnection()`, `setRemoteDirList()`, `setLocalDirList()`

**Risk**: These static setters are called from `FileTransferProcessMain.java` (lines 164–168) and from `callToUtilityClass()` (line 522–527) within a concurrent processing context. Multiple worker threads share the same `Utility` instance. If the connection is reset mid-processing by one thread, other threads using the stale reference will fail.

**Remediation**: Replace static shared state with thread-local variables or inject connection/state objects directly into worker threads. Priority: **MEDIUM**.

---

### VULN-008 — MEDIUM: Commented-Out Code Containing IP Addresses and Credentials

**Location**: `configuration.properties` lines 37–38; `SFtpConnection.java` line 39; `GPDBHelper.cs` (finance-webservice)

**Risk**: Commented-out code contains live IP addresses and credential hints (e.g., `#hostname = PPA_UAT_SFTP@169.175.98.88`, `#"10.2.6.122","service","redrain"`). Even in comment form, these expose network topology and test credentials.

**Remediation**: Remove all commented-out credential and IP address references. Priority: **MEDIUM**.

---

### VULN-009 — LOW: JUnit 3.8.1 and Single Unused Test

**Location**: `pom.xml` line 93; `src/test/java/com/ecount/fts/SFtpExample.java`

**Risk**: The testing framework is 22 years old and the single test file is in a different package namespace (`com.ecount.fts`) from the main code (`com.citiprepaid.process`), suggesting it is a placeholder. No meaningful test coverage exists.

**Remediation**: Write unit tests for `Configuration`, `SFtpConnection`, `TransferService`, and `SftpProcessStatusDaoImpl`. Upgrade test framework to JUnit 5. Remove the CI test skip flags. Priority: **LOW** (foundational technical debt).

---

## 3. Technical Debt Summary

| Debt Item | Severity | Effort |
|---|---|---|
| Java 1.6 source/target | CRITICAL | HIGH — full recompile, dependency audit |
| Spring 2.5.6 | CRITICAL | HIGH — full rewrite to Spring Boot |
| log4j 1.2.12 | CRITICAL | MEDIUM — dependency swap |
| Password in logs (VULN-001) | CRITICAL | LOW — remove log statements |
| Plaintext credentials (VULN-002) | CRITICAL | MEDIUM — integrate Key Vault |
| No tests / CI test skip | HIGH | MEDIUM — write tests, enable CI |
| Hardcoded Windows paths | HIGH | MEDIUM — externalize via config |
| JScape binary in repo | HIGH | MEDIUM — replace library |
| No payload encryption | HIGH | HIGH — content audit + PGP layer |
| Static shared state (thread safety) | MEDIUM | MEDIUM — refactor to thread-local |

---

## 4. Remediation Priority Matrix

| Priority | Action | Owner |
|---|---|---|
| P1 — Immediate | Remove password logging in `SFtpConnection.java` | Dev team |
| P1 — Immediate | Rotate all SFTP credentials exposed via logs | Security/Ops |
| P1 — Sprint 1 | Migrate credentials to Azure Key Vault | Dev + Infra |
| P2 — Sprint 1–2 | Upgrade log4j 1.x to logback | Dev team |
| P2 — Sprint 2 | Audit file content for PAN/sensitive data | Security + Compliance |
| P3 — Q3/Q4 | Migrate Spring 2.5.x to Spring Boot 3.x | Platform Engineering |
| P3 — Q3/Q4 | Replace JScape with MINA SSHD | Dev team |
| P4 — Roadmap | Full service modernization to Azure Data Factory / Azure SFTP | Enterprise Architecture |
