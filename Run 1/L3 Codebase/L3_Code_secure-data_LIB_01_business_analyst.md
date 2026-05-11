# secure-data_LIB — Business Analyst View

## Business Purpose
`secure-data_LIB` is a Spring Boot microservice that acts as a proxy/adapter for the **StrongBox** secrets repository. It exposes a REST API so that downstream consumers (specifically named as SSIS/SQL Server in the Swagger description) can retrieve sensitive data — such as connection strings, cryptographic keys, and configuration secrets — from the StrongBox service without embedding StrongBox client logic in every consumer.

The package namespace (`com.citi.prepaid.secureinfo.securedata`) and contact metadata (`service@wirecard.com`, `www.wirecard.com`) indicate this is a legacy artefact from the Wirecard/Citi Prepaid era that has been carried into the Onbe estate.

## Capabilities
1. **StrongBox Retrieval**: Given a `refId` reference key, calls the StrongBox `RepositoryService.Read` XML-RPC method via HTTP POST and returns the resolved data as a JSON/XML response.
2. **Service Discovery via Director**: Uses an internal `IDirectorClient` (XML-RPC) to locate the StrongBox service URI dynamically by asking a Director service for `SERVICES_SRONGBOX_REPOSVC_KEY`.
3. **Swagger / OpenAPI documentation** via Springfox Swagger 2.

## Entities
- `StrongBoxInput` — reference key + agent identifier sent to StrongBox.
- `StrongBoxOutput` — result code/message + `Map<String, Object>` data payload returned from StrongBox.

## Business Rules
- A reference string (`refId`) identifies what data to retrieve; the service does not validate or transform the payload — it passes through whatever StrongBox returns.
- The agent identifier (hardcoded as `"B2CTEST"` in `securedata.xml` line 23) scopes access within StrongBox.

## Process Flows
1. Consumer (SSIS/SQL Server) calls `GET /getData/{refId}`.
2. `SecureController` resolves StrongBox URI via `IDirectorClient.getSerivceLocationURI(directorLocation, SERVICES_SRONGBOX_REPOSVC_KEY, "Profile", agent)`.
3. `StrongBoxClient.readData(refId)` sends XML-RPC POST with `application/x-mapxml` content-type.
4. Response parsed by `XmlRPCToObjectMapper` and returned as `Map<String, Object>`.

## Compliance Relevance
- **PCI DSS Req 3/6/8**: This service retrieves and proxies secrets. If those secrets include encryption keys, card data elements, or authentication credentials, this service is directly in the Cardholder Data Environment (CDE) or key-management scope.
- The agent hardcoded as `"B2CTEST"` suggests the configuration has not been updated for production; a test agent in production is a compliance finding.
- Swagger UI is enabled — exposes API documentation in a potentially production-accessible endpoint.

## Risks
- `directorAgent` and `directorLocation` fields are injected via Spring but the constructor runs before injection is complete (see `SecureController` constructor issue — director client called with null values).
- No authentication on the REST API; any caller can retrieve any reference.
- Exception handling swallows errors silently (`e.printStackTrace()` in constructor).
