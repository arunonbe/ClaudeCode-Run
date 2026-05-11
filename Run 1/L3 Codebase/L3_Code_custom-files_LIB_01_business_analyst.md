# custom-files_LIB — Business Analyst View

## Business Purpose
`custom-files_LIB` (artifact: `custom-files-common`, version 2.0.0) is a **shared library** that provides Java beans, format constants, serialisation/deserialisation logic, and annotation infrastructure for reading and writing the **eCount fixed-width flat file format**. It is a foundation library consumed by ETL and batch processes that exchange cardholder and payment data with the eCount prepaid platform via file-based integration.

## Capabilities
| Capability | Class | Description |
|---|---|---|
| Fixed-width file serialisation | `EcountRequestFile.java` | Creates formatted lines for file header, batch header, request records, create-account, add-funds, payment detail, account addenda records |
| Fixed-width file deserialisation | `EcountRequestFile.java` | Reads reply lines back into Java bean objects |
| Annotation-driven PUID construction | `EcountRequestFile.createPUID()` | Builds Partner User ID from annotated fields using ordering |
| Annotation-driven payment detail | `EcountRequestFile.createPaymentDetails()` | Reflects over annotated fields to build PPD records |
| Annotation-driven account addenda | `EcountRequestFile.createAccountAddendas()` | Reflects over annotated fields to build addenda records |
| Reflection helper | `AnnoationHelper.java` (note: typo in class name) | Finds first field with a given annotation on any object |
| Buffered file writing | `BufferedFileWriter.java` | Utility for writing lines to a file |

## Key Entities / Record Types
| Record Type Code | Bean | Purpose |
|---|---|---|
| File Header | `EcountFileHeader` | File-level header (PartnerID, FileName, PassThrough, CreationDate, EPFlag) |
| File Footer | `EcountFileFooter` | File-level footer |
| Batch Header (BH) | `EcountBatchHeader` | Batch-level header (ProgramID, BatchDescription, PromotionID) |
| Batch Footer | `EcountBatchFooter` | Batch-level footer |
| Request Record | `EcountRequest` | Per-account request (EcountID, PartnerUserID, PassThrough) |
| Create Account (07) | `EcountCreateAccountRequest` | Full cardholder demographics for account creation |
| Create Account Reply | `EcountCreateAccountReply` | Response with card number, expiry, CVCode, status |
| Create Account Extended | `EcountCreateAccountExtended` | Extended address (company, attention line) |
| Create Account Extended Reply | `EcountCreateAccountExtendedReply` | Extended address response |
| Add Funds | `EcountAddFundsRequest` | Fund-load request (amount, taxable flag, notification indicator, PartnerPaymentID) |
| Add Funds Reply | `EcountAddFundsReply` | Fund-load response (eCountPaymentID, status) |
| Stop Payment | `EcountStopPaymentRequest` | Stop a payment by PartnerPaymentID or EcountPaymentID |
| Account Addenda | `EcountAccountAddenda` | Secondary label/value pairs attached to an account record |
| Payment Detail (PPD) | `EcountPaymentDetail` | Payment-level label/value pairs |

## Business Rules
- Fixed-width format is strict: each record type has a specific format string (defined as static constants in `EcountRequestFile.java`, lines 30–39), e.g., `CREATE_ACCOUNT = "%-2s%-32s%-25s..."`.
- `rightTrim()` (line 489): truncates to field length; `leftTrim()` (line 496): takes rightmost N characters. Overflow is silently truncated — no exception thrown.
- PUID is constructed by ordering annotated fields by `@PUID.pos` and concatenating with `@PUID.separator` (`EcountRequestFile.createPUID()` lines 418–450).
- Reply parsing uses substring offsets (e.g., `EcountCreateAccountReply` parsed at fixed column positions in `readCreateAccountReply()` lines 202–232).

## Compliance Notes
- `EcountCreateAccountReply` contains `cvCode` (line 225 in `EcountRequestFile.java`) — this is the card verification code returned in the file reply. Storing or logging CvCode (CVV/CVC) would violate PCI DSS SAD requirements. Library consumers must ensure this field is not persisted after use.
- `EcountCreateAccountRequest` bean contains PII: `firstName`, `lastName`, `email`, `address1`, `address2`, `city`, `state`, `postal`, `homePhone`, `businessPhone`, `mobilePhone`.
- File content (when created) contains cardholder PAN in the `EcountCreateAccountReply` (field `cardNumber` at offset 284–300). Files must be handled under PCI DSS file-handling controls.

## Risks
- Silent truncation in `rightTrim()` / `leftTrim()` can cause data loss if calling code passes values that exceed field widths without validation.
- Reflection-based field access (`EcountRequestFile.getField()` line 452) uses `field.setAccessible(true)` — bypasses Java module access controls; may cause issues on Java 21+ with strict module enforcement.
- Typo in class name `AnnoationHelper` (should be `AnnotationHelper`) — cosmetic, but indicates the age of this code.
