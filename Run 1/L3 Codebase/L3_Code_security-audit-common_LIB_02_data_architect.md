# security-audit-common_LIB — Data Architect View

## Data Stores
| Store | Type | Location | Purpose |
|---|---|---|---|
| Security audit database | SQL Server (jTDS driver) | `CbaseappDataSource` (JNDI) | Persistent storage of all audit events |
| BCP export files | Flat file (BCP format) | `DATAFOLDER\upload\SecurityAuditData\{csi}\` | Data extract for CSI reporting |

## Schema (Stored Procedure Parameters)
The stored procedure `insert_security_audit_user_data` accepts 28 parameters, reconstructed from `SecurityDataDAOImpl.java`:

| Parameter | Type | Source |
|---|---|---|
| userId | VARCHAR | `UserData.userId` |
| eventDateTime | DATE | `EventData.eventDateTime` |
| userName | VARCHAR | `UserData.destUserName` |
| appId | INTEGER | `ApplicationData.appId` |
| ipAddress | VARCHAR | `RequestData.ipAddress` |
| eventType | VARCHAR | `EventData.eventType` enum |
| eventName | VARCHAR | `EventData.eventType.eventName` |
| eventAccessType | VARCHAR | `EventData.eventAccessType` enum |
| eventResult | VARCHAR | `EventData.eventResult` enum |
| failureReason | VARCHAR | `EventData.failureReason` |
| validationInd | VARCHAR | `EventData.validationInd` |
| additionalEventInfo | VARCHAR | `EventData.additionalEventInfo` |
| destUserId | VARCHAR | `UserData.destUserId` |
| **accountNumber** | VARCHAR | `UserData.accountNumber` |
| **cardNumber** | VARCHAR | `UserData.cardNumber` |
| beforeData | VARCHAR | `EventData.beforeData` (Map.toString()) |
| afterData | VARCHAR | `EventData.afterData` (Map.toString()) |
| httpResponse | VARCHAR | `RequestData.httpResponse` |
| sessionId | VARCHAR | `RequestData.sessionId` |
| exceptionMsg | VARCHAR | `EventData.exceptionMsg` |
| user_country | VARCHAR | `RequestData.userCountry` |
| eventDateTime1 | DATE | `EventData.eventDateTime` (duplicate) |
| device_id | VARCHAR | `DeviceData.deviceTypeId` |
| device_browser | VARCHAR | `DeviceData.browser` |
| device_os | VARCHAR | `DeviceData.operatingSystem` |
| device_geography | VARCHAR | `DeviceData.geography` |
| device_name | VARCHAR | `DeviceData.deviceName` |
| login_type | VARCHAR | `DeviceData.loginType` |

## Sensitive Data — CRITICAL
- **`cardNumber`** field: passed as plain String to `UserData.setCardNumber()` and stored via the `cardNumber` stored procedure parameter. If a full PAN is supplied by the calling application, it will be stored unmasked in the audit database. This is a **PCI DSS Req 3.4 violation** if full PANs are logged.
- **`accountNumber`**: ACH/bank account numbers stored as plain VARCHAR.
- **`sessionId`**: HTTP session identifiers persisted; these could be used for session hijacking if the audit database is compromised.
- **`ipAddress`**: Client IP with X-Forwarded-For concatenation.

## Encryption
- No field-level encryption in the Java layer — data is written as plaintext to SQL Server.
- Database-level encryption (TDE) not visible from application source; must be verified on SQL Server configuration.
- jTDS JDBC connection to `CbaseappDataSource` — TLS for the JDBC connection is configured at the data source level (not visible in this library).

## Data Flow
```
Consumer App
  → SecurityAuditClientHelper.sendMessage(HttpServletRequest, ...)
    → SecurityDataLoggerImpl.sendMessage(AuditData)
      → SecurityDataDAOImpl.writeMessage(AuditData)
        → SQL Server SP: insert_security_audit_user_data (28 params)
          → Audit table (schema not visible in source)

(Separate, scheduled)
citiCPSSecurityAuditDataExtract.vbs
  → BCP queryout: security_audit_user_data_extract
    → Flat file (.bcp) on file system
```

## Data Quality / Retention
- `eventDateTime` is passed twice (`eventDateTime` and `eventDateTime1`) — likely a legacy artefact or a database schema that uses them differently.
- No data quality validation on input parameters before stored procedure execution.
- No retention policy configured in application code; database retention policy must exist at SQL Server level.
- `beforeData` and `afterData` stored as `Map.toString()` — not structured JSON, making field-level querying difficult.

## Compliance Gaps
- **PCI DSS Req 3.4**: `cardNumber` stored as plain VARCHAR — must verify that calling applications mask to first 6 / last 4 before passing.
- **PCI DSS Req 10.3**: Audit log integrity — no tamper-evidence mechanism (hashing, write-once storage) visible.
- **GDPR Art. 25**: No data minimisation on audit records; card and account numbers in audit logs may not be necessary for all event types.
- **PCI DSS Req 10.7**: Audit log retention policy not enforced in application layer.
