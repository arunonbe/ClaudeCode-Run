# Data Architect View — order_SVC

## Data Models

order_SVC is a multi-module Maven project. Data models span several sub-modules:

- **order-common**: shared domain objects — `Order`, `OrderActivity`, `OrderStatus`, order type enumerations
- **order-manager**: orchestration layer; holds order manager interfaces and implementations
- **order-processor**: processes order activity handlers; stateful transition logic
- **order-xmlrpc**: XML serialization/deserialization of order payloads for legacy integration
- **order-service**: Spring Boot deployable service; REST and XML-RPC endpoints
- **order-rest-controller**: REST API layer with request/response DTOs

Key domain entities (inferred from Javadoc and handler class names):
- `Order` — core record with order type, status, affiliate ID, program ID, card identifiers
- `OrderActivity` — audit trail of state transitions; each activity is immutable
- `FileOrderManager` — manages batch file order intake; file metadata, record counts, status
- `InstantIssueProcessor` — real-time card issuance record including card network response
- `SecureProfileActionSecureMemo` — memo attached to secure profile actions (PCI-sensitive)

## Sensitive Data Handled

| Data Category | Presence | Protection Status |
|---|---|---|
| PAN | Possible in order records (masked) | Must be masked (first 6 / last 4); full PAN must not persist |
| CVV/SAD | Must NOT be stored | Not expected in order records per PCI DSS Requirement 3.2 |
| Cardholder Name | Present in order requests | Stored in SQL Server database; access controlled by xsecurity |
| Program/Affiliate ID | Structural metadata | Not sensitive; used for routing |
| Bank Account (for ACH sweeps) | Possible in sweep orders | Must be masked at rest |
| Amount | Present in all order types | Financial data; subject to GLBA |
| Memo fields (SecureProfile) | Present | Must not contain SAD; audit logging required |

## Encryption and Protection Status

- Database encryption is not directly observable in service code; assumed to be SQL Server TDE (Transparent Data Encryption) at the infrastructure level
- IBM MQ messages carrying order payloads should be encrypted in transit; MQ channel security is infrastructure-managed
- No application-level field encryption observed in the order data model — encryption responsibility is delegated to the database and transport layers
- xsecurity (`xsecurity-impl`) handles service-level authorization, controlling which callers may invoke which order operations

## Database Schemas

- Primary database: SQL Server (`ecountcore` database, based on platform lineage)
- Sub-databases: `ecountcore_process`, `ecountcore_process_archive` for in-flight and historical orders
- Spring DBCTX (`spring-dbctx-container`) manages database context switching — indicates multi-tenant or multi-program database routing
- Stored procedures are the primary data access pattern (consistent with eCount Gen-1 architecture)

## Data Flows

```
Client / Batch File → order-xmlrpc (XML-RPC) OR order-rest-controller (REST)
  → order-manager (orchestration)
    → order-processor (activity handlers)
      → SQL Server (ecountcore, ecountcore_process)
      → IBM MQ (async event notifications)
      → inventory-mgmt (card inventory allocation)
      → repository-service (file/document storage)
      → banker service (financial settlement)
```

Sweep flow:
```
Sweep trigger → CreateSweepOrdersActivityHandler
  → banker service (balance inquiry)
  → SQL Server (sweep order records)
  → FreeSweepOrderFundsActivityHandler
  → CloseSweepOrdersActivityHandler
```

## Retention Concerns

- Active orders: retained in `ecountcore_process` while in flight
- Completed orders: archived to `ecountcore_process_archive` per archival schedule
- Audit trail (`OrderActivity`): must be retained per NACHA (7 years for ACH records) and GLBA obligations
- File order records must be retained to support return/reversal processing within NACHA return windows (typically 2 banking days for unauthorized, 60 days for certain error codes)

## PCI DSS Data Storage Compliance

- PCI DSS Requirement 3.3: SAD must never be stored after authorization. Order records must not contain CVV, full track data, or PIN.
- PCI DSS Requirement 3.4: PAN, if stored, must be rendered unreadable (truncation, tokenization, or encryption). The service's use of `SecureProfile` suggests tokenized card references are used rather than raw PANs.
- PCI DSS Requirement 10.2: All order state transitions should be logged with sufficient detail for audit (who, what, when, from which system). The `OrderActivity` model serves this purpose if properly populated.
- The `ecountcore_process_archive` database must be in scope for PCI DSS if it retains any PAN-adjacent data.
