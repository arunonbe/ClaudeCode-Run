# 05 Solution Architect — wirecard_utilities_LIB

## Technical Architecture
Pure Java 8 library JAR. All classes are stateless with static methods (per README contract). No Spring beans, no HTTP surface, no persistence. Single package tree: `com.wirecard.utilities.*`.

Modules by package:
| Package | Class(es) | Purpose |
|---|---|---|
| `context` | `ThreadLocalBatchJobContext` | Thread-local storage for batch job context |
| `datetime` | `DateTimeUtils` | Date/time parsing and formatting utilities |
| `generator` | `UniqueIdGenerator` | Unique ID (UUID-based) generation |
| `json` | `JsonUtils` | Jackson-based JSON serialisation/deserialisation |
| `money` | `MoneyUtils` | Monetary arithmetic (BigDecimal-safe) |
| `path` | `PathUtils` | File path construction utilities |
| `pgp` | `PGPUtils` | PGP file encrypt/decrypt using BouncyCastle |
| `validation/constraint` | `CountryCode`, `CurrencyCode` | Custom JSR-303 annotation constraints |
| `validation/validator` | `CountryCodeValidator`, `CurrencyCodeValidator` | ISO 3166-1 alpha-2 / ISO 4217 constraint validators |

Test utilities (test-only JAR):
- `TestUtils`, `EmailUtils`, `EmbeddedSftpServer` — test helpers including embedded SFTP server

## API Surface
No HTTP API. Programmatic static method API:

```java
// Key signatures
PGPUtils.decryptFile(InputStream in, OutputStream out, InputStream keyIn, char[] passwd)
PGPUtils.encryptFile(OutputStream out, String fileName, PGPPublicKey encKey, boolean armor, boolean withIntegrityCheck, int compressType, int encryptType)
PGPUtils.readPublicKey(InputStream in) -> PGPPublicKey
PGPUtils.findPrivateKey(InputStream keyIn, long keyID, char[] pass) -> PGPPrivateKey
JsonUtils.toJson(Object object) -> String
JsonUtils.fromJson(String json, Class<T> clazz) -> T
UniqueIdGenerator.generate() -> String
MoneyUtils.* (monetary operations)
DateTimeUtils.* (date parsing/formatting)
CountryCode / CurrencyCode (JSR-303 constraint annotations)
```

## Security Posture
- **PGPUtils**: BouncyCastle 1.48 (2012) — multiple known CVEs; using `AES_256` or similar is not guaranteed to be correctly applied in this version; **upgrade to 1.78+ is critical** for any production use involving payment partner file exchange
- `decryptFile()` adds `BouncyCastleProvider` via `Security.addProvider()` on every call — this is not thread-safe; multiple concurrent calls will attempt to add the provider repeatedly; `addProvider()` is idempotent but the pattern should be `Security.insertProviderAt()` once at startup (see `BCProviderApplicationContextInitializer` in the token service)
- `encryptFile()` similarly calls `Security.addProvider()` on every invocation — same thread-safety concern
- **JsonUtils**: `ObjectMapper` is a static singleton (thread-safe for read operations after configuration); `fromJson()` accepts `Class<T>` limiting some deserialization gadget exposure, but Jackson 2.9.9 CVEs remain; upgrade to Jackson 2.17+ required
- **`JsonConversionFailed`**: extends `RuntimeException`; catches `IOException` from Jackson and re-throws — callers must handle this unchecked exception
- PGP key material (`char[] passwd`) is passed as a method argument; callers should zero the char array after use (not enforced by the library)
- No logging of sensitive data observed in production code; `PGPUtils` logs only `exception.getMessage()` on encrypt/close errors

## Technical Debt
| Item | Severity |
|---|---|
| BouncyCastle `bcpg-jdk15on:1.48` (2012, multiple CVEs) | Critical |
| Jackson `2.9.9` (known CVEs) | High |
| `Security.addProvider()` called on every PGP operation (not thread-safe pattern) | High |
| Spring Core `5.1.8.RELEASE` (EOL) | High |
| Hibernate Validator `6.0.17.Final` + Javax EL (pre-Jakarta Namespace) | Medium |
| SLF4J `1.7.26` (old; 2.x available) | Low |
| SNAPSHOT version in production use | Medium |
| Commented-out `isForEncryption()` and `hasKeyFlags()` helper methods in `PGPUtils` | Low |
| `static ObjectMapper OBJECT_MAPPER` — not configurable by consumers | Low |

## Gen-3 Migration
The library API surface is stable and well-designed for its purpose. Recommended steps:
1. Upgrade BouncyCastle to `bcpg-jdk18on:1.78+` (note: artifact ID changed from `jdk15on` to `jdk18on` in 1.72)
2. Upgrade Jackson to `2.17.x`
3. Remove Spring Core dependency (replace any Spring utility use with JDK equivalents or Apache Commons)
4. Replace Javax namespaced Hibernate Validator with `hibernate-validator:8.x` (Jakarta EE 10)
5. Update to Java 17 or 21 compile target
6. Release as a fixed version (e.g., `2.0.0`) with a migration guide for consumers
7. Move `Security.addProvider(new BouncyCastleProvider())` to a one-time static initialiser block at the class level in `PGPUtils`

## Code-Level Risks
- `PGPUtils.encryptFile()` calls `out.close()` in a try/catch with comment "this is ArmoredOutputStream, not the input param OutputStream" — if `armor=false`, `out` is the caller's stream; closing it here is incorrect and will close the caller's output stream prematurely
- `decryptFile()` does not close the `clear` (decrypted) `InputStream` after processing; potential resource leak if the method returns normally without exception
- `JsonUtils.fromJson()` wraps all `IOException` (including `MismatchedInputException`) in `JsonConversionFailed`; callers have no way to distinguish between malformed JSON and type mismatch without inspecting the cause
- `ThreadLocalBatchJobContext` uses a `ThreadLocal`; if the batch framework reuses threads (e.g., in a thread pool), stale context from a previous job execution could be read if `remove()` is not called at job end — callers must clean up
