# Data Architect View — InternalOnbeAI

## Data Stores
| Store | Type | Purpose |
|-------|------|---------|
| Azure CosmosDB (NoSQL) | Serverless document store | Conversation and message history per user |
| Azure Cognitive Search | Search index | RAG knowledge base (employee handbook and other uploaded documents) |
| Azure Blob Storage | Object store | Document storage for ingestion pipeline |
| Azure OpenAI Service | Managed AI API | Chat completions and embeddings |
| Azure Form Recognizer | Document intelligence | Document chunking for search index |

## Schema / Collections (CosmosDB)
**Conversations container** — partition key: userId

| Field | Type | Description |
|-------|------|-------------|
| id | UUID string | Conversation identifier |
| type | string | Always 'conversation' |
| userId | string | Azure AD principal ID |
| title | string | Auto-generated conversation title |
| createdAt | ISO datetime | Creation timestamp |
| updatedAt | ISO datetime | Last update timestamp |

**Messages** (within same container, differentiated by type field):

| Field | Type | Description |
|-------|------|-------------|
| id | UUID string | Message identifier |
| type | string | Always 'message' |
| userId | string | Azure AD principal ID |
| conversationId | UUID string | Parent conversation |
| role | string | 'user', 'assistant', or 'tool' |
| content | string | Message text (full conversation content) |
| createdAt / updatedAt | ISO datetime | Timestamps |

## Sensitive Data Classification
| Data | Classification | Notes |
|------|---------------|-------|
| Conversation content | Potentially sensitive employee data | May contain PII, business information, or confidential queries |
| userId (Azure AD principal ID) | Pseudonymous PII | Links to identity directory |
| employee_handbook.pdf | Internal PII / HR data | Committed to repo `data/` directory |

## Encryption
- CosmosDB encrypts data at rest by default (AES-256 via Azure platform).
- TLS 1.2+ is enforced for all Azure service connections.
- AZURE_COSMOSDB_ACCOUNT_KEY option exists — if used, the account key should be stored in Azure Key Vault or App Service configuration, not in environment variables in CI/CD.
- DefaultAzureCredential (Managed Identity path) is the preferred auth mechanism and is implemented in the code — it avoids key management.

## Data Flow
1. User sends chat message → Flask app → Azure OpenAI Chat API (with or without Cognitive Search data source).
2. User message written to CosmosDB via `create_message()`.
3. OpenAI response written to CosmosDB via `create_message()`.
4. Conversation metadata updated in CosmosDB on each message.
5. On RAG path: user query → Azure Cognitive Search → top-K document chunks appended to OpenAI context.
6. Document ingestion (separate): documents → Azure Blob → Form Recognizer → chunked → indexed into Cognitive Search.

## Data Quality / Retention
- No automated retention or expiry policy is configured in this codebase (CosmosDB TTL not set via code).
- User can delete individual conversations or all conversations via API routes.
- No archival or backup strategy defined in code.
- Messages ordered by `timestamp` in retrieval query — note: message schema uses `createdAt` for writes but `timestamp` for the ORDER BY query; a field name inconsistency exists that could cause incorrect ordering.

## Compliance Gaps
1. Conversation content may contain employee PII or sensitive business information — a data classification and retention policy (GDPR Art. 5 / CCPA) must be defined and implemented.
2. Employee handbook PDF committed directly to repository — if it contains PII it should not be in source control.
3. No data residency constraints enforced in Bicep beyond the `location` parameter — ensure data stays in approved Azure regions per data residency obligations.
4. `AZURE_COSMOSDB_ACCOUNT_KEY` option bypasses Managed Identity — if populated, the key must be rotated and stored in Key Vault.
5. The `get_messages` query orders by `c.timestamp` but the field written is `createdAt` — potential data quality defect causing message ordering issues.
