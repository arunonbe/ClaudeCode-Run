# 05 Solution Architect — xsecurity_SVC

## Technical Architecture
Multi-module Maven WAR application (`com.ecount.service.xsecurity:xsecurity:4.0.4-SNAPSHOT`). Java 21 compile target with a legacy security framework (Acegi Security, the predecessor to Spring Security). The WAR is deployed as `xsecurity-war`, which aggregates all modules.

Module structure:
| Module | Purpose |
|---|---|
| `xsecurity-common` | Shared domain model: security BOs, event management, notification, ACL, password manager interface |
| `xsecurity-impl` | Service implementation: user management, password management, DAO layer (Hibernate + JDBC stored procs) |
| `xsecurity-client` | XML-RPC client library for consumers to call xSecurity remotely (`XmlRpcPrivilegeManagerClient`, `XmlRpcUserMamagementClient`, `XmlRpcHierarchyManagementClient`) |
| `xsecurity-web` | Web filter layer: `SecurityFilter`, `VelocityCheckingAuthenticationProcessingFilter`, `ForcedPasswordFilter`, `CheckTermsOfUseFilter`, `EcountMd5PasswordEncoder` |
| `xsecurity-xmlrpc` | XML-RPC service proxies (server-side): `XmlRpcSecurityServiceProxy`, `XmlRpcPrivilegeManagerServiceProxy`, `XmlRpcHierarchyManagementServiceProxy` |
| `xsecurity-war` | WAR assembly module |

Key security model entities (`xsecurity-common`): `Acl`, `CommonSecurityHelper`, `EcountPassword`, `BulkUserRecord`, `BulkHierarchyNodeFileRecord`, `Location`, `Promotion`, `UserActivity`, `UserActivityStatus`, `UserMessage`.

DAO layer (`xsecurity-impl`): extensive JDBC stored-procedure wrappers — `SecurityUserHome`, `SecurityGroupHome`, `SecurityRoleHome`, `SecurityPermissionHome`, `SecurityProgramRolePermissionHome`, `SecurityAuditLog`, `SecurityPasswordHistory`, `UserValidationAttemptHome`, `UserOtpStatusHome`, `InsertUpdateAdminTPinStoredProc`, `RetrieveAdminTPinStoredProc`, `SearchUserStoredProc`, `UserProgramsStoredProc`, `UserProgramRolesStoredProc`.

## API Surface
Dual interface: XML-RPC (primary, legacy) and limited internal Java API.

**XML-RPC server-side proxies** (exposed via `xsecurity-xmlrpc`):
- `XmlRpcSecurityServiceProxy` — authentication, session management, user validation
- `XmlRpcPrivilegeManagerServiceProxy` — privilege and role management
- `XmlRpcHierarchyManagementServiceProxy` — location hierarchy management

**XML-RPC client-side** (`xsecurity-client`, for consumer services):
- `XmlRpcPrivilegeManagerClient` — check privileges, manage roles
- `XmlRpcUserMamagementClient` (`XmlRpcUserMamagementClient` — note typo in class name) — user CRUD
- `XmlRpcHierarchyManagementClient` — hierarchy operations
- `RPCWrapper` — common RPC call wrapper

**GitHub Actions deployment** deploys as `userManagementAPI` with API suffix `user-management-api`, backend at `/services/userManagementServices` — indicating some APIM-exposed surface.

## Security Posture
- **Critical: MD5 password hashing** — `EcountMd5PasswordEncoder.encodePassword()` calls `Password.encryptPasswordMD5(rawPass)` — MD5 is cryptographically broken and explicitly prohibited by PCI DSS Req. 8.3.6 for password storage; this is a critical finding
- **Legacy Acegi Security** — `org.acegisecurity:jakarta-acegi-security:1.0.3`; Acegi Security was superseded by Spring Security in 2008; multiple known vulnerabilities; no longer maintained
- **Password validation with dual-format support**: `EcountMd5PasswordEncoder.isPasswordValid()` handles both a "new format" (salted hash, `Password.validateSaltedHashPassword()`) and the old MD5 format — this dual-mode is a migration artefact; the MD5 path should be fully retired
- **OTP status management** (`UserOtpStatusHome`) and **TPIN management** (`InsertUpdateAdminTPinStoredProc`, `RetrieveAdminTPinStoredProc`) — TPIN is sensitive authentication data (PIN equivalent); must be stored hashed/encrypted, not plain-text
- XML-RPC transport: unless enforced at the load-balancer/proxy, XML-RPC calls may traverse unencrypted HTTP — **PCI DSS Req. 4** risk for authentication credentials in transit
- **Security Audit Log** (`SecurityAuditLog`, `SecurityAuditLogHome`) — this is a PCI DSS Req. 10 control; ensure audit records cannot be deleted or modified by normal application users
- `VelocityCheckingAuthenticationProcessingFilter` — Velocity template engine used in authentication flow; verify no Server-Side Template Injection (SSTI) risk

## Technical Debt
| Item | Severity |
|---|---|
| MD5 password hashing (`EcountMd5PasswordEncoder`) | Critical |
| Acegi Security (`jakarta-acegi-security:1.0.3`) — EOL since 2008 | Critical |
| XML-RPC transport without enforced TLS | Critical |
| TPIN storage mechanism unknown — must be confirmed as hashed | Critical |
| `4.0.4-SNAPSHOT` — production deployment from SNAPSHOT | High |
| `EXCLUDE_STAGE: true` in deployment — no staging environment | High |
| Typo in class name `XmlRpcUserMamagementClient` (double 'a' in "Mamagent") | Low |
| `xsecurity-client` contains `RPCWrapper` — tightly couples consumers to XML-RPC | High |
| Velocity template engine in authentication filter — SSTI risk | High |
| Legacy `UserDomainHomeOld` alongside `UserDomainHome` — dead code | Medium |
| `@Deprecated(since="1.0.0")` class-level annotations not visible in source sample; verify no deprecated business-critical paths are still on main code paths | Medium |

## Gen-3 Migration
Migration is urgent given the MD5 password hash and Acegi Security findings. Recommended path:
1. **Immediate**: Force all users through a password reset to eliminate MD5-hashed passwords; ensure new passwords use bcrypt or Argon2
2. Replace Acegi Security with Spring Security 6.x
3. Replace XML-RPC interface with a REST API (Spring Boot + Spring Security OAuth2 Resource Server)
4. Migrate TPIN storage to a properly encrypted/hashed format using a modern algorithm
5. Deploy to AKS (container); the GitHub Actions `deployment.yml` exists but `EXCLUDE_STAGE: true` must be corrected
6. Retire `XmlRpcUserMamagementClient` consumer integration in favour of the REST API; update `xml-rpc-clients_LIB:securityServiceClient` consumers simultaneously
7. Enable staging deployment before any production release of the new version

## Code-Level Risks
- `EcountMd5PasswordEncoder.isPasswordValid()` checks `applicationId == 8` for a special login wizard path using `passwordManager.isPasswordVAlid(rawPass, applicationId)` — the integer comparison `applicationId == 8` uses auto-unboxing from `Integer`; if `applicationId` is null (its default), this comparison will throw `NullPointerException` — the null check `null != applicationId` guards against this, but the logic path `applicationId == 8` for the login wizard is undocumented
- `encodePassword()` returns an MD5 hash regardless of format — new password registrations will always produce MD5 hashes until the encoder is replaced
- `Password.isEncryptWithNewFormat(encPass)` branch in `isPasswordValid()` — the dual-format detection relies on the stored hash format; if a hash is misidentified, authentication will fail or use the wrong comparison algorithm silently
- `SecurityFilter.java` in `xsecurity-web` — not read in detail; verify it does not bypass authentication for certain URL patterns
- `InsertUpdateAdminTPinStoredProc` / `RetrieveAdminTPinStoredProc` — TPIN stored via stored procedure; the stored procedure implementation (in SQL Server) must be reviewed to confirm TPIN values are not stored in plaintext
- `SearchUserStoredProc` — ensure the stored procedure uses parameterised queries and is not vulnerable to SQL injection via the search input
