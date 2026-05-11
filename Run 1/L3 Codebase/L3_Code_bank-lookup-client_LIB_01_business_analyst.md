# bank-lookup-client_LIB — Business Analyst View

## Business Purpose

`bank-lookup-client` is a Java library/utility that performs ACH (Automated Clearing House) outbound file processing. Its specific job is to enrich an input flat file containing payment records with bank information (routing number, account number, account type, bank name, country) by looking up that information from an internal credential/secret store called **StrongBox**. The enriched file is written as a NACHA-format output file. The artifact is named `ACH Outbound Processor` (pom.xml line 15) and belongs to the `Core2` service layer within the `ecount` platform.

## Business Capabilities

- **ACH file enrichment**: Reads a delimited flat file of payment transaction records, locates bank details in StrongBox using a reference number found in column 10 (zero-based), and rewrites the file with that banking data injected at that column position.
- **Multi-threaded throughput**: Splits the input file into configurable chunks and distributes work across a Java `ThreadPoolExecutor`, supporting bounded queues, unbounded queues, and synchronous handoff (six processing combinations).
- **Retry on partial failure**: Records that cannot be enriched (e.g., StrongBox unavailable, reference not found) are collected and resubmitted up to a configurable number of retries with a configurable sleep interval between attempts.
- **In-memory bank data caching**: Retrieved bank records are cached in a `ConcurrentHashMap` (keyed on reference number) to avoid redundant network calls across threads within a single run (`AbstractProcessorHelper`, lines 45–46).
- **Two parsing strategies**: The library provides both a raw Java NIO/BufferedReader parser and a FlatPack (flatpack 3.1.1) XML-mapped parser, allowing the caller to choose based on file characteristics.

## Business Entities

| Entity | Source | Fields |
|---|---|---|
| ACH Input Record | Flat file, 16 positional columns (COLUMN_0–COLUMN_15) | Column 10 = reference number (bank lookup key) |
| Bank Information | StrongBox repository service | `routing_number`, `account_number`, `account_type`, `name` (bank name), `country` |
| StrongBox Reference | Input file column 10 | String key used to retrieve bank details |
| Configuration | `.properties` file (external or bundled) | All processor tuning parameters |
| NACHA Output Record | Written flat file | Same 16 columns with column 10 replaced by `routing:account:type:name:country` |

## Business Rules & Validations

1. **Exactly three command-line arguments are required**: properties file path, input file path, output file path (`AchOutboundProcessor.java`, lines 146–164). Any other count throws `ProcessorException`.
2. **Properties file must define all required keys**: `Processor.factory.type`, `Processor.processor.type`, `Processor.processor.queue.type` are mandatory. Numeric parameters must parse as integers/longs (`Configuration.java`, lines 192–510).
3. **Column 10 is always the reference number**: Hard-coded at `REFERENCE_NUMBER_COLUMN_ID = 10` in both `ProcessorHelper` (line 36) and `FlatPackProcessorHelper` (line 33). Records where no bank data is found are returned as unprocessed and retried.
4. **Queue type governs threading behaviour**: `BOUNDED` (ArrayBlockingQueue), `UNBOUNDED` (LinkedBlockingQueue), `SYNCHRONOUS` (SynchronousQueue) are the accepted values. Invalid combinations result in a null processor and a thrown `ProcessorException`.
5. **Retry limit enforced**: If `Processor.processor.number.retries` is set, unprocessed records are re-attempted up to that count; if still unprocessed, the run fails with a `FATAL ERROR` listing the unprocessed records.
6. **Output file is always created fresh**: `FileOutputStream(outputFileName)` without append flag — any prior output file is overwritten.
7. **FIFO policy accepted as "yes" or "true"** (case-insensitive) for queue ordering (`Configuration.java`, lines 274–279).

## Business Flows

```
[Operator/Scheduler]
      |
      v
AchOutboundProcessor.main(args[3])
      |-- validateArguments()         -- enforce 3-arg contract
      |-- Configuration.getInstance() -- load & validate .properties
      |-- ProcessorFactory            -- select DEFAULT or BUFFERED factory
      |-- ProcessorInterface          -- select JAVA or FLATPACK processor
            |                            with BOUNDED/UNBOUNDED/SYNCHRONOUS queue
            |
            v
      AbstractProcessor.createStrongBoxClient()
            |-- IDirectorClient.getSerivceLocationURI()  -- resolve StrongBox URL
            |-- StrongBoxClientFactory.getClient()       -- build HTTP client
            |
            v
      processor.process(inputFile, outputFile, delimiter, qualifier, threadLoad)
            |
            |-- Parse input file (FlatPack XML-mapped or Java NIO/BufferedReader)
            |-- Partition rows into chunks of size = poolThreadLoad
            |-- Submit each chunk as Callable to ThreadPoolExecutor
            |      |
            |      v
            |   ProcessorHelper / FlatPackProcessorHelper.call()
            |      |-- For each row: extract column 10 reference
            |      |-- AbstractProcessorHelper.retrieveBankInformation(reference)
            |      |      |-- Check ConcurrentHashMap cache
            |      |      |-- If miss: StrongBoxClient.readData(reference) --> XML-RPC POST
            |      |      |-- Parse routing/account/type/name/country
            |      |      |-- Cache result
            |      |-- Build enriched record string
            |      |-- Write to shared FileChannel (synchronized)
            |      |-- Return list of unprocessed (failed) records
            |
            |-- Wait for all Future<> to complete (busy-sleep loop)
            |-- Retry unprocessed records (up to numRetries)
            |-- Shutdown thread pool
            v
      [Enriched NACHA output file written to disk]
```

## Compliance & Regulatory Concerns

- **NACHA compliance**: The library's stated output is a NACHA standard ACH file (`ProcessorInterface.java`, lines 7–13). NACHA rules govern ACH file formats and require accurate routing/account data; incorrect enrichment would create erroneous ACH transactions.
- **Bank account data sensitivity**: The StrongBox responses contain `routing_number` and `account_number` — both are sensitive financial data. There is no masking, encryption, or access control applied to either the in-memory cache or the output file written to disk. The output file contains plaintext banking details.
- **PCI DSS relevance**: If any ACH reference points to card-linked accounts, the fields flowing through this processor could be in scope for PCI DSS handling requirements. No evidence of PCI controls exists in the code.
- **Reg E / NACHA**: Errors in routing or account number enrichment could result in misdirected ACH payments, triggering Reg E dispute obligations.
- **Audit trail**: No structured audit log is produced. The log file (`ach_processor.log`) captures warnings and errors but does not record which reference numbers were looked up or which records were written, preventing post-hoc reconciliation.

## Business Risks

1. **Plaintext sensitive output**: Routing and account numbers are written unencrypted to the output file on local disk with no access controls imposed by this code.
2. **In-memory caching without expiry**: The `ConcurrentHashMap` cache in `AbstractProcessorHelper` grows unboundedly and persists for the JVM lifetime. Stale bank data could be served within a long run.
3. **No input validation on bank data**: Retrieved `routing_number` and `account_number` are written directly to output without format validation (e.g., ABA 9-digit routing number check). Corrupt StrongBox data propagates silently.
4. **Silent partial failure risk**: If `numRetries` is null (not configured), the retry loop exits after one pass — records can be quietly dropped from the output file.
5. **No reconciliation count**: The processor logs elapsed time but does not log input record count vs. output record count, making it impossible to detect data loss without external comparison.
6. **Column index hard-coded**: `REFERENCE_NUMBER_COLUMN_ID = 10` is hard-coded in two helper classes. Any change to the input file schema would require a code change and redeployment.
