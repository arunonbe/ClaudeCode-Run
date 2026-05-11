# security-audit-common_LIB — Business Analyst View

## Business Purpose
`security-audit-common_LIB` is a shared Java library providing security audit event logging infrastructure for the Onbe (formerly Citi Prepaid) platform. It captures security-relevant user actions across web applications and persists them to a SQL Server database via a stored procedure. It is the backbone of the platform's security audit trail, supporting compliance with PCI DSS, FFIEC, and internal security monitoring requirements.

## Capabilities
1. **Security Audit Event Recording**: Records structured audit events (login, logout, registration, password change, ACH operations, payment selection, card activation, wallet operations, PayPal/Venmo/Push-to-Card transfers, etc.) to a database table via stored procedure `insert_security_audit_user_data`.
2. **Event Classification**: Provides enumerations for `EventType` (60+ event types), `EventResult` (SUCCESS/FAILURE/MPV variants), `EventAccessType` (VIEW/INQUIRY/ADD/UPDATE/DELETE), and `EventValidationIndicator`.
3. **ArcSight CEF Integration**: A stub `ArcSightCEFFormat` class exists for converting audit data to Common Event Format for SIEM forwarding — currently not implemented (returns null).
4. **Helper API**: `SecurityAuditClientHelper` provides convenience overloads for consumer applications to record audit events from HTTP request context.
5. **Data Export**: A legacy VBScript (`citiCPSSecurityAuditDataExtract.vbs`) exports audit data from SQL Server using BCP for two application IDs: `158929` (OnePlatform) and `159547` (ClientZone).

## Entities
| Entity | Description |
|---|---|
| `AuditData` | Root audit record aggregating all sub-entities |
| `ApplicationData` | App ID, CSI ID, server IP, device product/version/severity |
| `RequestData` | Client IP address, session ID, HTTP method/response, user country |
| `EventData` | Event type/name, access type, result, failure reason, before/after data, validation indicator, timestamp |
| `UserData` | User ID, destination user ID/name, account number, card number |
| `DeviceData` | Device type, browser, OS, geography, login type |

## Business Rules
- Events are written silently on failure — exceptions are caught and logged but do not propagate to the calling application (fail-open design).
- `failureReason` is only recorded when `validationInd == INVALID`.
- IP address truncated to 100 characters if `X-Forwarded-For` header causes overflow.
- `userId` defaults to `-1` if not provided.

## Process Flows
1. Consumer application (OnePlatform, ClientZone, etc.) calls `SecurityAuditClientHelper.sendMessage(request, appId, userId, ...)`.
2. Helper populates `AuditData` from HTTP request and parameters.
3. `SecurityDataLoggerImpl.sendMessage(auditData)` writes to database via `SecurityDataDAOImpl`.
4. `SecurityDataDAOImpl` calls stored procedure `insert_security_audit_user_data` with 28 parameters.
5. Separately, `citiCPSSecurityAuditDataExtract.vbs` runs on a schedule to BCP-export audit data from SQL Server for CSI IDs 158929 and 159547.

## Compliance Relevance
- **PCI DSS Req 10**: This library is the primary mechanism for PCI DSS audit logging — login/logout, authentication failures, card number access, ACH/payment operations are all captured.
- **FFIEC**: Security event monitoring supported via this audit trail.
- **GDPR/CCPA**: `UserData` holds account numbers and card numbers — data subject rights requests must account for audit records containing this data.
- The ArcSight CEF stub (if completed) would enable SIEM integration for real-time security event monitoring.

## Risks
- ArcSight CEF integration is a stub — `convertIntoCEFFormat` returns null. SIEM forwarding is not implemented, creating a gap in real-time security monitoring.
- `UserData` stores `cardNumber` as a plain String — if full PANs are passed, they are stored in the audit database without masking.
- The VBScript passes SQL Server credentials (`CBASE_USER`/`CBASE_PASSWORD`) via command-line arguments — credentials exposed in process list.
