# csa_WAPP — Business Analyst View

## 1. Business Purpose

**csa_WAPP** (Customer Service Application, Web Application) is the internal agent-facing portal used by Onbe/eCount customer-service representatives (CSRs) to service prepaid cardholders. It exposes the full lifecycle of a cardholder account — from search through resolution — to a tiered hierarchy of call-centre agents, risk analysts, programme managers, and operations staff. The application is the operational front-end that sits on top of the C-Base/ECount core prepaid processing platform.

`web.xml` line 6: `<description>Customer Service Application(CSA)</description>`

---

## 2. Business Capabilities

| Capability | Key Classes / Actions | Notes |
|---|---|---|
| Cardholder search | `SearchAction`, `SearchDisplayAction`, `SearchHelper` | Multi-attribute search (name, card, DDA, PUID) |
| Customer profile view/update | `CustomerProfileDisplayAction`, `CustomerProfileUpdateAction`, `MemberHelper` | Address, contact, status, security info, PUID, alerts, auth users |
| Account / card management | `AccountDisplayAction`, `AccountBalanceDisplayAction`, `ATMCashAccessAdjustmentUpdateAction` | Balance, block codes, lock/unlock, ATM OTB |
| Transaction history | `TransactionHistoryDisplayAction`, `AuthInquiryDisplayAction` | FDR ODS decode table wired in `csa.xml` lines 1177-1339 |
| Fund transfers | `ACHWithdrawalProcessAction`, `FundTransferHelper`, `AllotmentHelper`, `IEFTTransferManager` | ACH, allotments, credit-card push, cross-border (CBTS/Wirecard) |
| Fee management | `FeeReversalAction`, `FeeHelper`, `FeeReversalManager` | NSF fee, overlimit fee, reversal |
| Payment operations | `PaymentsDisplayAction`, `PaymentDetailDisplayAction`, `PaymentHelper`, `ClaimCodeHelper` | eCheck, OPUser, Claimable Choice (token-based) |
| Reversals & adjustments | `ReversalAction`, `ManagementAdjustmentAction`, `RiskFixedTransactionManager`, `RiskIndependentTransactionManager` | Risk, management, frontline chargeback |
| Plastic issuance | `PlasticIssuanceProcessAction`, `EmbossHelper` | Express/standard delivery scheduling |
| Check operations | `PreChecksProcessAction`, `CheckHelper`, `FraudQueueDisplayAction` | Pre-printed checks, fraud queue |
| Collections | `CollectionChargeOffAction`, `CollectionsChargeOff`, `FrontlineChargeback` | Charge-off, chargeback processing |
| KYC / CIP | `DisplayCIPAction`, `SubmitCIPAction` | Customer identification programme submission |
| CEMS (rebate) | `CEMSCreateProfile`, `CEMSUpdateProfile`, `CEMSProfileServiceImpl` | Rebate programme profile management |
| eCAP review | `EcapReviewDisplayAction`, `EcapReviewDetailDisplayAction` | Electronic card activation processing |
| Risk ACH review | `AggregateACHDisplayAction`, `IndividualACHDisplayAction`, `ProgramACHDisplayAction` | Velocity review queues |
| Escalation queue | `EscalationQueueDispalyAction`, `CommentEscalationProcessAction` | Agent-to-supervisor escalation |
| CTI / telephony | `RingCentralRequest`, `CTIInterfaceStartAction`, `CTIAgentAuthEventProcess` | RingCentral integration for auto-login |
| Manage CSA users | `CSAUserCreateAction`, `CSAUserUpdateAction`, `ManagePeopleHelper` | Role-based CSR lifecycle management |
| ATM network management | `AddNewATMProcessAction`, `ManageATMHelper` | ATM whitelist admin |
| Sanctions field control | `SanctionFieldHelper`, `SanctionFieldStateDaoImpl` | OFAC-flagged account field disabling |
| Comment & note management | `CommentHelper`, `CommentProcessAction`, `CommentEscalationProcessAction` | Free-text notes, escalation thread |

---

## 3. Business Entities

| Entity | Representation | Stored in |
|---|---|---|
| Cardholder (member) | `ICustomer`, `CSAMemberDetail` VO, `EMember` proxy | C-Base / ECount Core (remote call) |
| Card (device) | `IDevice`, `EcardDevice`, `OperatorDevice` | ECount Core DB (`EcountCoreDataSource`) |
| Account balance | `BalanceVO`, `BalanceCalculationVO` | Remote / cached in `Hashtable` beans |
| Transaction / journal | `AccountJournalVO`, `ReversibleTransaction`, `TransactionInformation` | FDR ODS via ECount Core |
| Claimable Choice | `ClaimableChoice`, `ClaimablePayment`, `ClaimableChoiceDAOImpl` | `app_profile_program_claimable_choice`, `claimable_payment` (EcountCore DB) |
| Claim code | `ClaimCodeIssuanceInfo`, `ClaimCodeRedemptionInfo` | `claim_code_issuance_info`, `claim_code_redemption_info` (EcountCore DB) |
| CSA Operator | `Operator`, `CSAUser`, `CSAUserDetails` | `CbaseappDataSource` (SQL Server) |
| Fee | `ReversibleFeeDefinition`, `CustomerFeeValueVO` | C-Base stored procs |
| ACH bank account | `ACHBankDetailsVO`, `ACHDetailsVO` | EcountCore stored procs |
| CEMS Profile | `CEMSProfile`, `CEMSComment`, `CEMSUser` | CbaseappDataSource |
| Escalation | `CommentEscalationVO`, `EscalationAssigneeVO` | CbaseappDataSource |
| Audit session/event | `AuditSession`, `AuditEvent` | CbaseappDataSource (`audit_session`, `audit_event` tables) |
| Sanction field state | `SanctionFieldStateDaoImpl` | CbaseappDataSource |

---

## 4. Business Rules

| Rule | Evidence |
|---|---|
| Role-gated URLs | `applicationContext-xsecurity-web.xml` lines 191-205: 20+ named CSR roles protect all `.do` endpoints |
| Card number masking varies by role | `CardMaskUtils` (lines 20-105): `maskThisCC`, `maskTheCC`, `maskThefirst12NumbersCC`, `getLast4NumbersCC` |
| SSN handled as split 3-part object | `SocialSecurityNumberVO` — area, group, serial — never stored whole in session |
| SSN audited in plain text in audit config | `audit.properties` line 48: `submitCIP.state=firstName,lastName,dob,SSN.SSNAreaNumber,...` — **risk item** |
| ACH scheduling: min 5 days, max 90 days start date | `csa.xml` lines 692-733 (`distACHCalendar`) |
| Express plastic delivery time varies by day-of-week | `csa.xml` `expressPlasticTimeFrame` bean (lines 899-1011) |
| Federal holiday exclusion list hardcoded (2006) | `csa.xml` `federalHolidays` bean (lines 1127-1174) — **stale, risk item** |
| Balance transfer programs require card-type validation | `CardHolderProgramValidator`, injected via `csa.xml` line 397 |
| Frontline transaction filter governs chargeback eligibility | `FrontlineTransactionFilter`, wired at `csa.xml` line 1449 |
| Sanctioned accounts disable specific UI fields | `SanctionFieldHelper.isDisable()` checks `accountSanctioned` request attribute |
| Claimable Choice min-threshold per modality enforced | `ClaimableChoiceDAOImpl` retrieves per-program thresholds for virtual, prepaid, ACH, check, PayPal, Venmo, FX |
| Password stored as MD5 (one-way) | `CSAUserCryptUtility.createMD5Hash()` using `qpl.util.MD5` — **weak, risk item** |
| Velocity check for risk monetary adjustments | `TransactionLimitByBusinessUnitQuery`, `RiskIndependentTransactionManager` |

---

## 5. Business Flows

### 5a. Standard Cardholder Service Flow
1. CSR logs in → `OperatorAuthenticationProcessingFilter.onSuccessfulAuthentication()` populates role/operator in session.
2. CSR searches → `SearchAction` / `SearchHelper` → `EMember.find()` (secured by AOP proxy, `applicationContext-xsecurity-web.xml` line 358).
3. `CustomerProfileDisplayAction` → `MemberHelper` → C-Base core → displays cardholder profile tabs.
4. CSR performs action (e.g. balance change) → corresponding `*Action.executeImpl()` → `DeviceHelper` or `PaymentHelper` → C-Base transfer/fee manager.
5. `AuditManagerImpl` (wired in `csa.xml` line 469) records pre/post state to audit tables.
6. JSP tiles render results via Struts 1 `action-servlet.xml` / `tiles-defs.xml`.

### 5b. Claimable Choice Flow (token payments)
1. `PaymentHelper` retrieves `ClaimablePayment` list via `ClaimablePaymentDAOImpl`.
2. Agent views payment details including issuance address from `ClaimableChoiceDetailsRetrieveDao` (SQL: `claim_code_issuance_info`).
3. Agent views redemption address from `ClaimCodeRedemptionInfoRetrieveDao` (SQL: `claim_code_redemption_info`).
4. Cancellation reverses via `ClaimableChoiceCancelAdjustment` (credit + debit transfers).

### 5c. CTI Auto-Login (RingCentral)
`RingCentralRequest` (path `/loginctl`) clears session, extracts `username`/`password`/`NA_Card_no` from request, forwards to `/j_acegi_security_check`, and places `cardHolderAuthentication` in session for auto-search.

---

## 6. Compliance Relevance

| Obligation | Evidence |
|---|---|
| PCI DSS — PAN masking | `CardMaskUtils.maskTheCC()` (first 4 + last 4 exposed by default); role-based full/masked display |
| PCI DSS — Audit logging | `AuditManagerImpl` persists pre/post state for all monetary actions; `audit.properties` declares 20 audited event types |
| OFAC Sanctions | `SanctionFieldHelper` / `SanctionFieldStateDaoImpl` disables edit fields when `accountSanctioned=true` |
| KYC / BSA | `DisplayCIPAction`, `SubmitCIPAction` — CIP (Customer Identification Programme) submission to core |
| Reg E — Dispute / chargeback | `FrontlineChargeBackProcessAction`, `FrontlineChargeback`, `CollectionsChargeOff` |
| GLBA / data minimisation | SSN decomposed into three parts; card numbers masked client-side except last 4 for most roles |

---

## 7. Business Risks

| Risk | Severity | Evidence |
|---|---|---|
| MD5 password hashing for CSA user accounts | High | `CSAUserCryptUtility.createMD5Hash()` — MD5 is cryptographically broken |
| SSN components written to audit log | High | `audit.properties` line 48 includes `SSN.SSNAreaNumber`, `SSN.SSNGroupNumber`, `SSN.SSNSerialNumber` in audit state |
| Federal holiday list frozen at 2006 | Medium | `csa.xml` `distACHCalendar` line 714 hardcodes 2006 dates; actual ACH scheduling may be off |
| Live-chat secret key / IV key in Spring context | High | `csa.xml` beans `liveChatSecretKey`, `liveChatIvKey` loaded from property file; key material in application config |
| Struts 1 (EOL framework) | High | `pom.xml` dependency `struts-core:1.3.10` — last release 2013; no security patches available |
| Spring 2.0.8 (EOL) | High | `pom.xml` `spring.version=2.0.8` — extremely outdated |
| Acegi Security (pre-Spring Security) | High | `applicationContext-xsecurity-web.xml` references `org.acegisecurity.*` — replaced by Spring Security 3+ |
| `ROLE_ANONYMOUS` allowed for CTI start | Medium | `objectDefinitionSource` line 189 `ctistart.do=ROLE_ANONYMOUS` — unauthenticated access |
| `forceHttps=false` on auth entry point | High | `applicationContext-xsecurity-web.xml` line 108 — credentials can travel over plain HTTP |
| `testFailureIgnore=true` in Maven Surefire | Medium | `pom.xml` line 169 — test failures silently swallowed in CI |
