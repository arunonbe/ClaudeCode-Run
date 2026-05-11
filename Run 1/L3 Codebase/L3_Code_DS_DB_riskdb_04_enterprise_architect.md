# DS_DB_riskdb — Enterprise Architect Assessment

## 1. Platform Generation and Role

RiskDB is a **second-generation on-premises compliance and operational risk platform** that has evolved into a multi-purpose database serving fraud monitoring, AML/CTF case management, regulatory reporting, operational tooling (DMT), and ad-hoc analytics. The presence of tables dating back to 2008, an archived Mantas AML integration, and hundreds of ad-hoc tables indicate this database has been in continuous operation for at least 15 years.

The database targets SQL Server 2016 (Sql130), consistent with the US prepaid warehouse, and is a current-generation SQL Server deployment. However, the internal design patterns (EAV case model, GOTO error handling in some procedures, hardcoded business logic) reflect organic growth rather than planned architecture.

---

## 2. Architectural Role

RiskDB is Onbe's **central compliance data hub** for the US business:

```
Operational Systems                    RiskDB                      Consumers
─────────────────────                  ──────                      ─────────
EcountCore (linked server) -->   Daily Risk Monitoring     -->  Risk Team Dashboard
FDR Processor              -->   AML Case Management       -->  Compliance Officers
NACHA/ACH files            -->   Fraud Dispute Tracking    -->  Customer Service
NESS Screening Engine      -->   DMT Back-end              -->  DMT Application
                                 CFPB Reporting            -->  CFPB (regulatory)
                                 EUC Analytics             -->  Excel/BI Add-ins
                                 NOC Processing            -->  Operations
```

---

## 3. Compliance System Dependencies

### 3.1 NESS Screening Integration
The NESS daily extract (`GBLoads.uspNESSDailyExtract` in the Vendor database) feeds cardholder data to an external NESS screening engine, with results returned as `ness_hits` records. The string-matching functions in RiskDB (`fn_calculateCommon`, `fn_GetCommonCharacters`, etc.) suggest that secondary in-database fuzzy matching may supplement the external NESS screening.

**Critical architectural gap:** The NESS screening is batch-based (daily). For a PCI DSS Level 1 / BSA-regulated payments processor, real-time or near-real-time OFAC screening is required at:
- Account opening
- Transaction processing for certain high-risk transaction types
- Name or address change events

The current batch screening architecture means there is a window (up to 24 hours) during which a newly sanctioned party could transact on a prepaid card without triggering a block.

### 3.2 DMT Application Dependency
The DMT application (`dmt-web_WAPP`, `dmt_WAPP` repos visible in the broader listing) is a critical operational tool whose entire data tier lives in RiskDB. The DMT manages:
- AML cases (and thus BSA SAR obligations)
- Fraud/dispute cases (Reg E)
- Client contracts
- Pricing data
- Program build information
- Subpoenas (legal hold)
- Vendor invoices
- User entitlements

RiskDB is therefore a **core operational dependency** for the Compliance, Legal, and Operations teams — not just an analytical database.

### 3.3 Mantas Legacy
The `_archived/mantas/` folder contains tables and procedures from an Oracle Mantas AML system integration. Mantas (now Oracle Financial Services Anti Money Laundering) was a commercial AML platform. Its retirement and replacement with the current DMT-based approach suggests a significant AML system migration occurred. The archived objects should be confirmed as truly retired and not referenced by any active procedure.

---

## 4. Integration Complexity

### 4.1 Linked Server Dependency
`DailyRiskReports` and `Analytics_sp_AML_Case_Module` depend heavily on the `[REPORTINGDBSERVER]` linked server. This creates the same operational brittleness as in the warehouse databases.

### 4.2 Cross-Database Joins in AML Procedure
`Analytics_sp_AML_Case_Module` (lines 32–36) joins:
- `[REPORTINGDBSERVER].ECountcore_ss.dbo.fdr_dda_account_balance_status`
- `[REPORTINGDBSERVER].ECountcore_ss.dbo.app_profile_promotion_label`
- `[REPORTINGDBSERVER].ECountcore_ss.dbo.app_profile_global_label`
- `[REPORTINGDBSERVER].ecountcore_ss.dbo.core_profile_programs_bin_bank_vw`
- `[REPORTINGDBSERVER].ECountcore_ss.dbo.fdr_card_account`
- `[REPORTINGDBSERVER].ECountcore_ss.dbo.fdr_card_account_registration`
- `[REPORTINGDBSERVER].ecountcore_ss.dbo.fdr_profile_scope`

Seven cross-database joins in a single AML procedure creates significant performance and availability risk. If any of these linked server tables is unavailable, the AML case module fails entirely.

---

## 5. Migration Complexity Assessment

Migrating RiskDB to a modern architecture would be among the most complex migrations in the Onbe portfolio:

| Component | Migration Complexity | Notes |
|---|---|---|
| Daily fraud monitoring | Medium | Can be re-implemented as Azure Stream Analytics or SQL jobs |
| AML case management | Very High | EAV model requires complete re-architecture; BSA data continuity requirements |
| DMT back-end | Very High | Application-database co-dependency; must migrate app and data together |
| CFPB/regulatory reporting | High | Regulatory continuity must be maintained during migration |
| OFAC screening | High | Must maintain screening coverage during any transition |
| Ad-hoc tables (hundreds) | Medium | Audit, archive, or delete; mostly dead data |

---

## 6. Technical Debt Summary

| Item | Impact | Severity |
|---|---|---|
| Hardcoded AML case owner | BSA compliance gap | High |
| Hardcoded AML threshold = 0 | Operational noise / false positives | Medium |
| EAV case model | Security, query complexity, scalability | High |
| Hundreds of ad-hoc staging tables | Governance, storage | Medium |
| No CI/CD | Unvalidated compliance-critical changes | High |
| Batch-only OFAC screening | Potential BSA gap | Critical |
| Linked server fragility | Availability | Medium |
| Mantas legacy objects | Dead code confusion | Low |
| Truncate-and-reload monitoring | Data loss on failure | Medium |
| Hardcoded business rules in procedures | Maintenance | Medium |
