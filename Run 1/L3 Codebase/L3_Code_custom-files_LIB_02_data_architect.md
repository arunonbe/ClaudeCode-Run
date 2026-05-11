# custom-files_LIB — Data Architect View

## Data Stores
This library does not own any database. It produces and consumes **fixed-width flat files** as the persistence mechanism. The library provides the serialisation/deserialisation layer; the actual file I/O is delegated to `BufferedFileWriter.java` and to consumer classes in other modules.

## File Format Specification
All records are 400 characters wide (format strings in `EcountRequestFile.java` lines 30–39):

| Format Constant | Width | Record Type Code |
|---|---|---|
| `HEADER` | 400 | File-level (2+4+50+32+8+1+303) |
| `FOOTER` | 400 | File-level (2+398) |
| `BATCH_HEADER` | 400 | Batch-level (2+4+64+32+8+290) |
| `BATCH_FOOTER` | 400 | Batch-level (2+398) |
| `REQUEST` | 400 | Per-account (2+16+50+32+300) |
| `ACCOUNT_ADDENDA` | 400 | Addenda (2+10+40+348) |
| `ADD_FUNDS` | 400 | Fund-load (2+32+10+1+10+40+1+304) |
| `CREATE_ACCOUNT` | 400 | Account create (2+32+25+25+25+25+50+26+26+18+2+10+2+16+16+16+10+2+72) |
| `PAYMENT_DETAIL` | 400 | PPD (2+10+40+348) |
| `CREATE_ACCOUNT_EXTENDED` | 400 | Extended address (2+50+50+50+50+25+173) |

## Sensitive Data in File Records
| Field | Record Type | PCI/Privacy Classification | Notes |
|---|---|---|---|
| `cardNumber` (offset 284–300) | `EcountCreateAccountReply` | PAN — PCI DSS Req 3 | Returned in file reply; consumers must not store |
| `cvCode` (offset 322–326) | `EcountCreateAccountReply` | SAD (CVV/CVC) — PCI DSS Req 3.3 | Must NEVER be stored post-authorisation |
| `expMonth` / `expYear` (300–302, 302–306) | `EcountCreateAccountReply` | SAD adjacent | Expiry contributes to full SAD risk |
| `firstName`, `lastName`, `email`, `address*`, phones | `EcountCreateAccountRequest` / Reply | PII — GLBA, CCPA | Standard cardholder demographics |
| `passThrough` | Multiple records | Business reference | 32-char opaque value; may contain client identifiers |
| `partnerPaymentID` | `EcountAddFundsRequest/Reply` | Payment reference | 40-char payment correlation |
| `ecountPaymentID` | `EcountAddFundsReply` | Internal payment ID | 40-char eCount-internal reference |

## Encryption
- Library itself applies no encryption.
- No encryption or hashing is performed on any field values before writing.
- File-at-rest encryption, TLS-in-transit for file transfer, and access controls must be enforced by the consuming ETL/batch processes and the SFTP/MFT infrastructure.
- PAN in file replies exists in cleartext — requires PCI DSS file-handling controls (encrypted media, restricted access, secure deletion).

## Data Flow
```
Consuming ETL/Batch Service
    |
    +-- calls EcountRequestFile.createFileHeader(EcountFileHeader)
    +-- calls EcountRequestFile.createBatchHeader(EcountBatchHeader)
    +-- calls EcountRequestFile.createRequest(EcountRequest)          [or annotation-driven variant]
    +-- calls EcountRequestFile.createAccountAction(EcountCreateAccountRequest)
    +-- calls EcountRequestFile.createAddFunds(EcountAddFundsRequest)
    +-- calls EcountRequestFile.createPaymentDetails(annotated obj)
    +-- calls EcountRequestFile.createAccountAddendas(annotated obj)
    +-- calls EcountRequestFile.createBatchFooter() / createFooter()
    |
    v
Fixed-width file (400 chars/line) written via BufferedFileWriter
    |
    v
SFTP / MFT to eCount platform
    |
    v
eCount reply file
    |
    v
EcountReplyFileListener / EcountReplyParser
    |
    v
EcountRequestFile.read*() methods --> Java beans
```

## Data Quality
- No field-length validation before formatting — `rightTrim()` silently truncates values exceeding field width. No exception, no logging.
- No null-safety beyond `rightTrim()` returning a single space for null inputs.
- `getField()` uses `field.setAccessible(true)` — will fail with `InaccessibleObjectException` on Java 21+ modules if the enclosing module does not export the package.

## Compliance Gaps
- `cvCode` is present in `EcountCreateAccountReply` bean and populated in `readCreateAccountReply()` — if this value is stored anywhere by consumers, it violates PCI DSS Req 3.3 (no SAD storage post-auth). Recommend sanitising this field immediately after card issuance use.
- No audit trail of file generation (no timestamp, operator ID, or hash/checksum in the library).
- No schema versioning mechanism — format changes require coordinated deployments with eCount platform.
