# DS_DB_ccp — Enterprise Architect View

## 1. Platform Generation Assessment

**Generation: Gen-2 (Wirecard/Northlane era data integration) with Gen-1 SSDT tooling**

Evidence:
- **SSDT project with SQL Server 2012 DSP**: Tooling vintage is consistent with the Wirecard/Northlane era (2015–2020), when this database type of BIN-level reporting store would have been introduced alongside NAM (North America) program migrations.
- **NAM prefix on tables**: `NAM_BIN_ACCOUNTS`, `NAM_BIN_TRANSACTION`, etc. — "NAM" is the Onbe/Wirecard naming convention for North America programs (contrasted with APAC or EMEA). This is a post-eCount naming convention.
- **FISERV as FI**: References to `Fiserv` in `FISERV_INVENTORY` reflect the post-Citi/eCount period when Fiserv (First Data) became the primary card-processing FI.
- **FVD (Fee/Value Data) pattern**: FVD tables indicate a Wirecard-era reporting framework for fee and value tracking.
- **No legacy eCount identifiers**: Unlike cbaseapp, CCP has no `ecount_guid` types, no `dda_id` patterns (though `DirectDepositID` appears in transactions), and no eCount-era stored procedure naming.
- **Moderate stored procedure count** (12 vs 781 in cbaseapp): Appropriate for a data-integration database, not an application database.

---

## 2. Role in the Onbe Payments Architecture

CCP serves as the **BIN-level operational reporting database** — the data layer between the financial institution (Fiserv) and Onbe's reporting and client-facing systems.

```
┌──────────────────────────────────────────────────────────────────────┐
│                        ONBE PAYMENTS PLATFORM                        │
│                                                                      │
│  ┌──────────────┐    Daily batch files    ┌────────────────────┐     │
│  │  Fiserv /    │ ──────────────────────► │  CCP (this DB)     │     │
│  │  FIS         │  Account/Tx/Balance/    │  BIN-level data    │     │
│  │  (card FI)   │  CardStatus files       │  integration store │     │
│  └──────────────┘                         └─────────┬──────────┘     │
│                                                     │                │
│                                                     ▼                │
│                                          ┌────────────────────┐     │
│                                          │  cf_report         │     │
│                                          │  (reporting DB)    │     │
│                                          └────────────────────┘     │
│                                                                      │
│  ┌──────────────┐                                                    │
│  │  cbaseapp    │  (separate cardholder identity — linked by         │
│  │              │   AccountIdentifier / program references)          │
│  └──────────────┘                                                    │
└──────────────────────────────────────────────────────────────────────┘
```

### Upstream
- **Fiserv/FIS**: The financial institution delivers daily batch extracts. The `FinancialInstitution` column on all NAM BIN tables stores the FI identifier.
- **SSIS packages**: Load staging tables from FI files.

### Downstream
- **cf_report**: Reporting stored procedures in cf_report query NAM BIN tables (e.g., `app_BI_Account_Balance_File`, `app_BI_Transaction_File`) to produce client-facing Bank Integration files.
- **Client reporting**: BIN-level account, transaction, balance, and card-status data is the basis for client-facing reports to bank partners.

### Lateral Links
- **cbaseapp**: CCP and cbaseapp are linked by `AccountIdentifier` (CCP) ↔ `ecount_member_id`/`dda_id` (cbaseapp). There is no FK relationship; linkage is by business key.

---

## 3. Integration Patterns

| Integration | Mechanism | Notes |
|---|---|---|
| Fiserv file receipt | SSIS / file-to-staging load | Batch, daily |
| cf_report | Linked-server or direct database queries | cf_report reads CCP tables |
| cbaseapp | No direct DB link; business-key join by account identifier | |
| SQL Agent job management | `package_execution` table | Execution metadata |

---

## 4. Migration Complexity Assessment

### Complexity Rating: MEDIUM

Factors:
1. **Moderate scale**: 23 tables, 12 stored procedures — manageable for migration.
2. **FI dependency**: A migration would require coordinating with the financial institution to modify or replace the batch file delivery and loading mechanism.
3. **SSN data**: Any migration must maintain or improve the SSN protection posture.
4. **cf_report dependency**: cf_report stored procedures reference CCP tables by name; migration of CCP table names or schema requires updating cf_report.
5. **Archive table data volume**: `*_ARCHIVE` tables likely contain years of daily batch data and would need a data migration strategy.
6. **Trigger-based archiving**: A Gen-3 replacement would likely implement a CDC (Change Data Capture) or event-sourcing pattern instead of delete-triggered archival.

---

## 5. Strategic Observations

1. **Data duplication with cbaseapp**: CCP holds account-holder name, address, DOB, and SSN for cardholders whose identity is already managed in cbaseapp. This duplication creates inconsistency risk (which is the authoritative source of truth?) and doubles the PII surface area.
2. **Batch-file architecture**: The daily batch file pattern is inherently T+1 for balances and transactions. A Gen-3 architecture would use real-time event streams (Kafka, Azure Event Hubs) for near-real-time cardholder data.
3. **FVD billing coupling**: Billing and revenue data in CCP suggests CCP serves dual purposes (BIN operations + financial reporting). A cleaner Gen-3 design would separate these domains.
