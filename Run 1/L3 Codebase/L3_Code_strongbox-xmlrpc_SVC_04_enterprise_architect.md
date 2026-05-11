# Enterprise Architect Report: strongbox-xmlrpc_SVC

## Platform Generation

**Gen-1 (eCount/Citi) with Gen-2 operational overlay**. The core service code — XML-RPC transport, Spring XML bean wiring, Oracle Financial Services Software (OFSS) authorship credits, `com.ecount.Core2` package namespace — is firmly Gen-1 origin. The operational posture has been partially modernised: Java 21 compile target, Docker containerisation, GitHub Actions CI/CD, Trivy container scanning, and a GitLab CI legacy pipeline. The service is running Gen-1 code on Gen-2/Gen-3 infrastructure.

This is the most critical Gen-1 service in the platform — not because it handles the most transactions, but because it provides the cryptographic foundation for all other Gen-1/Gen-2 data protection. Its security posture directly determines the security of all cardholder data encrypted using the platform's keys.

## Integration Patterns

- **XML-RPC server**: The primary integration pattern — HTTP POST with XML-encoded RPC calls. Clients use the `StrongBoxXMLRPCClient` or `CryptoServiceXMLRPCClient` generated stubs (in `strong-box-client`) to invoke remote methods
- **Director service integration**: `IDirectorLocationAware` on `RepositoryService` suggests integration with a "Director" service location resolver — this is the eCount service registry pattern for dynamic service endpoint discovery
- **Spring XML bean wiring**: The application context is fully XML-configured (following the Gen-1 pattern)
- **External PGP binary invocation**: `PGPExternalCommands` calls an OS-level PGP binary via `Runtime.exec()` or similar — this is a Gen-1 pattern for leveraging pre-existing system capabilities
- **JNDI DataSource**: Database access via the `spring-dbctx_LIB` `strongbox` DataSource configuration

## External Dependencies

- SQL Server `strongbox` database: the vault backing store — stores keys, symmetric key values, and encrypted data blobs
- External PGP binary installed in the container (version and source must be verified)
- eCount Director service: for dynamic service location resolution
- Apache XML-RPC 3.0.2: transport layer for all client-server communication
- `ecount-system:4.0.2`: internal DAL framework providing `DataProcedure` base classes for all DAO operations
- Consuming services via `strongbox-remote-client_LIB` or direct `StrongBoxXMLRPCClient` usage

## Position in the Broader Platform

StrongBox occupies the **trust anchor** position in the Gen-1/Gen-2 security architecture. It is the root of the cryptographic trust chain:

```
StrongBox (keys) → Gen-1/Gen-2 services (encrypt/decrypt) → Protected cardholder data
```

This means:
- StrongBox availability = ability to process and decrypt all Gen-1/Gen-2 encrypted data
- StrongBox integrity = integrity of all cryptographic operations across the platform
- StrongBox compromise = all Gen-1/Gen-2 protected data is compromised

The service is a **single point of cryptographic failure** for the entire Gen-1/Gen-2 platform. Its architecture (keys and ciphertext co-located in one database) makes the blast radius of a vault database breach encompass all encrypted data across all services.

Gen-3 services use Azure Key Vault (HSM-backed, separate from data, FIPS 140-2 Level 2) — a fundamentally different and more secure architecture that does not have these co-location problems.

## Migration Blockers

1. **All Gen-1/Gen-2 encrypted data is StrongBox-encrypted**: Any migration away from StrongBox requires re-encrypting every field and blob in every Gen-1/Gen-2 database using a new key management system — a multi-year, high-risk data migration project
2. **No key export mechanism visible**: The DAO operations include `sb_get_asymmetric_key` and `sb_get_symmetric_key` for reading keys, but migrating keys to Azure Key Vault requires a secure key import ceremony; the current key format (raw strings in SQL Server) is not in a format directly importable into Azure Key Vault (PKCS#8, PEM, or JWK required)
3. **PGP passphrase dependency**: Services using PGP encryption (file transfers, cardholder communications) rely on passphrases stored in StrongBox; migrating to modern envelope encryption requires identifying all PGP-encrypted data and re-encrypting
4. **Proprietary reference format**: The StrongBox reference string format (version + key_id + data_id encoding) is proprietary; consuming services have opaque references embedded in their databases; mapping these to new vault references requires a dual-read period during migration

## Strategic Status

**Critical legacy dependency requiring phased migration — highest risk Gen-1 service**. The architecture cannot remain as-is for PCI DSS compliance (co-located keys and ciphertext). The migration path:

1. **Immediate**: Implement column-level encryption for key_value and private_key columns in the vault database using SQL Server Always Encrypted or TDE with key separation
2. **Medium-term**: Deploy an intermediate StrongBox that stores keys in Azure Key Vault while maintaining the XML-RPC interface for existing consumers (a facade pattern)
3. **Long-term**: Migrate all consumers to Azure Key Vault directly; decommission StrongBox XML-RPC service; purge old vault database after migration verification
