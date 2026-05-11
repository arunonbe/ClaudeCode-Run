# csa_WAPP — Data Architect View

## 1. Data Stores

| Data Source Bean | JNDI / Driver | Role |
|---|---|---|
| `CbaseappDataSource` | `jdbc/CbaseappDataSource` (SQL Server — `com.microsoft.sqlserver.jdbc.sqljdbc`) | Primary operational store: CSA users, audit, fees, ACH config, escalations, programme config |
| `EcountCoreDataSource` | `jdbc/EcountCoreDataSource` (SQL Server) | Card/member/transaction data, eCAP, Claimable Choice, ACH unprocessed queue, ATM management |
| `JobSvcDataSource` | `jdbc/JobSvcDataSource` (SQL Server) | Job service: PUID lookup, one-time transactions |
| ECount Core (RPC/XML-RPC) | `director.address` property → `CoreDeviceServiceLocator` / `DeviceXMLRPCClient` | Real-time balance, device operations, member management via proprietary XML-RPC |
| CBTS (Cross-Border Transfer Service) | `cbtsClient.URIBase` (HTTP REST) | Wirecard/cross-border FX transfers (`csa-context.xml` lines 780-788) |
| Affiliate Service | `affiliateServiceApplicationContext.xml` | Programme/affiliate attribute retrieval |
| Symbol Service | `applicationContext-symbol.xml` | Currency symbol lookup |
| Comment Service | `com/ecount/services/comment/comment.xml` | Cardholder notes service |
| Message Center | `com/ecount/service/message/MessageCenter-client.xml` | Email notification dispatch |

`web.xml` lines 220-237 declare three JDBC `resource-ref` entries; `csa.xml` lines 10-19 wire property file locations.

---

## 2. Schema Knowledge (Tables Referenced in Source)

### CbaseappDataSource (SQL Server)

| Table / Object | Access Class | Operation |
|---|---|---|
| `csa_user` | `CSAUserDetailsServiceImpl`, `CSAUserManagerImpl` | SELECT by username; credential load |
| `audit_session`, `audit_event` | `JdbcAuditSessionDao`, `JdbcAuditEventDao` | INSERT pre/post state for all monetary actions |
| `acl_object_identity`, `acl_permission` | `JdbcExtendedDaoImpl` (`basicAclExtendedDao`) | Spring ACL for EMember access control |
| `reversible_fee` | `JDBCReversibleFeeDAO` | SELECT eligible fee reversals |
| `risk_monetary_adjustment` | `JdbcRiskMonetaryAdjustmentDAOImpl` | SELECT/INSERT risk adj records |
| `management_adjustment` | `JdbcManagementAdjustmentsDAOImpl` | SELECT/INSERT management adj records |
| `csa_comment_escalation` | `CommentEscalationDAOImpl`, `InsertCommentEscalationDAOImpl` | Escalation thread lifecycle |
| `csa_user_country` | `GetCSAUserCountriesSP`, `SetCSAUserCountry`, `DeleteCSAUserCountriesSP` | User country permissions via stored procs |
| `sanction_field_state` | `SanctionFieldStateDaoImpl` | Flag map for OFAC-sanctioned field disabling |
| `locale` | `LocaleDAOImpl` | ACH locale (US/CA) determination |
| `affiliate` | `JdbcAffiliateDAOImpl` | Programme affiliate data |
| `confirmation_number` (ecap_purchaser_info) | `JdbcConfirmationNumberDAOImpl` | SQL: `SELECT confirmation_number FROM ecap_purchaser_info WHERE member_id =?` (`csa.xml` line 1744) |
| `ecap_recipient_card_info` | `JdbcRecipientInfoDAOImpl` | UPDATE status_code; SELECT access_level, shipping_method |
| `ecap_financial_info` | `JdbcRecipientInfoDAOImpl` | SELECT `Issue_card_for_dda` |
| `ieft_device` | `IEFTDeviceDAO` | Allotment / IEFT beneficiary devices |
| Block codes | `GetBlockCodes`, `GetProgramDDABlockCodes` | Programme-level DDA block code lookup |
| `csa_user_password_history` | `UpdateCustomerPasswordDAO`, `UpdateCustomerPasswordStatusDAO` | Password lifecycle |
| `ecount_lock_status` | `GetEcountLockStatusCode` | Lock/unlock card status codes |
| Escalation assignee | `EscalationAssigneeDAOImpl` | Assignee list for escalation queue |
| `template_lookup` | `GetTemplateLookupDAOImpl` | Comment template lookup |
| Bridge programme details | `GetBridgeProgramAdminDetailsDAO` | Programme cross-referencing |
| `csa_user_update_status` | `UpdateUserStatus` | CSA user status flip |
| Virtual Express SP | `UserVirtualExpressExtractSP`, `UserVirtualExpressInstallSP`, `UserVirtualExpressUpdateSP` | Mobile wallet virtual card management |
| ACH verification | `GetACHVerificationStatuses`, `InsertACHVerificationMemoLog`, `GetACHVerificationMemoLogByMemberId` | Manual ACH bank verification workflow |

### EcountCoreDataSource (SQL Server)

| Table / Object | Access Class | Notes |
|---|---|---|
| `app_profile_program_claimable_choice` | `ClaimableChoiceDAOImpl` | Claimable Choice programme config; query at line 61 |
| `claimable_payment` | `ClaimablePaymentDAOImpl` | Token payment records |
| `claim_code_issuance_info` | `ClaimableChoiceDetailsRetrieveDao` | Issuance sender address |
| `claim_code_redemption_info` | `ClaimCodeRedemptionInfoRetrieveDao` | Redemption address, modality, IP; SELECT TOP 1 with ORDER BY redemption_date DESC |
| Check activity | `InsertCheckActivityDAOImpl` | Paper check activity log |
| Enrollment status | `UpdateCoreEnrollmentStatusDaoImpl` | CIP/enrollment state machine |
| Core enrollment check | `CoreEnrollmentCheckRequest` | Stored proc to validate check request eligibility |
| `WhatsApp country list` | `WhatsAppCountryListRetrieveSP` | International WhatsApp-enabled countries |
| ATM | `ManageATMDAOImpl` | ATM whitelist management |
| Extended registration | `ExtendedRegistration` | Additional member registration data |
| `SPGetCCTransactionInfoWithTxId` | `SPGetCCTransactionInfoWithTxId` | Credit card transaction info by TX ID |
| IEFT block beneficiary | `BlockBeneficiarieSP` | Block allotment beneficiary |
| Unprocessed ACH | `GetUnprocessedACHSP`, `CancelACHSP` | ACH cancellation workflow |
| Fee / emboss | `GetFeeSet`, `GetFeePresentationDetails`, `EmbossFeeCreditInquiryDao` | Emboss fee credit lookup |
| KYC | `KYCStatusInsertUpdateSP` | KYC status upsert (SQ-5287) |
| Nickname | `CoreIeftExtendedInfoNicknameRetrieveByDeviceIdSP` | IEFT beneficiary nickname (WARR-5333) |
| New description | `NewDescriptionSP` | Transaction description lookup (Jira 427) |
| Payment selection | `UserPaymentSelectionExtractSP` | Member payment preference |
| Fee sources | `FeeSourcesSP` | Account fee summary |
| Check transactions | `CheckTransactionsExtractSP` | Paper check history |
| PUID | `GetPuid` (JobSvcDataSource), `GetExistingPUIDInfoDAO` | Portable user identifier lookup |
| International countries/states | `InternationalCountriesListRetrieveSP`, `InternationalStatesListRetrieveSP` | Address dropdowns |

---

## 3. Sensitive Data Inventory

| Data Element | Class / Location | Handling |
|---|---|---|
| Card number (PAN) | `CardMaskUtils`, JSP forms | Masked by role: last-4 (default), first4+last4, or full (admin roles) |
| Social Security Number | `SocialSecurityNumberVO`, `SubmitCIPAction`, `audit.properties` line 48 | Split into 3 fields; **written to audit log unmasked** — critical risk |
| ACH account number | `CardMaskUtils.maskAchAccountNumber()` | Masked to last 4 digits |
| ACH routing number | Various ACH forms | Not masked in source; transmitted to C-Base core |
| Password (CSA operator) | `CSAUserCryptUtility.createMD5Hash()` | **MD5 only — no salting** |
| Live-chat encryption keys | `csa.xml` beans `liveChatSecretKey`, `liveChatIvKey` | Loaded from property file at `d:/c-base/config/csa/applicationContext-csa.properties` |
| CBTS service credentials | `csa-context.xml` line 785-786 | Username/password passed as constructor args from properties |
| Customer name / email | `CustomerProfileForm`, `CustomerProfileUpdateAction` | Transmitted in session/forms; no explicit encryption at app layer |
| Date of birth | `audit.properties` line 48 `submitCIP.state` includes `dob` | Written to audit log |
| IP address (cardholder redemption) | `ClaimCodeRedemptionInfoRetrieveDao` column `ip_address` | Stored in `claim_code_redemption_info` |

---

## 4. Encryption and Hashing

| Mechanism | Where | Assessment |
|---|---|---|
| MD5 (no salt) | `CSAUserCryptUtility` line 14 | **Critical — broken algorithm for passwords** |
| `EcountMd5PasswordEncoder` | `applicationContext-xsecurity-web.xml` line 149 | Wraps the same MD5 for Spring Security password encoding |
| Live-chat AES (assumed) | `liveChatSecretKey` / `liveChatIvKey` beans | Symmetric key, key management via property file only |
| SSL/TLS at transport | `applicationContext-xsecurity-web.xml` line 108 `forceHttps=false` | **HTTPS not enforced by the application — relies entirely on infra** |
| No field-level encryption | All DAO classes | PAN, SSN, ACH numbers stored/transmitted as plain strings |

---

## 5. Data Flow

```
Browser (CSR)
    │  HTTPS (not enforced in app)
    ▼
Struts 1 ActionServlet  ──►  Filter chain (Acegi Security, ParamFilter, PerformanceFilter, UserTimeZoneFilter, RecordIdFilter)
    │
    ▼
*Action.executeImpl()
    │
    ├──► MemberHelper / DeviceHelper / PaymentHelper
    │         │
    │         ├──► CSAMemberDelegateImpl  ──►  EMember (AOP proxy)  ──►  coreMemberManager  ──►  ECount Core XML-RPC (Director)
    │         ├──► CSADeviceDelegateImpl  ──►  coreDeviceManager     ──►  ECount Core XML-RPC
    │         ├──► distributionManager / IEFTTransferManager         ──►  CBTS REST API (cross-border)
    │         └──► PaymentHelper          ──►  BrandedCurrency DAO   ──►  EcountCoreDataSource (JDBC)
    │
    ├──► JdbcXxxDAO  ──►  CbaseappDataSource  (SQL Server)
    ├──► JdbcXxxDAO  ──►  EcountCoreDataSource (SQL Server)
    ├──► GetPuid     ──►  JobSvcDataSource     (SQL Server)
    │
    └──► AuditManagerImpl  ──►  JdbcAuditEventDao  ──►  CbaseappDataSource
```

---

## 6. Data Quality

| Issue | Evidence |
|---|---|
| Holiday list frozen at 2006 | `csa.xml` `distACHCalendar` hardcodes year-specific dates; ACH start-date validation will be incorrect for recent years |
| Deprecated address fields on `ClaimablePayment` | `ClaimablePayment.java` lines 33-46 mark `firstName`, `lastName`, `address1`, `city`, `state`, `zip`, `country` as `@Deprecated`; stale pattern remaining in codebase |
| `java.util.Hashtable` used as in-memory cache | `csa.xml` beans `authenticationStrategiesCache`, `tempEcountProgramInfoListCache` etc. (lines 776-788) — no TTL, no eviction; stale data possible |
| `displaytag.properties` — no server-side pagination capped | Potentially unbounded result sets for transaction history |
| `ecountCoreJdbcTemplate` defined in both `spring-jdbc.xml` and `csa-context.xml` | Duplicate bean definition (`spring-jdbc.xml` line 9, `csa-context.xml` line 977) — may cause context conflict |

---

## 7. Compliance (Data Layer)

| Obligation | Evidence / Gap |
|---|---|
| PCI DSS req 3.3 — Mask PAN on display | `CardMaskUtils` implements multiple masking variants; role-controlled in JSPs |
| PCI DSS req 3.4 — No full PAN in logs | `LogUtil.sanitizeForLog()` used in `PerformanceFilter`, `GlobalExceptionHandler`; but SSN components written to audit log |
| PCI DSS req 8.3 — Strong cryptography for passwords | **GAP**: MD5 without salt does not meet PCI DSS v4.0.1 requirement 8.3.6 (minimum complexity + strong hash) |
| PCI DSS req 10 — Audit logs | `AuditManagerImpl` / `JdbcAuditEventDao` provides event-level logging; 20 event types in `audit.properties` |
| GLBA data retention | No retention policy visible in source; audit tables grow unbounded |
| GDPR right-to-erasure | No data deletion workflow visible; `SocialSecurityNumberVO` stored in audit log complicates erasure |
