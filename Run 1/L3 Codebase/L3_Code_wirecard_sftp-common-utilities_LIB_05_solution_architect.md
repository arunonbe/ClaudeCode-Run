# Solution Architect — wirecard_sftp-common-utilities_LIB

## Technical Architecture
- **Build**: Maven, Java 21
- **Framework**: Spring Boot Starter Batch + Spring Boot Starter Integration
- **SFTP**: Spring Integration SFTP (`spring-integration-sftp`) — uses Apache MINA SSHD (replaces legacy JSch)
- **Batch**: Spring Batch `Tasklet` implementations (step-level, not chunk-oriented)
- **Retry**: Spring Retry (`@Retryable` annotation)
- **Lombok**: `@Slf4j`, `@Getter`, `@Setter`, `@ToString`, `@Builder` annotations
- **Parent POM**: `com.parents:prepaid-parent:6.0.12` provides BOM for dependency versions

## API Surface (Library API)
| Component | Type | Description |
|---|---|---|
| `ImportSftpDownloadTasklet` | Spring Batch Tasklet | Constructor takes `SftpRemoteFileTemplate` + `BatchPathImportConfig` |
| `PublishSftpUploadTasklet` | Spring Batch Tasklet | Constructor takes `SftpRemoteFileTemplate` + `BatchPathPublishConfig` |
| `BatchCommonChannelConfig` | Spring `@Configuration` | Factory methods for `SessionFactory` and `SftpRemoteFileTemplate` |
| `DirectoryGenerator` | Spring Bean | Called at startup; creates local directories |
| `DirectoryGeneratorApp` | Spring component | Wires `DirectoryGenerator` to `@PostConstruct` or init profile |
| `BatchCommonConfig` | POJO | Configuration holder; injected by consuming service |
| `BatchPathImportConfig` | Interface | Contract for import path config; implemented by consuming service |
| `BatchPathPublishConfig` | Interface | Contract for publish path config; implemented by consuming service |
| `SftpCommonUtilitiesContext` | Spring `@Configuration` | Component scan context for the library |

## Security Posture

### Authentication
- Password authentication: `sessionFactory.setPassword(...)` — plaintext password from config
- Private key authentication: `sessionFactory.setPrivateKey(new ByteArrayResource(...))` — PEM key loaded from config property
- Both options supported; library uses whichever is non-empty (inverted null check — see below)

### Host Key Verification — Critical Defect
```java
// BatchCommonChannelConfig.java:38
sessionFactory.setAllowUnknownKeys(true);
```
This disables SSH host key verification entirely. Any server can impersonate the configured SFTP host. All consuming services (NAM-bank-agent, any other consumer) inherit this vulnerability. This must be treated as a **critical security defect** requiring immediate remediation.

### Logic Inversion Bug
```java
// BatchCommonChannelConfig.java:31-34
if(!StringUtils.hasLength(commonConfig.getPrivateKey())) {
    sessionFactory.setPrivateKey(new ByteArrayResource(...));
}
if(!StringUtils.hasLength(commonConfig.getPassword())) {
    sessionFactory.setPassword(commonConfig.getPassword());
}
```
`!StringUtils.hasLength(x)` returns `true` when the string is EMPTY or NULL — so private key and password are set ONLY when the value is empty/null, and NOT set when a value is actually provided. This is a **logic inversion bug**: authentication credentials are set when absent and not set when present. This would cause authentication failures in any real deployment using this method.

### Sensitive Data in `@ToString`
`BatchCommonConfig` has `@ToString` (Lombok) with `password` and `privateKey` fields — if any logging framework calls `.toString()` on this object, credentials are emitted in plaintext logs.

### Known CVEs
| Library | Version | Risk |
|---|---|---|
| Apache MINA SSHD (via spring-integration-sftp) | From prepaid-parent BOM | Check current version; SSHD has had CVEs in cipher negotiation |
| commons-codec | (from parent) | Generally safe |

## Technical Debt
1. Logic inversion bug in `BatchCommonChannelConfig` — private key and password set when empty, not when populated
2. `setAllowUnknownKeys(true)` — security defect, not just tech debt
3. `FileOutputStream` in `ImportSftpDownloadTasklet` not closed in try-with-resources — resource leak on exception
4. `@ToString` on `BatchCommonConfig` — credential exposure risk
5. `Files.walk()` without depth limit in `PublishSftpUploadTasklet` — unintended subdirectory traversal
6. `@Retryable` without explicit `@Retryable(maxAttempts=..., backoff=@Backoff(...))` — unpredictable retry behavior
7. `sftpTemplate.afterPropertiesSet()` called in `PublishSftpUploadTasklet` constructor with exception swallowed as WARN — SFTP template may be in broken state silently

## Gen-3 Migration Requirements
1. **Fix critical bugs immediately** (before any migration):
   - Invert boolean condition in credential-setting logic
   - Replace `setAllowUnknownKeys(true)` with proper known-hosts management
2. Add `@ToString.Exclude` to `password` and `privateKey` fields in `BatchCommonConfig`
3. Wrap `FileOutputStream` in try-with-resources in `ImportSftpDownloadTasklet`
4. Add explicit `@Retryable` configuration (maxAttempts, backoff, retryable exceptions)
5. Add depth limit to `Files.walk()` in `PublishSftpUploadTasklet`
6. Consider replacing SFTP-delete-on-download with SFTP-move-to-processed pattern for idempotency
7. Publish to Azure Artifacts or AWS CodeArtifact for cloud-native consumption

## Code-Level Risks
| File | Line | Risk |
|---|---|---|
| `BatchCommonChannelConfig.java` | 38 | `setAllowUnknownKeys(true)` — SFTP MITM risk; critical |
| `BatchCommonChannelConfig.java` | 31 | `!StringUtils.hasLength(commonConfig.getPrivateKey())` — inverted logic; key not set when provided |
| `BatchCommonChannelConfig.java` | 34 | `!StringUtils.hasLength(commonConfig.getPassword())` — inverted logic; password not set when provided |
| `ImportSftpDownloadTasklet.java` | 49 | `new FileOutputStream(...)` not in try-with-resources — resource leak |
| `PublishSftpUploadTasklet.java` | 37-40 | `afterPropertiesSet()` exception swallowed as WARN — silent SFTP misconfiguration |
| `BatchCommonConfig.java` | Class level | `@ToString` exposes `password` and `privateKey` in logs |
| `PublishSftpUploadTasklet.java` | 48 | `Files.walk(outputPath)` — no depth limit; could traverse unexpected subdirectories |
