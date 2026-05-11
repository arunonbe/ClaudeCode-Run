# Data Architect Analysis — enrollment_WAPP

## Repository Overview

**Repo:** `enrollment_WAPP`
**Architecture:** Struts 1 MVC + Spring 2.0.3 XML + SQL Server (jTDS + mssql-jdbc)
**Build:** Maven WAR (`packaging: war`, `pom.xml` line 6)
**Java:** 1.8

---

## Data Architecture Overview

`enrollment_WAPP` is a **presentation and business-logic layer** that sits above the core enrollment profile persistence. It does not own the primary data store directly — instead, it delegates to:
1. **cBase profile service** (`AppProfileUserEnrollment` via `AppProfileUserEnrollmentClass`) — the backend enrollment state store.
2. **SQL Server** — for login/security data (`OneLoginUserDetailsSP`, `one_login_user.java`) and potentially for application context configuration.
3. **Content Management Service (CMS)** — for UI content retrieval.
4. **Mail service** — for outbound notification emails.

---

## Key Data Flows

### Enrollment Write Flow
```
Cardholder submits enrollment form (Struts Action)
    |
    v
EnrollmentManagerImpl.setUsersEnrollmentOption(enrollUnenrollDTO)
    |
    +--> AppProfileUserEnrollmentClass(caller=memberId, agent=agent)
    |
    +--> profile = userProfileClass.retrieve()
    |     If profile exists: update (eventName, optionName, addressUpdate, created)
    |     If no profile: create new AppProfileUserEnrollment
    |
    v
Profile state stored in cBase profile service (not SQL directly)
```

### Enrollment Read Flow
```
Page load / account summary
    |
    v
EnrollmentManagerImpl.getLastEnrollmentActivity(caller, agent)
    |
    v
AppProfileUserEnrollmentClass.retrieve()
    |
    v
Returns Map<String, String>: {enroll_option, enroll_event}
```

### Login / Authentication Flow
```
LoginAction (Struts)
    |
    v
SecurityContextService
    |
    +--> OneLoginUserDetailsSP.execute(username) -- SQL Server stored proc
    |     Returns: userId, passwordHash, status, roles
    |
    +--> get_password_status.execute() -- SQL Server stored proc
    |     Returns: password expiry status
    |
    +--> RSA MFA (rsa-mfa-impl)
    |
    v
Session established
```

---

## Data Entities and Transfer Objects

### `EnrollUnenrollDTO`
Referenced in `EnrollmentManagerImpl.java` line 22. Fields (inferred from usage):
- `memberId` — cardholder identifier (caller)
- `agent` — programme/brand agent identifier
- `programId` — programme
- `addressUpdate` — flag indicating if address update is permitted
- `optionName` — enrollment option (ACH, e-card, etc.)
- `eventName` — ENROLL / UNENROLL / SYSTEM-ENROLL

### `User`
Defined in `src/main/java/com/ecount/one/service/user/User.java`. Likely carries cardholder profile data for the session.

### `SSOUserInfo` / `ExternalSSOUserInfo`
Carry the SSO token claims for authentication.

### `UserContextConfig` / `UserContextService`
Manage the in-memory user context for the current session — programme membership, authentication state, preferences.

### `AppContextConfig` / `AppContextField` / `AppContextFieldValue` / `AppContextProfile`
Programme-specific configuration objects loaded from the application context service. These drive multi-brand rendering.

### `TermsAndConditionsDTO`
Carries T&C version and acceptance state.

---

## Database Schema (Visible from DAO Layer)

### `OneLoginUserDetailsSP`
Stored procedure that retrieves user login details from SQL Server. Column names not directly visible but implied fields: user ID, hashed password, status, roles.

### `get_password_status`
Stored procedure returning password expiry status.

Both use Spring `StoredProcedure` (same pattern as `enrollment_LIB`).

### `one_login_user.java`
A DAO object for the login user table — likely maps `user_id`, `username`, `password_hash`, `status`, `roles`.

---

## External Service Dependencies (Data Perspective)

| Service | Data Exchanged | Protocol |
|---------|---------------|----------|
| cBase profile service | `AppProfileUserEnrollment` (enrollment state) | Internal Java API (Spring bean) |
| Director / DB connection | SQL Server connection routing | `DirectorConfiguredDBCPdatasourceCreator` |
| CMS | Programme content, branding | HTTP (ContentManagementServiceClient) |
| Mail service | Notification email content | SMTP / MailContextService |
| xSecurity / xPlatform | Authentication tokens, session | eCount internal library |
| RSA MFA | One-time passwords | RSA SecurID API |
| Affiliate service | Affiliate/brand metadata | `xAffiliateService` library |

---

## Data Sensitivity Assessment

| Data Category | Where | Classification |
|---------------|-------|---------------|
| Cardholder identity (name, email, phone) | `User` DTO, session | PII — CCPA, GLBA |
| Authentication credentials | `OneLoginUserDetailsSP`, session | Security-critical |
| Enrollment state (option, event) | `AppProfileUserEnrollment`, `EnrollUnenrollDTO` | Operational |
| Address data | `AddressChangeTemplate` | PII |
| MFA tokens | RSA integration | Security-critical |
| T&C acceptance | `TermsAndConditionsDTO` | Legal/compliance record |

---

## Data Architecture Concerns

1. **Session state management** — `UserContextService` / `UserContextConfig` manage user state in HTTP session. In a multi-node Tomcat cluster, session replication must be configured or sticky sessions enforced.
2. **cBase profile service** — enrollment state is stored in a proprietary legacy service, not a queryable SQL table. This creates a data auditability gap (no direct SQL audit query for enrollment state).
3. **No event sourcing** — enrollment events are the business's core audit trail. The current design updates a mutable profile record rather than appending immutable events. If the `enrollment_LIB` extract is the only record of historical events, data loss risk is high.
4. **T&C version tracking** — `TermsAndConditionsDTO` exists but it is unclear whether T&C acceptance history is persisted with version, timestamp, and cardholder ID for regulatory evidence.
