# secure-data_LIB — Data Architect View

## Data Stores
No local data store. The service is a stateless proxy to the remote StrongBox repository service. Data is fetched on demand and returned in-memory; nothing is persisted locally.

## Schema / Tables
Not applicable — no local database.

## Sensitive Data
| Data Element | Location | Notes |
|---|---|---|
| StrongBox secrets (keys, credentials, config) | Transits through `StrongBoxOutput.data` (`Map<String, Object>`) at runtime | Nature of secrets depends on what `refId` resolves to in StrongBox |
| Agent identifier `B2CTEST` | `securedata.xml` line 23 (hardcoded) | Test-environment agent in what may be a production config |
| Director address `${director.address}` | `securedata.xml` line 26 — resolved from `file:///d:/c-base/config/director-client.properties` | References a Windows local file path |

No PANs, CVVs, or account numbers are observed in code; however, the service is designed to return whatever StrongBox holds, which could include cryptographic material.

## Encryption
- **Transport**: StrongBox communication uses Apache Commons HttpClient (`HttpClient` 3.x) over HTTP/HTTPS — the transport protocol is not enforced in code; it depends on the URI returned by Director. No TLS verification enforcement found in source.
- **At-rest**: No local persistence, so at-rest encryption is not applicable for this service.
- **Algorithm choices**: No custom cryptographic operations implemented in this library. Crypto is entirely delegated to StrongBox.

## Data Flow
```
Consumer → GET /getData/{refId}
  → SecureController
    → IDirectorClient (XML-RPC) → Director service (locates StrongBox URI)
      → StrongBoxClient (XML-RPC POST, application/x-mapxml)
        → StrongBox RepositoryService.Read
          → Returns Map<String,Object>
  → JSON/XML response to Consumer
```

## Data Quality / Retention
No data quality checks or retention policies. The service is a transparent proxy.

## Compliance Gaps
- **PCI DSS Req 6.4**: No authentication/authorisation on the REST endpoint — any network-accessible caller can retrieve secrets.
- **PCI DSS Req 4.2**: HTTP transport to StrongBox not verified as TLS; Apache HttpClient 3.x does not enforce certificate validation by default.
- **PCI DSS Req 3**: If the secrets returned include encryption keys or SAD, the absence of access controls means they are insufficiently protected in transit.
- **Req 2.2**: Hardcoded agent `B2CTEST` indicates test configuration potentially in production.
- Configuration file path `d:/c-base/config/director-client.properties` is a Windows absolute path — environment-specific hardcoding.
