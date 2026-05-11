# secure-data_LIB — Enterprise Architect View

## Platform Generation
**Gen-1** — Spring Boot with Springfox Swagger 2, Apache Commons HttpClient 3.x, XML-RPC via Ecount internal libraries (`com.ecount.xmlrpc.*`, `com.ecount.Core2.director.*`). Package namespace references `com.citi.prepaid` — Wirecard/Citi Prepaid lineage. No containerisation, no modern API gateway, no service mesh.

## Business Domain
**Security Infrastructure / Secrets Management**. Provides a REST-accessible proxy to the StrongBox secrets repository, enabling downstream services (particularly SQL Server/SSIS integration) to retrieve runtime secrets without embedding StrongBox client code.

## Role in Platform
Acts as a **secrets access gateway** — sitting between business applications and the StrongBox credential store. In a modern architecture this role would be fulfilled by a secrets management platform (HashiCorp Vault, AWS Secrets Manager, Azure Key Vault). This service is a legacy bridge.

## Dependencies
| Dependency | Direction | Notes |
|---|---|---|
| StrongBox RepositoryService | Outbound | XML-RPC; legacy Ecount/Wirecard secrets store |
| Director service | Outbound | Service discovery for StrongBox URI |
| `com.ecount.xmlrpc` library | Compile | Internal XML-RPC serialization/deserialization |
| `com.ecount.Core2.director` library | Compile | Internal Director client |
| Consumer applications (SSIS, SQL Server) | Inbound | Clients of this service |

## Integration Patterns
- **Synchronous REST (HTTP GET)** inbound from consumers.
- **XML-RPC** outbound to Director (service discovery) and StrongBox (secret retrieval).
- **Spring XML configuration** (`securedata.xml`) with `PropertyPlaceholderConfigurer`.

## Strategic Status
**Legacy / Candidate for Decommission or Replacement.**
- Depends on Ecount/Wirecard internal libraries (`com.ecount.*`) not available in standard repositories.
- XML-RPC protocol is obsolete.
- No authentication, no modern secret management patterns.
- Spring Boot + Springfox Swagger 2 combination is deprecated (Springfox does not support Spring Boot 2.6+).
- Should be replaced by direct integration with a modern secrets manager (Vault, AWS Secrets Manager) rather than maintained.

## Migration Blockers
- Dependency on internal `com.ecount.xmlrpc.*` and `com.ecount.Core2.director.*` libraries — must be reverse-engineered or replaced.
- StrongBox itself must be migrated before this service can be retired.
- Consumers (SSIS/SQL Server) must be re-pointed to new secrets source.
- Hardcoded Windows path (`d:/c-base/config/director-client.properties`) must be replaced with environment-neutral configuration.
- Constructor defect (`SecureController` calls Director before Spring injects fields) must be fixed for any continued use.
