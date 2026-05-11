# clientzone_WAPP — Business Analyst View

## Business Purpose

ClientZone is a B2B web portal that enables corporate client users (program sponsors and their designated administrators) to manage prepaid card programs on behalf of Onbe (formerly North Lane Technologies / ECount). The `display-name` in `web.xml` reads "North Lane Technologies ClientZone", confirming the legacy origin. It is the primary self-service interface for issuers and corporate administrators to enroll cardholders, disburse funds, manage inventory, perform customer service, and administer users — across multiple fulfillment rails (physical card, virtual card, instant issue) and multiple geographies.

The SCM URL `scm:git:ssh://git@github.com/OnbeEast/clientzone_WAPP.git` confirms the repository is under the OnbeEast GitHub organisation.

---

## Business Capabilities

The following capabilities are directly evidenced by source code and configuration:

| Capability | Evidence |
|---|---|
| New cardholder enrollment | `ClientZoneConstants.Application.NewCardholder`, `NewCardholderSystemAvailability` bean, `_infoName.jsp`, `_infoAddress*.jsp`, `_infoSSN.jsp`, `_infoBirthDate.jsp` JSPs |
| Fund loading / QuickPay | `QuickPayHelper.java`, `ClientZoneConstants.Application.QuickPay`, URL `/home.do?orderType=Quickpay` in `RoleUtil` |
| Order management (file-based & instant) | `OrderHelper.java`, `OrderServiceWebAdapterImpl.java`, `OrderHistoryHelper.java`, `bulkLoad` & `bulkLoadStatus` beans in `applicationContext.xml` |
| Instant issue card assignment | `InstantIssueHelper.java`, `InstIssueCZSetupScreenCfgManagerRequestHelper.java`, `PreChecksHelperImpl.java`, `VirtualExpressIssueAction` bean, JSPs under `instantIssue/` |
| Balance debit / sweep | `CardBalanceDebitAction.java`, `CardBalanceDebitHistoryAction.java`, `BalanceSweepImpl.java`, `ICardBalanceDebit.java`, `IDebitHelper.java`, `DebitAPIController.java` |
| Payment reversal | `PaymentReversalHelper.java`, JSPs `reversePayementReview.jsp`, `_reviewReversePayments.jsp` |
| Cardholder search and update | `CardholderSearch.java`, `UpdateCardholder.java`, `SearchCardholderAdministration.java`, `CustomerServiceAction.java` |
| User administration | `UserAdministrationDisplayAction.java`, `UserAdministrationProcessAction.java`, JSPs under `usermanagement/` (add, delete, reset password, find) |
| Program administration | `ProgramAdministrationDisplayAction.java`, `ProgramAdministrationProcessAction.java` |
| Inventory management | `InventoryManagementAction.java`, `InventoryManagementTrackListAction.java` |
| Security / MFA / OTP | `SecurityMainAction.java`, `OTPHelpr.java`, `OtpServiceClient.java`, `SharedServiceConnector.java`, JSPs under `security/mfa/` |
| SSO login | `SsoConfiguration` bean in `applicationContext.xml`, `SsoAuthenticationProcessingFilter`, `SsoUserUtil.java` |
| eDelivery (electronic statement) | `EdeliveryResponseUpdateDAO.java`, `EdeliveryResponseUpdateStatus.java`, `eDeliveryDTO` / `eDeliveryCustomerDTO` beans (Adobe IDP integration) |
| Help / searchable addenda | `ProxyHelpAction.java`, `SearchableAddendaServiceClient.java`, `SearchabaleAddendaHelper.java`, content-mapping properties for en_US, es_ES, pt_BR, en_GB |
| Reporting / file download | `DownloadInstantIssueBulkReplyAction`, `GenerateSweepOrderDetailsFileAction`, `ReportManagerRquestHelper.java` |
| Comment/audit trail | `CommentHelper.java`, `AuditInfo.java`, `security-audit-common` dependency |
| CAPTCHA (anti-bot) | `SimpleCaptchaServlet`, `AudioCaptchaServlet`, `displayJcaptchaFlag` bean, `reCaptchaService` bean (Google reCAPTCHA v3) |

---

## Business Entities

All located in `src/main/java/com/cbase/business/common/`:

| Entity | Class | Key Fields |
|---|---|---|
| Cardholder | `CardHolderInfo.java` | Aggregates `MemberInfo`, `CardInfo`, `NameInfo`, `AddressInfo`, `PaymentInfo`, `PhoneInfo`, `EmailInfo`, `PatriotActInfo`, `PuidInfo`, `ProgramInfo` |
| Card | `CardInfo.java` | `cardNumber`, `cardNumberDisplay`, `ecountId`, `cardStatus`, `cardType`, `expMonth/Year`, `quickPayAllowed`, `privateLabelCardNumber` |
| Patriot Act (KYC) | `PatriotActInfo.java` | `socialSecurityNumber` (split into area/group/serial), `birthDate`, `birthDay/Month/Year` |
| Order | `OrderInfo.java`, `OrderItems.java`, `SubFileOrdersInfo.java` | Order header and line items |
| Payment | `PaymentInfo.java`, `PaymentReversalInfo.java`, `LastPaymentInfo.java` | Funding details, reversal metadata |
| Member / Account | `MemberInfo.java`, `AccountInfo.java` | Core member/account identifiers |
| Program | `ProgramInfo.java`, `ProgramSupportInfo.java` | Program config, support details |
| Promotion | `PromotionInfo.java` | Promotion selection |
| PUID | `PuidInfo.java` | Partner user identifier |
| Address | `AddressInfo.java` | Up to 4 address lines, city, state, country, postal |
| Companion Card | `CompanionCardInfo.java` | Companion card assignment data |
| Instant Issue Card | `InstantIssueCardInfo.java`, `InstantIssueCardDetailDTO.java` | Instant issue device details |
| Audit | `AuditInfo.java` | `userLocationID`, event, eventStatus, user message, firstName, lastName, cardholderID, amount |
| Access Level | `AccessLevelInfo.java` | Role/access configuration |
| Deposit | `DepositInfoDTO.java` | Deposit information for initial funding |

---

## Business Rules & Validations

Evidence from source files:

1. **Password policy v1 vs v2** — `ClientZoneConstants.Application.PASSWORD_POLICY_V1/V2`; v1 = 8–20 chars, v2 = 12–64 chars, requiring 3 of 4 character types. Implemented in `ClientZonePasswordUtil.java` (`isValid()`, `generate()`). JIRA reference: INIT-2061.

2. **Card number masking** — `MaskHelper.maskCreditCardNumber()` implements display masking; two modes: pattern mode (last 4 only) and standard mode (last 8 unmasked). Bank account masking shows only last 4 digits. Check account masking shows last 4 digits.

3. **Session offset** — `sessionOffsetValue` = 180 seconds (3 minutes) is configured in `web.xml`.

4. **New cardholder system availability window** — `NewCardholderSystemAvailability` bean: unavailable 17:00–19:30 America/New_York.

5. **Debit transaction limits** — `DebitAPIController.handleException()` maps `ServiceFailureException` types including `AMOUNT_LESS_THAN_MIN_ALLOWED_PER_TRAN`, `AMOUNT_EXCEEDS_MAX_ALLOWED_PER_TRAN`, `AMOUNT_EXCEEDS_MAX_ALLOWED_PER_DAY`, `AMOUNT_EXCEEDS_MAX_ALLOWED_PER_MONTH`, `NUMBER_OF_TRANSACTIONS_EXCEEDS_MAX_ALLOWED_PER_DAY/MONTH`.

6. **Force HTTPS** — `SSLLoginFilter` redirects HTTP to HTTPS (configured `check=on`), with localhost/127.0.0.1 exempt.

7. **DoS protection** — `PreventDoSFilter` rate-limits requests; `urlHitTimeInterval` bean configures the time window. `RequestURLParaFilter` limits URL parameter length via `clientzone.requestParaLength.limit`.

8. **Terms of use** — `CheckTermsOfUseFilter` forces acceptance before access.

9. **Forced password change** — `ForcedPasswordFilter` redirects to `/profile/updatePassword/process.do` when password reset is required.

10. **CAPTCHA** — Google reCAPTCHA v3 required at login, SSO, forgot-password, forgot-username flows (constants in `ClientZoneConstants.ReCaptcha`).

11. **SSN validation** — `PatriotActInfo.setSocialSecurityNumber()` parses and validates the 3-2-4 SSN format (area-group-serial).

12. **Restricted email domains** — `restrictedEmailSuffix` bean controls which email domains are blocked for self-registration.

13. **Role-based UI routing** — `RoleUtil.checkRoleType()` enforces post-login redirects based on role: `ROLE_SHOW_DASHBOARD`, `NEW_CARDHOLDER`, `QUICK_PAY`, `SUBMIT_FILE`, `INSTANT_ISSUE_*`, `ROLE_PAY_REVERSAL_MAKER/VIEW`, `ROLE_FILE_CHECKER_ROLE`, `ROLE_INVENTORY_VIEW`, `PRECHECK_VIEW`, etc.

---

## Business Flows

**Cardholder Enrollment:**
Login → Terms of Use acceptance → Role check → New Cardholder order form (name, address, SSN/DOB via `PatriotActInfo`, payment, email, phone) → Pre-check validation (inventory, catalog, branch account via `PreChecksHelperImpl`) → Order submission via `OrderServiceWebAdapter` → Confirmation.

**Instant Issue / Virtual Express:**
Select program/promotion → Assign or find card via `InstantIssueHelper` → Load funds via `AccountManagementAPIHelper.createVirtualExpressAccount()` (calls `CreateAccountService`) → eDelivery notification (Adobe IDP SOAP call via `InstantIssueHelper`).

**Balance Debit / Sweep:**
Search cardholder by card/PUID → Select debit type (full or partial) → `BeginDebitHelper` → Review → `CommitDebitHelper` or `CancelDebitHelper` → Status tracked via `DebitStatusType` enum.

**Payment Reversal:**
Customer service search → locate transaction → `PaymentReversalHelper` → Maker/Checker approval workflow (`ROLE_PAY_REVERSAL_MAKER` submits, another reviews).

**User Management:**
Admin finds user (`GetUsersFilterAction`) → Create/update via `PrepareSetUserAction` / `SetUserAction` → Password reset (`reset_users_password.jsp`) → Temporary password generated by `ClientZonePasswordUtil`.

**SSO Login:**
`SsoRedirectFilter` → Azure AD B2C OIDC flow (MSAL4J `ConfidentialClientApplication`) → `SsoAuthenticationProcessingFilter` → session creation → post-login director.

---

## Compliance & Regulatory Concerns

1. **USA PATRIOT Act (KYC / CIP)** — `PatriotActInfo.java` collects full SSN (area/group/serial) and date of birth at enrollment. `PatriotActInfoHelper.java` supports this flow. This is a Customer Identification Program (CIP) data collection mechanism.

2. **PCI DSS** — `CardInfo` holds raw `cardNumber` alongside a `cardNumberDisplay` for masking. `MaskHelper.maskCreditCardNumber()` provides display masking. However, PANs transit through session state (`CardHolderInfo` is `Serializable`), raising questions about scope of the CDE. The `EncryptionUtil` uses AES (no IV specified — ECB mode risk — see Technical Debt section).

3. **Reg E** — Payment reversal workflow and dispute-handling support (`PaymentReversalHelper`, `_reviewReversePayments.jsp`) directly relate to Reg E error resolution obligations.

4. **GLBA / Data Privacy** — SSN, date of birth, full name, address, email, phone are collected and stored. No field-level encryption is visible in the data model DTOs; protection relies on application-layer masking and transport-layer TLS.

5. **OFAC / AML** — No direct OFAC screening code is visible in this repository; screening is presumably delegated to back-end services. The `xSecurity` dependency and `userManagement` bean contain user credentialing logic.

6. **Multi-locale / International** — Properties files exist for `en_US`, `es_ES`, `pt_BR`, `en_GB`. Locale-specific content mappings at `src/main/resources/com/ecount/clientzonehelp/contentmapping_*.properties` suggest international cardholder populations. `country_isd_codes.properties` and `country_codes.properties` are present.

---

## Business Risks

1. **SSN in session state** — `PatriotActInfo` (with full SSN) is embedded in `CardHolderInfo` which is `Serializable` and stored in the HTTP session. A session serialization/deserialization vulnerability or session fixation could expose SSNs.

2. **New cardholder blackout window** — Hard-coded 17:00–19:30 ET unavailability in `NewCardholderSystemAvailability` is a static bean. Any batch processing window changes require a code/config deploy.

3. **MFA filter commented out** — The `MultiFactorAuthenticationFilter` in `web.xml` and the corresponding `localMultiFactorAuthenticationFilter` bean in `applicationContext-xsecurity-web.xml` are entirely commented out. MFA enforcement for certain flows may be absent, increasing account takeover risk.

4. **Dependency on Adobe IDP SOAP service** — `InstantIssueHelper` calls `EDeliveryIDCInterfaceSoapBindingImpl` (Adobe LiveCycle). SOAP-based integrations are brittle and represent a migration target risk.

5. **Role complexity** — `RoleUtil.checkRoleType()` contains deeply nested, imperative role-checking logic with no unit tests directly visible. Misconfiguration could inadvertently grant or deny access.
