# Enterprise Architect View — file-conversion_LIB

## Platform Generation and Role

**Platform Generation**: Gen-1 (legacy batch processing layer)  
**Package Origin**: `com.ecount.file.conversion` — ecount era, pre-Onbe  
**Architectural Role**: File format contract library for FDR/Fiserv batch file exchange

This library defines the **data interchange format** between Onbe's internal batch systems and the FDR card processor. It is the schema definition — in code form — for the 400-character fixed-width batch file protocol used in Onbe's legacy disbursement system.

## Position in Batch Disbursement Architecture

```
[Onbe Batch Disbursement System]
    |
    | Uses file-conversion_LIB to write request files
    v
[Fixed-Width Batch Request File (400-char records)]
    |
    | SFTP delivery to FDR/Fiserv
    v
[FDR Card Processor]
    |
    | Processes: account creation, fund loads, stop payments
    v
[Fixed-Width Batch Reply File (400-char records)]
    |
    | SFTP pickup from FDR/Fiserv
    | Uses file-conversion_LIB to parse reply files
    v
[Onbe: process results, update card/payment status]
```

## Batch File Protocol Context

The fixed-width batch file format (400 characters per record, record type codes `01`–`72`) is a legacy batch protocol specific to FDR's (now Fiserv's) card program management system. This protocol:
- Predates REST APIs and modern web services.
- Is still in active use by many prepaid card programs on the FDR platform.
- Is governed by Fiserv's batch interface specification documents.
- Changes to this format require coordination with Fiserv, which has long change cycle times.

The `BatchFile.java` record type codes map to FDR's standard batch action codes. These codes are specific to the ecount/Onbe FDR client relationship and may vary slightly from other FDR clients.

## Relationship to Other Libraries

| Library | Relationship |
|---------|-------------|
| `fdr-batch-reports-processing_LIB` | Companion library — reads FDR report data. This library writes/parses FDR request/reply files. Together they form the complete FDR batch integration layer. |
| `FDRReports_LIB` | Also FDR-related but processes a different file format (RMS28 settlement reports vs. batch action files). |
| `request-file_LIB` | Likely a higher-level library that uses `file-conversion_LIB` to compose request files. |
| `batch_LIB` | Likely the batch orchestration layer that uses `file-conversion_LIB` for file I/O. |

## Migration Complexity Assessment

**Migration Complexity: VERY HIGH**

1. **Fiserv Protocol Lock-In**: The file format is governed by Fiserv's batch interface specification. Any change to the format requires Fiserv engagement and testing. The protocol is stable but immutable from Onbe's side.

2. **Implicit API Contract**: The field index constants (`FIELD_CREATE_ACCOUNT_CARD_NUMBER = 14`, etc.) in `RequestFileParser` and `ReplyFileParser` are referenced throughout consuming code. Any change to field positions (e.g., if Fiserv adds a field) ripples through all consumers.

3. **No Type Safety**: Field indices are bare integers. There is no compile-time check that a consumer is using the correct field index for the correct record type.

4. **CVV Handling**: The `FIELD_CREATE_ACCOUNT_CV_CODE` constant means some consumer code (not in this repo) is extracting CVV from reply files. A full audit of all consuming code is required before any migration, to ensure CVV handling is compliant with PCI DSS.

5. **Batch Processing Replacement**: Replacing the FDR batch file protocol with real-time API calls (Fiserv now offers REST APIs for card program management) would fundamentally change the architecture. This is a multi-year initiative requiring Fiserv contract renegotiation and extensive consumer refactoring.

## Compliance Architecture Concerns

For PCI DSS compliance:
- The fact that `ReplyFileParser` defines constants for `CARD_NUMBER`, `EXP_MONTH`, `EXP_YEAR`, and `CV_CODE` means this library's consumers are in PCI DSS scope.
- Any system that uses this library to parse reply files and stores those fields is subject to PCI DSS Requirements 3 (protect stored cardholder data), 4 (protect cardholder data with strong cryptography during transmission), and 9 (restrict physical access).
- The library itself has no security controls — it is a pure parsing/serialization utility. All security responsibility rests with consuming applications.

## GDPR / CCPA Considerations

The `writeCreateAccountAction()` method processes full cardholder demographics (name, address, phone, email). Any system using this method is processing personal data under GDPR and CCPA. The batch files produced:
- Must be transmitted over encrypted channels (TLS) to Fiserv.
- Must be stored at rest with encryption if retained.
- Must have a defined retention period.
- Must be accessible for data subject access requests / right to be forgotten under GDPR Article 17.

## Recommended Strategic Direction

1. **Short-term**: Add CVV handling documentation and guardrails (tests that verify CV code is not persisted by consuming code).
2. **Medium-term**: Engage Fiserv to evaluate migration from batch file interface to Fiserv's modern REST API (card issuance API, fund loading API).
3. **Long-term**: Replace this library and all consuming batch jobs with event-driven real-time card management using the Gen-3 Dapr/microservices pattern.
