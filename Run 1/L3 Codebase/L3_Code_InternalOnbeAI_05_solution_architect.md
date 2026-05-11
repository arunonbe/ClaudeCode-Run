# Solution Architect View — InternalOnbeAI

## Technical Architecture

**Stack**: Python 3.10, Flask 2.3.2, openai 0.27.7 (legacy v0 SDK), azure-identity 1.14.0, azure-search-documents 11.4.0b6, azure-cosmos 4.3.1, azure-storage-blob 12.17.0, React 18 (TypeScript, Vite), Azure App Service (Linux B1), Azure OpenAI, Azure Cognitive Search, Azure CosmosDB, Azure Bicep IaC.

**Architecture pattern**: Three-tier web application with RAG.
- **Frontend**: React TypeScript SPA (served as static files by Flask `static_folder`).
- **Backend**: Flask REST API (app.py ~615 lines) — handles conversation, history CRUD, and AI orchestration.
- **Infrastructure**: Azure PaaS (no compute management required).

**Key flows**:
1. `GET /` → serves React SPA from `static/` folder.
2. `POST /conversation` → `conversation_internal()` → `conversation_with_data()` or `conversation_without_data()`.
3. `POST /history/generate` → write to CosmosDB → call `conversation_internal()`.
4. History management routes (`/history/{list,read,update,delete,rename,clear,delete_all,ensure}`).

## API Surface

**REST endpoints** (Flask, default port):

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | / | EasyAuth | Serve React SPA |
| GET | /assets/* | EasyAuth | Static assets |
| GET/POST | /conversation | EasyAuth | Direct chat (no history) |
| POST | /history/generate | EasyAuth | Chat with CosmosDB history create |
| POST | /history/update | EasyAuth | Write assistant reply to history |
| DELETE | /history/delete | EasyAuth | Delete conversation |
| GET | /history/list | EasyAuth | List user conversations |
| POST | /history/read | EasyAuth | Read conversation messages |
| POST | /history/rename | EasyAuth | Rename conversation |
| DELETE | /history/delete_all | EasyAuth | Delete all user conversations |
| POST | /history/clear | EasyAuth | Clear messages in conversation |
| GET | /history/ensure | EasyAuth | Check CosmosDB connectivity |

Authentication is via Azure App Service EasyAuth (Azure AD). User identity extracted from `X-Ms-Client-Principal-Id` header.

## Security Posture

### Authentication / Authorisation
- **Platform-level auth**: Azure App Service EasyAuth with Azure AD (`authClientId`, `authClientSecret` injected via Bicep secure parameter).
- **User identity**: Extracted from `X-Ms-Client-Principal-Id` / `X-Ms-Client-Principal-Name` headers (set by EasyAuth).
- **Development bypass**: `backend/auth/auth_utils.py` — if `X-Ms-Client-Principal-Id` header is absent, falls back to `sample_user` module. This bypass will grant unauthenticated access if deployed without EasyAuth.
- **Group-based document filtering**: Optional — via `AZURE_SEARCH_PERMITTED_GROUPS_COLUMN` and Microsoft Graph API group membership lookup.
- **Data isolation**: CosmosDB queries always filter by `userId` (Azure AD principal ID) — correct user isolation.

### Cryptography
- All Azure service connections use HTTPS (enforced by Azure SDKs).
- CosmosDB data at rest encrypted by Azure platform (AES-256).
- `AZURE_COSMOSDB_ACCOUNT_KEY` option: if used, this is a symmetric key — preferred path is `DefaultAzureCredential` (Managed Identity).

### Secrets
- **Environment variables** (Azure App Service Application Settings): `AZURE_OPENAI_KEY`, `AZURE_SEARCH_KEY`, `AZURE_COSMOSDB_ACCOUNT_KEY` (optional), `authClientSecret`.
- `.env.sample` has all values empty — no secrets committed to source. Correct pattern.
- `infra/main.bicep` line 128-129: `AZURE_SEARCH_KEY: searchService.outputs.adminKey` and `AZURE_OPENAI_KEY: openAi.outputs.key` are passed as App Settings from Bicep outputs — these are injected at deployment time, not committed to source. Acceptable.
- `authClientSecret` is a `@secure()` Bicep parameter — not logged or committed.

### CVEs / Dependency Risks
- **openai 0.27.7**: Legacy v0 SDK; no active security maintenance. Azure OpenAI preview API `2023-06-01-preview` may be retired.
- **azure-search-documents 11.4.0b6**: Beta SDK — not production-supported.
- **Flask 2.3.2**: Check for CVEs; newer Flask 3.x releases available.
- **azure-cosmos 4.3.1**: Verify against current stable (4.5.x+).
- **Werkzeug** (Flask dependency): CVE-2023-25577 and CVE-2023-46136 in older versions.

## Technical Debt
1. `openai.ChatCompletion.create()` uses the deprecated v0 openai SDK — must migrate to `AzureOpenAI` client in openai v1.x.
2. `openai.api_version = "2023-03-15-preview"` in `conversation_without_data` — different API version than `2023-06-01-preview` in `conversation_with_data`; inconsistency.
3. `get_messages` query orders by `c.timestamp` but messages are written with `createdAt` key — field name mismatch will result in default (unordered) scan (`cosmosdbservice.py` line 146).
4. `generate_title()` function catches all exceptions and falls back to `messages[-2]['content']` — index error if message list has fewer than 2 items.
5. `stream_with_data()` assumes `lineJson["choices"][0]["messages"][0]["delta"]` structure — brittle; API response shape changes will cause silent failures.
6. No input sanitisation for the system message (`AZURE_OPENAI_SYSTEM_MESSAGE`) — prompt injection possible via environment variable.
7. No rate limiting on Flask endpoints — potential for abuse or cost runaway on Azure OpenAI.
8. `azure-search-documents` beta SDK should be pinned to a stable release.

## Gen-3 Migration Requirements
This is already Gen-3 with minor gaps:
1. Upgrade openai SDK to v1.x (`from openai import AzureOpenAI`).
2. Replace beta azure-search-documents with stable version.
3. Fix `c.timestamp` / `createdAt` CosmosDB query field mismatch.
4. Add Application Insights SDK for observability.
5. Define and enforce data retention policy via CosmosDB TTL.
6. Disable `sample_user` fallback in production deployment.
7. Add request rate limiting (Flask-Limiter or Azure API Management).
8. Upgrade App Service plan from B1 to Standard/Premium for production SLA.

## Code-Level Risks

| File | Line | Risk |
|------|------|------|
| `backend/auth/auth_utils.py` | 7-8 | Development fallback bypasses authentication if EasyAuth headers absent |
| `backend/history/cosmosdbservice.py` | 146 | `ORDER BY c.timestamp` — field should be `c.createdAt`; messages will be unordered |
| `app.py` | 288-289 | Sets global `openai.api_type` / `openai.api_base` — not thread-safe; concurrent requests could corrupt settings |
| `app.py` | 59 | `AZURE_OPENAI_MODEL_NAME` defaults to `gpt-35-turbo` — typo in model name check at line 95 uses `'gpt-35-turbo-4k'` — inconsistency |
| `app.py` | 248 | `conversation_with_data(request_body)` ignores `request_body` argument and reads from global `request` directly — parameter is unused |
| `app.py` | 79-81 | `AZURE_COSMOSDB_ACCOUNT_KEY` used as credential directly — string key stored in memory; Managed Identity preferred |
