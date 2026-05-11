# 01 Business Analyst — emboss-extract_LIB

## Overview

`emboss-extract_LIB` is a Java library that implements the **card personalisation (embossing) extract workflow** for the Onbe prepaid card platform. It generates XML data files that are transmitted to card manufacturers (card bureaus) so that physical prepaid cards can be printed (embossed) with cardholder names, card numbers, and expiry dates. The library is versioned as `com.ecount.process.emboss:embossExtract:1.0.0-SNAPSHOT` (`pom.xml` lines 3–6).

## Business Purpose — Card Personalisation Workflow

When Onbe issues a new prepaid card to a cardholder, the physical card must be manufactured and personalised by a third-party card bureau. The bureau requires a data file that specifies:

- The card number (PAN) to be embossed on the front of the card
- The cardholder name to be embossed on the front
- The expiry date (month/year) to be encoded in the magnetic stripe and printed on the card
- The cardholder's mailing address for card delivery
- Package configuration (card carrier/package design)
- Variable-text fields for client-specific personalisation text

The `emboss-extract_LIB` automates the production of these data files by:
1. Querying the EcountCore database for cards that are queued for embossing (`dbo.core_process_emboss_queue_extract` stored procedure)
2. Building an XML document containing one `<request>` element per card
3. Writing the XML file to a local filesystem path for subsequent transmission to the card bureau

## Card Bureau Vendor Map

The library identifies vendors by integer ID and maps them to vendor name strings (`appContext-emboss.xml` lines 47–56):

| Vendor ID | Vendor Name | Notes |
|---|---|---|
| 1 | FDR | First Data Resources — primary processor |
| 2 | FDR-OFFLINE | FDR offline batch |
| 3 | METACA | Metavante Canada |
| 4 | PSX | PSX vendor (different file-naming convention — Julian date format) |
| 5 | CITI-NAOT | Citi North America OTC |
| 6 | ARROWEYE | Arroweye Solutions — virtual/digital card art bureau |

## Workflow Steps (as implemented in `Extractor.java`)

1. **Insert Emboss File record**: Calls `dbo.core_process_emboss_file_insert` to create a tracking record in the database and obtain a `fileId`.
2. **Extract queue data**: Calls `dbo.core_process_emboss_queue_extract(vendorId, fileId)` which returns a result set of all cards queued for embossing for the specified vendor. The result set is streamed (fetch size 1,000 rows).
3. **Build XML document**: For each card record, `StaxEmbossExtractBuilder.createRequestNode()` writes a `<request>` element containing all personalisation fields including PAN (`<cardnumber>`) and expiry (`<cardexpiration>`).
4. **Update Emboss File record**: Calls `dbo.core_process_emboss_file_update` to record the file name and total record count.
5. **Write file**: The XML is written to the path configured in `EmbossFilePath` (default: `D:/c-base/runtime/ndmroot/` per `embossContext.properties` line 6, or `/upload/EmbossFileExtract/` per `Extractor.java` line 29).

## File Naming Convention

Files are named: `{VendorName}_{yyyyMMddhhmmss}.xml` for most vendors, or `{VendorName}{yyDDDHH}.xml` for PSX (Julian date format). Example: `FDR_20240507143022.xml`.

## PCI DSS Scope

This library directly handles **Primary Account Numbers (PANs)** and **expiry dates** — both classified as cardholder data under PCI DSS. The emboss file is a **cardholder data file** and the entire process of its creation, storage, and transmission is within the **Cardholder Data Environment (CDE)**. See `02_data_architect.md` for the full field inventory and `05_solution_architect.md` for the security analysis.

## Regulatory Obligations

- PCI DSS Req 3: Protect stored cardholder data — the XML file contains PANs in plaintext (see critical finding in `05_solution_architect.md`)
- PCI DSS Req 4: Encrypt transmission of cardholder data over open networks — if the file is transmitted to the card bureau via SFTP or NDM, the transport must be encrypted
- PCI DSS Req 9: Restrict physical access to cardholder data — the output directory (`/upload/EmbossFileExtract/` or NDM root) must be on media access-controlled per Req 9
