# xSecurity SVC — Enterprise Architect View

## 1. Role in the Platform Architecture

xSecurity is the identity and access management (IAM) core of the Onbe Gen-1 platform. It occupies the most foundational security tier: every operator authentication event, every session establishment, and every privilege check across the Gen-1 platform depends on xSecurity's availability and correctness. A failure in xSecurity would prevent all operator logins to CSA, ClientZone, and Workbench simultaneously.

Unlike modern IAM platforms (Okta, Auth0, Azure AD) that provide stateless JWT-based authentication, xSecurity implements a stateful, session-based model tightly coupled to the application server. The session token is the servlet container's `HttpSession` — there are no JWT tokens or OAuth2 flows in evidence.

## 2. Module Architecture

```
xsecurity (parent)
├── xsecurity-common    Domain objects, interfaces, constants, BO layer
├── xsecurity-impl      Hibernate DAOs, Spring JDBC stored procs, business logic
├── xsecurity-client    XML-RPC client library for consumers
├── xsecurity-web       Web security filters (Acegi), password encoder, user details
├── xsecurity-xmlrpc    XML-RPC service proxy wiring
└── xsecurity-war       WAR packaging (finalName: userManagement)
```

This six-module layout reflects significant organic growth. The `xsecurity-web` module contains both the servlet filter chain and the password encoding logic — these are different concerns that would benefit from further separation.

The `xsecurity-client` module provides XML-RPC client stubs (via `XmlRpcPrivilegeManagerClient`, `XmlRpcHierarchyManagementClient`, `XmlRpcUserMamagementClient` [note: typo in class name]) for consuming services to make RPC calls into xSecurity. The XML-RPC interface name is `SecurityService.PrivilegeManagerService` (line 22 of `XmlRpcPrivilegeManagerClient.java`).

## 3. Authentication Architecture

### Session Token Mechanism

xSecurity uses the Jakarta Servlet HTTP session (`HttpSession`) as the session token mechanism:
- `request.getSession().setAttribute("ECOUNT_MEMBER_ID", ecountUser.getMemberId())` (line 266, `VelocityCheckingAuthenticationProcessingFilter.java`) — member ID is stored in the HTTP session on successful authentication
- Session management is delegated to the Tomcat container; there are no custom session token generation routines
- The `invalidateSessionOnSuccessfulAuthentication` flag (line 75) defaults to `false` — **session fixation protection is disabled by default**

The `ECOUNT_SESSION_ID` constant (line 57, `VelocityCheckingAuthenticationProcessingFilter.java`) suggests a custom session identifier is also tracked, but its use is not fully visible in the reviewed code.

### Acegi Security Filter Chain

The authentication pipeline:
1. `RequestContextFilter` or equivalent — sets request context
2. `VelocityCheckingAuthenticationProcessingFilter` — velocity check + Acegi authentication processing
3. `CheckTermsOfUseFilter` — terms of use gate
4. `ForcedPasswordFilter` — intercepts users with FORCED password status
5. `SecurityFilter` — main Acegi security filter

Login form parameters: `j_username` (line 121 of `VelocityCheckingAuthenticationProcessingFilter.java`) and implicitly `j_password` (Acegi default). These are the legacy J2EE form-based authentication parameter names.

### `EcountUser` Principal

The authenticated principal is an `EcountUser` object (`xsecurity-web/.../EcountUser.java`) extending Acegi's `User`:
- `username` — login name
- `password` — hashed password (held in memory during authentication; see security note)
- `memberId` — linked ecount platform member ID
- `applicationId` — which application (CZ=10, Wizard=8)
- `securityUserId` — numeric user ID
- `passwordStatus` — current password lifecycle state

## 4. Privilege and Role Architecture

The RBAC model uses three layers:
1. **Security Groups** (`SecurityGroup`, `BasicSecurityGroup`, `DomainSecurityGroup`) — named groupings of roles
2. **Security Roles** (`BasicSecurityRole`, `AbstractSecurityRole`) — named role definitions
3. **Permissions** (`SecurityPermission`) — granular permission strings (e.g., `ROLE_USER_MANAGEMENT_EDIT`)

The permission constants in `SecurityConstants.Privilege` are:
- `ROLE_SECURITY`
- `ROLE_USER_MANAGEMENT` (and VIEW, EDIT, DELETE, RESET_PASSWORD, ADD variants)
- `ROLE_INVENTORY_VIEW`

The `DaoPathBasedFilterInvocationDefinitionMapTest` (integration test) validates that URL patterns are mapped to the correct required roles in the Acegi Security filter map — this is the access control enforcement point for web UI pages.

The `PrivilegeManagerImpl` manages all CRUD operations on the RBAC model and is the most complex single class in the service (80+ lines visible, likely 500+ total).

## 5. Multi-Application Support Architecture

The `applicationId` field threading through every authentication and authorization operation is the key to multi-application support. The same user identity store serves both ClientZone (ID=10) and Wizard (ID=8) with different:
- Password length requirements (8 vs. 6 characters)
- Password upgrade eligibility (SHA upgrade is controlled per application by `shaAppId` config)
- Audit event routing
- Lockout behavior (MFA blocking has different handling per app)

This design means that a security weakness in one application context (e.g., the weaker 6-character Wizard passwords) potentially affects the shared user table.

## 6. Integration Points

| Consumer | Integration Method | Functions Used |
|---|---|---|
| CSA (Customer Service App) | XML-RPC via xsecurity-client | User lookup, privilege checks |
| ClientZone | Web session (direct WAR) | Login, password management |
| Workbench/Wizard | XML-RPC via xsecurity-client | User management, hierarchy |
| xSSO | Indirect (via session context) | Session establishment |
| notification-framework | Event message | Password and user emails |
| security-audit-common | Direct client | Structured audit event publishing |

## 7. Architecture Gaps vs. PCI DSS Req 8

| PCI DSS Req 8 Requirement | Implementation Status | Gap |
|---|---|---|
| 8.2.2 — Individual accounts | Implemented | None observed |
| 8.3.4 — Account lockout (≤10 failed) | 3 attempts — compliant | None |
| 8.3.6 — Minimum 12-character passwords | 8 chars (CZ), 6 chars (Wizard) | **Non-compliant** |
| 8.3.7 — Password complexity (letters + numbers + special) | Letters + numbers only; no special chars | **Non-compliant** |
| 8.3.9 — Password rotation (≥90 days) | Not visible in code reviewed | Requires verification |
| 8.3.10 — No password reuse (last 4) | Password history implemented | Compliant if limit ≥ 4 |
| 8.6.1 — Shared accounts prohibited | Multiple users via individual records | Compliant |
| 8.2.8 — Session idle timeout (≤15 min) | Velocity window = 15 min; session timeout in Tomcat config | Requires verification |

## 8. Strategic Architecture Recommendations

1. **Replace Acegi Security with Spring Security 6.x** — this is the most critical architectural change needed; Spring Security provides session fixation protection, CSRF protection, and modern OAuth2/OIDC support out of the box
2. **Implement OAuth2/OIDC for operator authentication** — migrate from form-based Acegi auth to a standard identity protocol, enabling integration with enterprise IdPs (Azure AD)
3. **Increase password complexity requirements** — minimum 12 characters with at least one uppercase, lowercase, numeric, and special character per PCI DSS Req 8.3.6/8.3.7
4. **Enable session fixation protection** — set `invalidateSessionOnSuccessfulAuthentication = true` across all application contexts
5. **Increase PBKDF2 iteration count** — from 10,240 to at least 260,000 (PBKDF2-HMAC-SHA256 recommendation per OWASP 2024)
6. **Force-migrate legacy MD5 passwords** — run a batch job to identify and expire all remaining MD5-format passwords, forcing users to reset
