# 04 Enterprise Architect — wirecard_utilities_LIB

## Platform Generation
Gen-2 / Transitional. Java 8, Spring Core 5.x (as a library dependency), SNAPSHOT versioning, BouncyCastle 1.48. Sits between the Gen-1 Spring 2.x era and the Gen-3 Spring Boot 3 / Java 21 estate. Part of the Wirecard Issuing technology stack (package namespace `com.wirecard.utilities`).

## Business Domain
Cross-cutting Engineering Concern / Shared Infrastructure. Provides stateless utility functions consumed across Wirecard Issuing services: PGP file encryption/decryption, JSON serialisation/deserialisation, date/time manipulation, money arithmetic, unique ID generation, file path utilities, country/currency code validation, and a thread-local batch job context.

## Role
Shared utility library. No business logic; no domain model. Acts as a common dependency baseline ensuring consistent implementations of low-level cross-cutting concerns across the Wirecard Issuing service family.

## Dependencies
| Dependency | Direction | Purpose |
|---|---|---|
| BouncyCastle `bcpg-jdk15on:1.48` | Compile | PGP encrypt/decrypt for file exchange |
| Jackson `2.9.9` | Compile | JSON serialisation/deserialisation |
| Spring Core `5.1.8.RELEASE` | Compile | Utility base (e.g., `StringUtils`, resource loading) |
| Hibernate Validator `6.0.17.Final` | Compile | Bean validation for country/currency code constraints |
| SLF4J `1.7.26` | Compile | Logging facade |

## Integration Patterns
- **Static utility pattern**: all public methods are static; no Spring beans, no dependency injection
- **Pure library**: consumed at compile time by Wirecard Issuing services; no runtime service calls

## Strategic Status
**Needs security remediation — moderate strategic value.** The library provides genuinely useful shared utilities, particularly `PGPUtils` (used for secure file exchange with payment partners) and `JsonUtils`. However:
- BouncyCastle 1.48 is dangerously outdated for a library used in payment file encryption
- Jackson 2.9.9 contains known deserialization CVEs
- SNAPSHOT versioning makes dependency management unreliable

Recommended action: create a release (`1.0.9`) with updated dependencies (BouncyCastle 1.78+, Jackson 2.17+, Spring Core 6.x or removal, Hibernate Validator 8.x / Jakarta), then migrate all consumers. Longer-term, evaluate whether Spring Core is needed at all (most utilities are pure Java and could drop the Spring dependency).

## Migration Blockers
- No blockers for dependency updates; this is a library with a stable API surface
- Consumers must be recompiled after the BouncyCastle major version upgrade (breaking API changes in BC 1.70+)
- `PGPUtils.decryptFile()` and `encryptFile()` callers must be regression-tested after BouncyCastle upgrade
- Any consumer using `ThreadLocalBatchJobContext` in a multi-threaded environment must verify thread-local cleanup is handled correctly after migration
