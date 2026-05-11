# Business Analyst — wirecard_sftp-common-utilities_LIB

## Business Purpose
A shared Spring Boot library that provides reusable SFTP file transfer capabilities for any batch processing service in the Onbe/Wirecard platform. It abstracts the SFTP download and upload mechanics into configurable Spring Batch Tasklet components, allowing services such as NAM-bank-agent to exchange payment files with bank partners without re-implementing SFTP logic.

## Capabilities
- **SFTP Download Tasklet** (`ImportSftpDownloadTasklet`): Connects to a remote SFTP server, lists a configured directory, downloads each non-directory file to a local input directory, and deletes the remote file after successful download
- **SFTP Upload Tasklet** (`PublishSftpUploadTasklet`): Scans a local output directory, uploads each file to the configured remote SFTP directory, and archives the file locally after successful upload
- **Directory initialisation** (`DirectoryGenerator`): Creates required local filesystem directories (input, processed, failed, archive, output) on application startup, avoiding runtime directory-not-found errors
- **SFTP session factory** (`BatchCommonChannelConfig`): Configures a `DefaultSftpSessionFactory` supporting both password and private-key authentication
- **Retry support**: Both tasklets annotated with `@Retryable` — transient SFTP failures trigger automatic retry
- **Path configuration interfaces**: `BatchPathImportConfig` and `BatchPathPublishConfig` define the contract for directory layout; implementing services inject their specific paths

## Key Configuration Properties (via BatchCommonConfig)
| Property | Description |
|---|---|
| host | SFTP server hostname |
| port | SFTP server port |
| username | SFTP username |
| password | SFTP password (optional if private key used) |
| privateKey | PEM private key content (optional if password used) |
| pollingRate | Polling interval for scheduled SFTP polling |

## Business Rules
1. Only non-directory, non-symlink files are downloaded (file type check on `DirEntry.attributes`)
2. Remote file is deleted after successful download — "consume and delete" pattern
3. Local file is moved to archive after successful upload — provides audit trail
4. Upload fails with `MessagingException` if SFTP send fails — propagates to Spring Batch step failure
5. Both tasklets annotated `@Retryable` — default Spring Retry behavior applies (3 attempts)
6. Compiled with Java 21 (`maven.compiler.source=21`, `maven.compiler.target=21`)

## Business Flows
1. **File import (bank → platform)**:
   SFTP remote dir → `ImportSftpDownloadTasklet` downloads → local input dir → Spring Batch reader processes
2. **File export (platform → bank)**:
   Spring Batch writer creates file → local output dir → `PublishSftpUploadTasklet` uploads → SFTP remote dir; local file → archive dir

## Compliance Relevance
- Library handles payment files (ACH, wire, check) that contain sensitive financial data
- SFTP with private-key or password authentication supports PCI DSS Requirement 4.2 (secure transmission)
- `setAllowUnknownKeys(true)` in `BatchCommonChannelConfig` — **disables SFTP host key verification** — critical compliance gap for file-based payment exchange (see Risks)
- `@Retryable` on SFTP operations ensures transient failures don't cause silent data loss

## Risks
1. `setAllowUnknownKeys(true)` — host key verification is disabled; any server can impersonate the configured host without detection
2. FileOutputStream in `ImportSftpDownloadTasklet` is not explicitly closed in the `doWithInputStream` callback — potential file handle leak if `FileCopyUtils.copy` throws
3. `@Retryable` without explicit retry configuration — default retry behavior may attempt to re-upload or re-download partially written files
4. No file integrity check (checksum/hash) observed after download or before upload — file corruption would go undetected
5. Upload task uses `Files.walk()` without depth limit — could traverse subdirectories unintentionally
