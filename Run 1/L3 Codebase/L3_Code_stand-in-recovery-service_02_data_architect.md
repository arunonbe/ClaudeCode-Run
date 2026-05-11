# 02 Data Architect — stand-in-recovery-service

## Data Stores
| Store | Technology | Purpose |
|---|---|---|
| sasi (Azure SQL / primary) | SQL Server via Azure (`sql-az1-cluster-qa-ss`) | Recovery session, snapshot, message, event data |
| cbaseapp (SQL Server on-prem) | SQL Server (`u-lis-db01.nam.wirecard.sys:2231`) | Card/DDA number allocator state |
| ecountcore (SQL Server on-prem) | SQL Server (`u-lis-db02.nam.wirecard.sys:2231`) | eCount core data |
| jobsvc (SQL Server on-prem) | SQL Server (`u-lis-db01.nam.wirecard.sys:2231`) | Job service state |
| ordersvc (SQL Server on-prem) | SQL Server (`u-lis-db01.nam.wirecard.sys:2231`) | Order service state |
| Azure Service Bus | Azure Service Bus (session-enabled queue) | Recovery message ingestion and replay |

All credentials stored in Azure Key Vault (referenced via `key_vault_references` in `appsettings.json`).

## Schema / Tables
Inferred from repository layer (`stir-main`):
| Repository / Entity | Table (inferred) | Key Fields |
|---|---|---|
| `RecoverySessionRepository` | `recovery_session` | sessionId, status, startedBy, startedAt, endedAt, externalRef |
| `RecoverySnapshotRepository` | `recovery_snapshot` | snapshotId, sessionId, timestamp |
| `RecoverySnapshotCardDetailRepository` | `recovery_snapshot_card_detail` | snapshotId, cardNumber range data |
| `RecoverySnapshotDdaDetailRepository` | `recovery_snapshot_dda_detail` | snapshotId, DDA range data |
| `RecoveryMessageRepository` | `recovery_message` | messageId (composite), sessionId, content, status |
| `RecoveryMessageAttemptRepository` | `recovery_message_attempt` | attemptId, messageId, result, timestamp |
| `RecoveryEventRepository` | `recovery_event` | eventId, sessionId, eventType, timestamp |
| `MessageTransferRepository` | `message_transfer` | transferId, direction, status |
| `CardNumberStatusRepository` | (cbaseapp or sasi) | current card number upper-limit serial |
| `DdaNumberStatusRepository` | (cbaseapp or sasi) | current DDA number upper-limit serial |
| `LegacyNumberStatusRepository` | (cbaseapp legacy) | legacy number status |

## Sensitive Data
| Data Element | Classification | Location |
|---|---|---|
| Card number serials / upper limits | Payment card data (adjacent to PAN space) | sasi DB, cbaseapp DB |
| DDA account number serials | Financial account data | sasi DB, cbaseapp DB |
| Azure Service Bus connection string | Infrastructure credential | Key Vault reference |
| DB credentials (username/password) | Infrastructure credential | Azure Key Vault |
| `accountmanagementapi.security.service.visa.key` / `.sharedSecret` | Payment network credential | Azure Key Vault |
| `startedBy` (operator identity) | PII-adjacent (employee identifier) | recovery_session table |

No direct PAN storage; serial/range data is PAN-adjacent and controlled under PCI DSS Req. 3.

## Encryption
- Azure SQL (`sql-az1-cluster-qa-ss`): `encrypt=true;trustServerCertificate=false` — TLS enforced
- On-premises SQL Server (`u-lis-db01/02`): `trustServerCertificate=true` — TLS active but certificate not validated; **medium risk** in a PCI environment
- Azure Service Bus: TLS enforced by the platform
- Azure Key Vault: all secrets encrypted at rest (AES-256); accessed via managed identity or connection string
- Application-level data encryption: none observed for serial data at rest in the database tables

## Data Flow
```
Azure Service Bus (recovery messages)
  --> stir-main SessionProcessor
      --> RecoveryMessage (sasi DB)
      --> RecoveryMessageAttempt (sasi DB)
      --> AccountManagementAPI / DebitAPI / CSAPI v3 (replay operations)
      --> CardNumberStatus / DdaNumberStatus update (cbaseapp / sasi DB)

Operator trigger (POST /recovery/sessions)
  --> RecoverySession (sasi DB)
  --> RecoverySnapshot (sasi DB) → captures card/DDA serial state from cbaseapp + sasi
  --> RecoveryEvent (sasi DB)
```

## Quality / Retention
- `RecoveryMessageAttempt` provides a detailed audit trail of message replay attempts
- No explicit data retention / purge policy visible; recovery sessions, snapshots, and message attempts should be retained for PCI DSS Req. 10 (at least 12 months)
- Snapshot buffer (`stir.snapshot.buffer=5`) and safety-margin (`stir.snapshot.safety-margin=3`) provide overlap protection against number collision
- No database-level data quality constraints visible in repository layer; validation is application-level

## Compliance Gaps
- On-premises SQL Server connections use `trustServerCertificate=true` — bypasses certificate validation; **PCI DSS Req. 4** (protect cardholder data in transit) gap
- No explicit data retention policy for recovery session/message data — **PCI DSS Req. 10.7** gap
- `POST /recovery/sessions/reset-upper-limits` endpoint modifies serial state without visible authorisation enforcement — **PCI DSS Req. 7** (restrict access to cardholder data) gap
- Azure Service Bus connection string stored as a reference to Key Vault but the connection-string format exposes endpoint; ensure SAS token rotation policy is in place
