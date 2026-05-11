# Business Analyst — wirecard_check-agent_LIB

## Business Purpose
`check-agent` is a **Gen-2 payment disbursement microservice** for the Wirecard/Northlane issuing platform. It manages the full lifecycle of **paper check disbursements** issued to cardholders or beneficiaries. It orchestrates check creation, status tracking, voiding, reissuance, and event notification, integrating with the Wirecard CCP (Call Center Platform) for fund reservations and the Wirecard Brand Server for check template configuration.

## Capabilities
1. **Check Creation**: Accepts check creation requests (S2S and S2C APIs), reserves funds via CCP, assigns a unique check number (from an Oracle sequence), applies a check template, and persists the check record.
2. **Check Status Management**: Tracks check status through states (`CheckStatus` enum) driven by inbound `CheckStatusUpdatedEvent` messages from downstream check printing/mailing systems.
3. **Check Void**: Marks a check as `PENDING_VOID`, optionally attaches an agent note, and publishes a `VoidCheckEvent` to the event hub.
4. **Check Reissue**: Combines void + creation: marks the original check for reissuance (`reissue=true`), voids it, and the downstream system initiates a new check.
5. **Event Hub Integration**: Publishes `NewCheckEvent` and `VoidCheckEvent` to an ActiveMQ (or in-memory mock) topic `APP/CHECKAGENT`. Consumes `CheckStatusUpdatedEvent` from an inbound topic.
6. **Email Notifications**: Sends operational email notifications (e.g., job execution alerts) to configured recipients using the `production-support-template.txt` template.
7. **Retry Batch**: `EventsRetryBatchApp` — a Spring Batch job that retries failed EventHub publications.
8. **REST API (S2S and S2C)**: Exposes versioned REST endpoints for service-to-service (`S2SCheck`) and service-to-customer (`S2CCheck`) check operations.
9. **Idempotent Event Consumption**: `@IdempotentSubscriber` AOP aspect ensures `CheckStatusUpdatedEvent` is not processed twice (tracks processed event IDs in the `EVENT_HUB_EVENT` table).

## Entities / Domain Objects
| Entity | Description |
|---|---|
| `Check` (`CHECK_TRANSACTION`) | Core check disbursement record — amount, currency, payee names, address, check number, status, brand, alias |
| `CheckHistory` (`CHECK_TRANSACTION_HISTORY`) | Audit trail of status transitions |
| `CheckNote` (`CHECK_TRANSACTION_NOTE`) | Agent notes attached to a check (channel, context, subject, content) |
| `CheckNoteHistory` (`CHECK_TRANSACTION_NOTE_HISTORY`) | History of note changes |
| `CheckReissue` (`CHECK_TRANSACTION_REISSUE`) | Records reissuance details when a check is reissued |
| `EventHubEvent` (`EVENT_HUB_EVENT`) | Tracks EventHub message publish/consume state (idempotency, retry) |

## Business Rules
1. Each check has a unique `CHECK_NUMBER` (Oracle sequence `check_number_seq`) and a unique `REFERENCE_ID` (guaranteed by `UDX_CHECK_TX_REF_ID` unique constraint).
2. A check must have a fund reservation (`RESERVATION_ID`) from CCP before it can be created.
3. Check status transitions are driven by inbound events — the service does not arbitrarily change status.
4. A void operation sets status to `PENDING_VOID` and sets `PUBLISH_STATE = TO_PUBLISH`.
5. A reissue sets `reissue=true` on the original check before voiding.
6. Idempotency: if a `CheckStatusUpdatedEvent` with the same event ID is received twice, it is silently skipped.
7. Check expiration period is configurable (`check.expiration-days`); default 180 days.
8. Check prefix and template ID are configurable per deployment (`check.prefix`, `check.check-template-id`).

## Flows
1. **New Check**: S2S/S2C REST call → `CheckService.createCheck()` → CCP fund reservation → Oracle sequence for check number → persist `CHECK_TRANSACTION` → publish `NewCheckEvent` to EventHub.
2. **Status Update**: EventHub consumer receives `CheckStatusUpdatedEvent` → idempotency check → `CheckService.updateCheck()` → persist status + `CHECK_TRANSACTION_HISTORY`.
3. **Void Check**: REST void call → `CheckService.voidCheck()` → set `PENDING_VOID` → publish `VoidCheckEvent`.
4. **Retry Batch**: Scheduled Spring Batch job re-publishes events where `PUBLISH_STATE = TO_PUBLISH` and publication has failed.

## Compliance Relevance
- **PCI DSS Requirement 3 (Protect Stored Cardholder Data)**: Check records contain payee name, address, and check amounts. These are not PAN/CVV but are PII under GLBA, GDPR, and CCPA.
- **PCI DSS Requirement 4.2 (Protect CHD in transit)**: EventHub messages and REST calls must use TLS. TLS is enabled for the datasource (`tlsEnabled: true` in `application.yml`).
- **PCI DSS Requirement 10 (Audit Logging)**: `CHECK_TRANSACTION_HISTORY` and `CHECK_TRANSACTION_NOTE_HISTORY` tables provide an audit trail of all state changes.
- **Reg E / NACHA**: Check disbursements fall under payment instrument regulations. Accurate status tracking and reissuance capabilities are required for consumer protection.

## Risks
1. EventHub notification failures are caught and logged as WARN without halting the transaction (`CheckServiceImpl.java:95–99`). A check can be created without the event being published, causing downstream systems to miss the notification.
2. No compensation mechanism if the CCP fund reservation succeeds but the check DB insert fails — potential for orphaned reservations.
3. Plaintext credentials in `application.yml` (QA environment): `ccp.client.password: aaaa1111`, `iss-auth-server` URL pointing to `wirecard.sys` internal hostnames. If this configuration is not properly overridden in production, it poses a security risk.
