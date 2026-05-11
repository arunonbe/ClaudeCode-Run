# Business Analyst View — request-file_LIB

## Business Purpose

`request-file_LIB` is a Gen-1 eCount shared library that builds and serializes XML request files for batch payment processing. It serves as the file-generation layer for the eCount platform's batch disbursement pipeline: when Onbe needs to disburse funds to a large number of prepaid cardholders (e.g., a promotional sweep, instant-issue batch, or ACH payout batch), this library constructs the XML-format batch request file that is consumed by the eCount payment processing backend.

This library implements the file-based integration pattern between the Onbe order management system and the underlying payment processor (historically Citi/eCount), where batches of payment instructions are written to XML files that the processor picks up and executes. This is a Gen-1 architecture pattern predating REST-based APIs.

## Capabilities

The library provides:
- **XML schema mapping**: Java classes (`Cardtype`, `Batchtype`, `Requestfile`, `Requestfiletype`, `Request`, etc.) generated from or aligned with an XML Schema Definition (XSD) for the eCount payment request file format. These classes use JAXB annotations for XML marshalling.
- **Request file building**: `RequestBuilder` assembles `PaymentData` objects into a `Requestfile` JAXB object tree and marshals the result to an XML file on the filesystem.
- **Request type models**: Domain value objects for different payment instruction types — `AccountCreationVO`, `FundsAdditionVO`, `PaymentStopVO`, `SpinVO`, `BatchVO`, `RequestVO`, `RequestFileVO` — representing distinct disbursement operations.
- **File name generation**: `ReqFileNameGenerator` creates time-stamped or sequenced filenames for the output XML files.
- **Batch file lifecycle**: `RequestFileStatus` tracks the success/failure of file generation operations.

## Client and Cardholder Impact

This library is on the critical path for batch disbursements. A bug in XML generation can cause:
- Payment files that are rejected by the processor (malformed XML, missing required fields) — cardholders do not receive expected funds on time.
- Payment files that are incorrectly populated (wrong amounts, wrong card numbers) — cardholders receive incorrect amounts, creating a reconciliation and potential regulatory (Reg E) issue.
- Silent file generation failures — the library catches exceptions internally (`e.printStackTrace()`) without guaranteed error propagation, meaning a failed file write might not surface as an operational alert.

## Business Rules in Code

- The `Cardtype` object represents a payment card in the batch file. It carries `cardnumber`, `expmonth`, `expyear`, `cardtype` (network/type code), and `cvcode` (CVV/CVC). All five fields are marshalled to XML.
- The `Requestfile` root element includes a `creationdate` (the date the batch file was created, expressed as an `XMLGregorianCalendar`).
- The `Batchtype` element groups multiple `Request` elements, enabling multiple payment operations within a single file.
- Different request types (`Addfundsrequesttype`, `Createaccountrequesttype`, `Stoppaymentrequesttype`, `Spinrequesttype`, `Ppdtype`) represent distinct payment operations, each with its own XML element structure.

## Regulatory Obligations

- **PCI DSS Req 3.2 / 3.3**: The `Cardtype` object carries `cvcode` (CVV/CVC), which is Sensitive Authentication Data (SAD). PCI DSS Req 3.2 prohibits storage of SAD after authorization. The marshalling of `cvcode` to an XML file on disk constitutes potential SAD storage. This is a direct PCI DSS violation risk — see the Solution Architect analysis for the specific code finding.
- **NACHA**: If `Ppdtype` (PPD = Prearranged Payment and Deposit) represents ACH payment instructions, the file format and content must comply with NACHA operating rules for PPD entries, including correct routing/account number formatting and authorization documentation.
- **GLBA**: The batch files, once written to disk, contain financial account data and must be protected with appropriate access controls, encryption at rest, and secure deletion after processing.

## Key Business Risks

1. **CVV in XML file (PCI DSS Req 3.2 violation)**: The `Cardtype.cvcode` field is marshalled to XML without `@XmlTransient`. If CVV values are ever populated in the `Cardtype` object and the file is written to disk, SAD is stored in plaintext — a critical PCI DSS violation.
2. **Silent failure in file generation**: `RequestBuilder.createReqFile()` catches all exceptions and sets a failure status, but uses `e.printStackTrace()` rather than proper error propagation. In a production batch pipeline, this could cause silent data loss.
3. **Filesystem path from properties file**: The output path is read from `REQUEST_FILE_BASE_PATH` in a properties file managed by `ReqFileNameGenerator`. If this path points to an uncontrolled or insecure directory, batch files containing payment data could be accessible to unauthorized processes.
