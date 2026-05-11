# Data Architecture — om-content-management-api

## Data Stores
| Store | Technology | Purpose |
|-------|-----------|---------|
| Azure Blob Storage | Azure SDK `azure-storage-blob` | Primary store for XContent files |
| GitHub Repository (`OnbeEast/xContent-recipient`) | GitHub REST API v3 | Source-of-truth content repository (optional, feature-flagged) |
| Azure App Configuration | Azure SDK | Config, feature flags, secrets references |
| Azure Key Vault | Via App Config KV provider | Secrets (blob connection string, GitHub token) |

This service has **no relational database**.

## Data Managed
| Asset | Store | Notes |
|-------|-------|-------|
| HTML templates | Azure Blob | UI templates for recipient web; `text/html;charset=UTF-8` |
| SVG, CSS, JS, JSON files | Azure Blob | UI static assets |
| PNG, JPG, GIF (images) | Azure Blob | Promotional images |
| Properties files | Azure Blob | i18n / config files |
| Committed file versions | GitHub `xContent-recipient` repo | Version-controlled copy when feature flag enabled |

## Sensitive Data
- Azure Blob Storage **connection string** — sourced from App Config KV; must not appear in logs or responses.
- GitHub **Personal Access Token** (`github.token`) — injected via `@Value`; sourced from App Config.
- `LogSanitizer.java` — utility class sanitises log output; content file names may contain user-controlled path segments.

## Encryption
- Azure Blob Storage: Azure-managed encryption at rest (AES-256 by default on all Azure Storage accounts).
- Connection string includes credentials — transmitted over HTTPS to Azure SDK; not logged (protected by `LogSanitizer` and App Config secrets).
- GitHub API: HTTPS-only (`https://api.github.com`); Bearer token authentication.
- No application-level file encryption — content files stored in plaintext in blob storage.

## Data Flow
- Upload path: multipart HTTP → `XContentManagementController` → `FileUploadService` → `AzureBlobService.uploadFileToAzureContainerWithLease()` → Azure Blob; optionally → `GitHubAPIService.createOrUpdateFileInGitHub()` → GitHub.
- Delete path: `XContentManagementController` → `FileUploadService.deleteXContentFile()` → `AzureBlobService.deleteBlob()` → Azure Blob.
- Blob lease: acquired for 15 seconds before upload; released after; prevents concurrent overwrites to the same blob path.
- Content type inference: `AzureBlobService.getContentTypeForFile()` → Spring `MediaTypeFactory` or hardcoded for SVG/HTML/properties.

## Data Quality / Retention
- No versioning on Azure Blob (unless Azure Blob versioning is enabled at the storage account level — not configured here).
- GitHub commit history provides version history when the GitHub feature is enabled.
- No deletion audit log — delete operations are not recorded beyond application logs.
- No TTL or lifecycle policy observed in the service code.

## Compliance Gaps
- No file content scanning (malware, sensitive data) before upload — malicious HTML or scripts could be uploaded.
- `targetFilePath` from the upload request passed to Azure Blob client — if path traversal characters (`../`) are not blocked by `FileValidator`, a malicious caller could overwrite arbitrary blobs.
- GitHub token in `@Value("${github.token}")` (`GitHubAPIService.java:22`) — if debug-level logging captures Spring environment, token could appear in logs.
- No upload/delete audit trail beyond application logs — SOC 2 / change management requires a persistent audit record.
- `AzureBlobService.acquireBlobLease` throws `BlobStorageException` if blob already leased — no retry; concurrent uploads to the same path will fail with a 500.
