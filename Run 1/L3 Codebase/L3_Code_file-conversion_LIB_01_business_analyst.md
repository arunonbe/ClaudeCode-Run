# Business Analyst View — file-conversion_LIB

## Repository Overview

**file-conversion_LIB** is a Gen-1 Java library (`com.ecount.file.conversion`) that provides file format utilities for Onbe's (formerly ecount's) batch processing system. Specifically, it provides the tools to **produce and parse the fixed-width batch file format** used to communicate disbursement requests and replies between Onbe's internal systems and the FDR card processing platform (and related partners).

This is a foundational library in Onbe's batch disbursement workflow. It is not a standalone application — it is imported as a dependency by other batch processing jobs that need to generate batch request files for FDR or parse reply files received from FDR.

## Business Purpose

### Batch File Communication with FDR/Partners

Onbe's Gen-1 disbursement workflow operates via batch files exchanged with card processors. This library provides the data structures and format specifications for those files:

1. **Request File Writing** (`BatchFile.java`): Creates batch request files in the FDR fixed-width format. These files contain instructions for the card processor: create an account, load funds, stop payment, create a certificate (e-gift card / digital reward), send email notification.

2. **Request File Parsing** (`RequestFileParser.java`): Parses incoming request files from partners or upstream systems.

3. **Reply File Parsing** (`ReplyFileParser.java`): Parses reply files returned by FDR/partners confirming the result of each batch operation (account creation success/failure, fund load confirmation, payment status codes).

### Batch Operations Supported

| Record Type Code | Operation | Business Meaning |
|-----------------|-----------|-----------------|
| `01` | File Header | Start of batch file (partner ID, filename, creation date) |
| `02` | File Footer | End of batch file |
| `03` | Batch Header | Start of a batch (program ID, batch description, promotion ID) |
| `04` | Batch Footer | End of a batch |
| `05` | Add Funds | Load money to a prepaid card (amount, taxable flag, notification indicator, partner payment ID) |
| `07` | Create Account | Create a new cardholder account (full demographics: name, address, phone, email) |
| `09` | Request Header | Per-request header (ecount ID, partner user ID) |
| `12` | Create Certificate | Create a digital certificate/gift card (template, amount, recipient/sender info) |
| `13` | Certificate Memo | Addendum to certificate creation |
| `14` | Email Notification | Email delivery instruction |
| `18` | Spin Payment | Special payment type (direct claim, taxable, notification) |
| `20` | Stop Payment | Cancel a previously issued payment |
| `51` | PPD Record (Add Funds addendum) | Personal Payment Data for fund loads |
| `52` | PPD Record (Spin Payment addendum) | Personal Payment Data for spin payments |
| `53` | PPD Record (Stop Payment addendum) | Personal Payment Data for stop payments |
| `72` | Create Account Addenda | Additional data for account creation |

### Cardholder Data Handled

The `writeCreateAccountAction()` method in `BatchFile.java` (lines 320–363) accepts:
- First name, middle name, last name, suffix
- Email address
- Address1, Address2, City, State, ZIP, Country
- Home phone, business phone, mobile phone

This is **full cardholder PII** flowing through the batch file. The `ReplyFileParser.java` also defines constants for `FIELD_CREATE_ACCOUNT_CARD_NUMBER` (index 14), `FIELD_CREATE_ACCOUNT_EXP_MONTH` (15), `FIELD_CREATE_ACCOUNT_EXP_YEAR` (16), `FIELD_CREATE_ACCOUNT_CV_CODE` (18) in reply file parsing — indicating that reply files contain card number, expiration, and CV code fields returned by FDR.

**CRITICAL PCI FLAG**: The reply file parsing fields include `FIELD_CREATE_ACCOUNT_CARD_NUMBER`, `FIELD_CREATE_ACCOUNT_EXP_MONTH`, `FIELD_CREATE_ACCOUNT_EXP_YEAR`, and `FIELD_CREATE_ACCOUNT_CV_CODE`. These are Sensitive Authentication Data (SAD). Per PCI DSS Requirement 3.2, SAD must not be stored after authorization. The `CV_CODE` (CVV) must never be stored at all. Any system that processes reply files using this library must ensure these fields are not persisted.

## Domain Context

The `EcountPromotion` class (`EcountPromotion.java`) models a batch promotion (batch parameters: name, memo, amount, promotion ID, taxable flag, email notification code). This maps to Onbe's program/promotion concept — a configured disbursement campaign with specific rules.

The `TaxProfile` and `PromotionXref` classes support promotional cross-referencing and tax treatment, relevant to Onbe's consumer incentive and rebate disbursement use cases (healthcare, auto finance, insurance verticals).

## Validators

`FileValidator.java` and `FixedWidthRecordFileValidator.java` provide file-level validation before processing, ensuring files conform to expected format before attempting to parse or load.

## Summary of Business Value

This library is the **data format contract** between Onbe's batch disbursement systems and FDR/Fiserv. Without it, Onbe's batch card operations (account creation, fund loads, stop payments) cannot generate correctly formatted files for the card processor. It is a foundational dependency of the legacy batch disbursement platform.
