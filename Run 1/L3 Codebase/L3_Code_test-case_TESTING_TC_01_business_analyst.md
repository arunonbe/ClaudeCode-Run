# Business Analyst Report — test-case_TESTING_TC

## Business Purpose

`test-case_TESTING_TC` is a manual test-case repository for the Northlane/Onbe Gen-1 and Gen-2 platform. It serves as the central store of structured test plans covering the prepaid card, customer service, job-service batch, and API layers of the eCount/Citi and Wirecard/Northlane platforms. All content is in spreadsheet (XLS/XLSX) and Word document form; there is no executable code. The repository functions as an ALM (Application Lifecycle Management) artefact store, likely used alongside HP ALM or a GitLab-native test management tool.

## Capabilities

- **API test coverage**: Level 1 (smoke) and Level 2 (regression) spreadsheets for Client API, CS-API, Debit API, IVR, Pre-check API, and ACH Withdrawal endpoints.
- **ClientZone UI test coverage**: L1, L2, and L3 test cases for login, MFA, dashboard, file upload, inventory management, user management, profile, reports, instant issue, sweep, and QuickPay.
- **CSA (Customer Service Agent) test coverage**: US and Canada-specific L1/L2/L3 cases covering account details, balance link, payment hub, pre-checks, secondary accounts, risk review.
- **JobService batch test coverage**: Scheduler, FTP, PGP file encryption, XML/XLS/FLAT file formats, banker, ACH origination/returns, check issuance, blackout, content validation, enrollment, FDR MQ integration.
- **ALM Data artefacts**: Bank Integration ACH OUT end-to-end, Check Interface end-to-end, data feed file generation (account balance, account data, card status, transaction data) stored as Word documents with step-by-step test scenarios.

## Client and Cardholder Impact

These test cases exercise the complete cardholder-facing and client-facing surface of the platform. Deficiencies in test coverage directly translate into production defects affecting cardholder disbursements, ACH credit/debit accuracy, card activation, and client program management. Specific test suites (e.g., "PGP_File_Encryption_Testing", "File Encryption", "MFA") verify security controls that are required by PCI DSS and GLBA.

## Business Rules Encoded

The file structure reveals the following business rules and operational boundaries:
- Multi-level test progression (L1 smoke, L2 regression, L3 end-to-end) across all modules.
- Client-specific test cases exist for Grifols, KLM, T-Mobile, Home Depot, QBE, Adecco, NCH, NIIC — indicating client-isolation testing obligations.
- Separate Canada vs. US test branches for CSA indicate regulatory jurisdiction handling.
- FDR MQ integration test cases confirm the FDR processor interface is tested at the batch layer.
- Singapore MFA test cases in ClientZone Level 2 indicate multi-jurisdictional MFA policy enforcement.

## Regulatory Obligations

- **PCI DSS**: Test cases cover file encryption, MFA, pre-checks (cardholder data pre-check validation), and SAD (Sensitive Authentication Data) handling — confirming PCI DSS Req. 8 (authentication) and Req. 3 (stored data protection) are in scope.
- **NACHA**: ACH origination and return control-total test cases (Scheduler → ACH OUT, Returns) directly validate NACHA file structure and settlement accuracy.
- **Reg E**: Dispute and error resolution flows are implicitly covered through CSA payment hub and account action test suites.
- **GLBA**: Profile and secure data test cases align with non-public personal information protection requirements.

## Key Business Risks

1. **No automation linkage is visible.** All test cases are manual spreadsheets with no connection to an automated CI pipeline. This increases regression risk during releases and slows velocity.
2. **Client-specific test cases may be incomplete.** The presence of client names (KLM, T-Mobile, Home Depot) without systematic L3 coverage for all clients suggests uneven regression depth.
3. **Version control of test artefacts is immature.** Binary XLSX/XLS files cannot be meaningfully diffed, making change history opaque and audit trail weak — a concern for PCI DSS evidence requirements.
4. **No traceability artefacts.** There are no links from test cases to requirements or defects in the repository itself, reducing auditability.
