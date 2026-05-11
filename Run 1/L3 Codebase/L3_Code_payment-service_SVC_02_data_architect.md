# Data Architect — payment-service_SVC

## Data Stores
| Store | Type | Connection |
|-------|------|------------|
| `cbaseapp` SQL Server | Primary relational DB | Imported via `classpath:com/ecount/resources/db/appCtx-cbaseapp-ds.xml` (from xplatform library) |
| External ecount services | XMLRPC clients | director-service, member XMLRPC client, device XMLRPC client, transfer XMLRPC client, profile client |

## Schema / Stored Procedure Access
All data access is via Spring `StoredProcedure` subclasses against `cbaseapp`:

| SP Wrapper Class | Purpose |
|-----------------|---------|
| `CreateBulkUser` | Create batch user record |
| `LinkUserWithMemberId` | Associate user with ecount member |
| `UpdateUserDDA` | Update demand deposit account |
| `CreatePaymentActionItem` | Record payment action |
| `CreateRequestGroup` | Create request group |
| `CreateNotificationRequest` | Insert email notification trigger |
| `CreateTransactionHistory` | Record transaction history entry |
| `CheckUserPermissions` | Validate user access |
| `CreateTransactionDevice` | Register transaction device |
| `UpdateTransaction` | Update payment transaction status |
| `GetApplicationInfo` | Retrieve application config |
| `ValidateBulkEmail` | Validate email for bulk operations |
| `CreateCertificate` | Issue payment certificate |
| `CreateCertificateSasiRecovery` | SASI recovery path for certificate |
| `CreatePaymentConstraints` | Set payment business constraints |
| `UpdateCreateCertificateInfo` | Update certificate metadata |
| `CreateNotificationMergeData` | Insert notification merge data |
| `GetProgramPromotionEventsDetails` | Retrieve promotion event config |
| `UpdateStatusForEvent` | Update promotion event status |
| `GetPaymentExpiryDate` | Retrieve payment expiry |

## Sensitive Data Classification
| Data Element | Classification | Notes |
|-------------|---------------|-------|
| `paymentId` | Financial identifier | Integer; used in StopPayment |
| `programId` | Business identifier | Passed to CreateBulkUser and CreateCertificate |
| DDA device ID | Financial reference | Created and stored via `UpdateUserDDA` |
| `memberId` | Identity reference | ecount member GUID |
| Email address | PII | Used in `CreateEmailNotifications`; `partner@ecount.com` hardcoded for bulk |
| Certificate data | Payment instrument | Core payment record; in PCI DSS scope |
| Transaction history | Financial audit record | PCI DSS Req 10 data |
| Agent name | Operational metadata | Context parameter for all operations |

## Encryption
- SQL Server: TLS 1.2 (`sslProtocol=TLSv1.2`) enforced via the xplatform-provided `appCtx-cbaseapp-ds.xml` data source configuration.
- `server.xml` in the Docker configuration controls the Tomcat connector TLS settings (content reviewed — standard Tomcat 10 config).
- QA cert (`certfile_qa.crt`) imported to JVM trust store during Docker build.
- No application-layer encryption of data in transit within the XMLRPC payload.
- XMLRPC operates over HTTP by default within the VNet; TLS termination is at the load balancer/network layer.

## Data Flow
```
Caller (oneplatform-rest_API, other ecount services)
  └── XMLRPC POST /dispatch.asp
        └── EPaymentProxy → PaymentServiceImpl → PaymentServiceLibraryImpl
              ├── PaymentServiceDAOJDBCImpl (SPs) → cbaseapp SQL Server
              ├── memberXMLRPCClient → member service
              ├── deviceXMLRPCClient → device service
              ├── transferXMLRPCClient → transfer service
              └── profileClient → profile service
```

## Data Quality and Retention
- All writes are via stored procedures in `cbaseapp`; data quality and retention are enforced at the DB layer.
- No application-layer validation beyond `input.validate()` calls in `PaymentServiceImpl`; validation implementation resides in value objects (`CreateCertificateInput`, `CreateEmailInput`).
- `PaymentServiceValidation` and `PaymentServiceValidationImpl` classes present — additional validation layer exists.
- `ObjectMapper` configured with `FAIL_ON_UNKNOWN_PROPERTIES=false` in `PaymentServiceDAOJDBCImpl` — permissive deserialization may mask data issues.

## Compliance Gaps
- **PCI DSS Req 6**: XMLRPC endpoint (`/dispatch.asp`) is unauthenticated at the application layer — relies entirely on network controls.
- **PCI DSS Req 10**: Transaction history is created via SP but no audit logging of the payment service application layer operations is visible (e.g., no security event log for StopPayment, CreateCertificate calls).
- **PCI DSS Req 3**: Certificate data (payment instruments) flow through the service; confirm certificate values do not include full PANs logged or returned in XMLRPC responses.
- **`FAIL_ON_UNKNOWN_PROPERTIES=false`** in DAO: Unrecognized fields are silently dropped during deserialization — may cause data integrity issues if SP output schema changes.
- **Hardcoded email** `partner@ecount.com` and address in `CreateBulkUser`: These will appear in payment records and notifications for bulk-provisioned users — may create audit/compliance ambiguity.
