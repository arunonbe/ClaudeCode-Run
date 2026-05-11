# bmcwizard_WAPP — Business Analyst View

## Business Purpose

bmcwizard_WAPP (artifact ID: `wizard`, WAR name: `wizard.war`) is the **Program Configuration Wizard** — a back-office web application used by Onbe/ecount operations staff and client administrators to create, configure, and launch prepaid card and payment programs. It provides a guided, step-by-step interface for setting up all parameters that govern how a program behaves in the prepaid card processing platform. The application is described in `web.xml` as providing "access to tools for managing Program configuration and bulk processing management for Ecount, Inc."

## Business Capabilities

The following discrete configuration domains are directly evidenced in the source code:

| Capability | Key Implementation Classes |
|---|---|
| Program Dashboard / Program search | `ProgramDashBoardImpl`, `ProgramIdSearch` |
| Program Profile setup (branding, labels, access levels) | `ProgramProfileImpl`, `ProgramProfileConfigurationHelper`, `ProgramProfileFeatureHelper` |
| Card Settings (card platform, expiry, PIN, EMV, contactless, EMEA profiles) | `CardSettingsImpl`, `CardSettingsConfigurationHelper`, `CardSettingsDefaultHelper` |
| Fees configuration (fee structures, tiers, grace/credit periods, dormancy) | `FeesImpl`, `FeesGracePeriodHelper`, `FeesCreditPeriodHelper`, `FeesFeeDetailsHelper`, `FeesSymbolTimePeriodHelper` |
| Fee Credit Groups | `FeeCreditGroupsImpl` |
| Funding Controls (DD load limits, ACH, precheck, payment reversal, balance sweep) | `FundingControlImpl`, `FundingControlConfigurationHelper`, `BalanceSweepHelper` |
| Embossing Profile (card carrier, delivery, plastic type, TPIN, location codes) | `EmbossingProfileImpl`, `EmbossingProfileHelper` |
| Escheatment Configuration (state-level dormancy, waiting period, balance threshold) | `EscheatmentConfigImpl` |
| Global Regulatory Limits (AGML, Card Balance Limit, Load Monetary Limit) | `GlobalRegulatoryLimitImpl` |
| Promotion Settings | `PromotionSettingImpl`, `PromotionManagementHelper`, `PromotionACHOUTHelper`, `PromotionAllotmentHelper` |
| Configuration screen (access check, ACH, addenda, alerts, available cash, account maintenance) | `ConfigurationImpl`, `ConfigurationHelper`, `AccessCheckHelper`, `AccessCheckFraudControlHelper`, `ACHDetailsHelper`, `AlertSettingsHelper`, `AccountMaintenanceHelper`, `AddendaConfigurationHelper` |
| User / Role management | `UserRoleSettingImpl`, `CZRoleSetupImpl`, `CZAddRoleHelper` |
| CZ (client-zone) Setup — hierarchy, inventory control, instant issue, user setup, reports | `CZConfigurationImpl`, `CZProgramProfileImpl`, `CZInventoryControlImpl`, `InstantIssueImpl`, `UserSetupImpl`, `HierarchyImpl` |
| MPV / OP Setup (fees, graphics, terms & conditions, content approvers) | `OPSetupFeesDAO`, `OPSetupTCDAO`, `GraphicsDAO`, `GrAutomationDAO`, `ContentApproverDao` |
| Notification setup (email templates, SMS events, global/program-level configuration) | `NotificationHelper`, `NotificationDataDAO`, `SMSNotificationDataDAO` |
| Enrollment Setup | `EnrollmentSetupImpl` |
| PGP key management for programs | `HttpCryptoServiceHelper` (add/remove/list PGP keys on crypto servers) |
| Program Launch (status, summary display, defaults highlighting) | `LaunchProgramImpl` |
| Audit Trail | `AuditTrailImpl`, `AuditTrailDAO`, `AuditTrailStoredProc` |
| Bulk Location | `BulkLocationImpl` |
| Global VAT Settings | `GlobalVATSettingsImpl` |
| Risk Rules | `RiskRuleImpl` |
| CSA (Corporate Spending Account) Partner Setup | `PartnerDetailInfoImpl` |
| Claimable Choice Setup | `ClaimableChoiceSetUpImpl` |
| Enrollment Setup | `EnrollmentSetupImpl` |
| eCap (Electronic Card Activation Platform) emboss messages and financial info | `EcapSetupHelper`, `EcapSetupDAOImpl` |
| Program Relationship management | `ProgramRelationshipDAO`, `PromotionRelationshipDAO` |
| Billing Parameters | `BillingParamsDAO` |
| Card Package Sequence | `CardPackageSequenceDAO` |

## Business Entities

Derived from DAO, DataBean, and business implementation class names:

- **Program** — the core entity; identified by `programId` (8-character string). Has a type (domestic/EMEA), status (LAUNCH, LAUNCH_EDITED), and multi-dimensional configuration profiles.
- **Promotion** — a sub-configuration of a program (`BatchPromotion`, `BatchPromotionSpin`). Programs have a "spin zero" default promotion.
- **Affiliate** — the branding/skinning unit; managed via `AffiliateService` with locale, skin templates, and CSA (B2C) detail screens.
- **Access Level** — card delivery and configuration variant within a program (`ProgramAccessLevelProfile`).
- **Fee Structure** — tiered fee definitions with triggers, payees, tiers, amounts, and percentages.
- **Role / Group** — Workbench user roles with permission sets; managed via `WorkBenchGroup`, `WorkBenchUser`.
- **Card Profile** — `FDRCardProfile` (domestic), `FDRDDAProfile` (DDA), `EMEAProfile` (international).
- **Escheatment Rule** — per-state dormancy rules with balance thresholds and waiting periods.
- **Regulatory Limit** — AGML (aggregate monetary), CBL (card balance), LML (load monetary) with country/currency dimensions.
- **Embossing Profile** — plastic type, location/delivery codes, TPIN width.
- **Notification Template** — email and SMS event-trigger templates, global and program-scoped.
- **Hierarchy Node** — CZ setup tree of organizational units (`HierarchyTree`, `HierarchyTreeNode`).

## Business Rules & Validations

Evidence from source:

1. **Program ID must be 8 characters** — `ProfileAuditor.validateDBSave()` line 32: `programId.length() != 8` triggers error log.
2. **Chip Program ID padding** — `LaunchProgramImpl.getChipProgramId()` pads numeric chip IDs to 8 digits (lines 965–980).
3. **Program status lifecycle** — Programs transition through `LAUNCH` → `LAUNCH_EDITED` statuses (`BridgeGlobalConstants.ProgramStatus`). Only after launch can edit status be set.
4. **Deprecated fields feature flag** — `BridgeGlobalConstants.hideDeprecatedFields` controls whether `AcceleratedDormancy` and `PayReversalValidation` are shown or hidden/nulled out (`LaunchProgramImpl` lines 255, 831).
5. **Escheatment on/off toggle** — When escheatment is "off", only state, channel, end date, and flag are saved. When "on", all dormancy/fee fields apply (`EscheatmentConfigImpl.saveGlobalEscheatmentConfig()`).
6. **Regulatory limit types are mutually exclusive per save** — `GlobalRegulatoryLimitImpl.saveGlobalRegulatoryLimitData()` saves exactly one of AGML, CBL, or LML per invocation.
7. **Input validation via Struts validator** — `validation.xml` and `validation-special-characters.xml` provide field-level rules; `ParamFilter` checks for Unicode escape sequences (`\\u[A-Fa-f0-9]{4}`) and octal patterns in all request parameters and cookies (CVE-2014-0114 mitigation).
8. **Session invalidation on successful authentication** — `applicationContext-xsecurity-web.xml` line 58: `invalidateSessionOnSuccessfulAuthentication=true`.
9. **HTTP methods restriction** — `web.xml` blocks DELETE, SEARCH, COPY, MOVE, PROPFIND, PROPPATCH, MKCOL, LOCK, UNLOCK, TRACE, PUT, TRACK, LINK, UNLINK on all URL patterns.
10. **Profile audit cross-check** — `ProfileAuditor.validateDBSave()` compares in-memory label values against database values after save, logging discrepancies for label types 9, 11, 12, 13.

## Business Flows

### New Program Setup Flow
1. **Dashboard** — User searches for a program or starts new (`ProgramDashBoardImpl.retrieveProgramType()`).
2. **Program Profile** — Set affiliate, program type, labels, regulatory settings, PGP key (`ProgramProfileImpl`).
3. **Card Settings** — Configure card platform, expiry, PIN, EMV, access levels (`CardSettingsImpl`).
4. **Fees** — Define fee structures, tiers, grace/credit periods, dormancy schedule (`FeesImpl`).
5. **Funding Controls** — Set DD limits, ACH details, payment reversal, precheck, balance sweep (`FundingControlImpl`).
6. **Embossing Profile** — Set plastic, delivery codes, TPIN (`EmbossingProfileImpl`).
7. **Configuration** — Access check, ACH addenda, alerts, account maintenance, fraud control (`ConfigurationImpl`).
8. **Promotion Setup** — Attach bulk promotions with ACH-OUT, allotment, PPD groups (`PromotionSettingImpl`).
9. **Launch** — Review summary with highlighted deviations from defaults, set program status to LAUNCH (`LaunchProgramImpl.setProgramStatus()`).

### CZ (Client Zone) Setup Flow
Separate wizard track for CZ programs: Configuration → Hierarchy → Role Setup → User Setup → Inventory Control → Instant Issue → Reports.

### MPV / OP Setup Flow
Fees → Terms & Conditions → Graphics → Content Approval → Publish.

## Compliance & Regulatory Concerns

- **Escheatment** — Direct implementation of state escheatment rules: dormancy periods, waiting periods, balance thresholds, face value, and processing fees per state/channel (`EscheatmentConfigImpl`). This is a regulatory obligation under unclaimed property laws.
- **AML / Regulatory Limits** — `GlobalRegulatoryLimitImpl` and `RegulatorySettingsHelper` configure AGML (aggregate monetary limits) and Load Monetary Limits (LML), which are core to Bank Secrecy Act / AML program limits on prepaid cards.
- **Card-holder notifications** — Notification setup for Reg E compliance (SMS and email alerts for transactions, low balance, card expiry).
- **Password security** — `EcountMd5PasswordEncoder` (applicationId=8) used; MD5 is cryptographically weak but is what is wired in (`applicationContext-xsecurity-web.xml` line 177).
- **PCI DSS relevance** — The wizard configures card programs including BIN-level settings (via `GetBankBinDAO`), card platforms, and PIN assignment methods. Changes here directly affect the CDE configuration.
- **Audit Trail** — Every configuration action produces an `AuditTrailDataBean` record (affiliate, field name, value, updated-by, application name) written via stored procedure (`AuditTrailStoredProc`).
- **Role-based access control** — Acegi Security (pre-Spring Security) with role-based voters controls access to all screens.

## Business Risks

1. **Misconfiguration risk** — This application directly writes program parameters to the production prepaid platform database. An incorrect fee structure, wrong regulatory limit, or wrong card expiry setting immediately affects live cardholders.
2. **No maker-checker workflow** — The code shows no business-level approval workflow for changes (MPV/OP setup has a content approver step, but main program configuration does not). Changes by a single authorized user take immediate effect.
3. **Deprecated field management** — `hideDeprecatedFields` flag (toggled via `application.properties`) can silently suppress or expose fields. If misconfigured, deprecated settings could be inadvertently applied or hidden.
4. **Audit trail data completeness** — `AuditTrailDataBean` captures affiliate, field name, string value, updated-by, and app name, but there is no before/after value comparison; only the new value is recorded.
5. **Regulatory limit type exclusivity** — Only one limit type is saved per invocation. If the UI allows switching limit type without clearing the old type, stale regulatory limits may persist.
6. **Profile audit is log-only** — `ProfileAuditor` logs discrepancies between in-memory and DB values but does not block the save or alert operations staff programmatically.
