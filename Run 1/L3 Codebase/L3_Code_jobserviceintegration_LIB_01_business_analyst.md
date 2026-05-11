# jobserviceintegration_LIB — Business Analyst View

## Business Purpose

`jobserviceintegration_LIB` is a Gen-1 multi-module Java library that provides **client-specific file conversion and import integration adapters** for the Onbe/eCount prepaid-card platform. Each module converts an automotive or telecom client's proprietary data file format into the ecount standard batch request file format (fixed-width flat-file protocol), which is then processed by the job service to enrol recipients and load funds onto prepaid cards.

Named `J2EE Job Service Integration` in its Maven POM, this library represents the inbound integration layer for corporate clients disbursing prepaid rewards to their customers (e.g., automotive rebates, telecom incentive programmes).

## Capabilities

- **File format conversion**: Reads client-supplied fixed-width or delimited flat files and produces ecount-standard batch files (record types 01–72).
- **Validation**: Validates incoming files against configurable field templates before conversion.
- **Zip archive handling**: Processes multi-file ZIP archives (e.g., Chrysler contact header + letter form detail + fulfillment files).
- **Promotion cross-referencing**: Maps client stock codes or package IDs to ecount promotion IDs via a configurable properties file.
- **Reply file parsing**: Parses ecount reply files after job processing to extract outcome data.
- **Record generation**: Supports all major ecount batch record types — file header/footer, batch header/footer, create-account, add-funds, spin payment, stop payment, certificate creation, email notification, and PPD addenda records.

## Client Modules

| Module | Client / Programme |
|---|---|
| `Common` | Shared utilities: `BatchFile`, `BatchFileRecordFactory`, `FixedWidthRecordParser`, `DelimitedRecordParser`, `ReplyFileParser`, `FileValidator`, `ZipUtils` |
| `chrysler` | Chrysler (automotive rebate) |
| `jwt` | JWT (not identified further in source) |
| `LegacyForLife` | LegacyForLife programme |
| `nextel` | Nextel (telecom) |
| `qwest` | Qwest (telecom) |
| `subaru` | Subaru (automotive) |
| `toyota` | Toyota (automotive) |
| `BulkCardGen` (non-Maven) | Bulk card generation scripts/JARs (stored binaries) |

## Entities

| Entity | Description |
|---|---|
| `BatchFile` | Writes ecount flat-file batch records (record types 01–72) to a `PrintWriter` output stream |
| `BatchFileConstants` | Record-type constants (01=file header, 02=footer, 03=batch header, 04=batch footer, 05=add-funds, 07=create-account, 09=request-header, 12=certificate, 13=memo, 14=email, 18=spin-payment, 20=stop-payment, 51–53=PPD records, 72=create-account-addenda) |
| `EcountPromotion` | Maps stock code to promotion ID, amount, taxable flag, send-email flag, and memo |
| `PromotionXref` | In-memory lookup table loaded from a config file |
| `FixedWidthRecordParser` | Parses a fixed-width line using a field-template array |
| `DelimitedRecordParser` | Parses delimited (CSV-style) lines |
| `ReplyFileParser` | Parses ecount reply files |
| `FileValidator` / `FixedWidthRecordFileValidator` | Validates file structure against expected field templates |
| `TaxProfile` | Tax calculation data |
| `ValidationException` | Checked exception for file validation failures |

## Business Rules

1. The batch file record type prefix determines the action (e.g., "05" = add funds, "07" = create account, "12" = create certificate).
2. All field widths are fixed (400 characters per line); fields are padded with spaces to their declared widths.
3. Partner user IDs must be non-null and non-empty; a `ValidationException` is thrown if the prospect/contact ID is absent.
4. Promotion lookup (stock code → ecount promo ID) must succeed; unmatched stock codes will cause a conversion abort.
5. A program ID starting with "0501" uses partner ID "0501"; all others use "00" + characters 4–6 of the program ID.
6. Phone numbers equal to "0000000000" are replaced with "555-555-5555" as a sanitization step.

## Flows

1. **Import flow**: Client ZIP file → `ChryslerFileConverter.processFile()` → reads contact header, fulfillment, and letter-form-detail entries → cross-references promotions → writes `BatchFile` output → ecount standard batch file.
2. **Validation flow**: Input file → `FileValidator.validate()` → field-level checks → `ValidationException` on failure.
3. **Reply-parse flow**: ecount reply file → `ReplyFileParser` → extract outcomes per request.

## Compliance Relevance

- Processes PII: recipient first name, last name, middle name, email address, home/business phone, full mailing address, and partial payment amounts.
- Contains no PAN or card data, but does handle financial disbursement amounts and recipient identity data — relevant to GLBA, CCPA, and GDPR depending on cardholder jurisdiction.
- The presence of `BulkCardGen` JARs in the repository (binary artefacts committed to source control) represents a dependency management risk.

## Risks

- Binary JAR files committed to the repository (`alg/common/`, `BulkCardGen/JobImportFile/BulkCardGen/`) — these are unauditable supply-chain artefacts.
- VBScript (`.vbs`) and Windows Script Host (`.wsf`) files are present alongside Java code, indicating the original integration relied on Windows-based batch automation.
- Perl scripts (`create_bc_batch.pl`, `dump_reply.pl`, `padspaces.pl`) suggest multi-language processing pipelines.
- No unit tests found in the scanned Java source.
- Compiled with Java 1.6 target — extremely old, no longer supported.
