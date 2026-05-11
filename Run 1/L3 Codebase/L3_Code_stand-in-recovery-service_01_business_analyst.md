# 01 Business Analyst — stand-in-recovery-service

## Business Purpose
Critical payments infrastructure service that manages Stand-In Processing (STIP) recovery for Onbe's card and DDA (Demand Deposit Account) number allocation systems. When Wirecard/SASI card-number allocators fail or become unavailable, STIP stands in for authorisation decisions. This service (STIR — Stand-In Recovery) orchestrates the recovery procedure to re-synchronise card and DDA number serial state from STIP back into the primary systems after an outage, ensuring no card numbers or DDA account numbers are issued twice (no collisions) across the switchover boundary.

## Capabilities
- Manages named **recovery sessions** with lifecycle: start → active → end (COMPLETED | FAILED)
- Prevents concurrent recovery sessions (409 Conflict if a session is already active)
- Takes **snapshots** of current card-number and DDA-number serial state from both SASI (legacy allocator) and modern allocators
- Processes **recovery messages** from Azure Service Bus queues, replaying transaction data to reconcile number ranges
- Tracks per-session recovery progress (messages processed, errors, counts)
- Exposes DDA and card number upper-limit serial status for operational verification
- Supports **no-downtime switching** between DDA/card allocators (documented in `docs/`)
- Resets SASI upper-limit serials to NULL as part of switchover procedures
- Integrates with AccountManagementAPI, DebitAPI, and CSAPI v3 for card/account operations during recovery

## Entities
- **RecoverySession** — session record: sessionId, status (ACTIVE | COMPLETED | FAILED), startedBy, startedAt, endedAt, externalRef
- **RecoverySnapshot** — point-in-time snapshot of card/DDA serial state at session start
- **RecoverySnapshotCardDetail** / **RecoverySnapshotDdaDetail** — per-number-range detail rows within a snapshot
- **RecoveryMessage** — Azure Service Bus message captured for replay; tracks attempt history
- **RecoveryMessageAttempt** — individual processing attempt record (success/failure, timestamp)
- **RecoveryEvent** — audit event log for session lifecycle changes
- **CardNumberStatus** / **DdaNumberStatus** — current upper-limit serial state
- **MessageTransfer** — inter-system message transfer tracking

## Business Rules
- Only one recovery session may be active at a time
- Session start stops the normal message processor and starts the session-aware processor
- Session end stops the session processor (normal processor restart is a separate operator action)
- Snapshot buffer and safety-margin configurable (`stir.snapshot.buffer`, `stir.snapshot.safety-margin`)
- Session guard interval controls periodic session health checks (`stir.session.guard.interval-ms`)
- `startedBy` is required when opening a session; `externalRef` is optional for audit correlation

## Flows
1. Operator detects STIP stand-in period ending; calls `POST /recovery/sessions?startedBy=<operator>`
2. Service creates `RecoverySession`, stops normal Service Bus processor, starts session processor
3. Session processor consumes recovery messages from Azure Service Bus, replaying card/DDA allocations
4. Operator monitors progress via `GET /recovery/sessions/active/progress`
5. Operator verifies DDA/card serial upper limits via `GET /recovery/sessions/dda-card-serials`
6. Optionally resets SASI upper limits: `POST /recovery/sessions/reset-upper-limits`
7. Operator ends session: `POST /recovery/sessions/end?status=COMPLETED`
8. Service stops session processor; normal operations resume

## Compliance
- Critical path for payment card issuance — disruption constitutes a payment system outage; availability is a Reg E, NACHA, and network rule obligation
- Card and DDA number ranges are directly linked to PCI DSS Req. 3 (protect stored cardholder data); number allocation integrity prevents duplicate PAN issuance
- All session and recovery events should be retained as audit records for PCI DSS Req. 10 (track access to network resources)
- STIP stand-in decisions during recovery may include authorisation responses that must reconcile with Reg E's error resolution timeframes
- Credentials (DB passwords, Azure Service Bus keys) stored in Azure Key Vault per config

## Risks
- This is the most operationally critical service in the batch: a bug during recovery could result in duplicate card/DDA number issuance — a catastrophic PCI DSS and network rule violation
- The `POST /recovery/sessions/reset-upper-limits` endpoint modifies serial state directly — must be restricted to authorised operators only; no authorisation visible in the controller
- All `@Deprecated(forRemoval = true)` endpoints in `RecoveryServiceController` should be removed before production to reduce attack surface
- Azure Service Bus session processor state management is complex; a crash mid-session leaves the system in an indeterminate state requiring manual intervention
