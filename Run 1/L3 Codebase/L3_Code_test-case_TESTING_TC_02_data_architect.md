# Data Architect Report — test-case_TESTING_TC

## Data Models

This repository contains no executable code and therefore no formal data models. All artefacts are binary spreadsheet and Word document files. Data models are implicit in the structure of test cases, which reference the following logical entities:

- **Member/Cardholder**: member ID (UUID), secure profile (SSN/federal_id, date of birth), cardholder profile fields.
- **Account**: account details, balance, DDA accounts, secondary accounts.
- **Card**: card status, instant issue, plastic-only cards, card renewal and re-issue.
- **Transaction**: account activity, payments, ACH origination/returns, check issuance.
- **Job/File**: FTP files, XML/XLS/FLAT batch files, PGP-encrypted files, bank data feed files.
- **Program/Client**: client zone users, role matrix, program details, pricing matrix.

## Sensitive Data Identified

The test cases reference the following categories of sensitive data by name in test step descriptions and column headers within the XLSX files:

| Data Type | Evidence | PCI/GLBA Classification |
|-----------|----------|------------------------|
| SSN (Social Security Number) | ALM Data docs reference "secure_profile.federal_id"; VBS scripts in windows-scripts use the same field | GLBA-protected PII |
| Date of Birth | "Card Renewal and Re-Issue.docx", CSA Customer Profile test cases | GLBA-protected PII |
| Account Number / DDA | "F_Create DDA only Accounts.xlsx", CSA test suites | PCI DSS if linked to PAN |
| Card Status / PAN context | Card Status data feed files, card renewal test cases | PCI DSS SAD adjacent |
| Cardholder Name | Embedded in test step data throughout | PII |

No actual PAN, CVV, SSN, or account number values have been observed in the repository; test cases describe fields and steps only. However, given that these are manual test cases executed against live or near-production test environments, there is a risk that sensitive real data has been used as test data in execution artefacts stored elsewhere.

## Encryption Status

No encryption is applied to the repository content. All XLSX/XLS/DOCX files are stored in plaintext. If test data contains real cardholder data (a known risk in legacy QA environments), this constitutes a PCI DSS scoping violation.

## Data Flows

The test cases describe the following data flows:

1. **Batch inbound**: Client file (FLAT/XML/XLS) → Job Service → eCount Core → database.
2. **Batch outbound**: eCount Core → ACH / Check / FTP file → bank processor.
3. **API**: Client application → Client API / CS-API / Debit API → eCount Core.
4. **Bank integration**: eCount Core → ACH OUT (NACHA) or Check Interface → bank; Return files back.
5. **Data feed**: eCount Core → Account/Card/Transaction feed files → bank data consumers.

## Retention Concerns

- XLSX artefacts with test data observations are stored indefinitely in Git. If any test execution data containing real PAN or SSN has been committed (e.g., screenshots, copy-paste from screen), it would require git-history purging.
- Binary file storage in Git also means retention cannot be selectively scoped without full-branch pruning.

## PCI DSS Compliance

- Test environment scoping must ensure that test data is synthetic. There is no evidence that synthetic data generation tools or data-masking policies are enforced at the repository level.
- The test cases for SAD (Sensitive Authentication Data) in ClientZone/Cases/Cases L1 SAD.xlsx indicate that SAD handling is being tested, consistent with PCI DSS Req. 3.2. The test content itself should be reviewed to confirm that no real SAD values are embedded.
- PCI DSS Req. 6.3 requires that security testing covers all public-facing applications. The existence of API and ClientZone test cases satisfies the intent, but the absence of automated, continuous execution weakens the assurance posture.
