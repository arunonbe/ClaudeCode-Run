# Data Architect View — file-conversion_LIB

## Library Role in Data Architecture

`file-conversion_LIB` is a **data format translation library** that sits at the boundary between Onbe's internal data systems and the FDR card processor's batch file exchange format. It handles serialization (writing) and deserialization (parsing) of the FDR fixed-width batch file format.

## File Format Specification

### Fixed-Width Record Format

All batch file records are exactly 400 characters wide. Each record begins with a 2-character record type code. The `blankLine` static constant in `BatchFile.java` (lines 31–35) creates a 400-character padding string used to ensure all records are padded to exactly 400 characters.

Record type codes define the structure of each line. Field boundaries are defined by the `FixedWidthRecordParser` templates:

**Request File Templates (`RequestFileParser.java` lines 45–50):**

| Template Name | Template String | Total Width |
|-------------|----------------|-------------|
| FILE_HEADER | `A2A4A50A32A8A304` | 400 |
| BATCH_HEADER | `A2A4A64A32A8A290` | 400 |
| REQUEST_RECORD | `A2A16A50A32A300` | 400 |
| ADD_FUNDS_LINE | `A2A32A10A1A10A345` | 400 |
| PPD_LINE | `A2A10A40A348` | 400 |
| STOP_PAYMENT | `A2A32A32A32A10A292` | 400 |

**Reply File Templates (`ReplyFileParser.java` lines 90–98):**

| Template Name | Template String | Fields |
|-------------|----------------|--------|
| FILE_HEADER | `A2A4A50A32A8A304` | RecordType, PartnerID, FileName, PassThrough, CreationDate, Pad |
| REQUEST_LINE | `A2A16A50A32A300` | RecordType, EcountID, PartnerUserID, PassThrough, Pad |
| BATCH_LINE | `A2A4A64A32A8A290` | RecordType, ProgramID, BatchDescription, PassThrough, PromotionID, Pad |
| CREATE_ACCOUNT | `A2A32A25A25A25A25A50A26A26A18A2A10A2A16A16A2A4A16A4A4A16A16` | RecordType, PassThrough, FirstName, MiddleName, LastName, Suffix, Email, Address1, Address2, City, State, ZIP, Country, Phone, **CardNumber, ExpMonth, ExpYear, CardType, CVCode**, StatusCode, BusinessPhone, MobilePhone, NotificationCode, AccessLevel |
| ADD_FUNDS | `A2A32A10A4A1A10A40A40A261` | RecordType, PassThrough, Amount, StatusCode, Taxable, Notification, PartnerPaymentID, EcountPaymentID, Pad |
| STOP_PAYMENT | `A2A32A40A40A10A10A4A262` | RecordType, PassThrough, PartnerPaymentID, EcountPaymentID, Notification, Amount, StatusCode, Pad |
| CREATE_CERT | `A2A8A10A8A50A50A25A25A32A50A4A136` | |
| EMAIL_NOTIF | `A2A50A50A50A32A4A212` | |

## Sensitive Data — CRITICAL PCI DSS FLAGS

### FLAG 1: CVV/CV Code in Reply File Parsing (CRITICAL)
**File**: `ReplyFileParser.java` line 18: `FIELD_CREATE_ACCOUNT_CV_CODE = 18`  
**Template**: CREATE_ACCOUNT reply line includes a CV Code field (4 characters in position: `...A4...` in `CREATE_ACCOUNT_LINE_TEMPLATE`).  
**PCI DSS Requirement 3.2.1**: CVV/CVC codes must never be stored after authorization, under any circumstances. The presence of this field constant and the template definition means that systems using this library to parse reply files may inadvertently extract and store CVV codes.  
**Action Required**: Confirm whether Fiserv actually returns CVV in reply files. If so, the parsing logic must explicitly discard this field immediately after parsing, with no persistence.

### FLAG 2: Card Number in Reply File (HIGH)
**File**: `ReplyFileParser.java` line 14: `FIELD_CREATE_ACCOUNT_CARD_NUMBER = 14`  
**Detail**: The reply file for account creation returns a `CardNumber` field. This may be a full PAN returned by FDR to confirm the issued card number. Any consumer of this library that stores this value is in PCI DSS scope for PAN storage requirements (Requirement 3.4 — render PAN unreadable at rest).  
**Action Required**: Confirm PAN masking in Fiserv contract. Ensure consuming code truncates/masks this field.

### FLAG 3: Card Expiration Date in Reply File (HIGH)
**File**: `ReplyFileParser.java` lines 15–16: `FIELD_CREATE_ACCOUNT_EXP_MONTH = 15`, `FIELD_CREATE_ACCOUNT_EXP_YEAR = 16`  
**Detail**: Expiration date combined with card number constitutes a significant portion of the PAN data set. Storage is restricted under PCI DSS Requirement 3.  

### FLAG 4: Full Cardholder PII in Create Account Request
**File**: `BatchFile.java` `writeCreateAccountAction()` method (lines 320–363)  
**Detail**: The method writes full cardholder demographics: firstName, middleName, lastName, suffix, email, address1, address2, city, state, zip, country, homePhone, businessPhone, mobilePhone to the batch file. These are GDPR/CCPA-relevant personal data elements in addition to being part of the cardholder data set.

## Data Objects

### `BatchFile.java`
Stateful file writer. Opens a `PrintWriter` to a named file. Each `write*()` method appends a fixed-width record. Must be `close()`d after use.

### `EcountPromotion.java`
Promotional parameters for a batch disbursement: `name`, `memo`, `amount` (cents), `promotion` (promotion ID), `taxable` (boolean), `sendEmail` (notification code).

### `TaxProfile.java`
Tax calculation model: `federalRate` (%), `ficaRate` (%), `stateRate` (%), `stateBasedOffFederal` (flag). Methods: `calculateTax(paymentAmount)`, `calculateFederalTax()`, `calculateStateTax()`, `calculateFica()`. All amounts in integer cents.

### `PromotionXref.java`
Cross-reference between promotion codes (inferred — not fully read but present in file list).

### `DelimitedRecordParser.java`
CSV/delimited record parser (alternative to fixed-width parsing for delimited input formats).

### `StringUtils.java`
String utility functions for file processing.

### `ValidationException.java`
Exception thrown by validator classes.

### `ZipUtils.java`
ZIP file utility: `getZipContentsByExtension(ZipFile)` — returns entries keyed by file extension; `getZipContents(ZipFile)` — returns all entries keyed by name. Used to handle zipped batch file deliveries.

## Field Index Constants (Important for Downstream Parsing)

The `RequestFileParser` and `ReplyFileParser` expose static integer constants for each field position in each record type. These are the API contract for downstream consumers — they reference `replyFields[FIELD_CREATE_ACCOUNT_CARD_NUMBER]` to extract specific fields after parsing.

## Versioning Note

Library version is `1.0.1-SNAPSHOT` (pom.xml line 4). The `-SNAPSHOT` suffix suggests this was never formally released; it has been in snapshot state throughout its life.
