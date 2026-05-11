# Business Analyst View — InternalOnbeAI

## Business Purpose
An internal employee-facing AI chatbot and document Q&A application built on Azure OpenAI (GPT-3.5-turbo / GPT-4) and Azure Cognitive Search. It allows Onbe employees to query internal documents (e.g., employee handbook) using natural language and maintains persistent conversation history in Azure CosmosDB. The product is positioned as internal tooling, not a customer-facing or payment-processing system.

## Capabilities
- Natural language conversation with Azure OpenAI Chat Completions (GPT-35-turbo or GPT-4).
- Retrieval-Augmented Generation (RAG): queries are augmented with document search results from Azure Cognitive Search (an indexed knowledge base, seeded with documents such as the employee handbook).
- Optional semantic search via Azure Cognitive Search semantic ranking.
- Optional vector search via embedding endpoint.
- Streaming and non-streaming response modes.
- Persistent conversation history stored in Azure CosmosDB (conversations and messages containers).
- Conversation CRUD: create, read, update, rename, delete, and list conversations per authenticated user.
- Azure AD group-based document access filtering via Microsoft Graph API.
- User authentication via Azure App Service EasyAuth (Azure AD / Entra ID).
- Infrastructure provisioned via Azure Developer CLI (azd) and Bicep templates.
- Document ingestion pipeline via Azure Form Recognizer (prepdocs.py, referenced in Bicep).
- React TypeScript frontend served as static files.
- Docker devcontainer for local development.

## Entities
| Entity | Store | Key Fields |
|--------|-------|-----------|
| Conversation | CosmosDB | id, userId, title, createdAt, updatedAt, type='conversation' |
| Message | CosmosDB | id, userId, conversationId, role, content, createdAt, type='message' |
| Document Index | Azure Cognitive Search | content, title, filepath, url, vector fields (configurable) |

## Business Rules
- Users are identified by Azure AD principal ID extracted from EasyAuth headers (`X-Ms-Client-Principal-Id`).
- Each user can only access their own conversations (userId partition in CosmosDB queries).
- Document access can optionally be filtered to Azure AD group membership (AZURE_SEARCH_PERMITTED_GROUPS_COLUMN).
- In development mode (no EasyAuth headers), the application falls back to a `sample_user` object — this must be disabled in production.
- System message / persona is configurable via AZURE_OPENAI_SYSTEM_MESSAGE environment variable.

## Process Flows
1. **Chat**: User submits message → POST /conversation → Flask backend → Azure OpenAI Chat Completions (with or without RAG data source) → streaming SSE response to browser.
2. **History**: POST /history/generate → create/extend conversation → write user message to CosmosDB → call conversation_internal → write assistant response to CosmosDB via POST /history/update.
3. **Document Ingestion** (separate pipeline): Upload documents → Azure Blob Storage → Form Recognizer → chunked → Azure Cognitive Search index.

## Compliance Considerations
- This application handles employee conversations, not payment card data; it is outside PCI DSS CDE scope as deployed.
- Employee handbook PDF is committed directly to the repository (`data/employee_handbook.pdf`); any PII in that document would be at risk if the repo is broadly accessible.
- Azure OpenAI terms require that input data not be used to train models; verify the Azure OpenAI service agreement covers internal use.
- AZURE_OPENAI_KEY and AZURE_SEARCH_KEY are managed via environment variables / Azure App Settings — not committed to source in .env.sample (values are blank).
- Conversation data stored in CosmosDB may contain sensitive employee queries; data residency and retention policies should be defined.
- GDPR/CCPA: conversation data is tied to user principal ID; a deletion mechanism exists (delete_all route) but a formal DSAR process should be documented.

## Risks
- Development fallback user (`sample_user.py`) bypasses authentication; if deployed without EasyAuth this grants unauthenticated access.
- AZURE_COSMOSDB_ACCOUNT_KEY accepted as a credential option — key-based auth is less secure than managed identity (DefaultAzureCredential path is the preferred option).
- No rate limiting or prompt injection defences in the current code.
- openai SDK pinned to 0.27.7 (legacy v0 SDK); Azure OpenAI API version is preview (2023-06-01-preview).
