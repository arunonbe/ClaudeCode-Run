# bmcwizard_WAPP — Data Architect View

## Data Stores

The application uses four distinct JDBC data sources, all obtained via JNDI from the container (Tomcat). No connection strings or credentials appear in the deployed config files — all are externalized.

| JNDI Name | Bean ID | Purpose |
|---|---|---|
| `java:comp/env/jdbc/CbaseappDataSource` | `CbaseappDataSource`, `cbaseDS` | Primary application database; stores wizard/workbench config, roles, users, screen status, audit trail, program status, email templates, card packages, graphics, T&C, eCap data |
| `java:comp/env/jdbc/NotificationServiceDataSource` | `notificationsvcDS` | Dedicated notification service database; stores email/SMS templates, event-trigger mappings, subscriber IDs, program enable status |
| `java:comp/env/jdbc/JobSvcDataSource` | `jobsvcDS` (`JobSvcDataSource`) | Job scheduler database; stores card package sequences, job file types, error file types |
| `java:comp/env/jdbc/EcountCoreDataSource` | `ecountcoreDS` | Core ecount platform database; stores BINs, EMV/contactless flags, addenda, billing params, international countries, claimable choice data, program relationships, promotion relationships, brand attributes |

An in-memory EhCache cache is used for `countryNamesCache` (10-day idle TTL, 15-day max TTL, overflow to disk enabled, `ehcache.xml`). There is also an Acegi `EhCacheBasedUserCache` for authenticated user objects.

## Schema & Tables

The application exclusively uses stored procedures and stored proc wrappers (Spring's `StoredProcedure` subclasses) for all database interaction — no JPA/Hibernate ORM writes to these tables (Hibernate is used only for the `xAffiliateService` Hibernate session factory against `CbaseappDataSource`). Inferred tables and their owning database:

**CbaseappDataSource (cbaseapp / workbench DB):**

| Inferred Table / Proc | DAO / StoredProc Class |
|---|---|
| Program status | `AddProgramStatusStoredProc`, `FindProgramStatusStoredProc` → `AddProgramStatusDAO`, `FindProgramStatusDAO` |
| Screen status | `ScreenStatusExtractStoredProc`, `ScreenStatusInsertStoredProc` → `ScreenStatusExtractDAO`, `ScreenStatusInsertDAO` |
| Wizard configuration | `GetWizardConfigurationStoredProc`, `InsertWizardConfigurationStoreProc` → `GetwizardConfigurationDAO`, `InsertWizardConfigurationDAO` |
| User roles | `GetUserRoleStoredProc`, `AddUserRoleStoredProc`, `RemoveUserRoleStoredProc` → corresponding DAOs |
| Groups | `CreateGroupStoredProc`, `DeleteGroupStoredProc` → `CreateRoleDAO` |
| User countries | `GetUserCountriesStoredProc`, `SetUserCountriesStoredProc`, `DeleteUserCountriesStoredProc` → `GetUserCountriesDAO` |
| User block status | `GetUserBlockStatusStoreProc`, `UpdateUserBlockStatusStoreProc` → `UserBlockStatusDAO` |
| User history | `CheckUserHistoryStoredProc` → `CheckUserHistoryDAO` |
| User password helpers | `UserPasswordHelperStoredProc` → `UserPasswordHelperDao` |
| Email templates | `GetAllEmailTemplateStoredProc`, `UpdateEmailTemplateStoredProc`, `DeleteEmailTemplateStoredProc` → `GetAllEmailTemplateDAO`, `UpdateEmailTempalteDAO` |
| Alert country | `GetAlertCountryStoredProc` |
| Role / role users | `RoleStoredProc`, `RoleUsersStoredProc`, `AdminRoleUsersStoredProc` → `RoleDAO`, `RoleUsersDAO`, `AdminRoleUserDao` |
| Access level config | `FindAccessLevelConfigStoredProc`, `SaveAccessLevelConfigStoredProc` → `FindAccessLevelConfigDAO`, `SaveAccessLevelConfigDAO` |
| Program admin details | `GetProgramAdminDetailsStoreProc`, `SaveProgramAdminDetailsStoreProc` → corresponding DAOs |
| Promotion config | `GetWizardpromotionConfigurationStoredProc`, `AddWizardpromotionConfigurationStoredProc` → `WizardPromotionConfigDAO` |
| Redirect to BMC | `RedirectToBMCStoredProc` → `RedirectToBMCDAO` |
| Non-promo templates | `GetNonPromoTemplatesStoredProc` |
| Feature control section config | `FindFeatureControlConfigStoredProc`, `SaveFeatureControlConfigStoredProc` → `FeatureControlSectionConfigDAO` |
| CZ configuration | `CZFindConfigurationStoreProc`, `CZSaveConfigurationStoreProc` → `CZConfigurationDAO` |
| Load restriction | `RetrieveLoadRestrictionStoredProc`, `InsertLoadRestrictionStoredProc` → `LoadRestrictionDAO` |
| CZ reports (program/user report mappings) | Query classes `CZAllReportsQuery`, `CZProgramReportsQuery` etc. → `CZReportsSetupDAO` |
| Graphics | `RetrieveGraphicsStoredProc`, `SaveOrUpdateGraphicsStoredProc`, `DeleteGraphicsStoredProc` → `GraphicsDAO` |
| GR Automation / skin | `RetrieveGraphicsAutomationStoredProc`, `SaveOrUpdateGrAutomationStoredProc` → `GrAutomationDAO` |
| Terms & Conditions | `RetrieveTCStoredProc`, `SaveTCStoredProc` → `OPSetupTCDAO` |
| OP Setup fees | Multiple fee stored procs → `OPSetupFeesDAO` |
| Content approvers | `ContentApproversStoredProc`, `UpdateContentApproversStoredProc`, `ApproveXcontentStoredProc` → `ContentApproverDao` |
| eCap emboss messages, financial info | Multiple eCap stored procs → `EcapSetupDAOImpl` |
| Audit trail | `AuditTrailStoredProc` → `AuditTrailDAO` |
| CPP public key | `RetrieveCPPPublicKeyStoredProc` → `ProgramProfileDAO` |
| Card package sequence | `SaveCardPackageSequenceStoredproc`, `GetCardPackageSequenceStoredproc` → `CardPackageSequenceDAO` |

**NotificationServiceDataSource:**
Notification event templates, SMS/email program enable status, subscriber IDs, trigger-event-template mappings (managed by ~28 stored procs/queries in `com.ecount.bridge.storeproc.notification` and `com.ecount.bridge.queries.notification`).

**JobSvcDataSource:**
Card package sequences, error/job file types (`ErrorFileTypeListStoredProcedure`, `JobFileTypeDAO`).

**EcountCoreDataSource:**
BIN data, EMV/contactless flags, addenda config, billing parameters, claimable choice data, program/promotion relationships, international countries list, brand attributes.

## Sensitive Data Handling

The following sensitive data categories are present in the application:

| Data Type | Location / Evidence |
|---|---|
| **Username and password** (internal workbench users) | `UserRoleSettingImpl` creates users via `UserManagement`; `UserPasswordHelperDao` handles password operations; passwords encoded with MD5 (`EcountMd5PasswordEncoder`, applicationId=8) |
| **Remember-me token** (cookie) | `TokenBasedRememberMeServices` stores Base64-encoded `username:expiryTime:MD5(username:expiry:password:key)` as cookie `ACEGI_SECURITY_HASHED_REMEMBER_ME_COOKIE` |
| **PGP keys** (for program ACH/encryption) | `HttpCryptoServiceHelper` manages add/remove/list of PGP public keys for programs. Key paths are passed as strings; keys are stored on PGP crypto servers, not in the DB |
| **Card BIN data** | `GetBankBinDAO` / `GetBankBinStoredProc` retrieves BINs from `EcountCoreDataSource`. BINs are configuration data, not full PANs |
| **EMV / contactless flags** | `GetEMVEnabledDAO`, `GetContactlessEnabledDAO` — card feature flags |
| **Financial amounts** | Fee structures, balance thresholds, regulatory limits — stored as long-integer cents internally, converted via `StringHelper.lCentsToDollar()` / `lDollarToCents()` |
| **User email addresses / contact info** | `UserRoleSettingImpl` imports from `BrigantineUser`, `Customer`, `EMail` — contact details used for notifications |
| **Audit trail data** | `AuditTrailDataBean` fields: `strAffiliate`, `strFieldName`, `strValue`, `strApplicationName`, `strUpdatedBy`. Field values may include configuration parameter values |

No full PANs, CVV/CVC, or PIN data are stored or processed by this application. The wizard configures card parameters but does not handle card transactions.

## Encryption & Protection

| Mechanism | Detail |
|---|---|
| **Password encoding** | MD5 via `EcountMd5PasswordEncoder` — cryptographically weak (no salt visible in config). Application ID 8 is passed as a parameter. |
| **Remember-me cookie** | MD5-HMAC signed token (username + expiry + password hash + key). Marked `Secure; HttpOnly` in `TokenBasedRememberMeServices.makeValidCookie()` (lines 268–269). Cookie max age is 5 years, regardless of `tokenValiditySeconds`. |
| **PGP key management** | Programs use PGP public keys for ACH/crypto operations, managed via `HTTPCryptoServiceClient`. Keys are pushed to/pulled from external PGP crypto servers. |
| **HTTPS** | Referenced as `https` in GitLab CI and deployment URLs. `forceHttps=false` in `authenticationEntryPoint` (xsecurity-web.xml line 120) — HTTPS is not enforced at the application layer. |
| **Transport security** | Data sources are JNDI-managed; no plaintext credentials in app config. |
| **EhCache** | Country names cached in memory and optionally to disk (`overflowToDisk=true`); not encrypted at rest. |
| **Hibernate cache** | `SingletonEhCacheProvider` used for affiliate Hibernate L2 cache — not encrypted. |

## Data Flow

```
Browser (HTTPS) 
  → Tomcat (Acegi security filter chain)
    → Struts ActionServlet (*.do)
      → Business Impl (e.g., ProgramProfileImpl)
        → Helper classes (e.g., EmbossingProfileHelper)
          → xPlatform Profile Classes (FDRCardProfileClass, etc.)
            → EcountCoreDataSource / CbaseappDataSource (stored procs)
        → DAO classes (e.g., ScreenStatusInsertDAO)
          → StoredProc classes
            → CbaseappDataSource / NotificationServiceDataSource / JobSvcDataSource
        → AffiliateService (Hibernate) → CbaseappDataSource
        → HttpCryptoServiceHelper → External PGP Crypto Servers (HTTP)
        → JobServiceHelper → External Job Scheduler (XML-RPC)
```

The xPlatform layer (`com.cbase.business.ecount.profile.*`) acts as the primary data access abstraction for card program profiles. The application also issues XML-RPC calls to a Job Scheduler service (`JobScheduler-client.xml`, `JobServiceHelper`).

## Data Quality & Retention

- **No ORM-enforced schema validation** — Stored procedures own all referential integrity rules. The Java layer performs minimal validation before calling procs.
- **Feature flag for deprecated fields** — `hideDeprecatedFields=true` (default in `application.properties`) suppresses certain fields. When `false`, deprecated configuration is visible and saveable.
- **Profile auditor** — `ProfileAuditor.validateDBSave()` performs a post-save cross-check of label types 9, 11, 12, 13 against the DB, logging discrepancies. This is an advisory check only.
- **Audit trail** — Records affiliate + field + new value + user + app name. No before-value is captured. No TTL or retention policy is implemented in the Java code.
- **EhCache TTL** — `countryNamesCache`: 10-day idle TTL, 15-day max TTL. `defaultCache`: eternal=true (no expiry).
- **No soft-delete pattern** — DAOs use explicit delete stored procs (e.g., `DeleteEmailTemplateStoredProc`, `DeleteGraphicsStoredProc`). Hard deletes are the norm.

## Compliance Gaps

1. **MD5 password hashing** — `EcountMd5PasswordEncoder` uses MD5 without evidence of salting. PCI DSS v4.0.1 Req 8.3.2 requires strong cryptographic hashing (e.g., bcrypt, Argon2) for stored passwords.
2. **HTTPS not enforced at app layer** — `forceHttps=false` in security config. PCI DSS Req 4.2.1 and TLS requirements depend on infrastructure-layer enforcement, which is not verifiable from this code.
3. **Remember-me cookie lifetime** — Cookie set to 5 years (`60 * 60 * 24 * 365 * 5`) in `TokenBasedRememberMeServices`, regardless of session timeout of 60 minutes. This violates PCI DSS Req 8.2.8 (idle timeout) if remember-me functions as a persistent session.
4. **No field-level encryption for sensitive config values** — Audit trail `strValue` and wizard configuration data written to DB without field-level encryption.
5. **Audit trail lacks before-value** — Cannot reconstruct what changed, only what the new value was. Limits forensic capability for PCI DSS Req 10 and SOC logging completeness.
6. **Disk-overflow caching** — `countryNamesCache` overflows to disk (`java.io.tmpdir`). If temp directory is not encrypted, cached data (country lists, which are low sensitivity) may persist on disk unprotected.
7. **Hibernate L2 cache** — Affiliate entity cache uses unencrypted EhCache. Affiliate data contains business-sensitive branding configuration.
