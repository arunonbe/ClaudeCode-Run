# Business Analyst View — strongbox-lib_LIB

## Business Purpose
StrongBox is Onbe's (formerly ECount/Citi Prepaid) internal credential vault library. It provides encrypted storage and retrieval of **sensitive cardholder information** — specifically Social Security Numbers (SSNs), dates of birth, and bank account numbers. It is a security-critical, PCI DSS-relevant component used by ECount Core, Job Service, and Repository Service.

## Capabilities
- **Encrypt and store** arbitrary sensitive data objects (serialised to XML) in a dedicated Microsoft SQL Server database using a hybrid RSA + symmetric key scheme.
- **Decrypt and return** stored data objects by reference token.
- **Version-aware cryptography**: supports V1 (RSA/DESede) and V2 (RSA/AES-128) cipher suites.
- **Client library** (`strongbox-client`): provides a thread-safe XML-RPC client that discovers the StrongBox service address via a Director service and caches the location for one hour.
- **Server library** (`strongbox-impl`): provides the full encryption/decryption pipeline and JDBC DAO for direct database access.

## Entities
| Entity | Description |
|--------|-------------|
| `AsymmetricKey` | RSA public/private key pair (MASTER key), stored in the StrongBox SQL database; in-process cached after first load. |
| `SymmetricKey` | Per-record randomly generated DESede (V1) or AES-128 (V2) key; encrypted with the MASTER RSA key and stored alongside the data. |
| `SecureData` | Encrypted ciphertext of the actual sensitive payload (SSN, DOB, bank account). |
| `DataRepositoryReference` | Opaque reference token returned to callers; encodes the version, asymmetric key ID, symmetric key ID, and data ID. |
| `CipherText` / `PlainText` | Value objects wrapping byte arrays for ciphertext and plaintext respectively. |

## Business Rules
- All writes use the hardcoded MASTER key name (`"MASTER"`) to encrypt the per-record symmetric key.
- V1 references use DESede/CBC/PKCS5Padding with hex-encoded storage; V2 references use AES-128/CBC/PKCS5Padding with Base64-encoded storage.
- The `writeReferenceVersion` property controls which cipher version is used for new writes (default `"V1"`).
- Reads are version-aware: the stored reference version determines which cipher suite is used for decryption.
- The client layer locates the StrongBox service via a Director service and caches the URL for 3,600,000 ms (1 hour).

## Flows
1. **Write flow**: Caller passes a data object → marshalled to XML → random symmetric key created → symmetric key encrypted with MASTER RSA key → both stored in SQL → opaque reference token returned.
2. **Read flow**: Caller passes reference token → token parsed to extract version/key IDs/data ID → asymmetric key loaded (cached) → symmetric key decrypted with RSA private key → data decrypted with symmetric key → XML unmarshalled and returned as object.
3. **Remote client flow**: `StrongBoxXMLRPCClient` → Director service (location resolution, cached) → XML-RPC HTTP call to StrongBox service → same read/write semantics as above.

## Compliance Relevance
- **PCI DSS Requirement 3**: This system is the primary control for protecting stored sensitive authentication data (SSN, DOB, bank account). It implements encryption at rest for cardholder-related PII/SAD adjacent data.
- **PCI DSS Requirement 6.3**: Cryptographic algorithm selection (RSA, AES) and key management lifecycle must be reviewed.
- **GLBA**: Bank account numbers and SSNs fall under GLBA-protected financial information.
- **Reg E**: Bank account data used for ACH disbursements is in scope.

## Risks
- README explicitly states: "SSN, Date of Birth, Bank accounts" are stored — all are regulated data categories.
- `com.citi` group ID and "Citi Prepaid" artifact names remain in the codebase (unresolved TODO in README), indicating legacy Citi lineage and possible IP / branding governance concern.
- Tests require a live SQL Server (non-self-contained); CI/CD pipeline skips tests (`-Dmaven.test.skip`).
- V1 cipher suite (DESede/3DES) is cryptographically deprecated; PCI DSS v4.0 disallows 3DES for new implementations.
- RSA/ECB/NoPadding (`V1_ASYM_TRANSFORM`) is cryptographically weak; ECB mode is vulnerable and NoPadding allows oracle attacks.
