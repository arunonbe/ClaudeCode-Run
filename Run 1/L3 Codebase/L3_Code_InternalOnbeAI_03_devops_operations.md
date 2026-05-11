# DevOps / Operations View — InternalOnbeAI

## Build
- **Language**: Python 3.10 (backend Flask), TypeScript/React (frontend via Vite).
- **Backend dependencies**: `requirements.txt` — Flask 2.3.2, openai 0.27.7, azure-identity 1.14.0, azure-search-documents 11.4.0b6 (beta), azure-storage-blob 12.17.0, python-dotenv 1.0.0, azure-cosmos 4.3.1.
- **Frontend**: `frontend/package.json` — React, Vite. Lock file present (`package-lock.json`).
- **Dev dependencies**: `requirements-dev.txt` (content not read; presumably linting/testing tools).
- **Tests**: `test_app.py` exists in root (content not read).

## Deployment
- **Azure Developer CLI (azd)**: `azure.yaml` and `infra/` directory — full IaC deployment.
- **Azure App Service**: Python 3.10 Linux App Service (B1 SKU — 1 core, 1.75 GB RAM) deployed via Bicep.
- **Docker**: `WebApp.Dockerfile` present for containerised deployment. `.devcontainer/Dockerfile` for local dev.
- **GitHub Actions**: `.github/workflows/docker-image.yml` — Docker image build workflow.
- **Infrastructure as Code**: Bicep templates in `infra/` provision all Azure resources.
- **Azure resources provisioned**:
  - Azure App Service Plan + App Service (Python backend)
  - Azure OpenAI (Cognitive Services) — gpt-35-turbo model
  - Azure Cognitive Search (standard SKU)
  - Azure Blob Storage
  - Azure Form Recognizer (for document ingestion)
  - Azure CosmosDB (account, database, conversations container)
  - Azure AD App Registration (authClientId/authClientSecret)
  - RBAC role assignments (OpenAI Cognitive Services User, Search Index Data Reader, etc.)

## Configuration Management
- **Environment variables**: All secrets and service endpoints passed via environment variables (see `.env.sample`).
- **Azure App Service configuration**: Bicep injects all settings as App Settings (AZURE_SEARCH_KEY, AZURE_OPENAI_KEY, AZURE_COSMOSDB_ACCOUNT_KEY, etc.).
- **Auth**: Azure AD EasyAuth configured in `core/host/appservice.bicep` with `authClientId` and `authClientSecret` passed as secure Bicep parameters.
- **Managed Identity**: App Service uses system-assigned managed identity for accessing Azure resources (preferred path via `DefaultAzureCredential`).
- **Local dev**: `.env` file (not committed); `.env.sample` shows all required variables.

## Observability
- No application-level metrics or structured logging visible in the Python code beyond Python's `logging` module.
- Azure App Service provides platform-level metrics (CPU, memory, HTTP response times) via Azure Monitor.
- Flask default error logging to stderr.
- No distributed tracing (Application Insights not referenced in requirements.txt or app.py).

## Infrastructure Dependencies
| Dependency | Type | Notes |
|-----------|------|-------|
| Azure OpenAI | Managed AI API | gpt-35-turbo deployment |
| Azure Cognitive Search | Search | standard SKU, semantic search optional |
| Azure CosmosDB | NoSQL store | Conversation history |
| Azure Blob Storage | Object store | Document ingestion |
| Azure Form Recognizer | Document AI | Chunking for search index |
| Azure AD / Entra ID | Identity | EasyAuth + Microsoft Graph for group filtering |
| Azure App Service | Compute | Python 3.10, B1 SKU |

## Operational Risks
1. openai SDK 0.27.7 is the legacy v0 API — Azure OpenAI API version is `2023-06-01-preview`, which may be retired.
2. azure-search-documents 11.4.0b6 is a beta SDK — should be replaced with a stable release.
3. CosmosDB message ordering bug: `get_messages` queries `ORDER BY c.timestamp` but messages are written with `createdAt` field — messages may be returned in wrong order.
4. Development fallback user (`sample_user.py`) bypasses authentication if EasyAuth headers are absent; this creates an unauthenticated path if deployed without App Service EasyAuth.
5. App Service SKU B1 is a basic (non-production) tier — no autoscaling, limited SLA.
6. No Application Insights integration for distributed tracing or alerting.

## CI/CD
- **GitHub Actions**: `.github/workflows/docker-image.yml` — builds Docker image.
- **GitHub Actions**: `.github/workflows/docker-image.yml` — no deployment step observed in repo (deploy via `azd up` command).
- **Dependabot**: `.github/dependabot.yml`.
- **Azure Developer CLI**: `azd up` / `azd provision` commands drive infrastructure and deployment.
- No Helm, ArgoCD, or Kubernetes deployment pipeline.
