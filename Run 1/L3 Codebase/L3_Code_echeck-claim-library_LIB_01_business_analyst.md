# echeck-claim-library_LIB — Business Analyst Report

## Repository Overview

`echeck-claim-library_LIB` is the **eCheck claim processing library** — a two-module Maven project providing the business logic for claiming electronic check (eCheck) payments on the eCount platform. An "eCheck" in this context is not necessarily a traditional paper check — it is the eCount platform's electronic payment instrument (analogous to a virtual prepaid value unit) that recipients can claim and redeem.

The repository has two sub-modules:
- `eCheckClaim-common` — shared interfaces, value objects, and utilities
- `eCheckClaim-svc` — the service implementation with DAO layer and domain objects

The parent POM (`pom.xml`) inherits dependencies from a shared parent and sets up the multi-module build. The library version is defined in individual module POMs.

---

## Business Purpose

### Core Function: eCheck Payment Claim Processing
The library enables a recipient (cardholder) to **claim a pending eCheck payment** — converting a payment in "pending/claimable" state into an active, accessible account balance. The claim process involves:
1. **Certificate validation** — verify the redemption code/verification code is valid and not expired
2. **Velocity checking** — enforce anti-fraud rate limits on claim attempts
3. **Transaction creation** — create the user transaction history record
4. **Money transfer** — execute the fund transfer from the claimable payment to the recipient's account
5. **Transaction device creation** — link the transaction to specific account devices
6. **Status update** — mark the transaction as completed or failed

### Secondary Functions
- **Certificate detail retrieval** — `dbo.get_op_certificate_detail` stored procedure
- **Template detail retrieval** — `dbo.get_certificate_template_detail` (for UI display of certificate/eCheck imagery)
- **User eCount ID update** — `dbo.update_user_ecount_id` (links user to eCount account)
- **Service permission checking** — `dbo.check_service_permissions` (velocity/fraud control)

---

## Business Entities and Workflow

### Payment Lifecycle States (`PaymentVO.Action`)
The library handles payments in these states (defined in `PaymentVO.java` lines 9–24):

| Action Code | State | Business Meaning |
|---|---|---|
| 100 | `CREATED` | Payment issued, awaiting claim |
| 200 | `NOTIFICATION_EMAIL_SENT` | Recipient notified |
| 300 | `CLAIMED` | Successfully claimed by recipient |
| 400 | `CANCELED_BY_BUYER` | Purchaser revoked payment |
| 500 | `LOCKED_BY_ADMINISTRATOR` | Admin hold |
| 600 | `DENIED_BY_RECIPIENT` | Recipient rejected |
| 700 | `RESEND_NOTIFICATION` | Notification re-triggered |
| 800 | `NOTIFICATION_RESENT` | Notification re-sent |
| 1000 | `FROZEN_BY_FRAUD_SYSTEM` | Fraud hold — strategic delay |
| 1100 | `ACCEPTED_BY_FRAUD_DEPT` | Fraud review cleared |
| 1200 | `REJECTED_BY_FRAUD_DEPT` | Fraud rejected |
| 1300 | `HELD_FOR_REVIEW` | CSA review queue |
| 1400 | `IN_REVIEW_BY_CSR` | Under active CSR review |
| 1500 | `REISSUED` | Payment reissued |
| 50 | `QUEUED_FOR_RELEASE` | Pre-release queue |
| 99 | `RELEASED` | Released from hold |

### Payment Types (`PaymentVO.Type`)
| Type Code | Type | Description |
|---|---|---|
| 0 | `PERSON_TO_PERSON` | P2P payment |
| 1 | `APF_BULK` | Automated Program Funding bulk issuance |
| 2 | `CERTIFICATE` | Certificate/eCheck instrument |
| 3 | `BULK_CERTIFICATE` | Bulk certificate issuance |

---

## Key Business Rules

1. **Claim Expiry** — `PaymentVO.isActive()` (line 179) checks if the payment's expiration date has passed. Expired payments cannot be claimed.
2. **Activation Date Gate** — `PaymentVO.isFutureDate()` (line 198) checks if the activation date is in the future, preventing premature claims.
3. **30-Day Freshness** — `PaymentVO.isGreaterThanMonthOld()` (line 156) checks if the payment is more than 30 days old, used for reissue eligibility decisions.
4. **Strategic Delay (Fraud Hold)** — `PaymentVO.activateStrategicDelay()` (line 195) sets status to `FROZEN_BY_FRAUD_SYSTEM`, implementing a fraud delay mechanism.
5. **Velocity Control** — `UserTransaction.checkVelocity()` (lines 140–171) calls `dbo.check_service_permissions` to enforce rate limits. Returns codes:
   - `-1` or `6200` = Failed permission
   - `-2` = No velocities found
   - `>0` = Failed velocity constraint (constraint ID returned)
6. **DDA-Only Flow** — `ECheckClaimInput.isDDAOnly()` flag allows the claim to be restricted to DDA (bank account) redemption only.
7. **Confirmation Code** — `updateTransactionStatus2` returns a `confirmation_code` that is the final receipt for the claim transaction.

---

## Transaction Execution Flow

`UserTransaction.execute()` (lines 342–400) defines the complete claim transaction lifecycle:
1. `preProcess()` → calls `dbo.create_user_transaction_history_item` to register the attempt
2. `checkVelocity()` (optional) → calls `dbo.check_service_permissions`
3. `begin()` → calls ECountCore `eTransfer.begin` to start the money transfer
4. `commit()` → calls ECountCore `eTransfer.commit` to complete the transfer
5. `createTransactionDevices()` → calls `dbo.create_user_transaction_device` for each device
6. `postProcess()` → calls `dbo.update_transaction_status2` and captures confirmation code

---

## Regulatory Relevance

### Reg E (Electronic Fund Transfers Act)
The eCheck claim process constitutes an electronic fund transfer. The `UserTransaction.execute()` flow and its error states must map to Reg E §1005.11 error resolution categories:
- `UNEXPECTED EXCEPTION` in `preProcess` = system error requiring escalation
- Velocity failure (code 100/101/102) = service restriction requiring disclosure
- Transfer commit failure = funds transfer error requiring notification

### NACHA
If the claim triggers an ACH debit to fund the payment, NACHA Rules apply. The `UserTransactionVO.EcountActivityCode` (referenced in `UserTransaction.java` line 73) maps to ACH transaction types.

### GLBA / CCPA / GDPR
`UserTransaction.java` carries `ipAddress`, `memberId`, `userId` — all personal data under CCPA/GDPR. The IP address is stored in `user_transaction_history` — a PII-containing table.

### PCI DSS
The library processes payment redemption — it is in the CDE boundary. `ECheckClaimDAOImpl.java` constructs and executes SQL against `cbaseapp` — the core payments database. PCI DSS Requirements 6, 7, 8, and 10 apply.
