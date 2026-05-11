# Data Architect — wirecard_wire-transfer-agen_LIB

## Data Stores
| Store | Type | Notes |
|---|---|---|
| Oracle DB | RDBMS | Primary store; ojdbc8; two-schema pattern (consistent with FTC/NAM-bank-agent) |
| H2 in-memory | RDBMS | Dev/test only |
| ActiveMQ (EventHub) | Messaging | Both consumer and producer of wire transfer events |
| Local filesystem | File system | Batch JSON file staging: input/processed/failed/output directories |

## Inferred Schema
No Liquibase changelog was directly accessible in this repo's available files (db module follows same pattern as FTC). Schema is inferred from batch config and data prototype classes.

### Wire Transfer In (inbound — platform receives funds)
| Field | Source | Notes |
|---|---|---|
| Wire transfer record ID | IncomingWireTransferPrototype | Unique identifier |
| Status | WireTransferInStatusType | Enum: NEW, PROCESSED, FAILED, etc. |
| Method | WireTransferInMethod | Transfer method type |
| Amount/currency | AmountType | MoneyType |
| Account reference | AccountRef | Internal account |
| Transaction ID | String | Platform transaction reference |

### Wire Transfer Out (outbound — platform sends funds to bank)
| Field | Source | Notes |
|---|---|---|
| Transfer ID | NewWireTransferOutEvent | Platform-generated |
| Payee first name | NewWireTransferOutEvent | PII |
| Payee last name | NewWireTransferOutEvent | PII |
| Payee bank name | NewWireTransferOutEvent | |
| Payee bank account number | NewWireTransferOutEvent | **Sensitive financial data** |
| Payee bank routing number | NewWireTransferOutEvent | **Sensitive financial data** |
| Bank account number type | BankAccountNumberType | |
| Bank account type | BankAccountType | |
| Amount + fee | AmountType | MoneyType |
| Method | WireTransferOutMethod | S2S, S2C, SEPA |
| Transfer reason | String | Free text; may contain PII |
| Execution date | LocalDateTime | |
| NOC code | AchNotificationOfChangeCode | NACHA code |
| Status | WireTransferOutStatusType | Enum |
| Cancellation status | WireTransferOutCancellationStatusType | |

### Batch File Formats
| Format | Pattern | Notes |
|---|---|---|
| JSON Lines | One JSON object per line | `JsonLineMapper` / `JsonLineAggregator`; UTF-8 encoding |
| XML (EventHub events) | JAXB-annotated POJOs | `@XmlRootElement`, `@XmlElement` annotations throughout event classes |

## Sensitive Data Classification
| Field | Classification | Regulation |
|---|---|---|
| `payeesBankAccountNumber` | Sensitive financial — DDA account number | NACHA, PCI DSS scope (non-card), GLBA |
| `payeesBankRoutingNumber` | Sensitive financial — ABA routing | NACHA, GLBA |
| `payeesFirstName` / `payeesLastName` | PII | CCPA, GDPR, GLBA |
| `transferReason` | Potentially PII | Free text |
| `bankAccountIdentifier` | Financial reference | |
| `loginAlias` (in S2S request) | Internal identity reference | |

No PAN, CVV, or card track data observed. The sensitive data here is **bank account data** (routing + account number), which falls under GLBA and NACHA, not PCI DSS card data scope, but still requires appropriate protection.

## Encryption
- Database TLS: JKS truststore expected (consistent with FTC/NAM-bank-agent siblings; DataSourceConfiguration pattern)
- EventHub messages (XML): No message-level encryption observed — wire transfer events with bank account numbers transmitted over ActiveMQ without apparent payload encryption
- Local batch files (JSON): No encryption observed — bank account/routing numbers in plaintext JSON on batch server filesystem
- Transport to Oracle: TLS (ojdbc8 SSL)

## Data Flow
```
NAM Bank Agent
  │  (JSON file deposit to local filesystem)
  │
  ├── import-incoming-wire-transfers batch
  │   → Oracle DB (wire transfer in records)
  │   → EventHub (IncomingWireTransferStatusUpdatedEvent)
  │
  └── import-wire-transfer-out-status-update / NOC batches
      → Oracle DB
      → EventHub (status events)

EventHub (FTC, CCP events)
  │
  ├── CancelWireTransferOutEvent → Oracle → publish-cancel-wire-transfer-out batch → EventHub
  └── WireTransferOut events → processing → EventHub
```

## Data Quality / Retention
- `IncomingWireTransferPrototypeValidator` validates inbound file records before persistence
- JSON encoding: `StandardCharsets.UTF_8`
- File lifecycle: input → processed (success) or input → failed (failure)
- `SkipEmptyLineRecordSeparatorPolicy` handles blank lines in batch input files
- No retention/purge policy visible in available source
- Bank account data in EventHub persisted to `EVENT_HUB_EVENT` table as blob — retained per that table's retention policy (none observed)

## Compliance Gaps
1. Bank account numbers and routing numbers in EventHub XML messages stored as blobs in `EVENT_HUB_EVENT` — no payload encryption; data at rest exposure
2. JSON batch files on local filesystem contain bank routing/account numbers in plaintext
3. `NewWireTransferOutEvent` XML serialised via JAXB — no field-level masking for sensitive fields before logging
4. No duplicate-detection mechanism for batch file input — duplicate processing risk
5. `transferReason` free text field — potential uncontrolled PII ingestion
6. No data retention policy for wire transfer records or EventHub event blobs
