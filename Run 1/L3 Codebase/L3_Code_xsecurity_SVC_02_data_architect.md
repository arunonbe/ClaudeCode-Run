# xSecurity SVC — Data Architect View

## 1. Data Model Overview

xSecurity owns and manages the platform's identity and authorization data domain. Unlike xSearch (read-only) and xSSO (stateless), xSecurity is a fully read-write service whose database is the authoritative source of truth for all operator credentials, roles, and permissions across the Onbe platform.

## 2. Core Entity Model

### User Entity Hierarchy

```
User (UserHome, AbstractUserEcount)
├── BasicUserValidationInformation (credentials — password, status, username)
│   └── UserValidationInformationHistory (password history)
├── UserValidationAttempt (login attempt counter per user)
├── UserPersonalInfo (firstName, lastName, email, country, phone)
├── UserOtpStatus (MFA/OTP state)
└── UserEcount (memberId linkage to ecount platform)
```

**Key DAO Files:**
- `xsecurity-common/src/main/java/com/ecount/one/service/security/dao/AbstractUserEcount.java`
- `xsecurity-common/src/main/java/com/ecount/one/service/security/dao/AbstractUserValidationInformation.java`
- `xsecurity-impl/src/main/java/com/ecount/one/service/security/dao/BasicUserValidationInformationHome.java`
- `xsecurity-impl/src/main/java/com/ecount/one/service/security/dao/UserValidationAttemptHome.java`

### Credential Storage — `BasicUserValidationInformation`

This is the most security-sensitive entity. It stores:
- `username` — login identifier
- `password` — hashed password (format depends on algorithm; see Section 4)
- `passwordStatus` — integer matching `IPasswordStatus` codes (0-6)
- `applicationId` — associates the credential with an application context
- `userId` — foreign key to the user record

### Access Control Model

```
SecurityGroup (group membership)
├── SecurityRole (role definition)
│   └── SecurityPermission (permission strings, e.g., ROLE_USER_MANAGEMENT)
└── DomainSecurityGroup (domain-scoped group)

UserDomain (user ↔ program domain mapping)
LocationHierarchy (organizational hierarchy nodes)
ProgramProfile (program-level security configuration)
```

### Audit Data

```
SecurityAuditLog (SecurityAuditLogHome)
UserActivity (UserActivityDAO)
ApplicationEvent (ApplicationEventDAO)
UserMessage (UserMessageDAO)
UserPersonalInfo (UserPersonalInfoDAO — tracks PII field changes)
```

The `UserPersonalInfoDAO` tracks changes to PII fields (name, DOB, address, NINO/NI number) generating the SMOTS audit events listed in `SecurityConstants.Event`.

## 3. Password Storage Scheme — Critical Security Finding

### Dual Hashing Architecture

xSecurity implements a **dual-hash migration architecture** supporting two password formats simultaneously:

**Format 1 — Legacy (MD5, deprecated):**
- **File:** `xsecurity-common/src/main/java/com/ecount/one/service/security/admin/EcountPassword.java`, lines 37-53
- `encryptPasswordMD5(String password)` — iterates 4 times with string concatenation, then applies MD5
- The algorithm is annotated `@Deprecated` (line 36) confirming it is legacy
- MD5 is a cryptographically broken hash function — it is not considered a secure password hashing algorithm under any current standard
- The implementation uses `MessageDigest.getInstance("MD5")` and `BigInteger` hex encoding

**Format 2 — Current (PBKDF2-HMAC-SHA256):**
- **File:** `EcountPassword.java`, lines 66-90 (`genSaltedHashPassword`)
- Algorithm: PBKDF2 with HMAC-SHA256 (`HmacSHA256`)
- Iterations: `ITERATIONS = 10 * 1024 = 10,240` rounds
- Salt: 8 bytes (64 bits) from `SecureRandom.getInstance("SHA1PRNG")`
- Key length: 32 bytes (256 bits)
- Stored format: `S256$10240$<base64salt>$<base64hash>`

**PCI DSS Assessment:**
- PBKDF2-HMAC-SHA256 with 10,240 iterations meets PCI DSS v4.0.1 Req 8.3.2 (strong cryptography for stored passwords) at a minimum bar. However, NIST SP 800-132 recommends a minimum of 600,000 iterations for PBKDF2-HMAC-SHA256 as of 2023. The current 10,240 rounds is significantly below modern recommendations.
- MD5 passwords **in the database represent an active compliance violation** if any such records still exist. The migration code in `DaoAuthenticationProvider.java` (lines 82-112) transparently upgrades MD5 passwords to PBKDF2 on the next successful login — but accounts that have not logged in since the migration was deployed retain MD5 hashes in the database.

### Password Validation Logic

**File:** `EcountPassword.java`, lines 100-129 (`validateSaltedHashPassword`)

The validator:
1. Checks if the stored hash matches the `S256$...` format via `isEncryptWithNewFormat()`
2. If new format: re-derives the PBKDF2 hash and compares constant-time (via `equals()`)
3. If old format: falls back to MD5 comparison via `encryptPasswordMD5()`

**Security Note:** The comparison `hashOfInput.equals(saltAndPass[3])` at line 119 uses Java `String.equals()`, which is not a constant-time comparison. This creates a theoretical timing side-channel attack opportunity. A constant-time comparison (`MessageDigest.isEqual(byte[], byte[])` or Apache Commons `ConstantTimeComparator`) should be used instead.

## 4. Application-Gated SHA Migration

**File:** `PasswordManagerImpl.java`, lines 100-108 and 218-220

The upgrade from MD5 to PBKDF2 is controlled by `commonSecurityHelper.checkAppSHAEnabled(applicationId, shaAppId)`. The `shaAppId` is a comma-separated list of application IDs configured externally. Only application IDs in this list will have their passwords upgraded to PBKDF2; others remain on MD5. This means that if the SHA app ID list does not include all application IDs, some user populations will remain on MD5 indefinitely.

## 5. Velocity (Brute Force) Tracking Table

**File:** `xsecurity-impl/src/main/java/com/ecount/one/service/security/dao/VelocityCheckStoredProc.java`

The `dbo.security_check_velocity` stored procedure accepts a username and a negative time window (in seconds) and returns a count of login hits within that window. The default `velocitySeconds = 60 * 15 = 900` seconds (15 minutes) in `VelocityCheckingAuthenticationProcessingFilter.java` (line 59). The threshold is 3 attempts per 15-minute window before a `VelocityAuthenticationException` is thrown (line 95).

This is a separate, time-windowed velocity check that complements the persistent attempt counter in `UserValidationAttempt`. The velocity check prevents burst attacks within a time window even before the persistent attempt counter reaches the lockout threshold.

## 6. Password History Table

**File:** `xsecurity-impl/src/main/java/com/ecount/one/service/security/dao/SecurityPasswordHistoryHome.java`

`PasswordManagerImpl.getPasswordHistory()` (lines 260-282) retrieves a list of previous password hashes for comparison, supporting the "cannot reuse recent passwords" policy. The `passwordCompareLimit` parameter controls how many previous passwords are checked. The stored hashes in the history table are in the same format as the current credential (MD5 or PBKDF2 depending on when they were set).

## 7. Audit Trail Data Model

The security audit log (`SecurityAuditLog`, `SecurityAuditLogHome`) captures all security-relevant events. Integration with `com.citi.prepaid.audit.client.helper.SecurityAuditClientHelper` (used in `VelocityCheckingAuthenticationProcessingFilter.java`) generates structured audit messages with:
- `EventType` (e.g., LOGIN)
- `EventAccessType` (INQUIRY)
- `EventResult` (SUCCESS / FAILURE)
- `EventValidationIndicator` (VALID / INVALID)
- `userId`, `username`, `applicationId`
- Request context metadata

This audit trail supports PCI DSS Req 10.2 audit log requirements.

## 8. Org Hierarchy and Bulk File Import Data

The `BulkUserRecord` (`bo/BulkUserRecord.java`) and `BulkHierarchyNodeFileRecord` (`bo/BulkHierarchyNodeFileRecord.java`) structures support CSV/Excel-based mass user provisioning. Bulk file processing goes through `BulkFileManagmentImpl` and `BulkFileHierarchyManagementImpl` with file content stored to a `hierarchyRequests` directory. The error output goes to an `error` subdirectory (constants in `HierarchyBulkFile`). Bulk file operations generate the `BULK_FILE_ERROR` audit event on failure.

## 9. Database Technology

Microsoft SQL Server (via `mssql-jdbc:12.5.0.jre11-preview`). Spring Hibernate ORM is used for entity persistence (`sessionFactory.getCurrentSession().persist()`). Stored procedures are used for velocity checks (`dbo.security_check_velocity`) and user search (`SearchUserStoredProc`). Connection pooling is provided by HikariCP (`HikariCP:5.1.0`).
