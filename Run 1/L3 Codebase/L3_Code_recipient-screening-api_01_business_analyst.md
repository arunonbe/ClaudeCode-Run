# Business Analyst View — recipient-screening-api

## Business Purpose

`recipient-screening-api` is a Gen-3 NexPay/Onbe microservice responsible for OFAC (Office of Foreign Assets Control) and sanctions screening of payment recipients before disbursements are processed. When a payout is initiated — prepaid card load, ACH credit, push-to-card, or other rail — the recipient's identity must be screened against sanctions lists to ensure Onbe is not facilitating transactions with Specially Designated Nationals (SDNs) or restricted entities. This service orchestrates that screening workflow, delegates to an external sanctions vendor (via the `om-recipientsanctioning-svc` API), and applies the resulting block or approval status to the recipient's account in the eCount/ECountCore system.

## Capabilities

- **Synchronous screening request**: `POST /api/v1/screening/request` accepts a recipient's identity information (name, address, date of birth, email, phone, DDA number, program ID) and returns a sanction status: APPROVED, REFERRED, DECLINED, or IN_PROGRESS.
- **Sanction webhook processing**: Receives asynchronous webhook callbacks from the sanctions vendor when a screening result is updated (e.g., a REFERRED case is resolved to APPROVED or DECLINED), and applies the status change to the recipient's account.
- **Account status propagation**: On DECLINED or REFERRED status, the service resolves the DDA number to associated member accounts via ECountCore and blocks the relevant card/DDA devices.
- **BIN/Bank friendly configuration resolution**: Maps a program ID to a "friendly configuration ID" used by the upstream sanctions service to apply program-specific screening rules.
- **Pending record management**: Tracks screening operations that could not complete (e.g., due to downstream errors) in a `recipient_screening_pending` table for retry.

## Client and Cardholder Impact

This service is on the critical path for all payout disbursements in the NexPay platform. A failure or false-positive DECLINED result prevents a legitimate recipient from receiving their payment. A false-negative or service outage allows a sanctioned entity to receive funds, creating regulatory exposure. Cardholder-facing impact:
- APPROVED recipients receive their payment without delay.
- REFERRED recipients have their account blocked pending manual review.
- DECLINED recipients have their account permanently blocked.

## Business Rules in Code

- **DDA-to-member resolution**: The service uses the DDA number as the reference key to locate eCount member records. This is the primary linkage between the sanctions vendor's reference and Onbe's internal account system.
- **Feature flags**: Two boolean configuration properties control whether account status updates occur: `isUpdateAccountInApiCallEnabled` (default `false` in prod) and `isUpdateAccountInWebhookEnabled` (default `true` in prod). This allows the webhook-driven flow to be the primary update path while the synchronous API call path remains a fallback.
- **BIN/Bank mapping**: A `bin_bank_friendly_config_map` database table maps program IDs to vendor-specific configuration IDs. If no mapping is found, the screening request is rejected with HTTP 400.
- **Status mapping**: Vendor statuses (APPROVED, REFERRED, DECLINED, IN_PROGRESS) are translated to internal `SanctionStatus` enum values used to drive account blocking.

## Regulatory Obligations

- **OFAC/Sanctions**: The core business function. PCI DSS Req 12.4 and BSA/AML/OFAC regulations require screening of transaction parties. This service is a primary OFAC control.
- **Reg E**: Blocking a consumer's DDA or card based on sanctions screening has immediate Reg E implications. Error notices, dispute rights, and re-crediting obligations apply if a block is applied incorrectly.
- **GDPR/CCPA**: The service processes PII (first name, last name, address, DOB, email, phone, DDA number) for EU and US residents. Data minimization and purpose limitation apply — PII should only be forwarded to the sanctions vendor as required for screening.
- **GLBA**: Member financial information (DDA linkage, account status) is protected under GLBA data safeguard requirements.

## Key Business Risks

1. **Auth disabled in SecurityConfig**: `anyRequest().permitAll()` and CSRF disabled exposes the screening endpoint without authentication, creating a risk that unauthorized actors could query or trigger sanctions screening on arbitrary identities.
2. **Async account update errors are swallowed**: In `RecipientScreeningService`, async account updates use `CompletableFuture.runAsync()` with a catch block that only logs errors. A failed account block is not surfaced to the caller.
3. **False-block risk on REFERRED status**: REFERRED status blocks the account pending manual review, which could harm legitimate recipients if the vendor's screening generates false positives at scale.
