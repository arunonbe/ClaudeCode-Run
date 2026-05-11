# Business Analyst Report: strongbox-remote-client_LIB

## Business Purpose

strongbox-remote-client_LIB is a Gen-2 (Wirecard/Northlane) Java library that provides a client-side interface for communicating with the StrongBox cryptographic vault service. StrongBox is the platform's in-house key management and secrets vault, responsible for securely storing and retrieving RSA asymmetric keys, symmetric encryption keys, PGP passphrases, and other sensitive security material used across the Gen-1/Gen-2 platform. This client library abstracts the XML-RPC transport layer, enabling consuming services to read from and write to the StrongBox vault without direct knowledge of the underlying XML-RPC protocol.

The library is a Wirecard/Northlane-era artefact (groupId `com.northlane`) that bridges the Gen-1 StrongBox XML-RPC service with Gen-2 Spring-based services that need to access vault-stored secrets.

## Capabilities

- **`writeObject`**: Serialises a Java object to XML-RPC format and writes it to the StrongBox vault; returns a reference string that callers use for subsequent reads
- **`writeMap`**: Serialises a `Map<String, Object>` to XML-RPC and writes to vault; returns a reference string
- **`readMap`**: Given a StrongBox reference string, fetches the encrypted data from vault, decrypts it, and returns it as a `Map<String, Object>`
- **`readObject`**: Given a reference string and a target type object, fetches and deserialises the vault data into the target type

The library uses `XmlRPCFromObjectMapper` and `XmlRPCToObjectMapper` utilities (from the internal `com.citi.prepaid.service.core:xmlrpc` library) for serialisation/deserialisation, and delegates actual network calls to lambda/functional interfaces (`WriteMapXmlRemoteCall`, `ReadMapXmlRemoteCall`) that encapsulate the HTTP connection to the StrongBox service.

## Client and Cardholder Impact

This library is a transitive dependency of every Gen-2 service that needs to access encrypted secrets managed by StrongBox. The secrets accessible through this client include:
- PGP passphrases for cardholder data encryption/decryption operations
- RSA private keys used for card data signing and verification
- Symmetric AES keys for bulk data encryption

A failure or compromise of this library affects the confidentiality of cardholder data across the platform. If the XML-RPC transport is not secured, secrets could be intercepted in transit. If the deserialisation is not constrained, a malicious StrongBox response could execute arbitrary code on the consuming service's JVM.

## Business Rules in Code

- `StrongBoxRemoteServiceImpl` is a `@Component` (Spring-managed bean) — consumers autowire it via dependency injection
- Read and write operations require a `WriteMapXmlRemoteCall` or `ReadMapXmlRemoteCall` lambda to be provided by the caller; these encapsulate the server location and connection credentials, providing a strategy-pattern approach to the vault transport
- XML-RPC serialisation/deserialisation is handled by internal Citi/prepaid XML-RPC utilities; the format is not a public standard

## Regulatory Obligations

- **PCI DSS Requirement 3.5 (Key management)**: This library is part of the cryptographic key management system; the security of key retrieval directly affects the strength of data protection controls. Insecure key retrieval equals insecure cardholder data protection
- **PCI DSS Requirement 3.6 (Key custody)**: Key access must be restricted to those with a business need; the library provides no access control of its own — all access control is at the StrongBox service layer
- **PCI DSS Requirement 6 (Secure development)**: The library uses Java deserialisation via XmlRPC; deserialisation vulnerabilities are an ongoing CVE category
- **GLBA**: Encryption keys protecting customer financial data are themselves GLBA-protected assets

## Key Business Risks

1. **Unencrypted XML-RPC transport**: The default StrongBox service URL (`service.default.properties` in `strongbox-xmlrpc_SVC`) is `http://ecappdev:8080/...` — plaintext HTTP. If the production deployment uses HTTP rather than HTTPS, all key material retrieved from StrongBox travels over the network unencrypted
2. **Java object deserialisation attack surface**: `XmlRPCToObjectMapper.toObject()` deserialises XML-RPC responses; if an attacker can perform a man-in-the-middle on the StrongBox connection or compromise the StrongBox service, they can return a malicious XML-RPC response that exploits Java deserialisation gadget chains
3. **Reference string opacity**: The StrongBox reference string returned by write operations is an opaque token that encodes the location and encryption key reference for stored data; if this reference is stored unprotected, it provides a path to the encrypted data
4. **Spring 4.3.x dependency**: The library declares `spring.version=4.3.27.RELEASE` — Spring Framework 4.x has been end-of-life since December 2020 and has unpatched CVEs
