# Business Analyst View — wirecard_utilities_LIB

## Business Purpose

wirecard_utilities_LIB (`com.wirecard.issuing:utilities:1.0.9-SNAPSHOT`) is a Gen-2 (Wirecard/Northlane) shared utility library providing common infrastructure capabilities for the Wirecard Issuing microservices platform. It is a non-business-logic library — a pure technical utility that reduces code duplication across issuing services. The library was developed during the Wirecard era and continues to be used by Gen-2 services in the Onbe platform.

The library was eventually adopted more broadly under Onbe (`Implementation-Vendor: Onbe, Inc` in the JAR manifest), confirming active maintenance post-acquisition.

## Capabilities Provided

- **PGP encryption/decryption** (`PGPUtils`): Full PGP encrypt/decrypt using BouncyCastle (public key encryption, private key decryption, integrity verification, armored output). Used for encrypting sensitive file transfers (e.g., bank statement files, settlement files) between Wirecard Issuing services and partner banks/networks.
- **Date/time utilities** (`DateTimeUtils`): Common date/time formatting and parsing operations consistent across all issuing services
- **Unique ID generation** (`UniqueIdGenerator`): Generates unique identifiers for transactions, requests, and correlation IDs
- **JSON serialization** (`JsonUtils`): Jackson-based JSON utilities for consistent serialization/deserialization across services
- **Money/currency utilities** (`MoneyUtils`): Arithmetic and formatting for monetary amounts; prevents floating-point rounding errors in financial calculations
- **Path/file utilities** (`PathUtils`): Safe file path construction and validation
- **Thread-local batch job context** (`ThreadLocalBatchJobContext`): Carries batch job execution context (job ID, batch metadata) through the call stack without explicit parameter passing
- **Validation constraints** (`validation/`): Custom Bean Validation annotations:
  - `@CountryCode` / `CountryCodeValidator` — validates ISO 3166-1 alpha-2 country codes
  - `@CurrencyCode` / `CurrencyCodeValidator` — validates ISO 4217 currency codes
- **Test utilities** (`testutil/`): Email test utilities (`EmailUtils`), embedded SFTP server (`EmbeddedSftpServer`) for integration testing

## Client/Cardholder Impact

No direct cardholder impact — this is an infrastructure utility library. However, incorrect implementations in this library have cascading impacts across all Gen-2 issuing services:

- `PGPUtils` defects could cause: failed encryption of settlement files (security breach), failed decryption of bank-provided files (operational failure), or integrity check failures (data corruption)
- `MoneyUtils` defects could cause: incorrect financial amount calculations in any issuing service consuming the library — a high-severity financial risk
- `UniqueIdGenerator` defects causing ID collisions could corrupt transaction correlation across services

## Business Rules Found in Code

- PGP encryption supports both integrity-protected (`withIntegrityCheck=true`) and non-integrity-protected modes; integrity protection must always be enabled for production file transfers
- PGP encryption supports configurable compression and encryption algorithm types — algorithm selection is the responsibility of the calling service; weak algorithms must not be selected
- Country code validation uses ISO 3166-1 alpha-2 standard — ensures consistent geographic classification across all issuing services
- Currency code validation uses ISO 4217 — ensures consistent currency handling for multi-currency issuing programs
- `ThreadLocalBatchJobContext` binds context to the current thread — batch job context must be cleared after use to prevent context leakage between thread-pool-reused threads (ThreadLocal leak risk)
- `MoneyUtils` prevents floating-point arithmetic — uses `BigDecimal` internally (inferred from the purpose of the class); ensures NACHA-compliant amount precision

## Regulatory Obligations

- **PCI DSS Requirement 4.2.1** (strong cryptography for data in transit): `PGPUtils` provides the cryptographic capability for protecting sensitive files in transit to partner banks; the calling service must configure strong algorithms (AES-256, SHA-256 or better) when invoking `PGPUtils.encryptFile()`.
- **NACHA**: `MoneyUtils` precision is critical for ACH amount fields (must be exact cent-level values; no rounding errors).
- **GLBA**: File encryption via `PGPUtils` is a safeguard control for protecting financial data transmitted to external parties.

## Key Business Risks Found in Code

- **`1.0.9-SNAPSHOT` version**: SNAPSHOT artifact used in production builds violates Maven best practices and creates non-reproducible builds. A stable release version should be cut.
- **BouncyCastle 1.48 for PGP** (`bcpg-jdk15on:1.48`): Version 1.48 is from 2013 — extremely old. Current BouncyCastle is 1.78+. Multiple CVEs affect intermediate versions. For a library used to encrypt financial file transfers, using a 10+ year old cryptography library is a critical security risk.
- **Spring Core 5.1.8.RELEASE**: EOL (Spring 5.1.x); included as a dependency. Services consuming this library inherit this EOL Spring version if they don't override it.
- **Jackson 2.9.9**: EOL; CVE-2019-14379, CVE-2019-14439 and others affect Jackson 2.9.x. Wildcard deserialization vulnerabilities.
- **ThreadLocal context leak**: `ThreadLocalBatchJobContext` stores context in `ThreadLocal`. If the calling service uses a thread pool and fails to clear the context after batch job completion, the context leaks to subsequent requests processed by the same thread.
