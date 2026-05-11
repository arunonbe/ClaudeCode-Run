# citi-direct-file-process_LIB — Business Analyst View

## Business Purpose

This library generates a fixed-length flat-file extract destined for Citi Direct (Citibank's treasury/payment portal) as part of Onbe's B2C card disbursement workflow. Its sole runtime function is to query an internal database for accounts pending a CitiDirect submission, format each account record according to a configurable XML template, and write the result to a timestamped output file. The library acts as an ETL (Extract-Transform-Load) component sitting between Onbe's core cardholder database and Citibank's file-acceptance channel.

The artifact name in `pom.xml` is `CitiDirectFile`, group `com.ecount.one.etl`, version `1.0.1`. The declared main class is `com.ecount.one.etl.reports.CitiDirectFileProcess`.

## Business Capabilities

1. **Account extraction** — executes the stored procedure `core_citi_direct_process_extract` (referenced in `CitiDirectAccountFile.java` line 23) against the `EcountCore` database to retrieve new accounts awaiting CitiDirect file submission.
2. **Fixed-length file generation** — formats each account into a 140-character-wide record (constant `VALID_CARD_LENGTH = 140` at `CitiDirectAccountFile.java` line 51, though the length validation is commented out) using `FixedLengthPrintWriter`.
3. **Template-driven field layout** — reads field definitions from `newAccountFileTemplate.xml` (validated against `newAccountFileTemplate.xsd`) so that field order, width, alignment, and value sourcing can be changed without code modification.
4. **Multi-country support** — handles US, Canada (CA/CAN), and United Kingdom (UK/GBR/GB) country-code normalisation (`CitiDirectAccountFile.java` lines 60-74).
5. **French-character transliteration** — `FDRStringValidator.getValidateString()` converts accented French characters to their ASCII equivalents, important for Canadian cardholder names.
6. **Agent/brand scoping** — an `agent` property (default `B2C`, configurable via `etlContext.properties`) is passed to the director service to obtain the correct database connection for the requesting brand.
7. **Timestamped output file naming** — the main method appends `_yyyyMMddkkmmss` to the provided filename before the extension (`CitiDirectFileProcess.java` lines 143-147).

## Business Entities

| Entity | Source | Fields observed |
|---|---|---|
| Account / Card record | DB result set via `core_citi_direct_process_extract` | `preformatCode`, `transactionAmount`, `country`, `file_date` |
| File template card | `newAccountFileTemplate.xml` | `id`, `condition`, `seq`, `name`, `length`, `value_type`, `value`, `align` |
| Context / configuration | `etlContext.properties` + `Context.java` | `CitiDirectFilePath`, `agent`, `director.address`, `database` |

The mapper `CitiDirectFileMapper` (`citidirectdao/CitiDirectFileMapper.java`) defines the canonical DB column-to-key mappings:
- `KEY_PREFORMAT_CODE = "preformatCode"`
- `KEY_TRANSACTION_AMOUNT = "transactionAmount"`
- `KEY_HOME_COUNTRY = "country"`
- `KEY_FILE_DATE = "file_date"`

## Business Rules & Validations

1. **Output file path must not be null** — `CitiDirectFileProcess.getUniqFilePath()` (lines 95-99) calls `System.exit(-1)` if `CitiDirectFilePath` is null.
2. **Output filename must be supplied at runtime** — `main()` enforces `args.length >= 1` and `args[0].length() >= 1` (line 131); exits with code 1 otherwise.
3. **XML template must be valid** — `loadNewAccountXMLFile()` uses a validating `DocumentBuilder` with XSD schema validation (`CitiDirectAccountFile.java` lines 118-124). A parse error is treated as fatal.
4. **`enabled` flag on template** — the `<NewAccountFile enabled="true">` attribute gates processing; if the attribute is absent or false, `CitiDirectAccountFile.isEnabled()` returns `false` (lines 152-176).
5. **Country-code normalisation** — USA/US → "US"; CA/CAN → "CA"; UK/GB/GBR preserved; determines `isFormatted` (lines 273-287).
6. **Field alignment rules** — align=0 → left-justify with `#` filler; align=1 → left-justify with blanks; align=2 → right-justify with zeroes (`CitiDirectAccountFile.java` lines 353-356).
7. **Date format for file** — `CITI_DIRECT_DATE_FORMAT = "yyyyMMdd"` (line 29), applied to both `file_date` from DB and `date_now` logic values.
8. **Card must have at least one field node** — enforced at runtime with error message in `writeNewAccountCard()` (line 382).
9. **Sequential field ordering** — fields within a card are processed in `seq` attribute order (lines 308-366 of `CitiDirectAccountFile.java`).

## Business Flows

```
Runtime invocation (CLI):
  args[0] = base output file path
      │
      ▼
CitiDirectFileProcess.main()
  │  Appends timestamp to filename
  │  Sets log.file system property
      │
      ▼
CitiDirectFileProcess.writeECSProcessNasnewExtractFile()
  │  Loads Spring context (etlContext.xml)
  │  Resolves CitiDirectFilePath and agent from Context bean
  │  Obtains JDBC DataSource via Director service
  │  Calls loadNewAccountXMLFile() → parses & validates newAccountFileTemplate.xml
  │  Initialises FixedLengthPrintWriter → opens output file
      │
      ▼
CitiDirectAccountFile.processNewAccounts(jdbcTemplate)
  │  Executes: exec core_citi_direct_process_extract
  │  Spring JdbcTemplate calls CitiDirectDBListProcessor.processRow() per row
      │
      ▼
CitiDirectDBListProcessor.processRow()
  │  CitiDirectFileMapper.processRowIntoRecord() → fills Hashtable
  │  CitiDirectAccountFile.appendNewBatchAccountRecordToFile() → writes one line
      │
      ▼
Output: fixed-length flat file (one line per account)
```

## Compliance & Regulatory Concerns

1. **Payment data in flat file** — the output record contains `transactionAmount` and `preformatCode`. These are payment instruction fields transmitted to Citibank. Any interception or corruption of this file would constitute a payment integrity failure with Reg E / NACHA implications.
2. **Cardholder country data** — `country` field is written to the output file and used to differentiate US vs. international cardholders; GDPR/PIPEDA/Quebec Law 25 may apply to Canadian cardholders' data in transit.
3. **File-based data transfer to Citibank** — the file is written to a local filesystem path (`d:/c-base/runtime/citidirectfile/` per `etlContext.properties`). There is no evidence of encryption-at-rest or secure transfer (SFTP/FTPS) in this library; that would need to be confirmed as a downstream operational step.
4. **No PAN, CVV, or PIN fields** — the current field set (`preformatCode`, `transactionAmount`, `country`, `file_date`) does not include card PANs or SAD. However, `preformatCode` may carry issuer-specific account identifiers; clarification is needed from compliance.
5. **PCI DSS scope** — if `preformatCode` is a card token or account number derivative, the file and the system writing it fall within the Cardholder Data Environment (CDE) and must comply with PCI DSS v4.0.1 requirement 3 (data protection) and requirement 12.5 (PCI scope documentation).
6. **Audit trail** — logging is to a 100 KB rolling file (`citidirect.log`). This is insufficient for a regulated payment file generation process; log retention must meet internal audit and FFIEC requirements.

## Business Risks

1. **Hardcoded dev/test configuration** — `etlContext.properties` contains `agent=B2CTEST` and `director.address=http://ecappdev/service/dispatch.asp`. If a production deployment picks up this file, it will connect to the wrong agent and a non-production Director endpoint.
2. **No record count reconciliation** — the process logs "Total number of new accounts: N" but does not write a trailer/control record to the file; Citibank file reconciliation cannot be performed automatically.
3. **Silent data truncation** — `FixedLengthPrintWriter` silently truncates any field value that exceeds the configured `length` (e.g., `leftJustifyWithBlanks` at lines 94-98). Over-length `transactionAmount` or `preformatCode` values would produce corrupt records without any error.
4. **Commented-out card-length validation** — the 140-character record-length check is commented out in `CitiDirectAccountFile.java` (lines 372-379), meaning malformed records with wrong lengths can be written silently.
5. **`System.exit()` calls throughout** — at least five `System.exit()` calls exist across the codebase. These prevent graceful error propagation and make the library impossible to embed in a larger orchestration framework.
6. **Duplicate seq="9" in template** — `newAccountFileTemplate.xml` has two fields with `seq="9"` (lines 13-14). The current sequential-search logic in `writeNewAccountCard()` will only process the first one encountered; the second is silently dropped.
