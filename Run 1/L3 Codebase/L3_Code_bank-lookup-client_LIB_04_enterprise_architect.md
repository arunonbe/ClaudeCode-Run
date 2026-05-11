# bank-lookup-client_LIB — Enterprise Architect View

## Platform Generation (Gen-1/Gen-2/Gen-3)

**Generation: Gen-1 / Legacy Core2**

Evidence for this classification:
- Package root `com.ecount.process` and parent POM `com.ecount.service:service-parent:5` place it firmly in the historical `ecount` platform namespace predating the Onbe brand.
- SCM URL (`ecsvn.office.ecount.com/svn/ecount/services/Core2/bank-lookup-client/trunk`) confirms this is a Core2-generation artifact, consistent with Gen-1 or early Gen-2 era tooling.
- Dependencies on Java 6 target, Apache Commons HttpClient 3.x, SLF4J 1.1.0-RC1 (pre-release from circa 2006), FlatPack 3.1.1, and JDOM 1.0 are all consistent with mid-2000s to early-2010s development.
- Architecture is a standalone, batch-executed, file-processing fat JAR with no REST/HTTP API surface — characteristic of Gen-1 batch infrastructure.
- No Spring Framework, no dependency injection, no 12-factor app patterns.
- The Director/StrongBox service discovery pattern is an internal ecount/Core2 integration mechanism not present in Gen-3 designs.

## Business Domain

**ACH/NACHA Payments — Outbound ACH File Enrichment**

This component sits within the ACH outbound payment execution domain. It performs a pre-transmission enrichment step: taking raw payment records and resolving the banking details required to construct a valid NACHA ACH file. It is a supporting process in the disbursements/payouts pipeline, likely invoked before an ACH file is transmitted to a bank or ODFI (Originating Depository Financial Institution).

## Role in Platform

- **Role**: Batch file processor / data enrichment utility operating as a downstream step in ACH outbound file production.
- **Position in value chain**: Between internal payment record generation and NACHA file transmission. It converts a proprietary flat-file format to an enriched, bank-detail-populated output.
- **Deployment unit**: Standalone fat JAR invoked by an external scheduler. Not a service; does not expose any API.
- **Consumer pattern**: The output file is a flat file consumed by whatever downstream system transmits ACH files (a bank gateway, SFTP process, or payment rail adapter).
- **Upstream dependency**: Requires the ecount Director service (for StrongBox URI discovery) and the StrongBox repository service (for bank data retrieval) — both internal Core2 platform services.

## Dependencies

### Compile-Time (pom.xml)

| Artifact | Version | Type | Status |
|---|---|---|---|
| `com.ecount.service.Core2.director:director-client` | 1.0.11 | Internal JAR | Core2 legacy; provides `IDirectorClient`, `DirectorClientFactory` |
| `jdom:jdom` | 1.0 | OSS JAR | Superseded; EOL |
| `jexcelapi:jxl` | 2.4.2 | OSS JAR | Declared but no usage found in source |
| `org.slf4j:slf4j-api` | 1.1.0-RC1 | OSS JAR | Ancient pre-release |
| `org.slf4j:slf4j-simple` | 1.1.0-RC1 | OSS JAR | Ancient pre-release |
| `net.sf.flatpack:flatpack` | 3.1.1 | OSS JAR | Legacy flat file parser |
| `com.ecount.service:service-parent` | 5 | Internal POM | Core2 parent; provides commons-logging, commons-httpclient transitively |

### Runtime / Infrastructure

| Dependency | Description |
|---|---|
| Director service | Internal service discovery — resolves StrongBox URI |
| StrongBox repository service | Internal bank data repository — XML-RPC over HTTP |
| Local filesystem | Input ACH file, output NACHA file, properties files |

### Indirect (via `director-client` transitive)

- `com.ecount.xmlrpc.*` — internal XML-RPC serialisation utilities (`XmlRPCFromObjectMapper`, `XmlRPCToObjectMapper`)
- Apache Commons HttpClient 3.x (implied by `StrongBoxClient.java` imports)
- `com.ecount.Core2.director.client.*` — IDirectorClient interface, DirectorClientFactory

## Integration Patterns

| Pattern | Implementation |
|---|---|
| **File-based batch integration** | Input and output are local filesystem flat files. No message bus or API. |
| **Service discovery via Director** | `AbstractProcessor.createStrongBoxClient()` calls `IDirectorClient.getSerivceLocationURI()` to dynamically resolve the StrongBox endpoint at runtime. |
| **XML-RPC over HTTP** | `StrongBoxClient` communicates with StrongBox via HTTP POST with `Content-Type: application/x-mapxml`. Custom headers: `RPC-Interface`, `RPC-Method`, `RPC-Agent`, `RPC-TxID`, `RPC-Context`. |
| **Thread pool fan-out** | Work is distributed across a configurable `ThreadPoolExecutor` with one of three queue strategies (bounded, unbounded, synchronous). |
| **In-memory caching** | `ConcurrentHashMap` in `AbstractProcessorHelper` caches StrongBox responses within a single run to reduce network calls. |
| **Retry with sleep** | Failed records are re-queued up to `numRetries` times with a configurable sleep interval. |

## Strategic Status

**Status: Legacy — End-of-Life Candidate**

- Java 6 target, Core2 namespace, SVN origin, and SNAPSHOT version all indicate this is a legacy, unmaintained component.
- No Spring, no cloud-native patterns, no container support.
- Depends on Director and StrongBox — internal services that may themselves be decommissioned in Gen-3 migration.
- The only active maintenance signal is a weekly CodeQL scan added to the GitHub repository; no active development commits are visible from the repository state.
- No unit tests exist; test folder contains only a manual driver class.
- The `jxl` (jexcelapi) dependency is declared but unused, suggesting the codebase was partially cleaned up at some point.
- Architectural approach (file-based batch, command-line invocation, no API surface) is incompatible with Gen-3 microservices / event-driven architecture goals.

## Migration Blockers

The following are concrete obstacles to replacing or retiring this component in a Gen-3 migration:

1. **Hard dependency on Director + StrongBox**: The bank lookup mechanism depends on two proprietary internal Core2 services (`IDirectorClient`, StrongBox XML-RPC). A Gen-3 replacement must first have an equivalent bank data lookup capability (API, vault, or database) in the target architecture.

2. **Input file format undocumented**: Column semantics for COLUMN_0–COLUMN_9 and COLUMN_11–COLUMN_15 are not documented in the code or XML mapping. Migration requires reverse-engineering the column business meaning from the upstream system that generates the input file.

3. **Output format undocumented**: The enriched output format (colon-delimited bank data at column 10) is not independently documented. Downstream consumers of the NACHA output file must be identified before the processor can be replaced.

4. **No automated test coverage**: Zero JUnit tests. Migration cannot be validated through regression testing without writing tests from scratch, which requires understanding the full input/output contract.

5. **SNAPSHOT version**: Exact binary in production is unknown — the SNAPSHOT label means any build could be "the" production version. Version lineage must be established before decommissioning.

6. **Sensitive data handling requires remediation before migration**: A replacement would need to implement proper bank account data protection (encryption at rest, TLS enforcement, audit logging) to be compliant — requirements that cannot be carried over from the current implementation.

7. **External scheduler coupling**: The processor is invoked by an external scheduler whose identity and schedule are not in this repository. The migration must co-ordinate with the scheduling layer.
