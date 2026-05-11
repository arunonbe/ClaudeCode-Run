# Data Architect Report: strongbox-remote-client_LIB

## Data Models

This is a client library with no persistent data model of its own. The data it handles is entirely in-memory during the lifetime of a read or write call:

**Write path data**:
- Input: a Java `Object` or `Map<String, Object>` containing the secret/sensitive data
- Intermediate: XML-RPC serialised string representation (`XmlRPCFromObjectMapper.fromObject()`)
- Output: a StrongBox reference string (opaque token pointing to the encrypted blob in the vault database)

**Read path data**:
- Input: a StrongBox reference string
- Intermediate: XML-RPC serialised string fetched from vault
- Output: a Java `Map<String, Object>` or typed object containing the decrypted secret

The in-memory handling of secrets is the primary data concern: secrets are deserialized into heap-allocated Java objects without any zeroing mechanism after use. Long-lived secrets in JVM memory are subject to garbage collection delays and could be captured in heap dumps or memory dumps.

## Sensitive Data

The library is specifically designed to handle the most sensitive data in the platform:

- **RSA private keys**: Used for asymmetric encryption of cardholder data; if these keys are stored as heap objects after retrieval, they are in cleartext in JVM memory
- **Symmetric AES keys**: Used for bulk data encryption
- **PGP passphrases**: Used by `CryptoService` in StrongBox for PGP encrypt/decrypt operations; these are retrieved as plain strings
- **Other vault-stored secrets**: Any application secret stored in StrongBox is accessed through this library; in principle this could include API keys, database passwords, or certificate private keys

None of the library code shows use of `char[]` (which can be zeroed) instead of `String` for secret handling. Java `String` objects are immutable and cannot be zeroed — they remain in heap memory until garbage collected and could be captured in memory snapshots.

## Encryption Status

The library itself performs no encryption or decryption. It relies on:
1. The `WriteMapXmlRemoteCall` transport (provided by the caller) to handle TLS for the HTTP connection to StrongBox
2. The StrongBox server to encrypt data before storing it in the database
3. The StrongBox server to decrypt data before returning it in the XML-RPC response

The cleartext secret is returned to the calling service after the StrongBox server decrypts it — the library receives and handles plaintext secrets. There is no client-side encryption wrapper.

**Default URL is HTTP (unencrypted)**: The `service.default.properties` file in the related `strongbox-xmlrpc_SVC` repository sets `service.strongbox.url=http://ecappdev:8080/strong-box-xmlrpc/invoker/Strongbox`. If production uses this default or a similarly HTTP-based URL, secrets travel over plaintext HTTP between StrongBox and its clients.

## Data Flow

```
Consumer Service → StrongBoxRemoteServiceImpl.readMap(reference, readCall)
  → readCall.read(reference)  [HTTP GET to StrongBox XML-RPC endpoint]
    → StrongBox server receives reference
    → StrongBox queries vault DB (sb_get_symmetric_key / sb_get_asymmetric_key)
    → Decrypts symmetric key using co-located RSA private key
    → Returns plaintext data blob as XML-RPC response
  ← XML-RPC string containing plaintext secret
  → XmlRPCToObjectMapper.toObject(mapXml, target, logger)
  ← Map<String, Object> with plaintext secret values
← Consumer Service holds plaintext secret in JVM heap
```

The co-location of ciphertext and the RSA private key used to decrypt it in the same database (the StrongBox vault DB) is the most architecturally significant security concern: compromise of the vault database yields both the ciphertext and the key needed to decrypt it.

## Retention and Audit Concerns

- The library generates no audit log of what secrets are read or written; audit responsibility lies with the StrongBox server
- StrongBox references (opaque tokens) are stored by consuming services; if these services log the reference strings, they create an indirect path to encrypted secrets
- The XML-RPC logger (`LogFactory.getLog("SomeLoggerClassName")`) is instantiated in `StrongBoxRemoteServiceImpl`; the logger name `"SomeLoggerClassName"` is a placeholder, suggesting logging configuration is incomplete — audit trails for secret access may be missing

## PCI DSS Compliance Assessment

- **Req 3.5**: Key management procedures must include controlled access; this library provides no access control — any service that includes it can read/write vault secrets
- **Req 3.6**: Keys must be protected against disclosure and unauthorised use; HTTP transport and Java String storage are weaknesses
- **Req 4**: If the StrongBox connection uses HTTP, keys are transmitted without encryption in violation of Req 4.2
- **Req 10**: Access to cryptographic keys must be logged; the placeholder logger name suggests audit logging is not properly configured
