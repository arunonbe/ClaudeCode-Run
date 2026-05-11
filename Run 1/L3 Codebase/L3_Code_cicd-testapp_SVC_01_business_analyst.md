# cicd-testapp_SVC — Business Analyst View

## Business Purpose

`cicd-testapp_SVC` (artifact ID `cicd-testapp`, group `com.ecount.service.core`, version `2.0.0-SNAPSHOT`) is the **EcountCore** platform — a prepaid card and multi-rail payments back-end originally built under the Northlane/Wirecard/Citi Prepaid brand lineage. It exposes card lifecycle management, ACH/IEFT transfers, member registry, check (PreCheck) management, FDR (First Data Resources) debit card processing, and KYC screening as a shared service consumed by multiple downstream clients. The SCM URL (`gitlab.com/northlane/development/...ecount-core`) and artifact parentage (`com.citi.prepaid.service`) confirm the Citi Prepaid → Northlane → Onbe heritage.

## Business Capabilities

| Capability | Key Interface / Class | Notes |
|---|---|---|
| **Card (eCard) device lifecycle** | `IDeviceService`, `EDeviceJDBCDAO` | Create, inquiry, update, control, catalog inquiry for prepaid eCards |
| **Member (cardholder) management** | `IMemberService` | Add basic/extended/universal registration; KYC check; SSN/DOB via StrongBox |
| **Fund transfers** | `ITransferService` | Begin, commit, cancel, cancel-on-demand, quick-load, fee inquiry |
| **ACH device management** | `IACHDeviceDAO`, `ACHDeviceDAO` | ACH bank validate, account verify, transaction create/inquiry (US and Canada paths) |
| **IEFT transfers** | `IIEFTDeviceDAO`, `IEFTDeviceDAO` | Create, commit, cancel, cancel-on-demand, inquiry |
| **FDR debit card processing** | `FDRDebitServices`, `IFDRODSDAO` | Full debit card lifecycle via FDR ODS: activation, balance, PIN, plastic issuance, EMV chip |
| **Check management (PreCheck)** | `IManageService` | Check order, stop-payment, PreCheck assign/authorize/verify, DDA available auth |
| **Audit trail** | `IAuditActivityDAO`, `EAuditActivityDAO` | Activity journal insert with addenda |
| **KYC / sanctions screening** | `KYCLibrary` (in `KYCService.xml`) | Actimize MQ integration; `doKYCCheck` on `IMemberService` |
| **StrongBox encryption** | `IStrongBoxService` | Encrypt/decrypt sensitive member PII (SSN, DOB) via database-backed repository |
| **Fulfillment / emboss** | `IFulfillmentLibrary`, `IFDROfflineEmbossLibrary` | Card emboss queue, plastic request, issuance tracking |
| **Country regulation profile** | `ICountryRegulationProfileCheckLibrary` | Country-specific regulatory checks for US, Canada, Mexico (`CountryCodes.java`) |
| **Event service** | `IEventService` | Event-driven notifications (`NotificationEvents` enum) |

## Business Entities

- **Member**: cardholder identity (basic and extended registration, secure profile linked via StrongBox reference). `IMemberService.addBasic/addExtended/addUniversalRegistration`.
- **Device / Account**: a payment instrument attached to a member — types: eCard, eCheck, CreditCard, DDA, ACH, Plastic, IEFT, Operator (`DeviceTypes.java`).
- **Transfer**: a financial movement between accounts; lifecycle states tracked via `TransactionStates` enum.
- **ACH Transaction**: US/Canada ACH payment with status states in `ACHStatus` enum (ok, no-verification, pending-verification, failed-verification).
- **IEFT Transaction**: Canadian Interac EFT with cancel, commit, cancel-on-demand operations.
- **PreCheck / Check**: physical check-book and pre-authorized check products with catalogs, books, stop-payment, and merchant-verify flows.
- **Audit Activity Journal**: immutable activity record (insert only) via `CoreActivityJournalInsert` stored procedure.
- **Secure User Profile**: SSN, DOB, and other PII stored encrypted through `IStrongBoxService`; referenced by an opaque string key in member records.
- **Emboss Profile**: card personalization and physical plastic delivery tracking.

## Business Rules & Validations

- **Block codes** govern device eligibility (`BlockCodes.java`): active, closed, suspended, batch-initialized, stop-payment, pending-expiration, reissue-on-transaction/inquiry, no-authorizations, returned-plastic, pending/failed-verification, pending-activation, activation-rejected.
- **KYC status** (`MemberKYCStatus.java`): Unknown → Pass/Pending/Fail; failure prevents device creation or triggers manual review.
- **ACH verification** (`ACHStatus.java`): device must reach `ok` or `no-verification` before funds movement; `pending-verification` and `failed-verification` block ACH transactions.
- **Activation codes** (`ActivationCodes` enum) and **PIN selection codes** (`PinSelectionCodes`) control debit card activation pathways on FDR ODS.
- **Country-specific regulation checks** (`ICountryRegulationProfileCheckLibrary`) enforce identity params per `CountryRegulationIdentificationParams` for US, CA, MX.
- **Pre-Check authorization** requires merchant verify step before authorization amount settlement.
- **SQL timeout manager** (`SqlTimeoutManager` in `DataSources.xml`) sets 40-second timeout for all stored procedure calls; no-rollback exceptions for `DataExceptionReturnCode` and `CoreException`.
- **JMS retry policy** (`MQJMSImp.java` lines 36–38): 3 retries with 2-second sleep; 10-second window to distinguish MQ failover from timeout.

## Business Flows

1. **New cardholder onboarding**: `addExtended` → creates member with extended registration → optionally attaches secure profile (SSN/DOB written to StrongBox) → `create` device (eCard) → `CoreDeviceCreateECard` stored procedure → FDR ODS `newAccount` → plastic issuance via `issuePlastic`.
2. **Fund transfer (load/spend)**: `begin` transfer → `commit` or `cancel`; `quickLoad` for single-step load.
3. **ACH payment**: ACH bank validate (`AchBankValidate`) → ACH transaction create (`AchTransactionCreate`) → status poll via `AchTransactionInquiry`.
4. **KYC screening**: `doKYCCheck` → `KYCLibrary` sends SOAP message via Actimize MQ queue (`jms/ActimizeRequestQ`) → result updates member KYC status.
5. **Debit card lifecycle (FDR)**: all updates pass through FDR ODS JMS queues (`jms/FDRRequestQueue` / `jms/FDRReplyQueue`); ~30+ distinct operation types handled by individual procedure beans in `FDRDebitServices.xml`.
6. **Audit trail**: every service call posts to `CoreActivityJournalInsert` with addenda via `EAuditActivityDAO`.

## Compliance & Regulatory Concerns

- **PCI DSS**: PIN handling via `PinSelectionCodes`, `PinAssignmentMethods`, `GeneratePinChangeRefId`, `SetPinId`, `SetEMVPinId`; card numbers flow through FDR ODS JMS; StrongBox encrypts member PII but PAN handling is implicit in FDR ODS calls. No evidence of at-rest PAN tokenisation within this codebase — FDR ODS is the CDE boundary.
- **NACHA / Reg E**: full ACH device create/void/review-queue lifecycle supports NACHA return management; `ACHTxReviewQueueUpdate` implements review-queue disposition for disputed transactions.
- **KYC / AML**: Actimize integration (`actimizeMQJMSImp`, `KYCService.xml`) for real-time sanctions screening; `MemberKYCStatus` values support AML disposition tracking.
- **GLBA / State privacy**: SecureUserProfile (SSN, DOB) stored via StrongBox (`StrongBoxService.xml`, `StrongBoxJDBCDAOImpl`) — encrypted at database level. No field-level masking observed in log statements (see `MQJMSImp.java` line 72: full request string logged).
- **Country regulatory**: `ICountryRegulationProfileCheckLibrary` and `CountryRegulationIdentificationParams` support multi-jurisdiction identity requirements (US/CA/MX).
- **OFAC**: Actimize integration suggests OFAC screening capability, but screening result disposition logic is in upstream consumer code not visible here.

## Business Risks

1. **Request/response full content logged**: `MQJMSImp.java` line 72 logs the full `requestStr` at INFO level — this may include card numbers or account data depending on caller, creating a PCI DSS log-data risk.
2. **SNAPSHOT dependency in production pipeline**: `version 2.0.0-SNAPSHOT` and dependent SNAPSHOTs (`springutils 2.0.0-SNAPSHOT`, `config-server-client 2.0.0-SNAPSHOT`) indicate non-release builds may be deployed.
3. **Spring 5 upgrade blocked**: comment in `pom.xml` line 76 explicitly documents that Spring 5 upgrade is stalled due to multiple incompatibilities (KYCService.xml, web.xml, Configuration.xml). Application is pinned to Spring 4.3.27 (EOL).
4. **Tests skipped in CI**: both Jenkinsfile and `.gitlab-ci.yml` set `-Dmaven.test.skip=true` for build and deploy phases, meaning unit tests do not gate deployment.
5. **No authentication/authorisation on REST endpoints**: `DeviceController`, `MemberController`, `TransferController` carry no `@PreAuthorize` or Spring Security annotations — caller authentication is expected from the container layer (Tomcat JNDI) but is not verified in code.
6. **Manual JMX state-map reload**: `reloadStateMap` bean exposed via JMX (`prepaid:name=StateMap`) — stale state data during reload window could affect Mexican state code mapping on plastics.
