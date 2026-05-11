# bank-lookup-client_LIB — Data Architect View

## Data Stores

| Store | Type | Location | Access Pattern |
|---|---|---|---|
| ACH Input Flat File | Delimited text file | Local filesystem path (command-line arg) | Sequential read, single pass |
| NACHA Output Flat File | Delimited text file | Local filesystem path (command-line arg) | Write-only, overwrite each run |
| StrongBox Repository | Remote XML-RPC service | URI resolved dynamically via Director service | HTTP POST per unique reference; results cached in-process |
| In-Process Bank Cache | `ConcurrentHashMap<String, String>` | JVM heap (`AbstractProcessorHelper`, line 45) | Read/write; no eviction; keyed on reference string |
| Log File | Rolling text file | `ach_processor.log` (local filesystem) | Append-only, up to 10 MB x 5 rotations (`log4j.properties`) |
| Properties File | Java `.properties` text file | External filesystem path (command-line arg) | Read once at startup |

## Schema & Tables

### Input Flat File Schema (AchFileColumnMappings.xml)

The FlatPack mapping (`src/main/resources/AchFileColumnMappings.xml`) declares 16 generic columns:

| Column Index | FlatPack Name | Business Meaning |
|---|---|---|
| 0–9 | COLUMN_0–COLUMN_9 | Undocumented; passed through unchanged |
| 10 | COLUMN_10 | **Reference number** — StrongBox lookup key |
| 11–15 | COLUMN_11–COLUMN_15 | Undocumented; passed through unchanged |

Column 10's content is replaced in the output. The mapping uses no typed metadata; all columns are treated as strings.

### StrongBox Response Structure

Returned as a `Map<String, Object>` with outer key `"bank"` (`BANK_INFORMATION_KEY`). The inner `Map<String, String>` contains:

| Key constant | Field | Description |
|---|---|---|
| `routing_number` | ABA routing number | 9-digit US bank routing number |
| `account_number` | Bank account number | Sensitive: DDA/savings account number |
| `account_type` | Account type | e.g., checking, savings |
| `name` | Bank name | Institution name string |
| `country` | Country code | Country of the financial institution |

The five fields are concatenated colon-delimited into a single string: `routing:account:type:name:country` and written into column 10 of the output (`AbstractProcessorHelper.java`, lines 175–185).

### StrongBoxInput / StrongBoxOutput Objects

- `StrongBoxInput`: `reference` (String), `agent` (String) — serialised to XML-RPC via `XmlRPCFromObjectMapper`.
- `StrongBoxOutput extends OutputBase`: `data` (`Map<String, Object>`) + `Result` (`code`, `message`) from the `com.ecount.xmlrpc.common` library.

### Configuration Properties Schema

All values stored in a flat Java `.properties` file. Key names and types:

| Property Key | Java Type | Mandatory |
|---|---|---|
| `Processor.factory.type` | String (`DEFAULT_FACTORY` / `BUFFERED_FACTORY`) | Yes |
| `Processor.processor.type` | String (`JAVA_PROCESSOR` / `FLATPACK_PROCESSOR`) | Yes |
| `Processor.processor.queue.type` | String (`BOUNDED` / `UNBOUNDED` / `SYNCHRONOUS`) | Yes |
| `Processor.processor.queue.capacity` | int or `Integer.MAX_VALUE` | Yes |
| `Processor.processor.pool.minimum.size` | int | Yes |
| `Processor.processor.pool.maximum.size` | int | Yes |
| `Processor.processor.pool.keep.alive.time` | int (seconds) | Yes |
| `Processor.processor.pool.thread.load` | int | Yes |
| `Processor.processor.queue.fifo.policy` | boolean (yes/true) | Yes |
| `Processor.processor.file.column.delimiter` | char | Yes |
| `Processor.processor.file.column.qualifier` | char | Yes |
| `Processor.director.client.agent` | String | Yes |
| `Processor.director.client.configuration.file` | String (path) | Yes |
| `Processor.strongbox.maximum.host.connections` | Integer | Optional |
| `Processor.strongbox.maximum.active.connections` | Integer | Optional |
| `Processor.strongbox.host.connection.timeout` | Integer (ms) | Optional |
| `Processor.strongbox.pool.connection.timeout` | Long (ms) | Optional |
| `Processor.strongbox.host.socket.read.timeout` | Integer (ms) | Optional |
| `Processor.processor.number.retries` | Integer | Optional |
| `Processor.processor.retries.sleep.time` | Long (ms) | Optional |
| `Processor.processor.sleep.time` | Integer (ms) | Optional |

Note: `Configuration.java` line 65–66 has a **copy-paste error** — the key constants for `PROCESSOR_STRONGBOX_HOST_CONNECTION_TIMEOUT_KEY` and `PROCESSOR_STRONGBOX_POOL_CONNECTION_TIMEOUT_KEY` have their string values swapped (`"Processor.strongbox.pool.connection.timeout"` and `"Processor.strongbox.host.connection.timeout"` respectively), making the mapping inconsistent with the field names.

## Sensitive Data Handling

The following sensitive data classes flow through this library with no encryption or masking:

| Data Element | Sensitivity | Handling |
|---|---|---|
| Bank account number (`account_number`) | High — PII/financial | Stored in JVM heap cache, written to plaintext output file |
| Bank routing number (`routing_number`) | Medium — financial identifier | Stored in JVM heap cache, written to plaintext output file |
| StrongBox reference number (column 10 of input) | Medium | Logged at TRACE level (`AbstractProcessorHelper.java`, line 142), written in output |
| Agent/profile name | Low-medium | Transmitted as HTTP header `RPC-Agent` in cleartext (`StrongBoxClient.java`, line 465) |
| Bank information cache | High | Entire `ConcurrentHashMap` lives in heap for the process lifetime with no encryption |

**At-rest protection**: None. Output file written to the local filesystem in plaintext. No file permission management in code.

**In-transit protection**: StrongBox calls use Apache HttpClient 3.x (`commons-httpclient`). No evidence of TLS/HTTPS enforcement is present in the code — the URI comes from the Director service and its scheme is not validated. If the URI resolves to `http://`, traffic is unencrypted.

**In-memory protection**: Routing numbers and account numbers are stored as plain `String` objects in a `ConcurrentHashMap` with no SecureString equivalent.

## Encryption & Protection

- **None implemented in this library.** There is no use of `javax.crypto`, `java.security`, or any Onbe security utilities.
- The `transient` modifier is applied to `StrongBoxClient.agent` and `StrongBoxClient.location` (lines 47, 52) but this only affects Java object serialisation, not runtime security.
- TLS configuration must be enforced at the Director/StrongBox infrastructure layer; this library does not validate or enforce it.

## Data Flow

```
[Input flat file (disk)]
        |
        | -- BufferedReader / NIO FileChannel / FlatPack parser
        v
[In-memory List<String> or List<List<String>> record chunks]
        |
        | -- Column 10 extracted as reference string
        v
[ConcurrentHashMap cache lookup]
        |   Hit: return cached colon-delimited bank string
        |   Miss:
        v
[StrongBoxClient.readData(reference)]
        |-- XML-RPC POST over HTTP to StrongBox URI
        |-- Response: routing_number, account_number, account_type, name, country
        v
[Colon-delimited bank string assembled & cached]
        |
        | -- Injected into output record at column 10
        v
[FileChannel.write(ByteBuffer)] -- synchronized per thread
        |
        v
[Output flat file (disk)]

[Log file: ach_processor.log -- warnings and errors only]
```

## Data Quality & Retention

- **No input data validation**: Column count, data types, and reference format are not validated before submission to StrongBox.
- **No output record count assertion**: The processor does not verify that output record count equals input record count.
- **Error records**: Records that fail StrongBox enrichment are reported as a fatal error listing only if they remain unprocessed after all retries. There is no separate rejected-records file.
- **Log retention**: `log4j.properties` configures 5 rolling files of 10 MB each (50 MB total). Retention beyond rotation is not managed in-code.
- **Cache lifespan**: Bank data cache persists only for the duration of the JVM process. There is no persistent cache.
- **File overwrite policy**: Output file is always overwritten; no backup or versioning of prior output files.

## Compliance Gaps

1. **No masking of account numbers in logs**: The TRACE-level log in `AbstractProcessorHelper.java` (line 282–296) logs the full raw ACH row including the reference. While not directly logging the account number, trace logs of raw rows could include sensitive data if the input contains it.
2. **No encryption at rest for output file**: Account numbers and routing numbers written in plaintext violates PCI DSS Requirement 3 (protect stored cardholder data) if any accounts in scope are card-linked.
3. **No TLS enforcement for StrongBox transport**: PCI DSS Requirement 4 requires strong cryptography for sensitive data in transit. The HTTP transport layer is not enforced.
4. **No data retention policy enforced**: The output file accumulates enriched banking data on disk indefinitely.
5. **ConcurrentHashMap key collision risk**: The reference string is used as-is as a cache key with no namespace. A reference collision across different payment contexts within one run would return wrong bank data silently.
6. **Swap bug in timeout property key names** (`Configuration.java`, lines 65–66) could result in the wrong timeout values being applied, making connection tuning unreliable for production operations.
