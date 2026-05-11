# Business Analyst View — xplatform-library_LIB

## Business Purpose
xPlatformLibrary (`xplatformlibrary`) is the lowest-level infrastructure and utility library for the eCount/Onbe prepaid platform. It provides foundational cross-cutting capabilities — cryptography, caching, configuration, logging, networking, threading, SQL access, and XML parsing — that are consumed by `xplatform_LIB` and all downstream services. It has no direct business logic but underpins the security, performance, and reliability of the entire platform.

## Capabilities
- **Cryptography:** Symmetric (DES, 3DES/TripleDES, DES3, RC2, RC4, RC5, DESX, Twofish) and asymmetric (RSA) cipher implementations; DSA signing; Diffie-Hellman key agreement; MD5 and SHA1 hashing; custom padding (PKCS5, PKCS7, CBase, Zero, NoPad); JsafeCipher wrapper for RSA Data Security Jsafe SDK
- **Caching:** `CacheManager` / `SwarmCache` (JGroups-based distributed cache); `ICache` interface for pluggable implementations
- **Configuration:** `ConfigurationFile` INI-style file parser; `ConfigDB` (RPC-based configuration lookup with timeout caching); `RPCTimeoutConfigHelper`
- **Logging:** Custom multi-destination logging framework with filters, formatters, and log destinations (file, network, email, pager, circular buffer, encrypted store); `SystemLog` / `SystemLogger`
- **Networking:** Socket client/server framework, SMTP mailer, protocol handlers
- **Threading:** `ThreadPool`, `ThreadDispatcher`, `Mutex`, `ReaderWriterLock`, `Semaphore`
- **SQL access:** JDBC wrappers (`JdbcConnection`, `JdbcStoredProc`, `JdbcParamStmt`), `StoredProcedure`, `ParameterizedStatement`; parameterised statement parser
- **XML/SAX parsing:** `SaxTool`, `SaxParserFactoryPool` (pooled SAX parser factory for performance), `MapFromXML` / `MapToXML` (property binding XML mapping)
- **StrongBox (secure data store):** Asymmetric and symmetric key store SPI; data repository API for encrypted data storage
- **Data structures:** Custom queues, ordered hashtable, priority queue, quicksort, thread-dispatch queue
- **String utilities:** Hex converter, XML encoder, symbol table, string parser, byte conversion
- **RPC framework:** `rpcConnection`, `rpcDriverClient`, `rpcDriverServer`, `rpcHttpClient`, `rpcHttpMapXmlClient/Server` — custom HTTP/RPC transport layer

## Key Entities
| Entity | Package | Description |
|---|---|---|
| CacheManager / SwarmCache | `com.cbase.cache` | Distributed object cache using JGroups |
| CryptoFactory / various ciphers | `com.cbase.pi.encryption` | Cryptographic algorithm implementations |
| ConfigurationFile | `com.cbase.pi.configfile` | INI-style configuration file reader/writer |
| SystemLog / Logger | `com.cbase.pi.log` | Multi-destination logging engine |
| DataRepository (StrongBox) | `com.cbase.pi.strongbox` | Secure data store SPI |
| SaxTool / SaxParserFactoryPool | `com.ecount.saxtool` | XML parsing with pooling support |
| MapFromXML / MapToXML | `com.ecount.msmapxml` | XML-to-Java property binding |
| rpcService / rpcServlet | `ECount.System.RPC` | Custom RPC transport layer |

## Business Rules
- Crypto algorithms are provided as a library — the correct algorithm selection and key management are the responsibility of calling code
- `SwarmCache` uses JGroups multicast for cluster-aware cache invalidation
- `ConfigDB` fetches configuration via RPC with local timeout caching to avoid repeated file reads (performance fix in v4.1.0)
- `SaxParserFactoryPool` is configurable via JNDI or web.xml parameter (default pool size 10) — performance-critical for high-throughput XML processing
- RPC timeout configuration is loaded from `RPCTimeout.properties` on the classpath; defaults apply if not found

## Compliance Relevance
- Cryptographic primitives used throughout the platform for PAN protection, SSO token encryption, and secure profile storage — directly in scope for PCI DSS Req 3 (encryption) and Req 6 (cryptographic implementation)
- `StrongBox` secure data store SPI — designed for encrypted data persistence; relevant to PCI DSS key management requirements
- Custom logging framework — log content may include sensitive data; encrypted log destination (`EncryptedStoreDestination`) exists
- SMTP `SimpleMailer` — if used for notification of sensitive events, transport security must be verified

## Risks
- Proprietary cipher implementations (DES, 3DES, RC2, RC4, Twofish) — these are bespoke implementations, not standard JCA provider wrappers; correctness and side-channel resistance cannot be assumed
- RC4, RC2, DES, and MD5 are cryptographically weak/broken algorithms — their presence and use must be audited
- SHA1 hashing — deprecated for collision resistance; should be replaced with SHA-256 or higher
- Jsafe SDK (`jsafe` dependency) — RSA Data Security Jsafe is a legacy commercial cryptographic library; current licensing and maintenance status unknown
