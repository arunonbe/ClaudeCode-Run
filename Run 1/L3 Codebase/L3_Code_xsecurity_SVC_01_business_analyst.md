# xSecurity SVC — Business Analyst View

## 1. Service Identity and Business Purpose

xSecurity (`com.ecount.service.xsecurity:xsecurity:4.0.4-SNAPSHOT`) is the platform-wide authentication, authorization, and user lifecycle management service for the entire Onbe Gen-1 and Gen-2 prepaid payments platform. The README states: _"This is an XML-RPC Service called by Workbench and used to manage Client Zone users."_

Its scope is broader than that description suggests. xSecurity is the single system of record for:
- Operator identity and credential management across all Onbe applications
- Role-based access control (RBAC) for CSA, ClientZone (CZ), Workbench, and partner portals
- Password lifecycle operations (creation, validation, reset, force-change, expiry, locking)
- Multi-Factor Authentication (MFA) status tracking
- User domain management (program-scoped access boundaries)
- Organizational hierarchy management for location-based access control
- Security audit event generation for all authentication and authorization operations

Every operator login to every Onbe Gen-1 platform application flows through xSecurity for credential verification. Every privilege check for role-based UI rendering in CSA or ClientZone calls xSecurity. This makes xSecurity the most critical single service in the Onbe platform from a security and compliance perspective.

## 2. Application Scope

The `SecurityConstants.Application` interface (`xsecurity-common/.../constants/SecurityConstants.java`, lines 215-219) identifies two primary application contexts:
- `CLIENT_ZONE_ID = 10` — the ClientZone portal used by program administrators and clients
- `WIZARD_ID = 8` — the Workbench/Wizard application used by Onbe internal operators

Different password policies and authentication rules apply per application, as evidenced by the `isPasswordVAlid(String password, int applicationId)` method in `PasswordManagerImpl.java` (lines 313-344).

## 3. User Lifecycle Operations

The `SecurityConstants.Event` interface documents the full set of auditable events managed by xSecurity:

**User Management Events:**
- User creation (`INIT_USER`), inactivation (`USER_INACTIVATED`), deletion (`USER_DELETED`), reinstatement (`USER_REINSTATED`)
- Profile updates: name, email, country, phone number, BMC group, security question
- Role assignments and removals (`USER_ROLE_UPDATED`, `USER_ROLE_UPDATED_FOR_ISA`)
- Location and domain assignments (`USER_LOCATION_UPDATED`, `USER_DOMAIN_UPDATED`)
- Hierarchy node management (`ADD_HIERARCHY_FIALURE`, `EDIT_HIERARCHY_FIALURE`, `DELETE_HIERARCHY_FIALURE`)
- Bulk file operations for mass user provisioning/deprovisioning

**Authentication Events:**
- Login (`USER_LOGGED_IN`)
- Password operations: forgot password, password updates, password locks (`LOCK_PASSWORD`, `CANNOT_UPDATE_PASSWORD`)
- MFA blocking/unblocking (`USER_BLOCKED`, `USER_UNBLOCKED`, `TB_USER_BLOCKED`)
- Forgot username (`FORGOT_USERNAME`)

**Cardholder-Level Audit Events (SMOTS):**
- Customer search (`CUSTOMER_SEARCH`)
- Cardholder data updates: DOB (`CARDHOLDER_DOB_UPDATED`), NINO/SSN (`CARDHOLDER_NINO_UPDATED`), name, address
- Account operations: reissuance (`ACCOUNT_REISSUED`), plastic requests (`PLASTIC_REQUESTED`, `PLASTIC_RENEWED`)
- eToken operations (`ETOKEN_CREATED`, `ETOKEN_REDISTRIBUTED`)
- Nominee/secondary cardholder creation (`NOMINEE_CREATED`)
- Handshake completion (`HANDSHAKE_DONE`)

The presence of SMOTS cardholder audit events in the xSecurity audit log means this service's event log is in scope for PCI DSS Req 10 audit trail requirements.

## 4. Password Policy

`PasswordManagerImpl.java` (lines 294-344) defines password validation rules:

**Default and ClientZone (Application ID 10):**
- Minimum length: 8 characters
- Must contain both alpha and numeric characters (no all-alpha or all-numeric passwords)
- No special character requirement documented (passwords are `[a-zA-Z0-9]*` only — uppercase and lowercase letters plus digits)

**Wizard/Workbench (Application ID 8):**
- Minimum length: 6 characters (lower than CZ — a weaker policy for internal operators)
- Must match `[a-zA-Z0-9]*` pattern

**PCI DSS Assessment:** PCI DSS Req 8.3.6 requires passwords for user accounts to meet a minimum length of at least 12 characters. The current 8-character minimum (and 6-character minimum for Wizard) does not meet PCI DSS v4.0.1 requirements. This is a documented compliance gap.

**Account Lockout Policy:**
`SecurityConstants.MAX_FAILED_LOGIN_ATTEMPTS = 3` (line 316) — accounts are locked after 3 failed consecutive login attempts. This aligns with PCI DSS Req 8.3.4 (lock out after not more than 10 attempts; 3 is within compliance). The lockout is status-based (`IPasswordStatus.LOCKED = 3`).

## 5. Password Status Lifecycle

`SecurityConstants.IPasswordStatus` (lines 204-212) defines six password states:

| Status Code | Name | Business Meaning |
|---|---|---|
| 0 | FORCED | Password must be changed before access is granted |
| 1 | TEMPORARY | Temporary password issued by admin |
| 2 | NORMAL | Active password |
| 3 | LOCKED | Account locked after failed attempts |
| 4 | CANCELED | Account canceled/closed |
| 5 | SUSPENDED | Account suspended |
| 6 | MFA_BLOCKED | Blocked due to MFA failure |

The FORCED status (code 0) triggers the `ForcedPasswordFilter.java` in the web module, which intercepts requests from users who must change their password before proceeding.

## 6. Organizational Hierarchy and Domain Model

The xSecurity service manages a multi-level organizational hierarchy (`LocationHierarchy`, `LocationHierarchyHome`) that controls which programs, promotions, and locations a user can access. This hierarchy supports:
- Bulk hierarchy file imports/exports (Excel and XML format parsers are present)
- Program-scoped role assignments (`SecurityGroup`, `SecurityRole`, `SecurityPermission`)
- Domain-based access control (`UserDomain`, `UserDomainHome`) enabling users to have access scoped to specific program domains

This model supports Onbe's multi-client, multi-program business structure where a single operator may have access to multiple client programs with different roles in each.

## 7. Notification Integration

The xSecurity service integrates with the platform notification framework (`notification-framework_SVC`) for email communications:
- New user provisioning notifications (`FirstTimeUserNotification`, `AdminPasswordNotification`)
- Password reset emails (`ResetPasswordNotification`, `PasswordNotification`)
- Username reminder emails (`ResendUserNameNotification`)
- Admin update notifications (`AdminUserUpdateNotification`, `UserUpdateNotification`)

Email templates are identified by template keys in `SecurityConstants.Notification` (lines 291-302).
