# Business Analyst — wirecard_wire-transfer-agen_LIB

## Business Purpose
The Wire Transfer Agent (WTA) is a Spring Boot batch service that processes wire transfer transactions for the Wirecard/Northlane NAM platform. It is the internal bridge between the CCP/platform event bus and the NAM Bank Agent (which handles the external bank file exchange). It processes both inbound wire transfers (incoming funds from banks to cardholder accounts) and outbound wire transfers (cardholder-initiated send-money-to-bank-account).

## Capabilities

### Batch Jobs (5 defined in BatchJob enum)
| Job | Direction | Description |
|---|---|---|
| `import-incoming-wire-transfers` | Inbound | Reads JSON files of incoming wire transfer prototypes; validates and writes to platform/Oracle |
| `publish-cancel-wire-transfer-out` | Outbound | Reads cancel requests from Oracle; publishes CancelWireTransferOutEvent to EventHub |
| `import-wire-transfer-out-status-update` | Inbound | Reads status update files; imports wire transfer out status updates |
| `publish-wire-transfer-in-status-updated-event` | Outbound | Reads wire transfer in status changes from Oracle; publishes IncomingWireTransferStatusUpdatedEvent |
| `import-wire-transfer-out-notification-of-change` | Inbound | Reads NOC files; imports notifications of change for wire transfers out |

### Service Layer
- `WireTransferInService`: Wire transfer inbound processing
- `WireTransferOutService`: Wire transfer outbound orchestration
- `WireTransferOutStatusUpdateService`: Status update processing
- `WireTransferOutNotificationOfChangeProcessor`: NOC processing
- Email service: Operational email notifications

## Key Entities / Data
| Entity | Description |
|---|---|
| IncomingWireTransferPrototype | JSON file record for inbound wire transfer |
| IncomingWireTransferStatusUpdatePrototype | Status update for inbound wire |
| WireTransferOutStatusUpdatePrototype | Status update for outbound wire |
| IncomingWireTransferOutNotificationOfChangePrototype | NOC record for outbound wire |
| CancelWireTransferOutPrototype | Cancel request for outbound wire |
| NewWireTransferOutEvent | EventHub event: new wire-out with payee bank account and routing number |
| CancelWireTransferOutEvent | EventHub event: cancel wire-out |
| IncomingWireTransferStatusUpdatedEvent | EventHub event: wire-in status change |
| WireTransferOutStatusUpdatedEvent | Consumer event: wire-out status from NAM bank agent |
| WireTransferOutNotificationOfChangeEvent | Consumer event: NOC from bank |
| WireTransferOutCancellationStatusEvent | Consumer event: cancellation outcome from bank |
| S2SSendMoneyBankAccountRequest | REST API request: send money to bank account |
| S2CSendMoneyBankAccountRequest | REST API request (C2C variant) |

## Business Rules
1. `NewWireTransferOutEvent` carries: payee first/last name, bank name, bank account number, bank routing number, bank account type, transfer reason, execution date, amount — all required
2. Wire transfer out methods observed: S2S (system-to-system), S2C (system-to-customer), SEPA
3. Notifications of change (NOC) carry NACHA NOC codes (`AchNotificationOfChangeCode`)
4. `IncomingWireTransferPrototypeValidator` validates incoming wire transfer records before writing
5. JSON line format for batch file input (JsonLineMapper / JsonLineAggregator)
6. Files partitioned by directory (`FilesInDirectoryPartitioner`) — multi-file parallel processing
7. 90% minimum Jacoco code coverage enforced

## Business Flows
1. **Incoming wire transfer**: NAM bank agent deposits JSON file → WTA `import-incoming-wire-transfers` batch → validates → writes to Oracle → publishes status event to EventHub
2. **Outbound wire cancellation**: EventHub cancel event → Oracle → WTA `publish-cancel-wire-transfer-out` batch → publishes CancelWireTransferOutEvent
3. **Wire-out status update**: NAM bank agent deposits status file → WTA `import-wire-transfer-out-status-update` → Oracle update → publishes status event
4. **Wire-out NOC**: NAM bank agent deposits NOC file → WTA `import-wire-transfer-out-notification-of-change` → processes NOC

## Compliance Relevance
- `NewWireTransferOutEvent` carries bank routing number and bank account number — **Fedwire/CHIPS sensitive data**; governed by NACHA and banking regulations
- Payee name (first + last) in wire events — PII under CCPA/GDPR
- Transfer reason stored in event — may contain free-text PII
- Reg E applicability: incoming wire transfers credited to prepaid accounts are subject to Reg E error resolution
- `AchNotificationOfChangeCode` handling — NACHA NOC compliance required

## Risks
1. `NewWireTransferOutEvent` carries bank routing/account numbers in XML-serialised EventHub messages — if EventHub message store is not encrypted, financial account data at rest is unprotected
2. No observed idempotency mechanism for file-based batch input — duplicate file delivery could cause duplicate wire transfer processing
3. Wire transfer batch files stored on local filesystem in JSON format — plaintext financial data at rest
4. Email service for operational notifications may include sensitive wire transfer details in email content
