# Data Architect Report: stand-in-processing-api

## Data Models

SASI maintains its own primary database ("Primary SASI DB") plus read connections to four legacy databases. Key entities in the primary database:

**Primary SASI entities** (in `stip-main/src/main/java/com/onbe/stip/api/datasources/primary/model/`):
- `CardMaster` — card master record (likely contains masked or tokenised card reference)
- `AccountBalance` — current balance for a cardholder account
- `CardNumberStatus` — status of a card number (active, blocked, expired)
- `DdaNumberStatus` / `DdaReservation` — DDA (Demand Deposit Account) number tracking
- `MemberAccountShadow` / `SecondaryMemberAccountShadow` — shadow of member account state for stand-in period
- `MemberCardLink` — mapping between member and card
- `ClaimCode` — claim/activation codes for card distribution
- `TransactionLog` / `TransactionStatus` — stand-in transaction audit records
- `SASIRequestDetail` / `SasiSweepRequest` — request audit and sweep operation records

**Legacy database entities** (read-only during stand-in):
- `cbase/model/AccessEntity`, `CBaseEntity`, `CertificateTemplate` — access control and product configuration
- `ecount/model/OdsData`, `OpenToBuySasiResult`, `CoreDeviceResult` — cardholder ODS data and limit results
- `jobsvc/model/JobAccountMapEntry`, `UserMapping`, `ProfileSymbols` — job/profile mapping
- `ordersvc/model/RequestDetail`, `ActionDefinitionEntity` — order and action state

## Sensitive Data

**Highly sensitive data present:**

- `DdaNumberStatus` and `DdaReservation` contain DDA (bank account) number references — these are Sensitive Authentication Data under PCI DSS and are regulated under Reg E and GLBA
- `CardMaster` and `CardNumberStatus` contain card number references; the nature of storage (tokenised/masked vs. PAN) is critical for PCI DSS Requirement 3 compliance. Given that SASI connects to `EcountCoreDAO` and `DdaInquiryRepository`, live PAN/DDA data is likely accessible
- `AccountBalance` contains real-time account balance — financial PII
- `stip-generated` module contains `SetPinRequest` class — PIN-related operations are Sensitive Authentication Data; the handling of PIN data requires HSM protection under PCI DSS
- `AccessEntity` and related models contain IP address and certificate data used for authentication
- `TransactionLog` — transaction audit records likely contain card references, amounts, and merchant data

## Encryption Status

Per the architecture document and code:
- **At rest**: Azure SQL Database with Transparent Data Encryption (TDE) for the Primary SASI database
- **In transit**: HTTPS/TLS 1.3 for external; TLS for database connections; mutual TLS for Fiserv integration
- **Key management**: Azure Key Vault with managed identities
- **Application-level encryption**: The `LegacyCryptoService` class in `ecount/repository/` suggests field-level encryption is applied to some ECount data, likely using the StrongBox-derived keys. SASI reads this data and must understand the encrypted format
- **PIN handling**: `SetPinRequest` is in the generated API models; the actual PIN handling implementation is not visible in available source, but must use HSM or equivalent for PCI DSS compliance

## Database Schema and Data Flows

Five databases with separate JPA configurations:

| JPA Config | Database | Role |
|---|---|---|
| `PrimaryJpaConfig` | Primary SASI DB (Azure SQL) | Own stand-in state, read/write |
| `CbaseJpaConfig` | cbaseapp | Legacy card config, read during stand-in |
| `EcountJpaConfig` | ecountcore | Cardholder master/balance, read during stand-in |
| `JobsvcJpaConfig` | jobsvc | Job/profile mappings, read during stand-in |
| `OrdersvcJpaConfig` | ordersvc | Order state, read during stand-in |

Additionally, `BankerNaJpaConfig` and `BankerEcntJpaConfig` suggest connections to Banker NA (North America) and ECount banker systems.

Data flow during stand-in: Fiserv sends authorisation request → SASI REST/SOAP endpoint → Security filter (IP + header/cert validation) → Domain service → Queries ecountcore for balance/status + cbaseapp for product rules → Writes to Primary SASI DB (TransactionLog) → Responds to Fiserv

## Retention Concerns

- `TransactionLog` in the primary database accumulates all stand-in transactions; retention policy and purge schedule must be defined for PCI DSS Requirement 3.1 (minimise PAN storage duration)
- Azure SQL backups provide 7–35 day point-in-time recovery per the architecture document; PCI DSS requires encrypted, access-controlled backups
- `SASIRequestDetail` audit records must be retained per Reg E dispute resolution requirements (minimum 2 years) and PCI DSS audit log retention (minimum 1 year, 3 months immediately accessible per Req 10.7)

## PCI DSS Compliance Assessment

- **Req 3**: DDA numbers in `DdaNumberStatus`/`DdaReservation` are Sensitive Authentication Data; their storage post-authorisation must be reviewed; PAN in `CardMaster` must be masked/truncated or tokenised
- **Req 4**: Mutual TLS for Fiserv is correct; all database connections must verify server certificates
- **Req 6**: Spring Boot 3.5.5 with explicitly patched Tomcat (`10.1.45` for CVE-2025-55752) and Jackson — proactive patching is evident and positive
- **Req 9**: `SetPinRequest` requires HSM-backed PIN handling; if PIN is processed in software, this is a critical Req 9 gap
