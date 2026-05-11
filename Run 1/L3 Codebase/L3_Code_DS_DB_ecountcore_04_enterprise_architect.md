# DS_DB_ecountcore — Enterprise Architect View

## Platform Generation

`Ecountcore` is a **legacy monolithic OLTP database** that has been in continuous production service since approximately 2002-2003 (the earliest table backup dates in `DS_DB_ecountcore_rollback` reference 2002 and 2003). It is built on SQL Server and has evolved from a simple prepaid card tracking system into a comprehensive financial services platform supporting:
- Multiple card processing rails (FDR/First Data, Fiserv, Citi NAOT)
- Multiple payment instruments (prepaid debit, eCard, eCheck, credit card)
- Multiple geographies (North America, Canada, EMEA references)
- Multiple business lines (rebates, healthcare disbursements, insurance, incentives)

The SQL Server 2016 target version is current for Microsoft mainstream support (which ended October 2026), though enterprise extended support considerations apply.

---

## Role in the Payments Architecture

`Ecountcore` is the **system of record for the prepaid card platform** — the authoritative database for all cardholder, account, card, and transaction data:

```
[Client Systems / APIs]
  clientapi_API, cs-api-v*, csapiws-payout_API
  ecount-core_SVC, ecap-backend-process_LIB
        ↓
  [EcountCore Service Layer - Java]
  ecore-batch_LIB, prepaid-batch-framework_LIB
        ↓
  [Ecountcore Database] ← THIS REPO
        ↓                        ↓
  [Ecountcore_Process DB]    [EcountCore Archive]
        ↓
  [FDR / Fiserv / Citi NAOT] (external card processors)
  [ACH / Mellon Bank / Citi]  (external settlement banks)
  [Oracle Mantas]              (AML surveillance)
```

Every other database in the Onbe estate that contains card or member data either:
1. Derives its data from `Ecountcore`, or
2. Writes processed results back into `Ecountcore`

This makes `Ecountcore` the **central hub** of the Onbe data architecture.

---

## System Dependencies

### Upstream (callers into Ecountcore)
| System | Type | Access Type |
|---|---|---|
| `ecount-core_SVC` | Java service | ORM/JDBC via stored procedures |
| `ecap-backend-process_LIB` | Java library | Stored procedure calls |
| `clientapi_API`, `cs-api-v*` | REST APIs | Via EcountCore service layer |
| SSIS ETL packages (DS_DB_dtsx) | Batch ETL | Direct SQL (SELECT queries) |
| `ecore-batch_LIB`, `prepaid-batch-framework_LIB` | Spring Batch | Stored procedure calls |
| `enrollment_LIB`, `enrollment_WAPP` | Enrollment service | Member/card creation |
| `notification-framework_SVC` | Notification service | Reads member contact data |
| `job-scheduler_SVC` | Scheduler | Triggers batch processing |

### Downstream (Ecountcore writes to / depends on)
| System | Type | Relationship |
|---|---|---|
| `Ecountcore_Process` | SQL Server | Staging/processing intermediary |
| `EcountCore Archive` (DS_DB_ecountcore_rollback tables) | SQL Server | Archived closed accounts |
| FDR (First Data Resources) | External payment network | Card authorisation/settlement |
| Fiserv | External card processor | Card fulfilment |
| Citi NAOT | External | Card fulfilment |
| ACH Network (via Mellon/BofA/Citi) | Banking | ACH settlement |
| Oracle Mantas | External AML platform | Compliance surveillance |
| `prepaid_warehouse` / `cf_report` | Reporting DBs | Read-only analytics |

---

## Architectural Patterns

### Stored Procedure API Pattern
EcountCore exposes its entire data model through stored procedures. The Java service layer (`ecount-core_SVC`) calls stored procedures rather than generating SQL. This pattern:
- Provides a stable API contract between the service layer and database
- Centralises business logic in the database (including velocity checks, escheatment rules, fee calculations)
- Creates a tight coupling between the service layer and stored procedure signatures
- Complicates migration to ORM-based or microservices patterns

### Certificate-Based Column Encryption
PANs are encrypted using SQL Server's `DecryptByKeyAutoCert` mechanism with a certificate named `card_number_cert`. The unmasked PAN is only surfaced via specific decryption functions, and a parallel masking function (`app_func_get_card_number_by_id_masked`) provides first6+last4 for display purposes.

### Dual Identifier Pattern
The platform uses both:
- `card_id` (integer surrogate key) for internal joins
- `card_hash` (SHA-1 hash of card number) for cross-database matching
- `card_encrypted` (the encrypted PAN) for decryption when full PAN is required
- `dda_number` (16-char account number) as the primary account identifier

---

## Migration Complexity Assessment

| Dimension | Complexity | Notes |
|---|---|---|
| Data volume | Very High | 20+ years of cardholder, transaction, and ACH data |
| Schema complexity | Very High | 100+ tables, 300+ procedures, complex FK relationships |
| Business logic in database | Very High | Velocity checks, fee calculations, escheatment rules, NACHA date calculations all in T-SQL |
| Certificate migration | Critical | `card_number_cert` must be migrated alongside data; BYOK (Bring Your Own Key) planning required for cloud |
| Stored procedure dependency | Very High | Service layer is tightly coupled to specific procedure signatures |
| Multi-rail support | High | FDR, Fiserv, Citi NAOT each have distinct table sets (`fdr_*`, `Fiserv_*`, `NAOT_*`) |
| Regulatory compliance | Very High | Any schema change may have PCI DSS, NACHA, OFAC compliance implications |
| Active customer data | Critical | Zero-downtime migration required — live cardholder accounts cannot be taken offline |

---

## Strategic Architecture Recommendations

1. **Decompose by bounded context**: The monolithic database can be decomposed into microservice-owned databases: CardService (card lifecycle), MemberService (identity), ACHService (payments), FeeService (billing), NotificationService (alerts). This is a multi-year programme.

2. **Migrate business logic from database to service layer**: The 300+ stored procedures contain business logic that belongs in the application tier. This enables language-agnostic unit testing and cloud portability.

3. **Replace column-level encryption with HSM-based tokenisation**: Replace `card_number_cert` with a network tokenisation vault (e.g., Azure Payment HSM, Braintree, or a dedicated tokenisation service) to improve key management, reduce PCI scope, and enable cloud migration.

4. **Implement read replicas for reporting**: The `monitor_*`, `rpt_*`, and reporting procedures should run against a read replica, not the OLTP primary, to reduce production impact.

5. **Modernise ACH to API-based rail**: Replace NACHA file-based ACH with modern ACH API providers (Same-Day ACH via API, RTP/FedNow for instant payments) to reduce batch complexity and improve cardholder experience.
