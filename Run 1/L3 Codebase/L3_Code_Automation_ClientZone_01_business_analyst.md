# Automation_ClientZone — Business Analyst View

## Business Purpose

This repository is a UI test automation suite for Onbe's client-facing and cardholder-facing web platforms. It uses Playwright (Java) and Cucumber BDD to validate the functional behavior of four distinct web applications:

1. **ClientZone** (`clientzone-qa.mypaymentadmin.com`) — Onbe's internal B2B client administration portal, used by client program managers to manage prepaid card programs, cardholders, inventory, and payment operations.
2. **MyPaymentVault (MPV)** (`mypaymentvault.qa.onbe.dev`) — Onbe's Gen-2 B2C cardholder self-service portal, where cardholders register accounts, activate cards, manage profiles, and initiate transfers.
3. **Wizard / Program Setup Assistant** (`q-na-app05.nam.wirecard.sys:8090`) — An internal tool for Onbe program administrators to configure program profiles and website display settings.
4. **IdPassMe** (`qa.idpassme.com`) — A KYC (Know Your Customer) identity verification portal for global card recipients, handling identity verification flows for multi-currency cards.

The repo contact (per README) is `viktor.potok@onbe.com`.

## Business Capabilities

### ClientZone Module
- **Authentication**: Standard username/password login; SSO login via external identity provider (Microsoft Entra ID); SSO enforcement that blocks legacy login for SSO-configured accounts.
- **Multi-Program Access**: Users managing multiple programs select a program from a dropdown after authentication.
- **New Cardholder Issuance (NCH)**: Feature tag `@Newcardholder` — issue new cardholder accounts (feature stub; login only currently automated).
- **Quick Pay / Add Funds**: Feature tag `@Quickpay` — add funds to existing cardholder accounts (feature stub).
- **Payment Reversal**: Feature tag `@Paymentreversal` — reverse payments on cardholder accounts (feature stub).
- **Manage Inventory**: Feature tag `@Manageinventory` — issue bulk instant-issue card inventory (feature stub).
- **Instant Issue — Assign Card**: Feature tag `@InstantIssueAssign` — assign instant-issue cards to cardholders (feature stub).
- **Instant Issue — Link to Primary**: Feature tag `@InstantIssueLinktoPrimary` — link instant-issue cards to primary accounts (feature stub).
- **Issue Virtual Card**: Feature tag `@Issuevirtualcard` — issue virtual cards (feature stub).
- **Virtual Resend Link**: Feature tag `@VirtualResendlink` — resend virtual card express email links (feature stub).
- **Searchable Addenda**: Feature tag `@SearchableAddenda` — fully implemented; allows client service agents to search cardholder accounts by memo/addenda fields, compare UI record counts against the `EcountCore` database, request plastic cards for cardholder accounts, and validate DDA-only vs. non-DDA account distinctions.

### MyPaymentVault Module
- **Login / Logout**: Username+password authentication with inline error validation, language switching (English/Spanish/French).
- **Card Activation**: Multi-step card activation with DOB or postal code second-factor authentication; PIN creation flow.
- **Registration**: Multi-step account creation: card number + CVV + postal → username/password → SSN + DOB → terms and conditions → confirmation.
- **Dashboard**: Available balance display, card details (toggle), wallet options, recent transactions, PayPal integration reference.
- **Transactions**: Transaction history with fee summary, date/description/amount/balance columns, beginning/ending/available balances, view details.
- **Bank Transfer (ACH)**: Standard ACH and Express ACH one-time and recurring transfers; confirm and cancel flows.
- **Request Check**: Mailing address check disbursement with fee display and success/error handling.
- **Request Card (Plastic)**: Order replacement physical card.
- **Change PIN**: Two-step PIN change with card number + DOB verification.
- **Change Password**: Current/new/confirm password flow with success and failure validations.
- **Profile Management**: View and edit contact information (address, email, phone), SSN, DOB display, username.
- **Manage Bank**: Bank account CRUD (feature commented out; not currently automated).
- **Forgot Password / Forgot Username**: Self-service credential recovery.
- **Dispute Form / Fraud Form**: Links to external dispute and fraud form pages (open in new tab).
- **FAQ, Fees & Disclosures, Privacy Policy, Terms and Conditions, Contact Us**: Informational/compliance pages.
- **Global Transfers (IBAN)**: Commented out in feature file; cross-border transfers (not automated).

### Wizard Module
- **Program Setup Login**: Admin authentication to the Wirecard/Onbe program setup tool.
- **Program Profile**: Look up existing program by program ID.
- **One Platform (OP) Setup**: Navigate to OP Setup for a program.
- **Website Display Settings**: Toggle "Display Card Details" ON/OFF for a program and validate the effect on the MPV cardholder dashboard.

### IdPassMe Module
- **Card Login (Card Activation Entry)**: Submit card number and CVV to initiate identity verification.
- **Identity Verification (KYC)**: Path routing based on card status (ACTIVE, READY, CLOSED, INVALID), recipient country (allowed/restricted), and currency (CAD, CHF).
- **Edit Profile**: Modify country on the KYC page.
- **Edit Address**: Edit mailing address for KYC-verified recipients.

## Business Entities

| Entity | Evidence |
|---|---|
| **Program** | Program ID `04014978` hardcoded in `SearchableAddenda.feature`; `existingProgram_id: "04010993"` in `wizard.json`; `getDomains.do` URL path |
| **Cardholder / Payee** | `SelectPayee` locator in `SearchableAddendaPage.java`; `cardholder` in `DashboardPage.java` |
| **Card** | `cardNumber`, `cvv`, `pinNumber_CardNumber` fields in `DataMapper.java`; `ChangePinPage.java` card number input |
| **DDA Account** | `core_device_dda` table; DDA-only vs. non-DDA logic in `SearchableAddendaSteps.java` lines 270–298 |
| **Transaction** | `TransactionsPage.java` — date, description, amount, balance, fee summary |
| **Bank Account** | `accountNumber`, `routingNumber`, `bankName` in `DataMapper.java`; `BankTransferPage.java` |
| **Addenda / Memo** | `core_member_addenda` table; searchable addenda fields `Dynamic_memo1` in `SearchableAddendaSteps.java` |
| **Block Code** | `fdr_profile_block_code` table joined in DB queries in `SearchableAddendaSteps.java` |
| **Recipient (KYC)** | `firstName`, `lastName`, `DOB` in `IdPassMe/LoginPage.java`; country/currency in `IdPassMe/Login.feature` |

## Business Rules & Validations

1. **SSO Enforcement**: If a user's account is configured for SSO and they attempt legacy CZ login, they receive the error "Your account is configured for SSO. Please use the SSO login page to access your account." (`SSLoginSteps.java` line 183).
2. **SSO Error Redirect**: Legacy CZ forgot-password for SSO users shows "It looks like your email belongs to an SSO account..." (`SSLoginSteps.java` line 204).
3. **Login Lockout**: After invalid credentials, the error "Your username or password is incorrect or locked." is displayed (`LoginPage.java` line 36).
4. **Email Field Length (SSO)**: Email field enforces a maximum length under 51 characters (`SSLoginSteps.java` lines 208–228). Note: the assertion logic is inverted (bug — `assert(false)` is unconditional at line 219).
5. **Searchable Addenda — Mandatory Fields**: "Please select a Search Option." and "Please enter a Search Term." errors enforced before executing search (`SearchableAddendaSteps.java` lines 73, 87).
6. **Addenda DB/UI Count Reconciliation**: Record count from UI must match SQL query across `core_device_dda`, `fdr_card_account`, `core_device_eCard_extended`, `fdr_profile_block_code` tables (`SearchableAddendaSteps.java` lines 172–266).
7. **DDA-Only Accounts**: Accounts with no card role (column 4 blank) are DDA-only; "Request Plastic" button must not be present for them (`SearchableAddenda.feature` lines 83–95).
8. **Card Activation — Second Factor**: Valid card number + CVV must be followed by DOB or postal code validation before PIN can be set (`ActivateCard.feature`).
9. **Registration — SSN + DOB Required**: Registration flow collects SSN (`socialSecurityNumber`) and DOB for identity verification (`RegistrationPage.java`, `Registration.feature`).
10. **Change PIN — Card + DOB Required**: PIN change requires card number and date of birth verification before new PIN entry (`ChangePin.feature`).
11. **ACH Transfer Amount Mandatory**: Clicking Continue without entering a transfer amount displays an Error message (`BankTransfer.feature` — `@AChSendmoneyamountmandatory`).
12. **Password Complexity**: Password change validates that new and confirm passwords match (`ChangePassword.feature`).
13. **IdPassMe — Country Restriction**: Cards with READY status and a restricted recipient country route to a new KYC profile page (`Login.feature` in IdPassMe).
14. **Pagination Record Count**: UI records per page must equal the "Record Count" field value across all pages except the last (`SearchableAddendaSteps.java` lines 392–415).

## Business Flows

### ClientZone Login Flow
1. Navigate to `/login.jsp` on `q-na-app02.nam.wirecard.sys:9107` (legacy) or `clientzone-qa.mypaymentadmin.com` (modern).
2. Enter username → enter password → click "Log in."
3. Single-program users: redirect to `/messageHome.do`. Multi-program users: redirect to `/getDomains.do` → select program → redirect to `/messageHome.do`.

### SSO Login Flow
1. Navigate to `clientzone-qa.mypaymentadmin.com/sso.jsp`.
2. Enter Onbe email → click login → redirect to Microsoft identity provider → enter password → sign in → redirect to CZ at `/login/getDomains.do`.
3. Sign Out: click "Sign Out" link → redirect to SSO login page.

### Searchable Addenda — Customer Service Flow
1. Log in to ClientZone.
2. Select program from dropdown (e.g., `04014978`).
3. Select email OTP option → send code → submit OTP (15-second wait in test for OTP arrival).
4. Click "Customer Service" tab.
5. Select search-by field (memo/addenda type) → enter addenda value → click "Find."
6. Review paginated results; select payee.
7. Either: resend virtual link, or request plastic card with delivery method selection.

### MPV Card Activation
1. Click "Activate Your Card" on login page.
2. Enter card number + security code → Continue.
3. Enter DOB or postal code → Continue.
4. Set PIN + confirm PIN → Continue.
5. Success message → click Register → redirect to registration.

### MPV Bank Transfer (ACH)
1. Log in → navigate to `/banktransfer`.
2. Click "Send Money" → select Standard ACH or Express ACH.
3. Enter transfer amount → Continue.
4. Review confirmation screen (frequency, type, amount, fee, total) → "Confirm & Transfer."
5. Success message displayed.

## Compliance & Regulatory Concerns

1. **SSN Collection**: `RegistrationPage.java` collects Social Security Number via `input[name='socialSecurityNumber']`; `DataMapper.java` field `ssn = "987654321"`. SSN is stored in test data JSON in plaintext — a PII risk if the JSON file is committed to version control.
2. **Card Numbers in Test Data**: `mypaymentvault.json` contains 16-digit card numbers (e.g., `"5445446588231925"`, `"5445446583086258"` — BIN 544544) and CVV values (`"944"`, `"930"`) in plaintext. These appear to be test/QA cards, but storing CVV in source-controlled JSON violates PCI DSS Requirement 3.3 (SAD must not be stored post-authorization) if any value is live. These should be declared synthetic test data.
3. **DOB in Test Data**: `dob: "06-04-1985"`, `dobforactivation: "06041985"` stored in plaintext in JSON — regulated as PII under CCPA/GDPR.
4. **KYC Identity Verification**: IdPassMe module tests the identity verification path for cross-border disbursements; country-restriction logic tested for allowed vs. restricted recipients aligns with OFAC/sanctions screening requirements.
5. **Reg E / Error Disclosure**: `TransactionsPage.java` has an "In Case of Errors or" locator, confirming the Reg E error disclosure statement is present on the transactions page and is UI-tested.
6. **Terms & Conditions / Privacy Policy**: Features `TermsAndConditions.feature` and `PrivacyPolicy.feature` exist in the mypaymentvault module, confirming these disclosures are automation-covered.
7. **GLBA / Data Minimization**: Test data includes home phone, mobile phone, email, address, city, state, zip — full PII profile collected during registration. No masking or tokenization observed in the test data layer.

## Business Risks

1. **Stub-only Feature Files**: Seven of twelve ClientZone feature files (QuickPay, PaymentReversal, ManageInventory, InstantIssueAssign, InstantIssueLinktoPrimary, IssueVirtualCard, VirtualResendLink) contain only a login scenario and no actual business-flow steps. These business-critical payment operations are unvalidated by automation.
2. **Global Transfers / Manage Bank Commented Out**: `GlobalTransfers.feature` and `ManageBank.feature` are fully commented out, leaving IBAN cross-border transfers and bank account management untested.
3. **Hardcoded Credentials in Test Data**: `clientzone.json` contains `bhagyashree.bijagarni@onbe.com` with a plaintext password. If compromised, this provides access to the QA ClientZone environment.
4. **OTP Flow Dependency**: The SearchableAddenda flow uses a 15-second `Thread.sleep` to wait for an OTP email, creating an unreliable test that depends on email delivery timing rather than an automated OTP retrieval mechanism.
5. **Broken Assertion in SSO Test**: `SSLoginSteps.java` line 219 contains `assert(false)` unconditionally inside a conditional block, meaning the email length validation scenario will always fail regardless of actual behavior.
