# jobserviceintegration_LIB — Data Architect View

## Data Stores

This library **does not maintain persistent data stores**. It operates as a file-transformation utility:

| Store | Type | Usage |
|---|---|---|
| Client input files (ZIP/flat) | Filesystem | Read at runtime; client-provided fixed-width or delimited flat files |
| ecount batch output files | Filesystem | Written by `BatchFile`; consumed by ecount job service |
| Promotion config properties file | Filesystem | `PromotionXref.loadFromFile(ChryslerFileContants.PROMO_CONFIG_FILE)` — path is a compile-time constant |
| ecount reply files | Filesystem | Parsed by `ReplyFileParser` for post-processing outcome extraction |

No JDBC, no JPA, no message queue connections are present in this library.

## Schema / File Formats

### ecount Standard Batch File (Fixed-Width, 400 chars/line)

| Record Type | Description | Key Fields |
|---|---|---|
| `01` | File header | Partner ID (4), filename (50), passthrough (32), create date |
| `02` | File footer | Blank padding |
| `03` | Batch header | Programme ID sub (4), description (64), passthrough (32), promo ID (8) |
| `04` | Batch footer | Blank padding |
| `05` | Add-funds action | Passthrough (32), amount (10), taxable (1), notification indicator (10), partner payment ID (40) |
| `07` | Create-account action | Passthrough (32), first/middle/last/suffix name, email (50), address1/2, city, state (2), zip (10), country (2), phones (16 each), notification indicator (10) |
| `09` | Request header | EcountId (16), partner user ID (50), passthrough (32) |
| `12` | Create-certificate action | Template ID (8), amount (10), start date (8), names (50 each), passthrough (32) |
| `13` | Certificate memo addenda | Memo (250), passthrough (32) |
| `14` | Email notification action | Recipient email (50), sender email (50), bounce email (50), passthrough (32) |
| `18` | Spin payment action | Passthrough (32), directClaim (1), taxable (1), notification (10), partner payment ID (40) |
| `20` | Stop payment action | Passthrough (32), partner payment ID (40), ecount payment ID (40), notification (10) |
| `51`–`53` | PPD records | Name (10), value (40) |
| `72` | Create-account addenda | LabelId (10), LabelValue (40) |

### Promotion Config File (`PROMO_CONFIG_FILE` constant in `ChryslerFileContants`)
Properties file mapping stock codes to `EcountPromotion` objects (promotion ID, amount, taxable, send-email, memo).

## Sensitive Data

| Data | Classification | Location in file |
|---|---|---|
| Recipient first name | PII | Record type 07, field ~offset 34–58 |
| Recipient last name | PII | Record type 07, field ~offset 84–108 |
| Recipient email address | PII | Record type 07, field ~offset 134–183 |
| Full mailing address | PII | Record type 07 |
| Home / business / mobile phone | PII | Record type 07 |
| Partner user ID (PUID) | Cardholder-adjacent | Record type 09, offset 2–51 |
| Payment amount (in cents as integer) | Financial | Record type 05, offset 34–43 |

No PAN, CVV, or track data is present in this file format.

## Encryption

- **None.** Files are written as plain-text ASCII/UTF-8 flat files with no encryption.
- No transport encryption is implemented — file delivery mechanisms (SFTP, shared filesystem) are external to this library.
- Promotion configuration files and input client files are stored unencrypted on the filesystem.

## Data Flow

```
[Client ZIP/flat file on filesystem]
        |
        v
[ChryslerFileConverter / other converter]
        |
        +-- reads contact header  --> in-memory Hashtable (PUID → contact line)
        +-- reads fulfillment     --> in-memory Hashtable (packageId → stockCode)
        +-- reads letter-form     --> in-memory Hashtable (stockCode → List<records>)
        |
        v
[PromotionXref.loadFromFile]  <-- PROMO_CONFIG_FILE on filesystem
        |
        v
[BatchFile.writeXxx()] --> ecount standard batch flat file on filesystem
        |
        v
[ecount Job Service (external)] reads and processes the batch file
        |
        v
[ReplyFileParser] <-- reply file written back by ecount job service
```

## Data Quality and Retention

- No data quality enforcement beyond field-width truncation (fields longer than declared width are silently truncated).
- No retention policy; file lifecycle management is external to this library.
- Null/empty key fields (prospect ID, package ID) are detected and raise exceptions, but other field validation is minimal.
- The Hashtable-based in-memory processing means that all records from a client file must fit in JVM heap — no streaming.

## Compliance Gaps

1. **PII in plain-text files**: Recipient PII (name, address, email, phone) is written to unencrypted flat files — violates GDPR Art. 32 and PCI DSS Req. 3 expectations around data protection in transit and at rest if these files traverse untrusted paths.
2. **No audit trail**: There is no logging of what PII was processed, transformed, or written. No record of who triggered the conversion.
3. **Binary JARs in source control**: `alg/common/*.jar` and `BulkCardGen/.../*.jar` are unversioned, unauditable binaries committed to the repository — PCI DSS Req. 6.3 (secure development) risk.
4. **Phone number replacement**: `0000000000` → `555-555-5555` is a data-quality fix applied silently; production data consumers may receive synthetic phone numbers without knowing.
5. **No data minimisation**: Full recipient records are held in memory for the entire duration of file processing.
