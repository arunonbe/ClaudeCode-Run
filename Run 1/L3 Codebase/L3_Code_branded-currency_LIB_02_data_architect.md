# branded-currency_LIB — Data Architect View

## Data Stores

### Primary Database: `cbaseapp` (Microsoft SQL Server)
- **Connection**: Configured in `brandedCurrencyContext.xml` via Spring `DriverManagerDataSource` bean `CbaseappDataSource`. The JDBC driver is `net.sourceforge.jtds.jdbc.Driver` (jTDS).
- **Test connection** (committed to source, `brandedCurrencyTestContext.xml` line 22–34): `jdbc:jtds:sqlserver://ppamwdcdifsql1.nam.nsroot.net:2232/cbaseapp`, user `b2ctest`, password `b2ctest` — plaintext in version control.
- **Schema owner**: `dbo` (all stored procedure calls use `dbo.<proc_name>`).

### External / Platform Data Stores
- **ECountCore / xplatform**: Money movement is delegated to `MoneyTransferHelper` (from `com.ecount` / `xplatform` dependency v6.1.9). This system manages ecard, echeck, DDA, IEFT device ledgers. No direct SQL is issued against xplatform from this library.
- **CBase MemberManager**: Member PII lookup is performed via `IMemberManager.InquiryBasic()` (from `com.cbase.business.core.IMemberManager`). This calls into the CBase platform, not `cbaseapp` directly.

---

## Schema & Tables

The library does not define or migrate schema directly. All database access is through stored procedures. The following tables/stored procedures are referenced and imply schema:

### Stored Procedures Called (all `dbo.*`)

| Stored Procedure | Called From | Description |
|---|---|---|
| `dbo.create_certificate` | `CreateCertificateSpringImpl` | Inserts payment + certificate rows; returns `payment_id`, `certificate_id`, `claim_code` |
| `dbo.get_op_certificate_detail_new` | `GetCertificateDetailSpringImpl` | Reads certificate + payment fields by `verification_code` |
| `dbo.get_op_certificate_detail_new` (IVR variant) | `GetCertificateDetailIVRSpringImpl` | Reads certificate by IVR claim code |
| `dbo.claim_payment` | `ClaimPaymentSpringImpl` | Marks payment as claimed; inputs: `user_id`, `verification_code`, `claim_transfer_id`, `claimed_by` |
| `dbo.update_payment` | `UpdatePaymentSpringImpl` | Updates `claim_transfer_id` and `echeck_id` on payment by `verification_code` |
| `dbo.create_payment_action_item` | `CreatePaymentHistorySpringImpl` | Appends action history row; inputs: `payment_id`, `action_code`, `action_data` |
| `dbo.check_claim_payment_constraints` | `CheckPaymentConstraintsSpringImpl` | Validates whether a payment can be claimed; return codes: 0=ok, 9901=not found |
| `dbo.create_reissued_payment_reference` | `CreateReissuedPaymentReferenceSpringImpl` | Links reissued payment to original |
| `dbo.update_create_certificate_info` | `UpdateCreateCertificateInfoSpringImpl` | Updates certificate record post-creation with member info |
| `dbo.get_certificate_templates` | `GetCertificateTemplatesSpringImpl` | Returns list of templates by category |
| `dbo.get_template_detail` / variant | `GetTemplateDetailSpringImpl` | Returns `card_html` and template metadata |
| `dbo.create_user_transaction_history_item` | `CreateUserTransactionHistoryItemSpringImpl` | Inserts `user_transaction_history` row; returns `transaction_id` |
| `dbo.update_transaction_status2` | `UpdateTransactionStatus2SpringImpl` | Updates transaction result; returns `conf_code`, `return_code` |
| `dbo.create_transaction_device` | `CreateTransactionDeviceSpringImpl` | Associates device (ecard, echeck, DDA) with transaction |
| `dbo.check_service_permissions` | `CheckServicePermissionSpringImpl` | Velocity + permission check; return -1/6200=no permission, -2=no velocity, >0=failed constraint |
| `dbo.get_user_transaction_velocity` | `GetUserTransactionVelocitySpringImpl` | Returns 14 velocity counters/amounts by user + credit_debit_flag + member_id |
| `dbo.get_user_service_constraints` | `GetUserServiceConstraintsSpringImpl` | Returns min/max values for user + service + unit_of_measure |
| `dbo.get_group_service_constraint_info` | `GetGroupServiceConstraintInfoSpringImpl` | Returns group-level constraint |
| `dbo.get_group_service_constraint_info_detail` | `GetGroupServiceConstraintInfoDetailSpringImpl` | Returns service_id, service_desc, min/max, unit_of_measure |
| `dbo.update_user_ecount_id` | `UpdateUserEcountIdSpringImpl` | Binds `ecount_id` (device GUID) to `user_id` |
| `dbo.get_op_unclaimed_payments` | `GetUnclaimedPaymentsSpringImpl` | Returns unclaimed CertificateVO list by `member_id` |
| `dbo.get_op_claimed_payments` | `GetClaimedPaymentsSpringImpl` | Returns claimed CertificateVO list by `member_id` (includes `claim_transfer_id`) |
| `dbo.get_member_id_from_code` (inferred) | `GetMemberIdFromCodeSpringImpl` | Resolves `verification_code` to `member_id` |
| `dbo.set_user_group` (inferred) | `SetUserGroupSpringImpl` | Assigns user to velocity group |
| `dbo.get_user_groups` (inferred) | `GetUserGroupsSpringImpl` | Retrieves user's velocity groups |
| `dbo.enotify_get_schedule_numbers_by_type` | `EmailScheduleSpringImpl` | Returns email schedule numbers by type |
| `dbo.enotify_set_action_template` (inferred) | `CreateEmailActionSpringImpl` | Sets email action template |
| `dbo.enotify_get_template_name_for_action` (inferred) | `GetTemplateNameSpringImpl` | Gets email template name |
| `dbo.enotify_list_one_schedule` (inferred) | `GetScheduleDetailSpringImpl` | Gets schedule detail |
| `dbo.get_event_handler_id_for_certificate_id` (inferred) | `GetEventHandlerIdForCertificateId` | Returns event handler IDs for virtual card stop-notification |

### Inferred Table Structure (from stored procedure I/O columns)

**Payment table** (inferred from `dbo.get_op_certificate_detail_new` and `dbo.create_certificate`):
- `payment_id` (int), `amount` (int, US pennies), `echeck_id` (varchar GUID), `verification_code` (varchar), `buyer_id` (int), `recipient_id` (int), `recipient_first_name`, `recipient_last_name`, `recipient_email` (varchar), `activation_date` (date), `expiration_date` (date), `created` (date), `last_action` (int), `last_action_date` (date), `memo` (varchar), `payment_type` (tinyint), `claim_transfer_id` (varchar UUID), `reissuing_payment_id` (int nullable), `apiFlag` (int).

**Certificate table** (inferred):
- `certificate_id` (int), `certificate_template_id` (int), `recipient_informal_name` (varchar), `sender_informal_name` (varchar), `image_path_thumbnail` (varchar), `subject` (varchar), `description` (varchar), `is_spin_game` (bit), `affiliate_id` (int, commented-out in queries).

**User transaction history table** (inferred from `dbo.create_user_transaction_history_item` and `dbo.update_transaction_status2`):
- `transaction_id` (int, auto), `user_id` (int), `service_type` (int), `ip_address` (varchar), `amount` (int), `fee` (int), `member_id` (varchar), `result_code` (int), `result_message` (varchar), `ecount_transfer_id` (varchar), `conf_code` (varchar output).

---

## Sensitive Data Handling

| Data Element | Class / Field | Current Handling | Risk |
|---|---|---|---|
| Full PAN (card number) | `CreditCardVO._number` / `getNumber()` | Unmasked `String`, passed in-memory to `MoneyTransferHelper.addCreditCardDevice()` | **CRITICAL** — PCI DSS Req. 3 violation if logged or serialized |
| CVV/CVC | `CreditCardVO._cvCode` / `getCVCode()` | Unmasked `String` | **CRITICAL** — PCI DSS Req. 3.3 prohibits storage of SAD |
| Recipient email | `PaymentVO._recipientEmail`, `CertificateVO`, stored via `dbo.create_certificate` | Stored in `cbaseapp`, no masking in VO | GDPR/CCPA concern |
| Recipient name (first, last) | `PaymentVO._recipientFirstName/LastName` | Stored in `cbaseapp` | GDPR/CCPA concern |
| Verification/claim code | `PaymentVO._verificationCode` | Stored in DB, passed in clear text in stored procedure params | Treat as authentication credential |
| Member ID (UUID) | `ClaimTransactionVO`, `UserTransactionVO` | String UUID, no encryption | Low risk but identifies cardholder |
| IP address | `UserTransactionVO._ipAddress` | Stored in `user_transaction_history` for velocity | May constitute PII under GDPR |
| DB credentials | `brandedCurrencyTestContext.xml` lines 27–33 | **Plaintext in source code** | **CRITICAL** — secret leakage |

---

## Encryption & Protection

- **No field-level encryption** in any VO or DAO class. PAN and CVV are passed as plaintext Java strings.
- **No tokenization**: There is no call to a tokenization vault for card data. Card details flow directly into `MoneyTransferHelper.addCreditCardDevice()`.
- **No TLS/SSL configuration** in this library layer (JDBC connection properties are not visible — the DataSource URL does not include `ssl=true` or `encrypt=true` parameters in the test context).
- **No password hashing or masking** for the test database credentials.
- The only partial protection is `CreditCardVO.last4Digits()` which returns the last 4 of the card number — but the full number is also accessible via `getNumber()`.

---

## Data Flow

```
Caller (web app / service)
    |
    v
[Transaction VO construction] — contains PAN, CVV, PII if AddFunds
    |
    v
[UserTransactionImpl / ClaimTransactionImpl / CertificatePurchaseTransactionImpl]
    |—— [MoneyTransferHelper (xplatform)] ——> ECountCore (ecard/echeck/DDA/IEFT ledger)
    |
    v
[Spring StoredProcedure implementations]
    |—— SELECT/EXECUTE via jTDS ——> cbaseapp (SQL Server)
    |         dbo.create_certificate, dbo.claim_payment, etc.
    |
    v
[CBase MemberManager (IMemberManager)]
    |—— InquiryBasic() ——> CBase platform (member registry)
    |
    v
[StopNotificationService (cbase.services)]
    |—— runService() ——> Notification scheduling system
```

---

## Data Quality & Retention

- **No data quality validation** within the library. Input validation is entirely the caller's responsibility.
- **No retention policy** implemented. Deletion, archival, or anonymization logic is absent.
- **Date arithmetic issues**: `PaymentVO.isGreaterThanMonthOld()` uses deprecated `Date.getDate()/getMonth()/getYear()` methods, which are not timezone-safe and can produce wrong results near month boundaries.
- **Null safety**: `GetCertificateDetailSpringImpl.execute()` casts `out.get("apiFlag")` and `out.get("reissuing_payment_id")` with null checks, but most other field mappings do not guard against null from the database, which will throw `NullPointerException` if the stored procedure returns unexpected nulls.
- **Amount representation**: All monetary amounts are stored as plain `int` (US pennies implied). No `BigDecimal` or explicit currency field. Currency is hard-coded US dollars with no multi-currency support.

---

## Compliance Gaps

1. **PCI DSS Req. 3.3**: `CreditCardVO` stores CVV (`_cvCode`). No SAD purge after authorization.
2. **PCI DSS Req. 3.4**: Full PAN stored as plaintext `String`. No truncation, masking, or encryption at rest or in transit within the VO layer.
3. **PCI DSS Req. 2.2.7**: Hardcoded database credentials in `brandedCurrencyTestContext.xml` committed to the repository.
4. **GDPR Art. 25 (Privacy by Design)**: No data minimization; recipient PII (name, email) is propagated through every certificate object unnecessarily.
5. **GDPR Art. 17 / CCPA**: No deletion or anonymization capability exists in the library.
6. **NACHA / Reg E**: ACH-related device types (IEFT, DDA) are present but no return-code handling for NACHA return codes (R01–R99) is implemented at this library level.
7. **Audit log completeness**: `dbo.create_payment_action_item` records lifecycle events, but the library does not enforce that all state transitions produce an audit record. For example, the `activateStrategicDelay()` method changes `lastAction` in memory but does not call `updateStatus()`.
