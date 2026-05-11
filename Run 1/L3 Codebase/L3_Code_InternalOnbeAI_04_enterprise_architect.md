# Enterprise Architect View — InternalOnbeAI

## Platform Generation
**Gen-3 (New/Modern)** — This is a cloud-native Python application built on Azure PaaS services (App Service, CosmosDB, Cognitive Search, OpenAI). It uses managed identities, Bicep IaC, Azure Developer CLI, and React TypeScript frontend. It is architecturally modern but uses preview/beta SDK versions.

## Business Domain
**Internal Productivity / AI Tooling** — Not a payments domain service. This application serves Onbe employees and is positioned as an internal tool for knowledge retrieval and Q&A against internal documents.

## Role
- **Primary role**: Internal employee AI assistant / chatbot with document grounding.
- Provides Retrieval-Augmented Generation (RAG) over internal documents (employee handbook, etc.).
- Persistent conversation history per employee.
- **Not in CDE (Cardholder Data Environment)** — no payment data should flow through this application per its design intent.

## Dependencies
### Inbound (consumers)
- Onbe internal employees (via browser).
- Azure AD identity provider (Entra ID) for authentication.

### Outbound (runtime)
| Dependency | Type |
|-----------|------|
| Azure OpenAI (GPT-35-turbo) | AI API |
| Azure Cognitive Search | RAG knowledge base |
| Azure CosmosDB | Conversation history |
| Azure Blob Storage | Document ingestion |
| Azure Form Recognizer | Document chunking |
| Microsoft Graph API | User group membership (for document filtering) |
| Azure AD / Entra ID | Authentication |

## Integration Patterns
- **REST API (Flask)**: Internal REST endpoints for conversation and history management.
- **RAG (Retrieval-Augmented Generation)**: Azure Cognitive Search as a data source injected directly into the Azure OpenAI Chat Completions extensions API.
- **Streaming SSE**: Server-Sent Events for streaming AI responses to the browser.
- **CosmosDB NoSQL**: Document model for conversation persistence.
- **Managed Identity**: System-assigned identity for Azure service authentication (preferred).
- **Azure AD EasyAuth**: Platform-level authentication at the App Service layer.

## Strategic Status
**Active / Evolving** — This is an internal tooling application with active use potential. It should be maintained and evolved as Azure OpenAI and SDK versions mature.

Key evolution priorities:
1. Upgrade openai SDK from v0.27.7 to the current v1.x Azure OpenAI SDK.
2. Replace azure-search-documents beta (11.4.0b6) with stable release.
3. Add Application Insights for observability.
4. Define and implement data retention policy for CosmosDB conversations.
5. Fix the `c.timestamp` vs `createdAt` field name bug in get_messages query.
6. Disable sample_user development fallback in production.

## Migration Blockers
- No migration needed — this is already Gen-3.
- The key risk is scope creep: if employees start inputting payment card data, PII, or confidential client information into the chat, the system's data governance posture becomes inadequate. Clear acceptable use guidelines are required.
- Consider integration with Onbe's enterprise AI governance framework as it matures.
