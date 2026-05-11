# custom-files_LIB — Enterprise Architect View

## Platform Generation
- **Generation: Gen-1 / Legacy.**
- Fixed-width flat file integration is a classic Gen-1 batch pattern. The library itself has been compiled for Java 21 (a Gen-2/3 runtime) but the integration pattern it supports is mainframe-era file exchange.
- No Spring, no REST, no reactive components — pure Java utility library.

## Domain
- **Payments Domain → Batch/ETL Subdomain → eCount File Integration.**
- Supports card issuance (create account), fund loading (add funds), stop payment, and account profile updates via the eCount fixed-width flat file channel.

## Role in the Ecosystem
| Role | Detail |
|---|---|
| Integration library | Provides the serialisation/deserialisation contract for the eCount file format |
| Consumed by | ETL processes, batch jobs that submit files to eCount (e.g., `DS_ETL_*` repos, `prepaid-batch-framework_LIB`, `request-file_LIB`) |
| Produced by | N/A — library only |

## Upstream Dependencies
- `com.parents:prepaid-parent:6.0.12` (parent POM — defines common dependency versions).
- No other runtime dependencies declared in the local `pom.xml`.

## Downstream Consumers
- Any batch or ETL module that creates or parses eCount request/reply files.
- Identified likely consumers from the broader repo inventory: `DS_ETL_*`, `prepaid-batch-framework_LIB`, `request-file_LIB`, `global-deposit-batch_LIB`, `ecore-batch_LIB`.

## Architectural Patterns
- **Value Object / DTO pattern:** All `Ecount*` beans are plain Java objects with getters/setters.
- **Static utility class:** `EcountRequestFile` is a non-instantiable utility class (no public constructor) with all-static methods.
- **Annotation-driven reflection:** Custom annotations (`@PUID`, `@PPD`, `@AccountAddenda`, `@FlatField`, `@Passthrough`, `@EcountID`, `@RequestBlockPad`, `@RequestEcountID`, `@RequestPassThrough`) drive runtime reflection for field discovery.
- **Strategy-like record building:** `createRequest(Object... objects)` accepts any annotated object and extracts eCount-specific fields via annotation scanning.

## Status
- Stable release version (2.0.0); unlikely to be under active development.
- Compiled to Java 21 but the code style is pre-Java 8 (no streams, no generics in key methods, manual StringBuilder usage).

## Blockers / Migration Considerations
1. Fixed-width file integration is a Gen-1 pattern. Gen-3 strategy should use REST/event-driven APIs for all eCount communication. This library would become obsolete once file-based eCount integration is retired.
2. `field.setAccessible(true)` usage is incompatible with Java 21 strict module encapsulation without explicit `opens` declarations. Consuming modules must add `--add-opens` JVM flags.
3. No unit tests — any refactoring is high-risk.
4. `cvCode` in the reply bean is a PCI DSS concern that needs a formal data-handling review before any new consumers are onboarded.
