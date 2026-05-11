# Business Analyst — payment-service_SVC

## Business Purpose
The core payment processing service for Onbe's legacy ecount/EcountCore platform. It implements the back-end payment lifecycle: certificate creation (prepaid card issuance), bulk user provisioning, email notification creation, stop payment processing, and transaction/device/notification record management against the `cbaseapp` SQL Server database. It exposes its functionality via XML-RPC (`/dispatch.asp`) for consumption by all other ecount platform services.

## Capabilities
- **StopPayment**: Cancels an active payment by paymentId with reason `CANCELED_BY_BUYER`.
- **CreateCertificate**: Creates a payment certificate (card/prepaid instrument issuance); includes SASI recovery path (`CreateCertificateSasiRecovery`).
- **CreateEmailNotifications**: Creates email notification records for payment events.
- **CreateBulkUser**: Provisions a batch user account with a default profile, DDA device, and ecount member record — used for programmatic user creation.
- **Transaction management**: DAO operations for creating transaction history, payment action items, request groups, notification requests, payment constraints, transaction devices, and updating transactions/certificate info/event status.
- **Application info lookup**: `GetApplicationInfo` and `GetPaymentExpiryDate`.
- **Program promotion events**: `GetProgramPromotionEventsDetails` and `UpdateStatusForEvent`.
- **Bulk email validation**: `ValidateBulkEmail`.
- **Health check**: HTTP `/hc` endpoint via Spring MVC (`DispatcherServlet` on `/hc`).

## Key Entities
| Entity | Description |
|--------|-------------|
| Certificate | Payment instrument (prepaid card/virtual instrument); created by `CreateCertificate` |
| DDA | Demand Deposit Account device linked to a user |
| Payment | Core payment record with constraint and action item tracking |
| Transaction | Transaction history record |
| Notification Request | Email notification trigger for payment events |
| BulkUser | Batch-provisioned user with default ecount member and DDA |
| Request Group | Groups related payment requests |
| Program Promotion Event | Lifecycle event for promotional payment programs |

## Business Rules
- StopPayment requires `paymentId > 0`.
- CreateCertificate validates input before delegation (`input.validate()`).
- CreateEmailNotifications validates input before processing.
- CreateBulkUser requires `app_affiliate_id != 0`; throws `PaymentServiceException` with `ERROR_CODE.UNEXPECTED_EXCEPTION` if affiliate ID is missing.
- Default bulk user profile address: 555 North Lane, Conshohocken, PA 19428 — **hardcoded** in `PaymentServiceImpl.java` (lines 161-166).
- Default bulk user email: `partner@ecount.com` — hardcoded.
- Default bulk user phone: `610-941-4600` — hardcoded.
- Minimum Java module opens configured for Tomcat 10 compatibility (`java.base/java.lang`, `java.base/java.io`, etc.).

## Key Flows
1. **Certificate issuance**: XMLRPC request → `EPaymentProxy.CreateCertificate()` → `PaymentServiceImpl.CreateCertificate()` → `PaymentServiceLibraryImpl.createCertificate()` → DAO SPs in cbaseapp.
2. **Stop payment**: XMLRPC request → `PaymentServiceImpl.StopPayment(paymentId, agent)` → library → DAO `updateTransaction`.
3. **Bulk user creation**: XMLRPC request → `CreateBulkUser(agentName, affiliateId, programId, name)` → create user → create ecount member → create DDA device.
4. **Email notification**: XMLRPC request → `CreateEmailNotifications(input, agent)` → library → DAO `createNotificationRequest`.

## Compliance Relevance
- Core payment processing service — directly in PCI DSS scope (Req 6, 10, 12).
- Creates and manages transaction history records — audit trail for PCI DSS Req 10.
- Stop payment capability supports Reg E dispute/error resolution obligations.
- SSL/TLS on all DB connections (`TLSv1.2`).
- XMLRPC interface is unauthenticated at the service level; access control via network/VPN and agent-based authorization in the ecount layer.
- `certfile_qa.crt` bundled in Docker image for QA environment trust store.

## Risks
- **Hardcoded contact information** in `PaymentServiceImpl.CreateBulkUser()` — default user profile with a specific physical address, email, and phone number hardcoded in Java source (lines 161-166). This is a data integrity risk for bulk user creation.
- **Raw `Map` and `Hashtable`** usage throughout — no type safety on context maps.
- **ThreadLocal logger**: `PaymentServiceImpl` uses `ThreadLocal<Logger>` which is an unusual pattern and adds complexity without clear benefit.
- **Jakarta servlet shim** (`jakarta/servlet/http/HttpUtils.java`) — a manually created shim placed in the WAR source to satisfy Jakarta EE compatibility; indicates non-standard Jakarta migration approach.
- **Tests marked to skip**: `MAVEN_BUILD_OPTS: "-Dmaven.test.skip=true"` in GitLab CI — tests are not run during build.
