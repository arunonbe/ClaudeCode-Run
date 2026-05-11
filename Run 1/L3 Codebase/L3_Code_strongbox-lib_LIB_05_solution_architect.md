# Solution Architect View — strongbox-lib_LIB

## Technical Architecture
- Multi-module Maven project: `strongbox` (parent POM), `strongbox-impl` (server JAR), `strongbox-client` (client JAR).
- Java 21 compiler target; Spring Framework (XML-based DI, no Spring Boot).
- Server-side: `RepositoryService` → `RepositoryServiceLibrary` → `IStrongBoxDAO` → `StrongBoxJDBCDAOImpl` → stored procedures on SQL Server.
- Client-side: `StrongBoxXMLRPCClient` → Director service (URL discovery) → XML-RPC HTTP → StrongBox server.

## API Surface
### Server-side (`strongbox-impl`)
Implements `IStrongBoxService`:
| Method | Signature | Description |
|--------|-----------|-------------|
| `repositoryServiceRead` | `(String agent, String reference, Object target) → Object` | Decrypt by reference, deserialise into target object |
| `repositoryServiceReadMap` | `(String agent, String reference) → Map<String,Object>` | Decrypt by reference, return as Map |
| `repositoryServiceWrite` | `(String agent, Object data) → String` | Encrypt object, return reference |
| `repositoryServiceWriteMap` | `(String agent, Map<String,Object> data) → String` | Encrypt map, return reference |

### Client-side (`strongbox-client`)
Same interface via XML-RPC transport. Additional constructors expose HTTP connection pool tuning (maxConnectionsPerHost, maxActiveConnections, timeouts).

## Security Posture

### Authentication
- No authentication between `StrongBoxXMLRPCClient` and the StrongBox service observed in code. The `agent` string is passed as a parameter but there is no cryptographic authentication or token-based auth visible.
- SQL Server access via username/password (hardcoded `b2cstage`/`b2cstage` in test `spring.xml`).

### Cryptography — Critical Findings
| Finding | Location | Severity |
|---------|----------|----------|
| DESede (3DES) used for V1 symmetric encryption | `StrongBoxCiphers.java:14-15` | Critical — NIST deprecated, PCI DSS v4.0 non-compliant |
| RSA/ECB/NoPadding used for asymmetric key encryption | `StrongBoxCiphers.java:12-13` | Critical — semantically insecure, vulnerable to CCA |
| AES-128 (not 256) used for V2; CBC mode without AEAD | `StrongBoxCiphers.java:17-19` | High — PCI DSS v4.0 recommends authenticated encryption |
| RSA private key stored in the same database as ciphertext | `SbGetData.java:24-26` | Critical — key and ciphertext co-location |
| Static in-process HashMap used as key cache | `AsymmetricKey.java:25`, `RepositoryServiceLibrary.java:23-24` | High — no TTL, no key rotation without restart |

### Secrets Management
- Test database credentials (`b2cstage`/`b2cstage`) hardcoded in `strongboxImpl/src/test/resources/spring.xml:24-29`.
- No external secrets manager (Vault, AWS SSM, etc.) observed.
- Production credentials expected to be injected by the consuming service's Spring XML configuration.

### Logging — PCI DSS Concern
| Issue | Location | Severity |
|-------|----------|----------|
| `log.get().info("Data to be decrypted:" + data.getData_value())` logs the **encrypted** ciphertext value at INFO level | `RepositoryServiceLibrary.java:74` | Medium (encrypted, but exposes DB contents to log aggregators) |
| `log.get().debug("Decoded data: " + textResult.getPlainText().toString())` logs the **plaintext decrypted data** at DEBUG level | `RepositoryServiceLibrary.java:87` | Critical — if DEBUG logging is ever enabled in production, decrypted SSN/DOB/bank account data will appear in logs |
| RSA private/public key hex values logged at DEBUG | `AsymmetricKey.java:40-41` | Critical — key material in logs |

### Known CVE Exposure
| Library | Concern |
|---------|---------|
| Apache HttpClient 3.x (`org.apache.commons.httpclient`) | EOL; no security patches since ~2011; vulnerable to multiple CVEs depending on JVM TLS configuration |
| JTDS JDBC driver | Not the official Microsoft JDBC driver; limited security update history |
| `commons-dbcp:1.x` / `commons-pool:1.x` (test scope) | Old versions; DBCP2/Pool2 preferred |

## Technical Debt
| Item | Location | Severity |
|------|----------|----------|
| `com.citi.prepaid` group IDs / artifact names not renamed | `pom.xml:6`, `strongboxClient/pom.xml:17`, `strongboxImpl/pom.xml:1` | Medium (branding/IP governance) |
| Log name hardcoded as `com.ecount.Core2.StrongBox` | `LoggingUtils.java` (noted in README) | Low |
| Tests require live SQL Server — not self-contained | README, `spring.xml` | High |
| `maven-wrapper.jar` committed to repository | `.mvn/wrapper/maven-wrapper.jar` | Medium (supply chain) |
| `CipherText(String)` deprecated constructor with no version | `CipherText.java:30-33` | Low |
| `IOException` in `CipherText` V2 Base64 decode swallowed via `e.printStackTrace()` | `CipherText.java:46-48` | Medium |
| `SbDeleteData` class exists but is not wired into production DAO | `SbDeleteData.java` | Medium (data retention) |

## Gen-3 Migration Requirements
1. Replace DESede/3DES with AES-256-GCM (authenticated encryption) — requires bulk re-encryption of all stored records.
2. Replace RSA/ECB/NoPadding with RSA-OAEP-SHA256 for asymmetric key encryption.
3. Migrate key storage from same SQL database to a dedicated HSM or cloud KMS (HashiCorp Vault, AWS KMS, Azure Key Vault).
4. Replace XML-RPC + Apache HttpClient 3.x with REST/gRPC over TLS 1.3.
5. Replace static in-process key cache with a TTL-based cache with key rotation support.
6. Remove all DEBUG-level plaintext and key material logging before any Gen-3 deployment.
7. Introduce self-contained integration tests using an in-memory or containerised SQL Server.
8. Rename all `com.citi.prepaid` group IDs to Onbe namespace.
