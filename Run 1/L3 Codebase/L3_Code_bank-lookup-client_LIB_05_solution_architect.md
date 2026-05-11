# bank-lookup-client_LIB — Solution Architect View

## Technical Architecture

The library is a **multi-threaded batch file processor** implemented in Java. It uses an Abstract Factory + Strategy pattern to select from six processor implementations and dispatches work via `java.util.concurrent.ThreadPoolExecutor`. The architecture has three logical tiers:

```
[Entry point]
  AchOutboundProcessor (main class)
      |
      v
[Factory tier]
  ProcessorFactory  -->  DefaultProcessorFactory | BufferedProcessorFactory
      |
      v
[Processor tier]
  AbstractProcessor (base)
    |- DefaultProcessor          (Java NIO read, JAVA_PROCESSOR + any queue)
    |- BufferedProcessor         (BufferedReader, JAVA_PROCESSOR + any queue)
    |- FlatPackDefaultProcessor  (FlatPack full-load, FLATPACK_PROCESSOR + any queue)
    |- FlatPackBufferedProcessor (FlatPack streaming, FLATPACK_PROCESSOR + any queue)
      |
      v
[Worker/Helper tier - runs in ThreadPoolExecutor threads]
  AbstractProcessorHelper (StrongBox cache + lookup)
    |- ProcessorHelper          (Callable<List<String>>)      -- used by Java processors
    |- FlatPackProcessorHelper  (Callable<List<List<String>>>) -- used by FlatPack processors
      |
      v
[External I/O]
  StrongBoxClient  -->  HTTP POST XML-RPC  -->  StrongBox service
  FileChannel      -->  Output flat file
```

**Key design choices observed in code:**
- `ProcessorFactory` is a double-indirection factory (factory of factories). Singletons via static field initialisation — not thread-safe if `getInstance()` is ever called from multiple threads before initialisation completes (race condition on the null check at `ProcessorFactory.java` line 27).
- `Configuration` uses the same unsafe singleton pattern (double-checked without `volatile`, `Configuration.java` lines 70, 91).
- Worker threads share a single `FileChannel` and synchronise writes with `synchronized (outputChannel)`. This is correct but creates a write serialisation bottleneck.
- `DefaultProcessor` uses Java NIO `FileChannel.map()` (memory-mapped file) to load the entire input file into a `CharBuffer` before processing, which will fail on files larger than ~2 GB (integer cast at line 212: `(int) channel.size()`).

## API Surface

This component has **no network API surface**. It is a command-line batch executable.

**Entry point (command-line)**:
```
AchOutboundProcessor.main(String[] args)
  args[0] = path to .properties configuration file
  args[1] = path to input ACH flat file
  args[2] = path to output NACHA file
```
Exit code: `0` on success, `1` on failure.

**Programmatic API (library use)**:
- `Configuration.getInstance(String propertiesFileName)` — load config
- `ProcessorInterface.process(inputFileName, outputFileName, fileDelimiter, columnQualifier, maxRowsPerThread)` — execute enrichment
- `StrongBoxClient.readData(String reference)` → `StrongBoxOutput` — individual bank lookup

There is no REST, gRPC, JMS, or event interface.

## Security Posture

### Critical Issues

1. **No TLS enforcement on StrongBox transport** (`StrongBoxClient.java`): Apache Commons HttpClient 3.x (`MultiThreadedHttpConnectionManager`) is used with no SSL socket factory configuration. The URI comes from the Director service at runtime; if it resolves to `http://`, bank account numbers and routing numbers transit the network unencrypted. HttpClient 3.x does not support TLS 1.2/1.3 by default.

2. **Plaintext sensitive data written to filesystem**: Output file contains `routing_number:account_number:account_type:bank_name:country` in cleartext for every payment record. No file permission enforcement, encryption, or temporary file cleanup.

3. **In-memory cache contains aggregated sensitive financial data**: `AbstractProcessorHelper.cache` (a static `ConcurrentHashMap`) accumulates all bank lookups for the JVM lifetime with no eviction or encryption. A heap dump would expose all processed bank records.

4. **Agent/profile name transmitted as cleartext HTTP header** (`StrongBoxClient.java`, line 465: `postMethod.addRequestHeader("RPC-Agent", this.agent)`). If the agent acts as a credential, it is exposed in plaintext in HTTP traffic and potentially in logs.

5. **Properties file stores infrastructure addresses in plaintext**: The director address and StrongBox connection parameters are stored in a properties file on the filesystem with no secrets manager integration.

6. **No input sanitisation**: Reference strings from the input file are passed directly to `StrongBoxClient.readData()` and included in XML-RPC request bodies via `XmlRPCFromObjectMapper`. If the XML-RPC serialiser does not escape properly, XML injection is possible.

### Moderate Issues

6. **Unsafe singleton pattern**: `Configuration` and all factory classes use non-volatile static fields with null checks for lazy initialisation. Under Java Memory Model rules without `volatile` or `synchronized`, a second thread could observe a partially initialised object.

7. **`@SuppressWarnings("unchecked")`**: Used in `FlatPackBufferedProcessor.java` (lines 75, 245) and `FlatPackDefaultProcessor.java` (line 216) to suppress unchecked cast warnings on `parser` and `DataSet` collections. These casts are not verified at runtime, risking `ClassCastException` on unexpected FlatPack responses.

8. **`postMethod.releaseConnection()` called even if `postMethod` is null** (`StrongBoxClient.java`, line 449 in `finally` block): If `createPostMethod()` threw an exception before assigning `postMethod`, this would throw a `NullPointerException` in the `finally` block, masking the original exception.

## Technical Debt

### High Severity

| Item | Location | Description |
|---|---|---|
| Java 6 target | `pom.xml` lines 68–69 | EOL since 2013; dependency chain incompatible with modern TLS and security |
| Apache Commons HttpClient 3.x | `StrongBoxClient.java` imports | EOL; superseded by HttpComponents 4.x/5.x; no TLS 1.2+ support |
| SLF4J 1.1.0-RC1 | `pom.xml` lines 48–55 | Ancient pre-release from 2006; current release is 2.x |
| Property key name swap bug | `Configuration.java` lines 65–66 | `PROCESSOR_STRONGBOX_HOST_CONNECTION_TIMEOUT_KEY` and `PROCESSOR_STRONGBOX_POOL_CONNECTION_TIMEOUT_KEY` have swapped string values, causing wrong timeout values to be set |
| Memory-mapped full file load | `DefaultProcessor.java` line 212 | `(int) channel.size()` silently truncates files > 2 GB |

### Medium Severity

| Item | Location | Description |
|---|---|---|
| SNAPSHOT version | `pom.xml` line 14 | Non-reproducible build; mutable artifact |
| Unsafe singleton initialisation | `Configuration.java` lines 70–95; all factory classes | Non-volatile lazy singleton; not thread-safe under JMM |
| Unused `jxl` dependency | `pom.xml` lines 39–43 | Declared but no `jxl` import in any source file |
| Column index hard-coded | `ProcessorHelper.java` line 36, `FlatPackProcessorHelper.java` line 33 | Schema coupling; breaks silently if input format changes |
| `printProperties()` label swap | `Configuration.java` lines 622–625 | Prints `fileColumnDelimiter` under qualifier label and vice-versa |
| `AchOutboundProcessorDriver` in test tree | `src/test/.../AchOutboundProcessorDriver.java` | Near-duplicate of main class; not a test; adds confusion and maintenance risk |
| Busy-wait polling | `BufferedProcessor.java` line 133, `DefaultProcessor.java` line 141 | `while (!areDone) Thread.sleep()` is inefficient; should use `Future.get(timeout)` or `CountDownLatch` |

### Low Severity

| Item | Location | Description |
|---|---|---|
| `new Integer(int)` / `new Long(long)` | `Configuration.java` throughout | Deprecated constructor calls; should use `Integer.valueOf()` / `Long.valueOf()` |
| jdom 1.0 dependency | `pom.xml` | Declared but not directly used in source; likely transitive |
| SVN SCM metadata still in pom.xml | `pom.xml` lines 20–24 | Stale reference to decommissioned SVN server |
| JDOM 1.0 | `pom.xml` | EOL library |

## Gen-3 Migration Requirements

To migrate this component to a Gen-3 / modern architecture, the following must be addressed:

1. **Bank data lookup service**: Replace Director + StrongBox XML-RPC with a Gen-3 API-based bank data service (REST/gRPC) with proper authentication (OAuth2/mTLS), TLS 1.2+ enforcement, and response caching at the service layer.

2. **Secrets management**: Replace properties-file configuration of infrastructure addresses and agent names with a secrets manager (e.g., HashiCorp Vault, AWS Secrets Manager). Agent credentials must not be plaintext.

3. **Sensitive data protection**:
   - Encrypt output files at rest or deliver enriched data through an encrypted channel rather than a filesystem file.
   - Avoid caching full bank account data in-process heap; use reference tokens or masked representations where possible.
   - Enforce TLS for all network I/O.

4. **Java version upgrade**: Migrate from Java 6 to a supported LTS release (Java 17 or 21). Replace Commons HttpClient 3.x with HttpClient 5.x or equivalent. Update SLF4J to 2.x, replace FlatPack 3.1.1 with a maintained parser.

5. **Input/output schema documentation**: Before migration, the business meaning of all 16 columns must be documented. The output format (colon-delimited bank injection at column 10) must be formalised or replaced with a structured format.

6. **Event-driven or API-driven processing**: Replace the file-polling batch model with an event-driven trigger (e.g., file landing event via S3/blob storage notification, or a REST endpoint receiving payment records) to align with Gen-3 platform patterns.

7. **Observability**: Replace file-based log4j with structured logging (JSON) shipped to a centralised log platform. Add metrics (record counts, latency, error rates) via Micrometer or equivalent.

8. **Automated test coverage**: Write unit and integration tests covering: Configuration parsing, all six processor/queue combinations, StrongBox lookup success/failure/timeout paths, retry logic, and output file correctness.

9. **Fix property key swap bug** (if the component must continue operating pre-migration): Correct `Configuration.java` lines 65–66 to restore correct timeout assignment.

## Code-Level Risks

| Risk | Severity | File | Line(s) | Detail |
|---|---|---|---|---|
| Integer overflow on large files | High | `DefaultProcessor.java` | 212 | `(int) channel.size()` will corrupt or throw on files > 2,147,483,647 bytes |
| NullPointerException in finally | Medium | `StrongBoxClient.java` | 449 | `postMethod.releaseConnection()` with potentially null `postMethod` |
| Wrong timeout applied | High | `Configuration.java` | 65–66 | Key names for host and pool connection timeouts are swapped |
| Non-volatile singleton | Medium | `Configuration.java` | 70, 91 | Object may be observed partially initialised in multi-threaded start-up |
| Unprocessed records silently dropped | High | `BufferedProcessor.java` | 339 | If `numRetries` is null (not configured), `do-while` exits without retrying and the check `numRetries != null && currRetries < numRetries` short-circuits — records returned in `unprocessedFutures` at the final `checkForUnprocessedRecords` call do trigger an exception, but the initial `do {}` loop will not retry at all (currRetries stays 0, retry stays false on first pass when numRetries is null) |
| Fixed 1024-byte ByteBuffer | Medium | `ProcessorHelper.java` line 60, `FlatPackProcessorHelper.java` line 59 | `ByteBuffer.allocate(1024)` — enriched records exceeding 1024 bytes will overflow and `BufferOverflowException` will be thrown |
| Raw row logged at WARN | Low | `BufferedProcessor.java` lines 290–295 | Unprocessed raw ACH rows (which may contain PII or financial data) are logged at WARN level |
| Shared static HttpClient | Low | `StrongBoxClient.java` line 57 | `private final static HttpClient httpClient` is a static field; every `StrongBoxClient` constructor overwrites the shared connection manager, which could cause unexpected behaviour if multiple clients are created |
