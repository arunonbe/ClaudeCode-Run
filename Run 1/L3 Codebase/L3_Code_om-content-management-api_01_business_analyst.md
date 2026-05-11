# Business Analysis — om-content-management-api

## Business Purpose
An internal OnePlatform (OM) microservice that manages static content files (images, HTML templates, CSS, SVG, properties files) used by the recipient web application. It provides a REST API for uploading and deleting XContent files, persisting them to Azure Blob Storage and optionally committing them to the `xContent-recipient` GitHub repository. This service acts as a content management gateway for recipient-facing UI assets.

## Capabilities
- Upload XContent files (images, HTML, SVG, CSS, JS, properties) to Azure Blob Storage container via multipart form upload.
- Acquire a blob lease before writing to prevent concurrent overwrite (optimistic concurrency on blobs).
- Delete XContent files from Azure Blob Storage.
- Optionally commit/update the uploaded file to a GitHub repository (`OnbeEast/xContent-recipient`) when the `api.settings.github.enable` feature flag is active.
- File type and extension validation before upload.
- File size limits: 20 MB per file, 30 MB per request.
- Azure App Configuration integration for feature flag control and runtime config.

## Key Entities
| Entity | Description |
|--------|-------------|
| `XContentFileUploadRequest` | Multipart upload request: file, file type, locale, target path |
| `XContentFileDeleteRequest` | Delete request: target file path |
| `PromoImageData` | Model for promotional image metadata |
| `APIResponse` | Standard response wrapper: `success/failure` with message |

## Business Rules
- File type validated against `FileType` enum before processing.
- File extension validated against `FileExtension` enum: `html`, `htm`, `svg`, `css`, `js`, `json`, `png`, `jpg`, `jpeg`, `gif`, `pdf`, `txt`, `properties`.
- Locale validated against `Locale` enum.
- `FileValidator.validateXContentUploadFileRequest` and `validateXContentDeleteFileRequest` enforce request field constraints.
- Content type is inferred from file extension; HTML files explicitly set `text/html;charset=UTF-8`.
- Blob lease acquisition (15-second duration) used for upload with lease — prevents concurrent overwrites.
- GitHub commit is conditional on feature flag `api.settings.github.enable` (from Azure App Config).
- GitHub file create/update uses SHA-based update detection (existing file SHA fetched before PUT).

## Data Flow
1. Client POSTs multipart request to `POST /xcontent/upload`.
2. `FileValidator` validates file type, extension, locale.
3. `FileUploadService` checks if `AzureBlobService` is active (non-dev profile).
4. `AzureBlobService.uploadFileToAzureContainerWithLease()` acquires blob lease, uploads, releases lease.
5. If GitHub feature flag enabled, `GitHubAPIService.createOrUpdateFileInGitHub()` commits the file to the configured branch of `OnbeEast/xContent-recipient`.
6. Response returned as `APIResponse`.

## Compliance Relevance
- Content files (HTML templates, images) may embed personalisation tokens but do not themselves contain cardholder data or PII at rest.
- GitHub token (`github.token`) grants write access to the `xContent-recipient` repository — must be treated as a secret.
- Azure Blob Storage connection string is a secret — sourced from Azure App Configuration.
- `LogSanitizer` utility present — indicates awareness of log injection risk from file-name/path inputs.
- File upload endpoint accepts up to 20 MB files — DDoS/abuse risk if not rate-limited at gateway.

## Risks
- GitHub Personal Access Token stored as config secret — token rotation not enforced by this service.
- No authentication on the upload/delete endpoints visible in this service's code — auth must be at APIM/gateway.
- File path injection risk: `targetFilePath` from request is passed directly to Azure Blob client — must be validated to prevent path traversal.
- Large file uploads (up to 20 MB) in memory — potential OOM under high concurrency.
- `AzureBlobService` is `@Profile("!dev")` — active in all non-dev environments; `dev` profile uses a different (unimplemented) service path.
