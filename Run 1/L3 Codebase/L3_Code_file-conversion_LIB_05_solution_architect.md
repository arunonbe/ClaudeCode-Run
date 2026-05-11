# Solution Architect View — file-conversion_LIB

## Complete Class/Method Inventory

### `BatchFile.java` — Fixed-Width Batch File Writer

**Constructor `BatchFile(String fileName)`**: Opens a `PrintWriter` to the specified file path. Throws `IOException`.  
**Constructor `BatchFile(String filename, String programId)`**: Empty constructor body — does nothing. Likely placeholder (lines 48–52).  
**`close()`**: Closes the underlying `PrintWriter`.  
**`print(String str)`**: Writes string without newline.  
**`println(String str)`**: Writes string with newline.  
**Static `makeField(String value, int maxLen)`**: Right-pads or truncates `value` to exactly `maxLen` characters using `blankLine` padding string.  
**Static `createFileHeader(String programID, String passthrough, String createDate, String outputFileName)`**: Creates a 400-char file header record (record type `01`). Partner ID logic: if program ID starts with `"0401"`, partner ID is `"00"` + programID[4:6]; otherwise programID[0:5].  
**`writeFileHeader(...)`**: Calls `createFileHeader()` and writes to file.  
**`writeFileFooter()`**: Writes record type `02` padded to 400 chars.  
**`writeBatchHeader(String programID, String batchDescription, String passthrough, String promoID)`**: Writes record type `03` batch header.  
**`writeBatchFooter()`**: Writes record type `04`.  
**`writeRequestHeader(String ecountId, String partnerUserID, String passthrough)`**: Writes record type `09`.  
**`writeAddFundsAction(String passthru, int amount, boolean taxable, int notificationIndicator)`**: Delegates to overloaded version with empty `partnerPaymentId`.  
**`writeAddFundsAction(String passthru, int amount, boolean taxable, int notificationIndicator, String partnerPaymentId)`**: Writes record type `05` (add funds). Amount is integer (cents). Taxable as `"1"`/`"0"`.  
**`writePPDRecord(String name, String value)`**: Writes record type `51` (PPD addendum for add funds).  
**`writeSpinPaymentAction(String passthru, boolean directClaim, boolean taxable, int notificationIndicator, String partnerPaymentId)`**: Writes record type `18` (spin payment).  
**`writeSpinPPDRecord(String name, String value)`**: Writes record type `52`.  
**`writeStopPaymentAction(String passthru, String partnerPaymentId, String ecountPaymentId, int notificationIndicator)`**: Writes record type `20`.  
**`writeStopPaymentPPDRecord(String name, String value)`**: Writes record type `53`.  
**`writeCreateAccountAction(String passThrough, String firstName, String middleName, String lastName, String suffix, String email, String address1, String address2, String city, String state, String zip, String country, String homePhone, String businessPhone, String mobilePhone, int notificationIndicator)`**: Writes record type `07` with full cardholder PII.  
**`writeCreateAccountAddenda(String labelId, String labelValue)`**: Writes record type `72`.  
**`writeCreateCertificateAction(String templateId, int amount, String startDate, String recipientInformalName, String senderInformalName, String recipientFirstName, String recipientLastName, String passthrough)`**: Writes record type `12`.  
**`writeCertificateMemoAddenda(String memo, String passthrough)`**: Writes record type `13`.  
**`writeEmailNotificationAction(String recipientEmail, String senderEmail, String bounceEmail, String passthrough)`**: Writes record type `14`.

---

### `FixedWidthRecordParser.java` — Fixed-Width Line Parser

**Constructor `FixedWidthRecordParser(String template)`**: Takes a template string like `"A2A16A50A32A300"`. `A` = trim whitespace; `a` = preserve whitespace. Numbers = field widths.  
**`parseLine(String record)`**: Parses a 400-char record into a `String[]` using the template. Returns fields in order. Known bug: does not trim the last token when whitespace preservation is not needed (comment at line 25).  
**Note**: Uses raw `Vector` (pre-generics). Returns `String[]`.

---

### `RequestFileParser.java` — Request File Record Parsers + Field Index Constants

Static integer constants define field positions for each record type (FIELD_HEADER_*, FIELD_BATCH_*, FIELD_REQUEST_*, FIELD_ADD_FUNDS_*, etc.).  
**`parseFileHeader(String line)`**: Parses using `FILE_HEADER_TEMPLATE`.  
**`parseBatchHeader(String line)`**: Parses using `BATCH_HEADER_TEMPLATE` (trims whitespace).  
**`parseBatchHeader(String line, boolean preserveWhiteSpace)`**: Overload — if `preserveWhiteSpace=true`, uses lowercase template (preserves spaces).  
**`parseRequestRecord(String line)`**: Parses using `REQUEST_RECORD_TEMPLATE`.  
**`parseAddFundsAction(String line)`**: Parses using `ADD_FUNDS_LINE_TEMPLATE`.  
**`parsePPD(String line)`**: Parses using `PPD_LINE_TEMPLATE`.

---

### `ReplyFileParser.java` — Reply File Record Parsers + Field Index Constants

Static integer constants for all reply record types, including:
- `FIELD_CREATE_ACCOUNT_CARD_NUMBER = 14`
- `FIELD_CREATE_ACCOUNT_EXP_MONTH = 15`
- `FIELD_CREATE_ACCOUNT_EXP_YEAR = 16`
- `FIELD_CREATE_ACCOUNT_CV_CODE = 18` — **CVV field — MUST NOT be stored**

**`parseFileHeaderLine(String)`**, **`parseBatchLine(String)`**, **`parseRequestLine(String)`**, **`parseCreateAccountAction(String)`**, **`parseAddFundsAction(String)`**, **`parseStopPaymentAction(String)`**, **`parsePPD(String)`**, **`parseCreateCertificate(String)`**, **`parseEmailNotitification(String)`** [note: typo in method name `parseEmailNotitification` — double `t`]: Each delegates to the corresponding `FixedWidthRecordParser`.

---

### `FileValidator.java` — Abstract File Validator (Template Method Pattern)

**Abstract `validateLine(String line)`**: Subclasses implement this to validate each line.  
**`validate()`**: Template method — calls `preProcess()`, reads all lines, calls `validateLine()` for each, calls `postProcess()`.  
**`preProcess()` / `postProcess()`**: Hooks for subclasses (no-op defaults).  
**`assertFieldNotEmpty(String fieldName, String fieldValue)`**: Validates field is non-null/non-empty.  
**`assertFieldIsInteger(String fieldName, String fieldValue)`**: Validates field is numeric.  
**`failRecord(String error)`**: Increments error count, prints error.  
**`fail(String error)`**: Non-recoverable failure.  
**`stopProcessing()`**: Signals early termination of validation loop.

### `FixedWidthRecordFileValidator.java` — Concrete validator for fixed-width files (extends FileValidator)

### `BatchFileConstants.java` — Constants
- `DEFAULT_EMAIL_ADDRESS = "none@ecount.com"` — Default email placeholder.
- `DEFAULT_PHONE_NUMBER = "555-555-5555"` — Default phone placeholder.

### `EcountPromotion.java` — Promotion model
Fields: `name`, `memo`, `amount` (int, cents), `promotion` (ID string), `taxable` (boolean), `sendEmail` (int notification code).

### `TaxProfile.java` — Tax calculation
Fields: `federalRate` (float, %), `ficaRate` (float, %), `stateRate` (float, %), `stateBasedOffFederal` (boolean).  
**`calculateTax(int)`**: Total tax = federal + state + FICA.  
**`calculateFederalTax(int)`**: `amount × federalRate × 0.01` (rounded).  
**`calculateStateTax(int)`**: Direct rate or rate-off-federal.  
**`calculateFica(int)`**: `amount × ficaRate × 0.01` (rounded).

### `ZipUtils.java` — ZIP file utilities
**`getZipContentsByExtension(ZipFile)`**: Returns `Hashtable<extension, ZipEntry>`.  
**`getZipContents(ZipFile)`**: Returns `Hashtable<filename, ZipEntry>`.

### `DelimitedRecordParser.java` — CSV/delimited parser (not fully read)
### `PromotionXref.java` — Promotion cross-reference (not fully read)
### `StringUtils.java` — String utilities (not fully read)
### `ValidationException.java` — Custom validation exception
### `BatchFileRecordFactory.java` — Factory for batch record creation (not fully read)

## Security Vulnerabilities

### VULN-1: CVV/CV Code Field in ReplyFileParser (CRITICAL — P0)
**File**: `ReplyFileParser.java` line 18  
**Detail**: `FIELD_CREATE_ACCOUNT_CV_CODE = 18` — any code using this constant to extract and store the CV code violates PCI DSS Requirement 3.2.1 (CVV must never be stored).  
**Action**: Audit all consumers. Document and enforce that this field must be immediately discarded after parsing.  
**Priority**: P0.

### VULN-2: Full PII in Batch File (HIGH)
**File**: `BatchFile.java` `writeCreateAccountAction()` (lines 320–363)  
**Detail**: Full cardholder demographics written to file. The file itself is a PII artifact requiring encryption at rest and in transit.  
**Priority**: P1 — Confirm all file handling code uses encrypted channels and encrypted storage.

### VULN-3: Typo in Method Name — API Quality (LOW)
**File**: `ReplyFileParser.java` — method `parseEmailNotitification` (double `t`)  
**Detail**: Minor API quality issue — consuming code must use the misspelled name.  
**Priority**: P3.

### VULN-4: Raw Types / Pre-Generics Code (LOW)
**File**: `FixedWidthRecordParser.java` — uses `Vector` (raw), `Enumeration` (raw)  
**Detail**: Unchecked cast warnings, no compile-time type safety.  
**Priority**: P3 — Modernize to Java generics.

## Remediation Priority Summary

| Priority | Item |
|----------|------|
| P0 | Audit all consumers of `FIELD_CREATE_ACCOUNT_CV_CODE` — ensure CVV is never stored |
| P1 | Confirm all batch file paths use TLS and encrypted storage |
| P1 | Release stable version (remove `-SNAPSHOT`) |
| P2 | Add unit tests for all parser/writer methods |
| P3 | Fix `parseEmailNotitification` typo |
| P3 | Modernize code: generics, try-with-resources |
| P3 | Upgrade Java version target |
