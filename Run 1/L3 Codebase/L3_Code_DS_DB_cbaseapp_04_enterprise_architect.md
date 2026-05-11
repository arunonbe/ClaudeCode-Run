# DS_DB_cbaseapp — Enterprise Architect View

## 1. Platform Generation Assessment

**Generation: Gen-1 (eCount/CitiPrepaid Legacy Core)**

The evidence for Gen-1 classification is extensive and unambiguous:

- **Project name**: `Cbaseapp` — "cbase" is the eCount cardholder base application, a term from the original eCount (later CitiPrepaid) platform.
- **SQL Server 2012 DACPAC target**: `Sql110DatabaseSchemaProvider` indicates the schema was authored against SQL Server 2012, consistent with the eCount era (2010–2014 platform vintage).
- **eCount data types and naming**: User-defined types include `ecount_guid`, `ecount_transaction_amount`, `ecount_avs_message`. Tables use `ecount_member_id`, `ecount_id`, `dda_id` — all eCount internal identifiers.
- **Cross-database linked server references**: `csa_GetEcountHist` queries `VSQL3.ecountcore.dbo.core_transaction_journal` and `VSQL1.webcert.dbo.*`, naming the two core Gen-1 databases: `ecountcore` (card processing) and `webcert` (web certificate/shopper system).
- **CITIPREPAID_PUBLICKEY table**: A table named `CITIPREPAID_PUBLICKEY` is in the schema, confirming CitiPrepaid heritage.
- **ecount.com email references**: The `utl_dba_drive_space_alert` procedure in the dbadmin repo (which cross-references cbaseapp) sends alerts to `dba-notify@ecount.com`, confirming the eCount domain.
- **Historical table naming**: Tables like `user_ecount_20050413_1643`, `affiliate_fieldname_20050620`, `certificate_template_LE20050124`, and `instant_issue_preregistration_rollback_20110727` contain dates from 2005–2011, the eCount/CitiPrepaid era.
- **Functional breadth**: A 509-table schema supporting prepaid card issuance, enrollment, payment, rewards, CSA operations, and multi-program affiliate configuration is characteristic of a monolithic Gen-1 platform that grew organically over 15+ years.

---

## 2. Role in the Onbe Payments Architecture

`cbaseapp` is the **authoritative cardholder system of record** for Gen-1 prepaid programs. Its role in the architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                   ONBE PAYMENTS PLATFORM                    │
│                                                             │
│  ┌──────────────┐    ┌──────────────┐   ┌───────────────┐  │
│  │  cbaseapp    │◄──►│  ecountcore  │   │  ccp (DS_DB)  │  │
│  │  (this DB)   │    │  (DDA ledger │   │  (BIN/NAM     │  │
│  │  cardholder  │    │  & txn core) │   │   reporting)  │  │
│  │  identity +  │    └──────────────┘   └───────────────┘  │
│  │  payments    │           │                   │           │
│  └──────────────┘           │                   │           │
│         │                   ▼                   ▼           │
│         │           ┌──────────────┐   ┌───────────────┐   │
│         └──────────►│  cf_report   │   │  CBTS         │   │
│                     │  (reporting  │   │  (cross-border│   │
│                     │  database)   │   │   transfers)  │   │
│                     └──────────────┘   └───────────────┘   │
│                                                             │
│  ┌──────────────┐    ┌──────────────────────────────────┐  │
│  │  dbadmin     │    │  database_maintenance             │  │
│  │  (DBA ops)   │    │  (index/stats/integrity)         │  │
│  └──────────────┘    └──────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Upstream Dependencies (data flows into cbaseapp)
- **Web/Mobile Portal**: The application tier calls stored procedures (`b2c_create_user`, `b2c_login_user`, etc.) over JDBC/ODBC.
- **ECAP subsystem**: External embossing/card activation process writes to `ecap_*` tables.
- **Partner batch files**: Affiliate batches populate `batch_payment`, `batch_payment_detail`.
- **Rewards feeds**: GM-ICT and Subaru reward calculation processes write to `rewards_gmict_*` and `rewards_subaru_*`.

### Downstream Dependencies (cbaseapp data consumed by)
- **ecountcore**: `user_ecount` links cbaseapp `user_id` to ecountcore `ecount_member_id` and `dda_id`. ecountcore maintains the DDA ledger and transaction journal.
- **cf_report**: Linked-server queries from `cf_report` stored procedures reference cbaseapp for enrollment data, payment data, and demographic data for reporting.
- **ccp (DS_DB_ccp)**: CCP receives BIN-level account/transaction/balance/card-status files from the financial institution; these cross-reference the same `AccountIdentifier` / card records managed in cbaseapp.
- **CSA Portal**: The Bridge CSA application queries cbaseapp directly for member search and service operations.
- **IVR**: The `ivr_claim_code` computed column on `payment` feeds the telephone (IVR) claim flow.

---

## 3. Integration Patterns

| Integration | Mechanism | Notes |
|---|---|---|
| ecountcore | Linked-server SQL queries (VSQL3.ecountcore) | Tightly coupled; schema changes in ecountcore can break cbaseapp views |
| webcert | Linked-server SQL queries (VSQL1.webcert) | Legacy webcert database reference in `csa_GetEcountHist` |
| Application tier | Stored procedure calls | ~781 procedures form the data-access layer |
| Reporting | Linked-server reads from cf_report | cf_report pulls from cbaseapp; no ORM layer |
| Email/SMS | Internal queue tables (`email_queue`, `sms_*`) | Async processing by notification service |
| Embossing | ECAP tables written by card-ordering service | File-based batch to card manufacturer |

---

## 4. Migration Complexity Assessment

### Complexity Rating: VERY HIGH

Factors driving complexity:

1. **Scale**: 509 tables, 781 stored procedures. This is one of the largest OLTP database schemas in the Onbe platform.

2. **Cross-database coupling**: Hard-coded linked-server references to `VSQL3.ecountcore` and `VSQL1.webcert` create tight coupling that cannot be migrated without coordinating ecountcore and webcert simultaneously.

3. **Application-layer coupling**: 781 stored procedures form the complete data-access API. The application tier calls procedures by name. Any migration must maintain all procedure signatures or update all calling applications.

4. **Historical data accumulation**: Tables like `user_ecount_20050413_1643`, `affiliate_fieldname_20050620`, `cbaseapp_rollback11072007`, and `rewards_gmict_batch20100106` suggest 20 years of accumulated data with no migration/cleanup. Historical data volume is unknown but likely very large.

5. **PCI DSS compliance migration**: Any migration path must maintain CDE classification and encryption standards; the presence of `ecap_transaction_info.credit_card_number` in plaintext means a migration must also remediate this finding.

6. **No ORM or service layer**: There is no intermediate service layer — the database is the API. A Gen-3 migration would require building a new API layer before the database can be replaced.

7. **Gen-3 target unknown**: No migration scripts toward a Gen-3 (Azure/cloud-native) architecture were found in this repository.

---

## 5. Strategic Architecture Observations

- **Monolith characteristics**: cbaseapp exhibits classic monolith database anti-patterns: single large schema covering many domains, direct cross-database queries, application logic encoded in 781 stored procedures.
- **Opportunity for domain decomposition**: Natural domain boundaries exist — Identity/Auth, Payments, Notifications, Fraud, Rewards, CSA/Admin — that could be extracted into separate microservice databases.
- **Tokenisation gap**: The presence of plaintext `credit_card_number` in `ecap_transaction_info` and 16-digit `dda_number` in `pdm_registration` indicates that tokenisation has not been applied consistently. A Gen-3 architecture should integrate a payment-token vault (e.g., Basis Theory, Spreedly) as a first-class component.
- **eCount GUID pattern**: The use of `ecount_guid` UUIDs as the primary inter-system identifier (linking cbaseapp to ecountcore) provides a natural abstraction point for tokenisation — the GUID can persist while the underlying CHD is vaulted.
