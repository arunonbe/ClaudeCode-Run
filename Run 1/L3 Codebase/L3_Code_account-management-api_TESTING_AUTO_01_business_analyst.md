# account-management-api_TESTING_AUTO — Business Analyst View

## Business Purpose

This repository is a **test automation suite** for Onbe's Account Management API — a SOAP/XML web service layer that sits over a prepaid card and account lifecycle management platform. The suite exercises the external-facing SOAP endpoints of the `accountmanagementapiws` and `accountmanagementpayoutapiws` services hosted on `webservice-qa.wirecard.com`, the QA environment for the (former) Wirecard/Citi prepaid processing platform. There is no production application code here; the sole purpose is automated functional regression testing of the account management web service contract.

## Business Capabilities

The tests cover the following account management operations, mapping directly to SOAP operations against the `AccountManagementApiWebServices` endpoint:

| Test Class | SOAP Operation | Business Capability |
|---|---|---|
| `AccMgmtAPI.CreateAccount` | `createAccountRequest` | Open a new prepaid account with initial load |
| `AccMgmtAPI.CreateAccountLink` | `createAccountRequest` (with `link` element) | Open account and link to an existing card package |
| `AccMgmtAPI.AddFunds` | `addFundsRequest` | Credit funds to an existing prepaid account |
| `AccMgmtAPI.AssignPackage` | `assignPackageRequest` | Assign a card package to a registered cardholder |
| `AccMgmtAPI.ActivationStatusInquiry` | `activationStatusInquiryRequest` | Query card activation state (prepaid program) |
| `AccMgmtAPI.CreateBulkOrder` | `createBulkOrderRequest` | Bulk-order card packages to a shipping address |
| `AccMgmtAPI.CreatePackage` | `createPackageRequest` | Create a personalised card package (primary + secondary cardholder) |
| `AccMgmtAPI.GetRequest` | `serviceRequest` | Generic account/service inquiry |
| `AccMgmtAPI.LinkCard` | `linkCardRequest` | Link a card package to an existing account |
| `AccMgmtAPI.SetPin` | `setPinRequest` | Set/change cardholder PIN |
| `AccMgmtAPI.UpdateAccStatus` | `updateAccountStatusRequest` | Update account status (e.g., CLOSED) |
| `AccMgmtAPI.UpdateReg` | `updateRegistrationRequest` | Update cardholder registration/KYC data |
| `AccMgmtAPI.WithdrawAch` | `withdrawRequest` (type=1) | Initiate ACH bank transfer withdrawal |
| `AccMgmtAPI.WithdrawCheck` | `withdrawRequest` (type=2) | Initiate paper check withdrawal |
| `AccMgmtAPI_Payout.ActivateCard` | `activationStatusInquiryRequest` (payout endpoint) | Activate payout card |
| `AccMgmtAPI_Payout.ActivationStatusInquiryPayout` | `activationStatusInquiryRequest` (payout endpoint) | Query payout card activation status |
| `AccMgmtAPI_Payout.SetPinPayout` | `setPinRequest` (payout endpoint) | Set PIN for payout card |

The payout tests use a distinct service path (`accountmanagementpayoutapiws/...`) and a different port (4007 vs 4005), indicating a separate payout product line.

## Business Entities

The following business entities are visible in the SOAP request fixtures:

- **Account**: Identified by `accountNumber` (e.g., `0401661300001758`, `0401661300001000`). These are 16-digit numeric identifiers combining a program ID prefix and a sequential number.
- **Card / Card Package**: Identified by `cardPackageId` (e.g., `217`, `230`) and card PAN (`card_number`). Card packages are physical prepaid card inventory units.
- **Program**: Identified by `program_id` (e.g., `04012521`, `04016613`, `04010929`, `04014347`). Each program represents a prepaid card product.
- **Partner User**: Identified by `partner_user_id` — the client-side user identifier that maps an external cardholder to Onbe's internal account.
- **Transaction**: Identified by `transaction_id` — a unique idempotency key per operation.
- **Cardholder Registration**: Contains PII fields — `firstName`, `lastName`, `address1`–`address4`, `city`, `state`, `postal`, `country`, `date_of_birth`, `emailAddress`, `homePhone`, `mobilePhone`, `ssn`.
- **Load / Fund Transfer**: Contains `amount`, `comment`, `claimable` flag, `notificationIndicator`, `templateId`.
- **ACH Details**: `account_holder_name`, `account_number`, `routing_number`, `account_type`, `bank_name`.
- **Withdrawal**: `withdraw_type` (1=ACH, 2=check), `amount`, `express_flag`, `partner_withdraw_id`.

## Business Rules & Validations

Rules observed from test fixtures and response assertions:

1. **Success Validation**: All tests assert `PROCESSED_SUCCESSFULLY` in the SOAP response body (via `ns2:description` or `sub_code` XPath). There is no negative-path, boundary, or error-scenario testing present.
2. **Account Status Transitions**: `UpdateAccStatus` test demonstrates setting `accountStatus` to `CLOSED` (`SoapRequest/UpdateAccStatus.xml` line 17). Other status values (e.g., ACTIVE, SUSPENDED) are not tested.
3. **PIN Format**: `SetPin.xml` and `SetPinPayout.xml` use `new_pin` value `1234` — a sequentially trivial test PIN; no PIN complexity rules are validated.
4. **Withdraw Types**: Type `1` = ACH, type `2` = check, evidenced in `WithdrawAch.xml` (line 18) and `WithdrawCheck.xml` (line 17).
5. **Claimable Flag**: `AddFunds.xml` uses `claimable=0`; `CreateAccount.xml` uses `claimable=1`. This flag likely controls self-service fund claiming.
6. **Access Level**: `accessLevel=1` used consistently for account and card access tier.
7. **Express Mail**: `CreatePackage.xml` uses `express_mail=true` for expedited delivery.
8. **Postal Validation (Payout)**: `ActivationStatusInquiryPayout.xml` includes `validate_postal=1`, which is absent from the prepaid equivalent — indicating an additional cardholder validation step for payout products.
9. **Transaction Idempotency**: Each request fixture contains a unique `transaction_id`. However, since test data is static, repeated test runs will send duplicate `transaction_id` values, which may cause failures if the platform enforces idempotency.

## Business Flows

**Prepaid Account Lifecycle Flow** (inferred from test classes):
1. `CreatePackage` — create a card package with cardholder registration
2. `CreateAccount` — open an account with initial load
3. `CreateAccountLink` — alternatively, create account already linked to a card package
4. `AssignPackage` — assign a card package to the account holder
5. `LinkCard` — link card to account (if not done at create time)
6. `ActivationStatusInquiry` — verify card is active
7. `SetPin` — cardholder sets PIN
8. `AddFunds` — load funds onto account
9. `UpdateReg` — update cardholder KYC data
10. `UpdateAccStatus` — change account status (e.g., CLOSED)
11. `WithdrawAch` / `WithdrawCheck` — cardholder withdraws funds

**Payout Card Flow**:
1. `ActivateCard` (payout) — activate payout card using card_number + CVV + postal_code
2. `ActivationStatusInquiryPayout` — confirm activation with postal validation
3. `SetPinPayout` — set PIN on payout card

Note: Tests are independent; there is no chaining of test output (e.g., account numbers are hardcoded, not dynamically retrieved from a preceding test's response).

## Compliance & Regulatory Concerns

- **PCI DSS**: The SOAP fixture files `SoapRequest/ActivateCard.xml` and `SoapRequest/ActivationStatusInquiry.xml` (and `ActivationStatusInquiryPayout.xml`) contain what appear to be **real or realistic card numbers** (`5115531022041490` and `5445446554206695`) and **CVV values** (`308`, `319`). These are sent in plaintext XML over HTTPS. If these are live PANs/CVVs committed to the repository, this constitutes a critical PCI DSS violation (Requirement 3.2.1 — SAD must not be stored). The repository is hosted on both GitLab and GitHub (GitHub Actions present), creating a broad exposure surface. The numbers should be replaced with synthetic values (e.g., Luhn-valid test numbers per the BIN ranges designated for testing).
- **SetPin fixtures** (`SetPin.xml` line 11, `SetPinPayout.xml` line 10) embed literal PIN values (`1234`) in committed files. While `1234` is a trivially non-sensitive test PIN, any PIN in a fixture file violates PCI DSS SAD requirements if the account numbers mapped to them are real.
- **PII in fixtures**: `SoapRequest/UpdateReg.xml` contains `ssn` value `741859632` (line 48), `date_of_birth` `01/04/1997`, and several email addresses including `gaurav.sharma@onbe.com`. The SSN value in a committed test fixture is a potential data exposure issue under GLBA and state privacy laws.
- **Internal email addresses**: Multiple fixture files reference `gaurav.sharma@onbe.com` and `himanshu.goyal@external.wirecard.com` in PII fields — Onbe employee/contractor emails embedded in committed test data.
- **NACHA**: `WithdrawAch.xml` contains a realistic-looking bank routing number (`096001013`) and a 17-digit account number (`99087060252122451`). If these reference a real account, this is a data exposure risk under GLBA/NACHA rules.
- **Reg E**: The test suite exercises ACH and check withdrawal flows, which are Reg E-regulated transactions. There are no tests for Reg E error resolution, reversal, or dispute flows.

## Business Risks

1. **No negative or error-path testing**: Every test asserts only `PROCESSED_SUCCESSFULLY`. There are no tests for invalid accounts, insufficient funds, duplicate transactions, blocked cards, or API authentication failures.
2. **Static hardcoded test data**: Account numbers, program IDs, and transaction IDs are hardcoded. Tests are not idempotent across runs; repeated execution against the same QA environment will fail on idempotency-enforced operations.
3. **Hardcoded QA endpoint**: `RestAssured.baseURI` is set in every class (`webservice-qa.wirecard.com:4005` / `:4007`). There is no environment-switching mechanism. The QA domain `wirecard.com` may be decommissioned or transferred following the Wirecard insolvency.
4. **No test data management**: Test data (card numbers, account numbers, program IDs) is not managed externally. Tests rely on pre-existing QA environment state.
5. **Single assertion per test**: Each test has one pass/fail assertion — the description/sub_code string match. Field-level response validation is absent.
6. **PII/SAD in version control**: As noted above, SSN, card numbers, CVVs, bank account details, and email addresses are committed in plain text — a significant compliance and reputational risk.
