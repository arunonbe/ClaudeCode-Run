# Data Architect — wirecard_sftp-common-utilities_LIB

## Data Stores
This is a library — it has no persistent data store of its own. It facilitates data movement between:

| Store | Role | Notes |
|---|---|---|
| Remote SFTP server | Source (import) / Destination (export) | Bank partner SFTP (Sunrise, PDS, etc.) |
| Local filesystem (input dir) | Download staging | Files land here from SFTP before batch processing |
| Local filesystem (output dir) | Upload staging | Batch-generated files wait here for SFTP upload |
| Local filesystem (archive dir) | Post-upload retention | Files moved here after successful upload |
| Local filesystem (processed/failed dirs) | Batch flow control | Managed by calling Spring Batch steps |

## Schema / Data Model
No database schema. The library manages file streams and filesystem paths.

Key configuration data model (`BatchCommonConfig`):
```
host: String
port: int
username: String
password: String  (sensitive — must not be logged)
privateKey: String  (sensitive — PEM key material; must not be logged)
pollingRate: long
```

`BatchPathImportConfig` interface defines:
```
input: String (local path)
processed: String (local path)
failed: String (local path)
remoteDirectory: String (SFTP path)
archive: String (local path for received files)
getAllDirectoryPaths(): Set<String>
```

`BatchPathPublishConfig` interface defines:
```
output: String (local path)
archive: String (local path for sent files)
remoteDirectory: String (SFTP path)
pageSize: Integer
maxItemCount: Integer
getAllDirectoryPaths(): Set<String>
```

## Sensitive Data Handled
The library itself is transport-layer only, but the files it moves contain payment-sensitive data:

| File Type (handled by consumers) | Sensitive Fields |
|---|---|
| NACHA ACH origination/direct-deposit | Bank routing numbers, bank account numbers, individual names, amounts |
| Wire drawdown files | Bank routing numbers, beneficiary account data, amounts |
| Check issuance files | Payee names, amounts, MICR data |
| Customer data files | Name, address, account reference |

**The library itself logs only filenames and upload status** — no file content is logged.

`BatchCommonConfig.password` and `BatchCommonConfig.privateKey` are SFTP credentials that must not be exposed in logs. The `@ToString` annotation on `BatchCommonConfig` is present — if this object is logged, password and private key would be printed. This is a **security risk**.

## Encryption
- **In transit**: SFTP protocol (SSH-2) provides transport encryption for all file transfers
- **Host key verification**: DISABLED via `setAllowUnknownKeys(true)` — encrypted channel to potentially wrong server
- **At rest (local staging)**: No encryption observed for local input/output/archive directories — payment files stored in plaintext on batch server filesystem
- **Credential storage**: `privateKey` field holds PEM key as a String in `BatchCommonConfig` — key material in JVM heap; no secure memory clearing observed

## Data Flow
```
Bank SFTP Server
  │
  ├── SSH/SFTP (encrypted channel, unverified host key)
  │
  │  ImportSftpDownloadTasklet
  │  ├── list remote directory
  │  ├── download file to local input/
  │  └── delete remote file
  │
  └── Local filesystem (input/) ──▶ Spring Batch consumer (in calling service)

Spring Batch producer (in calling service)
  ──▶ Local filesystem (output/)
         │
  PublishSftpUploadTasklet
  ├── scan output/ directory
  ├── upload each file to SFTP remote/
  └── move local file to archive/
         │
  Bank SFTP Server (SSH/SFTP)
```

## Data Quality / Retention
- No file integrity check (MD5/SHA) performed by the library
- Files in `archive/` directory accumulate indefinitely unless calling service implements purge
- Failed downloads/uploads leave partial files in `input/` or `output/` directories — no cleanup mechanism observed in library
- `@Retryable` retry count defaults to 3; partial writes on retry are possible

## Compliance Gaps
1. `setAllowUnknownKeys(true)` — SFTP host verification disabled; violates PCI DSS Requirement 4.2 and NACHA file security requirements
2. `@ToString` on `BatchCommonConfig` — password and privateKey would appear in any accidental `toString()` log call
3. No file checksum verification — data integrity cannot be guaranteed for payment files
4. Local staging files (containing payment data) stored unencrypted on filesystem
5. `FileOutputStream` in `ImportSftpDownloadTasklet.doWithInputStream()` not explicitly closed — potential handle leak and incomplete file on exception
