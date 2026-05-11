# Data Architect View — drawdown-data-manager_LIB

## Data Stores
| Store | Type | Location | Purpose |
|-------|------|----------|---------|
| StrongBox Vault | Proprietary XMLRPC secret store | URI from `director.address` property | Stores encrypted bank account records; returns opaque reference IDs |
| GreatPlains (GP) Database | SQL Server (via DBCP connection pool) | `gp.agent` / `gp.database` properties via Director | Receives ProgramID + PromotionID + vault reference after successful write |
| CSV Input File | Flat file | `input.file.path` property (e.g., `D:\c-base\config\`) | Source of bank account data for bulk load |

## Schema / Data Model
### CSV Input Columns (positional, comma-separated)
| Index | Field | Validation |
|-------|-------|-----------|
| 0 | ProgramID | 8-digit numeric |
| 1 | PromotionID | 1–9 digit numeric |
| 2 | InstitutionNumber | 3-digit numeric |
| 3 | TransitNumber | 5-digit numeric |
| 4 | AccountNumber | 4–17 digit numeric |
| 5 | ClientBankName | 2–30 chars |
| 6 | AccountType | string (no validation) |
| 7 | Country | string (no validation) |

### StrongBox Payload Keys
`routing_number`, `account_number`, `account_type`, `name`, `country` (nested under key `bank`)

### GreatPlains Stored Procedure
`DrawdownReferenceUpdateSP` — receives `DrawdownReferenceUpdateVO(programID, promotionID, vaultReference)`.  Schema of the target table is not visible in this repository.

## Sensitive Data Inventory
| Data Element | Classification | Location |
|--------------|---------------|---------|
| Bank account number | Financial / PII (GLBA, PCI DSS Req 3) | CSV input file (plaintext), StrongBox (encrypted) |
| Routing number | Financial | CSV input file (plaintext), StrongBox |
| Program/Promotion IDs | Operational reference | GP database |
| StrongBox vault reference | Operational key | GP database |

## Encryption and Data Protection
- Account and routing numbers are encrypted at rest inside StrongBox after writing.
- The CSV source file has no documented encryption or access control.
- The `director-client.properties` and `drawdown.properties` files hold connection strings and StrongBox agent credentials; file-level protection depends solely on OS ACLs.

## Data Flow Diagram
```
[CSV on disk] ──plaintext read──► [Java process]
                                      │
                              validate fields
                                      │
                              ┌───────┴────────┐
                           pass              fail → stderr + abort
                              │
                    StrongBox XMLRPC write
                              │
                       vault reference
                              │
                    GP SQL stored procedure
                              │
                    [GP Database row updated]
```

## Data Quality
- Structural validation (length, numeric) is implemented per field.
- No duplicate-check before writing to vault (same account could be written multiple times).
- No rollback if GP stored procedure fails after vault write (orphaned vault record risk).

## Compliance Gaps
1. **PCI DSS Req 3.3** — plaintext account numbers in CSV file at rest; no masking or tokenisation before file is read.
2. **PCI DSS Req 10** — no audit logging; only `System.out.println` statements.
3. **GLBA** — no documented data-retention / purge policy for the CSV file.
4. **Reg E** — no error-handling chain that would produce a customer-visible dispute trail.
