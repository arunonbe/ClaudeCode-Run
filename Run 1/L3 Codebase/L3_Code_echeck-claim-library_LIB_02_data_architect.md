# echeck-claim-library_LIB — Data Architect Report

## CRITICAL FINDING: Hardcoded Database Credentials in Source Control

**File**: `eCheckClaim-svc/src/main/resources/ECheckClaimDAO.xml` (lines 74–78)

```xml
<bean id="CbaseappDataSource" class="org.apache.commons.dbcp.BasicDataSource">
    <property name="driverClassName" value="net.sourceforge.jtds.jdbc.Driver" />
    <property name="url" value="jdbc:jtds:sqlserver://ppamwdcdifsql1:2232/cbaseapp" />
    <property name="username" value="b2ctest" />
    <property name="password" value="b2ctest" />
</bean>
```

**A SQL Server service account username and password are hardcoded in plaintext in a Spring XML configuration file committed to the git repository.**

Exposed credentials:
- **Server**: `ppamwdcdifsql1` (SQL Server host)
- **Port**: `2232`
- **Database**: `cbaseapp` (the core payments database)
- **Username**: `b2ctest`
- **Password**: `b2ctest`

**Impact**:
- Anyone with read access to this repository can obtain credentials to connect to the `cbaseapp` SQL Server database
- `cbaseapp` is the core payments database containing cardholder accounts, transaction history, payment records, and potentially card account data
- This is a **PCI DSS Requirement 8.3.1** violation (passwords must not be hard-coded)
- This is a **GLBA Safeguards Rule** violation
- The credential `b2ctest/b2ctest` suggests this may be a test/default credential — confirming whether these credentials work against production requires immediate investigation

**Immediate Actions Required**:
1. Rotate the `b2ctest` SQL Server credentials immediately
2. Audit all git history for any other instances of credentials
3. Replace with externalized configuration (Spring PropertySource + secrets vault)
4. Verify whether `ppamwdcdifsql1:2232/cbaseapp` is a production, staging, or test server

---

## Database Architecture

The library connects to the **`cbaseapp`** SQL Server database — the core eCount payments database. The JDBC connection uses the JTDS driver (`net.sourceforge.jtds.jdbc.Driver`) — a legacy open-source SQL Server driver.

Connection pool: Apache Commons DBCP (`org.apache.commons.dbcp.BasicDataSource`) — no connection pool size limits are configured in `ECheckClaimDAO.xml`, meaning unlimited connections could be acquired, risking database connection exhaustion.

---

## Stored Procedures Invoked

All database operations use SQL Server stored procedures. From `ECheckClaimDAO.xml` (lines 25–66):

| Bean ID | Stored Procedure | Purpose |
|---|---|---|
| `getCertificateDetail` | `dbo.get_op_certificate_detail` | Retrieves eCheck certificate details by verification code |
| `getTemplateDetail` | `dbo.get_certificate_template_detail` | Retrieves HTML template for certificate display |
| `createUserTransactionHistory` | `dbo.create_user_transaction_history_item` | Creates transaction audit record |
| `createTransactionDevice` | `dbo.create_user_transaction_device` | Links transaction to account device |
| `checkServicePermission` | `dbo.check_service_permissions` | Velocity and permission checking |
| `updateTransactionStatus2` | `dbo.update_transaction_status2` | Updates transaction outcome + returns confirmation code |
| `claimPayment` | `dbo.claim_payment` | Executes the actual payment claim |
| `updateUserEcountId` | `dbo.update_user_ecount_id` | Links user to eCount account ID |

All stored procedures are in the `dbo` schema of `cbaseapp`.

---

## Key Value Objects and Their Database Mappings

### `CertificateVO.java` (2,661 bytes) — maps to `dbo.get_op_certificate_detail` output
| Field | Type | Sensitivity |
|---|---|---|
| `verificationCode` | String | Payment credential — HIGH |
| `certificateId` | int | Internal |
| `paymentId` | int | Payment reference |
| `templateId` | int | UI template reference |
| `echeckId` | String | eCheck instrument ID |
| `buyerId` | int | Purchaser user ID |
| `recipientId` | int | Recipient user ID |
| `recipientFirstName`, `recipientLastName` | String | **PII — Name** |
| `senderName` | String | Purchaser name — PII |
| `amount` | int (cents) | Financial |
| `lastAction` | int | Payment status code |
| `lastActionDate`, `activationDate`, `createdDate`, `expirationDate` | Date | Date fields |
| `memo` | String | User-entered text |
| `paymentType` | int | Payment classification |
| `affiliateId` | int | Program ID |
| `isSpinGame` | boolean | Gamification flag |

### `PaymentVO.java` — maps to payment records
| Field | Type | Sensitivity |
|---|---|---|
| `paymentId` | int | Internal |
| `amount` | int (cents) | Financial |
| `echeckId` | String | eCheck ID |
| `verificationCode` | String | **Payment credential — HIGH** |
| `buyerId`, `recipientId` | int | User IDs |
| `recipientEmail` | String | **PII — Email** |
| `recipientFirstName`, `recipientLastName` | String | **PII — Name** |
| `activationDate`, `createdDate`, `expirationDate`, `lastActionDate` | Date | Dates |
| `memo` | String | Free text |
| `reissuingPaymentId` | Integer | Reissue chain reference |

### `UserTransactionVO.java` (6,731 bytes) — maps to `user_transaction_history` table
| Field | Type | Sensitivity |
|---|---|---|
| `userId` | int | User ID |
| `ipAddress` | String | **PII — IP Address (GDPR)** |
| `memberId` | String | Account identifier |
| `amount`, `fee` | int (cents) | Financial |
| `serviceType` | int | Transaction type |
| `transactionId` | int | Transaction audit ID |
| `confirmationCode` | String | Transaction receipt |
| `ecountTransferId` | String | ECount transfer GUID |
| `ecountActivityCode` | String | ACH activity type |
| `addenda` | Dictionary | PPD/xPPD addenda |

### `TransactionStatusVO.java` (2,272 bytes)
Tracks transaction processing phases:
- `INIT`, `PRE_PROCESS`, `VELOCITY_CHECK`, `EE_BEGIN`, `EE_COMMIT`, `CREATE_TX_DEVICES`, `POST_PROCESS`

### `ClaimTransactionVO.java` (1,794 bytes)
Encapsulates the claim input parameters passed to the domain layer.

### `TransactionDeviceVO.java` (1,146 bytes)
Links a transaction to an account device (card/DDA); includes `debitCredit` direction flag.

---

## Database Tables Implied

Based on stored procedure names and value objects:

| Inferred Table | Database | Purpose |
|---|---|---|
| `certificate` or `op_certificate` | cbaseapp | eCheck certificate records |
| `certificate_template` | cbaseapp | HTML templates for certificate display |
| `user_transaction_history` | cbaseapp | Transaction audit trail — stores IP address, amount, fees |
| `user_transaction_device` | cbaseapp | Links transactions to account devices |
| `user` or `ecount_user` | cbaseapp | User records with eCount ID |
| `payment` or `echeck_payment` | cbaseapp | Payment records with all lifecycle states |

---

## Sensitive Data Summary

| Data Element | Classification | Table/Object | Risk |
|---|---|---|---|
| `verificationCode` / `redemptionCode` | Payment Credential | `certificate`, `PaymentVO`, `ECheckClaimInput` | High — enables payment claim |
| `echeckId` | eCheck Instrument ID | `certificate` | High — payment identifier |
| `recipientFirstName`, `recipientLastName` | PII — Name | `PaymentVO`, `CertificateVO` | GDPR/CCPA |
| `recipientEmail` | PII — Email | `PaymentVO` | GDPR/CCPA |
| `ipAddress` | PII — IP Address | `user_transaction_history`, `UserTransactionVO` | GDPR recital 49 |
| `memberId` | Account Identifier | `UserTransaction`, `ECheckClaimInput` | Internal |
| `amount` | Financial | All transaction VOs | GLBA |
| DB credentials `b2ctest/b2ctest` | **Credentials — CRITICAL** | `ECheckClaimDAO.xml` lines 76–77 | **PCI DSS 8.3.1 VIOLATION** |
