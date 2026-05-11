# Solution Architect View — js-import_SVC

## Solution Overview

`js-import_SVC` is a solution-level component responsible for the **translation layer** between client-supplied bulk data files and the internal `jobsvc` relational schema. The solution architecture centres on three concerns: (1) parsing correctness for a complex hierarchical fixed-width format; (2) reliable transactional persistence to SQL Server; and (3) extensibility for new record types.

## Component Design

### Parser Architecture

The core parsing engine (`com.ecount.datagen.Parser`) implements a **finite state machine (FSM)** parser. States are integer-keyed constants defined in `RequestFileParser.java`. Transitions are declared via `ParserRule` objects added at construction time (~70 rules registered in `RequestFileParser()` constructor).

The lexer (`JobSvcParserLineLexer`) tokenises input line-by-line. Each line's record type byte is used to instantiate the correct `RecordLine` subclass. The FSM then validates that the current record type is a legal transition from the current state — rejecting structurally invalid files at the grammar level.

This is a sound design for a fixed-format protocol but carries the following architectural risks:
- **No formal grammar specification** (e.g., ANTLR): the parser is entirely code-defined, making it difficult to validate against client documentation.
- **State explosion**: 70+ rules across 30+ states. Adding new record types requires careful insertion of rules in the correct state transitions — a brittle modification surface.
- **No streaming/checkpointing**: the entire file is processed in a single pass with no resume capability. Large files that fail midway must be resubmitted in full.

### DAO Layer Design

Each record type has a dedicated DAO class (`com.ecount.jobsvc.db.*DAO`). This one-DAO-per-record-type pattern provides clear separation of concerns but results in ~25 DAO classes, all sharing the same `JobSvcDataSource`. The DAOs are Spring-wired beans (not Spring Data / JPA), executing direct SQL or stored procedure calls.

`InsertRecordsDAO` and `InsertRecordsDAOManager` act as a coordinator — the `DBRequestProcessor` orchestrates the sequence of DAO calls for a single `Request` record, maintaining transactional integrity across the parent record and its addenda.

### Threading and Concurrency

The `JSContext` singleton pattern (`JSContext.java`) uses a `static final INSTANCE` initialised at class-load time. This is thread-safe for reads but means the application context is shared across all servlet threads. DAO instances are also shared Spring singletons — they must be stateless, which appears to be the case since state is passed as method parameters.

`IDGeneratorImpl` wraps `GetIDSequenceDAO` / `UpdateIDSequenceDAO` with compare-and-swap logic. This provides optimistic concurrency for ID generation but under high load could cause spin-wait contention.

## Security Architecture

### Authentication and Authorisation

`JobValidatorServlet` (`src/main/java/com/ecount/web/JobValidatorServlet.java`) is the HTTP entry point. There is no visible in-application authentication — access control is delegated entirely to the network and container (Tomcat `web.xml` security constraints).

**Finding**: If `web.xml` does not define `<security-constraint>` elements restricting access to authenticated callers, the import endpoint is unauthenticated. This is a critical security gap given the PII content of import files.

### Input Validation

Input validation occurs at two levels:
1. **Structural**: The FSM parser rejects malformed record sequences.
2. **Field-level**: `CharType` / `NumericType` enforce maximum field widths and (via `ValidDataTypesContainer`) character set restrictions.

**Gap**: There is no injection sanitisation specifically for SQL. The DAOs rely on Spring's `JdbcTemplate` parameterised queries — which is appropriate — but this should be confirmed for all DAOs, particularly those with dynamic SQL construction.

### Transport Security

The service listens on HTTP (`PROJECT_SERVICE_PROTO: http`). Import files containing PII and financial data are transmitted without TLS at the application layer. This must be mitigated by the network layer (private VLAN, no internet-facing exposure) or upgraded to HTTPS.

## Solution Patterns and Anti-Patterns

| Pattern | Assessment |
|---|---|
| FSM file parser | Appropriate for fixed-format protocol |
| One-DAO-per-record-type | Appropriate separation but high class count |
| Shared Spring XML app context | Acceptable for WAR; limits testability |
| JNDI data source | Appropriate for J2EE but environment-coupled |
| Hard-coded filesystem path | Anti-pattern: prevents containerisation |
| Tests skipped in CI | Anti-pattern: zero automated regression coverage |
| Singleton IDGenerator | Adequate for single-instance; fails under HA |

## Solution Gaps and Recommendations

1. **Add application-level authentication** to `JobValidatorServlet` — validate a client certificate or API key before accepting file uploads.
2. **Enable HTTPS** — configure Tomcat TLS connector for the `8480` port or place behind a TLS-terminating reverse proxy.
3. **Add integration tests** — reinstate `maven-failsafe-plugin` execution; the `-Dmaven.test.skip=true` flag in CI must be removed.
4. **Externalise the `D:/c-base` path** — replace with an environment variable or Spring property, enabling deployment flexibility.
5. **Implement structured error logging** — the `ErrorLogger` utility should mask PII fields before logging; currently exception messages may expose cardholder names, addresses, or phone numbers.
6. **Add file-level checksum validation** — the `FileHeader` / `FileFooter` record pair should be validated against a CRC or record count to detect truncated or corrupted files before processing begins.
7. **Implement transactional rollback** — if a batch fails midway, the partial inserts into `jobsvc` should be rolled back. The current `DBRequestProcessor` design should be wrapped in a Spring `@Transactional` boundary.
8. **Upgrade dependency chain** — as detailed in the Enterprise Architect view, the Log4j 1.x, jTDS, commons-collections 3.2 vulnerabilities must be resolved before this service can be considered compliant.
