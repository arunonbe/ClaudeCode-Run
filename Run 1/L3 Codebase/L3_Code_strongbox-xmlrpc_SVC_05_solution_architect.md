# Solution Architect Report: strongbox-xmlrpc_SVC

## API Surface

The service exposes two XML-RPC interfaces, both via HTTP POST to the service endpoint (e.g., `http://host:8080/strong-box-xmlrpc/invoker/Strongbox`):

**RepositoryService (IStrongBox)**:
- `repositoryServiceRead(agent, reference, target)` → decrypted object
- `repositoryServiceReadMap(agent, reference)` → `Map<String, Object>`
- `repositoryServiceWrite(agent, data)` → reference string
- `repositoryServiceWriteMap(agent, Map<String, Object>)` → reference string

**CryptoService (ICryptoService)**:
- `encryptPGP(EncryptPGPInput)` → `EncryptPGPOutput`
- `decryptPGP(DecryptPGPInput)` → `DecryptPGPOutput`

There is no REST API, no OpenAPI/WSDL documentation, and no health endpoint visible in the source.

## Security Posture

**Critical risk — the most security-deficient service in the batch despite being the platform's security anchor.**

This is paradoxical: StrongBox is the trust anchor for cardholder data protection, yet its own security posture has multiple critical vulnerabilities.

**No authentication on the XML-RPC endpoint**: The `service.default.properties` URL is plain HTTP; no authentication mechanism (Basic Auth, mutual TLS, token) is visible in any Spring XML configuration. Any process that can make an HTTP POST to the StrongBox endpoint can retrieve any stored key by name or decrypt any vault-stored reference.

**HTTP transport for key material**: Default service URL uses `http://` — cryptographic keys travel over the network unencrypted.

## Critical Vulnerabilities

1. **RSA private keys stored as plaintext strings in SQL Server** (`SbGetAsymmetricKey.java`, lines 23–25; `SbGetSymmetricKey.java`, lines 22–25):
   - `@OutParameter(index=2) public String private_key` — the RSA private key is a SQL Server output parameter returned as a plain `String`
   - The key is stored in a string column in the vault database without column-level encryption
   - PCI DSS Requirement 3.6.1: "Key-encrypting keys... used to protect data encryption keys must be stored separately from data encryption keys" — this is violated; the key-encrypting key (RSA private) is in the same database as the encrypted symmetric keys

2. **Symmetric key values stored as plaintext strings** (`SbGetSymmetricKey.java`, line 22):
   - `@OutParameter(index=2) public String key_value` — symmetric key material returned as a plain SQL output parameter string
   - Both the AES symmetric key and the RSA private key that wraps it are returned from the same stored procedure, fetched from the same database

3. **No access control on key retrieval** (`RepositoryService.java`):
   - The `agent` parameter (lines 57, 92, 124, 155) is accepted but no visible authorisation check enforces which agent can access which keys; any caller can request any key by name or any vault data by reference
   - `SbGetAsymmetricKey` takes only `name` as input — no caller identity or authorisation token
   - PCI DSS Requirement 7: "Limit access to system components and cardholder data to only those individuals whose job requires such access"

4. **Plaintext data written to filesystem during PGP operations** (`CryptoService.java`, lines 164–183):
   - `writeFile(input.getText(), inputFile)` — the plaintext to be encrypted is written to a temp file before PGP invocation
   - `log.info("PGP Encrypt Input ==> " + input.getText())` (line 173) — the plaintext is logged at INFO level, potentially writing sensitive data to log files
   - `log.info("PGP Encrypt Output ==> " + encrypted_text)` (line 184) — the PGP ciphertext is also logged at INFO level
   - PCI DSS Requirement 3: plaintext sensitive data (which could include PAN data) must not be logged

5. **External PGP binary via `Runtime.exec()`** (`PGPExternalCommands`):
   - Invoking external processes with user-supplied key names and passphrases as arguments carries command injection risk if arguments are not properly escaped
   - External binary path is not visible in available source; if the path is configurable, a compromised configuration could point to a malicious binary

6. **No authentication on XML-RPC endpoint** (inferred from absence of security configuration):
   - No Spring Security configuration visible in available source
   - No `web.xml` security constraints visible
   - Service is accessible to any internal network caller

## Technical Debt

- **Spring XML wiring throughout**: No annotation-driven configuration; all wiring in XML bean definitions
- **Gen-1 DAL framework (`DataProcedure`)**: All DAO operations extend `DataProcedure` from `ecount-system:4.0.2` — an internal eCount data access framework that must be maintained alongside the service; it does not use Spring Data or standard JDBC Template patterns
- **`@Slf4j` mixed with XML Spring context**: Lombok annotations are used (`@Slf4j` on implementation classes) while the application context is fully XML-driven; this mix of annotation and XML config is inconsistent and adds cognitive overhead
- **`Base64` custom implementation** (`strings/Base64.java`): A custom Base64 implementation is included; Java standard library has `java.util.Base64` since Java 8 — this custom implementation is unnecessary and may have edge case differences from the standard
- **`VectorHelper` using `java.util.Vector`**: `datastructures/VectorHelper.java` uses `Vector`, a thread-safe but deprecated (in spirit) collection; `CopyOnWriteArrayList` or `ArrayList` with explicit synchronisation would be more appropriate
- **`UUID`-based temp file names**: Temp files for PGP operations use UUID suffixes for uniqueness — while functional, this creates files that accumulate if the JVM crashes mid-operation; a cleanup mechanism on startup should remove orphaned temp files
