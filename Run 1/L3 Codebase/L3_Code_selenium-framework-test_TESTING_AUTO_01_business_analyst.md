# Business Analyst Report — selenium-framework-test_TESTING_AUTO

## Repository Overview

`selenium-framework-test_TESTING_AUTO` is a Selenium-based UI test automation framework targeting the Onbe/Northlane payments platform. It automates functional regression testing for three distinct web application surfaces: the **OnePlatform (OP)** cardholder portal, the **Client Zone (CZ)** client administration portal, and the **Customer Service Application (CSA)** internal agent portal. The project is a Maven module (`groupId: OnePlatform`, `artifactId: Desktop`, `version: 0.0.2-SNAPSHOT`) compiled for Java 21.

## Business Domain Coverage

The test suite covers the complete lifecycle of a prepaid card program from a business perspective:

### OnePlatform (OP) — Cardholder Self-Service
- **Card Registration and Activation** (`Registration.java`, `ActivateCard.java`): End-to-end cardholder registration flows including card number entry, CVV validation, postal code security check, username/password creation, and PIN setup.
- **Login and Session Management** (`LoginLogout.java`, `ExpressLogin.java`): Standard and express login paths with logout verification.
- **Payment Disbursement Selection** (`PaymentHubFlow.java`): Tests the Payment Hub journey where recipients choose their disbursement method — virtual card, prepaid plastic card, ACH bank transfer, or physical check. This is a core payments business process supporting Onbe's multi-rail payout orchestration.
- **International Direct Deposit (IDD)** (`Iddflow.java`): Registration, bank account addition, editing, and deletion for international bank payout recipients. Covers cross-border transfer registration (`WorldLinkFlow.java`, `CambridgeFlow.java`).
- **Profile Management** (`EditProfileFlow.java`, `ForgotPassCheck.java`, `ForgotUserCheck.java`): Cardholder self-service profile updates, password recovery, and username recovery.
- **Claim Code and ACH Flows** (`ClaimCode.java`, `StandardACH.java`, `ExpressACH.java`): Claim code redemption and ACH withdrawal initiation.
- **Plastic Card Request** (`RequestPlasticFlow.java`, `RequestCheckFlow.java`): Requesting physical card issuance and paper check payment.

### Client Zone (CZ) — Client Administration Portal
- **Login and Program Selection** (`CZLoginFlow.java`, `CZNavigationFlow.java`): Client login and program context switching.
- **Cardholder Onboarding** (`CZNewCardHFlow.java`, `CZIssuesingleCardFlow.java`): New cardholder creation and instant card issuance.
- **Balance Loading** (`CZLoadMultipleFlow.java`, `CZQuickPayFlow.java`): Bulk and quick-pay loading operations.
- **File Upload** (`CZFileUploadFlow.java`): Batch file uploads for card programs.
- **Card Linking** (`CZLinkInstantIssueflow.java`, `CZLinktoPrimaryFlow.java`): Instant issue and primary card linking.

### Customer Service Application (CSA) — Internal Operations
- **Account Search** (`CSASearchFlow.java`): Search by ecount ID, card number, username, and PUID with result validation.
- **ACH Transfers** (`CSATransferACH.java`): One-time and recurring ACH withdrawal processing by agents.
- **Fee Reversals and Payment Reversals** (`CSAFeeReversalFlow.java`, `CSApaymentReversalFlow.java`): Regulatory compliance-critical reversal operations.
- **Reissue and Rebuild** (`CSAReissueRebuildAccountFlow.java`): Card reissuance and account rebuild.
- **Manage People** (`CSAManagePeopleFlow.java`): Adding and managing secondary cardholders.
- **Check Requests** (`CSACheckReqFlow.java`, `CSACheckRoleFlow.java`): Check disbursement request flows with role-based access checks.
- **Global Deposit** (`CSAGlobalDepositCambridgeFlow.java`, `CSAGlobalDepositWLFlow.java`): Cross-border deposit initiation via Cambridge and WorldLink rails.
- **Precheck and Redemption** (`CSAPrecheckFlow.java`, `CSARedeemClaim.java`): Pre-qualification checks and claim code redemption.

## Test Data Strategy

Test data is sourced from Excel workbooks (`CSA Test Data.xlsx`, `CZ Test.xlsx`, `Op Test Data.xlsx`) via the `ExcelUtils` utility. Some tests still reference these files via UNC network paths pointing to `\\q-na-app05.nam.wirecard.sys`, indicating dependence on shared QA infrastructure.

## Key Business Risk Observations

1. **Hardcoded card number in Registration.java (line 102)**: The data provider at line 102 contains `data[0][0]= "5445446557563720"` — a full 16-digit card number embedded in source code. This is a PCI DSS Requirement 3 violation risk if this is or ever was a real card number. Even in test code, hardcoding PANs is prohibited by PCI DSS v4.0.1.
2. **Hardcoded test passcode** (line 107): `data[0][4]= "passcode1"` is hardcoded as a test password.
3. **Hardcoded CVV value** (line 103): `data[0][1]= "331"` — potential SAD exposure.
4. **Test coverage is regression-focused**: The suite verifies that previously working flows continue to work. There is limited boundary/negative test coverage visible in the committed test files.

## Stakeholder Value

This framework provides Onbe QA teams with automated regression coverage across the three primary application surfaces (OP, CSA, CZ). Given Onbe's PCI DSS Level 1 obligations, automated functional regression testing is an important quality gate before patch releases.
