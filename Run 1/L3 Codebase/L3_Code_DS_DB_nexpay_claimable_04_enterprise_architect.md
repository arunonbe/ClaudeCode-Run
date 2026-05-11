# DS_DB_nexpay_claimable — Enterprise Architect Report

## 1. Platform Generation Assessment

`DS_DB_nexpay_claimable` is a **Generation 3 (NexPay Microservices)** component. It represents the modern approach to database design at Onbe — a purpose-built, minimal schema that serves a single microservice through a clean abstraction layer. This contrasts sharply with the thousands-of-table GP databases or the multi-purpose jobsvc database.

The design philosophy is explicitly described in the README:
> "SQL Server database project providing cross-database views over EcountCore tables. These views supply read-only data to the nexpay-claim-code-svc microservice."

## 2. Role in Onbe's Architecture

This database occupies the **NexPay platform tier** — the modern microservices payment processing layer:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        NEXPAY MICROSERVICES TIER                        │
├────────────────────────────────────────────────────────────────────────┤
│  nexpay-claim-code-svc  (Spring Boot)                                   │
│      ↓ reads via                                                        │
│  DS_DB_nexpay_claimable (this repo)                                     │
│      ↓ cross-DB views over                                              │
│  EcountCore..claimable_payment                                          │
│  EcountCore..core_member                                               │
│  EcountCore..core_registration_*                                        │
│                                                                         │
│  Sibling NexPay services:                                               │
│  nexpay-auth-svc | nexpay-cardprocessor-svc | nexpay-order-orchestrator │
│  nexpay-recipient-profile-svc | nexpay-recipientweb-bff                 │
└────────────────────────────────────────────────────────────────────────┘
```

The database serves as an **Anti-Corruption Layer (ACL)** in Domain-Driven Design terms — it isolates the NexPay service from the complexity of EcountCore's normalised data model, presenting a clean, denormalised API surface.

## 3. Architectural Pattern Analysis

### 3.1 Strengths

1. **Single Responsibility**: Serves exactly one microservice (`nexpay-claim-code-svc`). Clean bounded context.
2. **Read-Only**: All views are SELECT-only; no writes, no stored procedures. Eliminates write-side risk.
3. **Abstraction Layer**: Insulates `nexpay-claim-code-svc` from EcountCore schema changes. Changes to EcountCore's internal structure only require updating 4 view files.
4. **Explicit Documentation**: Best-documented database in the analysis set. README documents every view, source table, and deployment procedure.
5. **COALESCE Fallback Logic**: `recipient_registration` uses intelligent COALESCE patterns to provide address/phone data from primary or extended tables, reducing null data in the service layer.

### 3.2 Weaknesses

1. **Wildcard Projections**: `claimable_payment` uses `SELECT p.*` — creates implicit coupling to EcountCore's full column list.
2. **Cross-Database Views**: SQL Server cross-database views are a tight coupling mechanism. If EcountCore moves to a different SQL Server instance or Azure SQL Elastic Pool, these views will break without a significant re-architecture.
3. **NOLOCK Throughout**: Dirty reads acceptable for some operations but potentially problematic for security-critical reads.
4. **No Schema Versioning**: No SSDT project, no flyway/liquibase. A single view change requires manual deployment.

### 3.3 Anti-Patterns

- **`SELECT p.*` Wildcard**: Violates the principle of explicit interface — a view claiming to be an abstraction should explicitly list its columns so the contract is clear.
- **Cross-Database Reference at Scale**: As NexPay grows, multiple microservices creating cross-database views over EcountCore creates a hub-and-spoke anti-pattern where EcountCore becomes a god database. Long-term, recipient and payment data should be owned by a dedicated domain service (possibly `nexpay-recipient-profile-svc`).

## 4. Integration Dependencies

### 4.1 Upstream
| System | Type | Dependency |
|--------|------|------------|
| EcountCore database | Hard dependency | All data originates here |
| `jobservice` (via EcountCore) | Indirect | Claimable payment records created by job actions |
| `DS_DB_ordersvc` | Indirect | Order processing creates claimable_payment records |

### 4.2 Downstream
| System | Type | Usage |
|--------|------|-------|
| `nexpay-claim-code-svc` | Primary consumer | Reads all 4 views |
| Recipient claim portal (web UI) | Via BFF | Portal queries via claim-code-svc |
| Payment execution services | Via claim-code-svc | Modality selection drives payment rail |

## 5. EcountCore Coupling Risk

The most significant architectural risk is **EcountCore coupling**. As Onbe transitions to microservices, EcountCore is becoming a legacy platform. The `nexpay_claimable` views create a dependency path:

```
nexpay-claim-code-svc → nexpay_claimable views → EcountCore tables
```

If Onbe's roadmap includes migrating claimable payment and recipient registration data out of EcountCore into a purpose-built microservice data store, this view layer must be replaced with a service API call or event-sourced cache.

**Recommendation**: Add this to the EcountCore decommissioning roadmap. Identify whether `nexpay-recipient-profile-svc` (already in the repo list) is intended to own recipient registration data, and plan migration accordingly.

## 6. Azure SQL / Cloud Migration Assessment

The README explicitly lists "Azure SQL" as a supported target (alongside SQL Server 2019+). This indicates the NexPay team has cloud migration in mind for this component. Cross-database views behave differently in Azure SQL:
- **Azure SQL Single Database**: Cross-database views **do not work** (no cross-database queries in single-database tier)
- **Azure SQL Managed Instance**: Cross-database views **do work** (same as on-premises SQL Server)
- **Azure SQL Elastic Pool**: Cross-database views **do not work** unless databases are in the same elastic pool with elastic queries configured

If migration to Azure SQL Single Database is planned, these views must be replaced with:
- External Tables via Elastic Queries, or
- Materialised replicas in the `nexpay_claimable` database, or
- A service API layer

## 7. Regulatory Architecture Position

Despite its simplicity, this database sits at the intersection of several regulatory domains:
- **PCI DSS**: Potential CDE adjacency via `claimable_payment` view
- **TCPA**: Phone numbers exposed in `recipient_registration`
- **GDPR/CCPA**: Full recipient PII exposed
- **GLBA**: Consumer financial data (payment amount + recipient identity combined)

The clean architecture means that adding a column-level security policy (SQL Server Row-Level Security or Column-Level Security using `GRANT SELECT` on specific view columns) would be straightforward and is recommended before this view is accessed by additional services.
