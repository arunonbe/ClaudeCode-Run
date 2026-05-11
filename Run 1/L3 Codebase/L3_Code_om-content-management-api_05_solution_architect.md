# Solution Architecture — om-content-management-api

## Technical Architecture
- **Framework**: Spring Boot 3.5.9, Java 21.
- **Architecture style**: Single-module Spring MVC; traditional layered (controller → service → external client).
- **Package root**: `com.onbe.internal.content.management.api`.
- **Azure SDK**: `azure-storage-blob` for blob operations; `spring-cloud-azure-starter-appconfiguration-config` for config.
- **Validation**: Jakarta Bean Validation + custom `FileValidator` static methods + `EnumValidator`/`ValidEnum` annotation.
- **API docs**: springdoc-openapi 2.8.15; `openapi.json` in repo root.

## API Surface
| Method | Path | Description |
|--------|------|-------------|
| POST | `/xcontent/upload` | Upload XContent file (multipart/form-data) |
| DELETE | `/xcontent/file` | Delete XContent file |
| GET | `/hc` | Health check |
| GET | `/info` | Info |

## Security Posture
- **Authentication**: No Spring Security configuration observed in the source tree — authentication must be enforced at APIM gateway level.
- **Transport**: HTTPS assumed via Azure deployment; no TLS in application code.
- **Secrets**: `github.token` injected via `@Value("${github.token}")` in `GitHubAPIService.java:22`; sourced from Azure App Config / Key Vault. Connection string via `@Value("${spring.cloud.azure.storage.blob.connection-string:}")` in `AzureBlobService.java:34`.
- **Log sanitisation**: `LogSanitizer.java` present — caller must invoke it manually; not an automatic filter.
- **Path traversal**: `targetFilePath` from `XContentFileUploadRequest` is passed to `blockBlobClient = containerClient.getBlobClient(targetFilePath)` — no path traversal check observed. A caller could potentially pass `../../sensitive-path` — Azure Blob path resolution must be validated.
- **File content scanning**: No virus or malicious content scan on uploaded files.
- **Blob lease**: 15-second lease duration for concurrent write protection — valid concurrency control.

## Technical Debt
- `AzureBlobService.init()` is `@PostConstruct` and throws on missing connection string — startup fails silently if App Config is unavailable; no graceful degradation.
- `rediscache-admin-service-url` hardcoded in default `application.yaml` with staging URL — environment bleed risk.
- GitHub PAT injected via `@Value` — if Spring's `logging.level.org.springframework=DEBUG` is set, property sources including secrets may appear in logs.
- No input sanitisation on `targetFilePath` — path traversal risk.
- `GitHubAPIService.getFileFromGitHub()` and `createOrUpdateFileInGitHub()` use `RestTemplate` (deprecated in favour of `RestClient` in Spring Boot 3.2+).
- No JaCoCo coverage thresholds enforced in pom.xml — coverage gates missing.
- CI/CD references `feature/IN-9108-inverse-aks` branch of `om-ci-setup` — not production-stable.
- No structured log format configured — unstructured logs hinder log aggregation and SIEM ingestion.

## Code-Level Risks
| File | Line | Risk |
|------|------|-------|
| `AzureBlobService.java` | 34-49 | `@Value` connection string; `@PostConstruct` throws `IllegalStateException` — hard startup failure if App Config unavailable |
| `GitHubAPIService.java` | 22 | `@Value("${github.token}")` — GitHub PAT in property context; debug logging could expose it |
| `GitHubAPIService.java` | 63-68 | `AzureBlobService.uploadFileToAzureContainer` (and `WithLease`) passes `targetFilePath` from request — no path normalisation or traversal check |
| `AzureBlobService.java` | 121 | `leaseClient.acquireLease(15)` — 15-second lease; no retry if lease acquisition fails; throws BlobStorageException (HTTP 409) propagated as 500 to caller |
| `application.yaml` | 41 | `rediscache-admin-service-url` staging URL in default profile — will be used if a non-overriding profile is active |
| `XContentManagementController.java` | 38-44 | `@ModelAttribute` for upload — validates field constraints but `targetFilePath` traversal not validated |

## Gen-3 Migration Requirements
- This service is Gen-2 / OnePlatform and is not targeted for NexPay Gen-3 migration.
- If NexPay Gen-3 needs content management, create a new service aligned to Gen-3 conventions (OpenAPI-first, Flyway, OTEL, Azure Container Apps, `nexpay-iac` pipeline).
- Before production promotion of this service: re-enable container scan, add path traversal validation on `targetFilePath`, add structured logging, stabilise CI/CD to `main` branch, add Spring Security or confirm APIM enforcement.
