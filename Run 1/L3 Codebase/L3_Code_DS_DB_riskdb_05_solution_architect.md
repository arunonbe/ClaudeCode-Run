# DS_DB_riskdb — Solution Architect Assessment

## 1. Critical Security and Compliance Findings

### 1.1 CRITICAL: Hardcoded AML Case Owner in Production Code
**Finding:** `dbo/Stored Procedures/Analytics_sp_AML_Case_Module.sql`, line 512:
```sql
'Nathan.Sandiford' [Field Value]  -- Current Owner
```
A named individual is hardcoded as the owner for all auto-created AML cases. This means:
- If this individual has left Onbe, new AML cases are assigned to a non-existent or former employee
- Cases may go uninvestigated, creating a direct BSA/AML Program violation
- SAR filing deadlines (30 days for known SAR, 60 days for suspected) may be missed

**Remediation (Priority: P0 — Immediate):**
- Verify whether Nathan Sandiford is still an active employee in the AML role
- Replace the hardcoded name with a configurable parameter from a reference table
- Add an alert if AML case owner assignment fails due to unrecognised username

### 1.2 CRITICAL: Batch-Only OFAC Screening Architecture Gap
**Finding:** OFAC screening relies on the NESS daily batch extract from the Vendor database. There is no real-time screening procedure in RiskDB. The `fn_calculateCommon*` / `fn_GetCommonCharacters` string-matching functions implement fuzzy name matching but do not reference a local OFAC SDN list table.

**Regulatory Basis:** OFAC regulations and BSA require that transactions to/from OFAC-designated parties be blocked immediately. A 24-hour screening window means:
- A cardholder added to the SDN list at 9 AM could transact throughout the business day
- A new account opened for a sanctioned party would pass real-time controls if the daily NESS batch has already run

**Remediation (Priority: P0 — Consult Compliance):**
- Engage Compliance/Legal to determine if the current batch screening cadence satisfies OFAC obligations for Onbe's specific product types and risk profile
- If not, implement real-time screening at account opening and high-risk transaction types
- Investigate whether the NESS platform provides a real-time API that can be called synchronously

### 1.3 HIGH: PII Stored in Risk Monitoring Tables Without Data Governance
**Finding:** `DailyRiskReports.sql`, lines 388–407, the `monitor_ach_detail` insert query pulls `first_name`, `last_name`, `home_email` from the operational database and stores it in RiskDB's `monitor_ach_detail` table. This table is repopulated daily (not retained historically), but it contains live PII during each 24-hour window.

**Impact:**
- Any user or service with access to RiskDB can query cardholder names and email addresses
- If the daily TRUNCATE fails (e.g., a rare lock acquisition failure), PII from previous day persists
- `monitor_ach_detail` is not subject to the same data retention or access controls as the core cardholder systems

**Remediation (Priority: P1):**
- Review whether cardholder name and email are necessary for the ACH monitoring use case, or whether DDA number alone suffices for risk decisioning
- If PII retention is required, apply the same access controls as for primary cardholder systems
- Add explicit retention enforcement: ensure the TRUNCATE at the start of each daily run is transactionally committed before repopulation

### 1.4 HIGH: AML Threshold Set to Zero — Operational False Positive Risk
**Finding:** `Analytics_sp_AML_Case_Module.sql`, line 7: `Declare @Threshold int = 0`

This threshold controls the minimum balance for AML case generation. Set to 0, it includes every account with any positive balance in the monitored verticals.

**Impact:**
- Potentially generates an enormous volume of AML investigation cases
- AML analysts may be overwhelmed by false positives, causing genuine SAR-worthy cases to be missed
- If the threshold is genuinely intentional (all positive-balance accounts in Maritime Payroll are investigated), this should be documented as a deliberate policy decision

**Remediation (Priority: P1 — Consult AML Compliance Team):**
- Confirm the intended threshold with the AML Compliance team
- If the zero threshold was an unintentional development artifact, set an appropriate risk-based threshold
- Replace the hardcoded threshold with a configurable parameter in a reference table

### 1.5 HIGH: Ad-hoc Tables Containing Potentially Sensitive Client Data
**Finding:** The `Tables1` subfolder contains tables named with client-identifiable names:
- `0328240_Grifols_Letters.sql` — named for Grifols (a healthcare client)
- `04012388_JAN2012.sql`, `04012388_DEC2011.sql` — dated client-specific tables

These tables were created for ad-hoc analyses and may contain cardholder data, transaction records, or other sensitive information without any data governance controls.

**Remediation (Priority: P1):**
- Audit the contents of all dated and client-named tables in Tables1/Tables2/Tables3
- If they contain cardholder data, apply appropriate access controls or delete
- Implement a governance policy prohibiting ad-hoc tables in production databases

---

## 2. All Database Objects — Key Objects

### 2.1 Core Stored Procedures

| Procedure | Purpose | Compliance Criticality |
|---|---|---|
| `DailyRiskReports` | Daily fraud monitoring — 8 risk tables | High — fraud operations |
| `Analytics_sp_AML_Case_Module` | AML case auto-generation | Critical — BSA |
| `Analytics_sp_DMT_AMLCDD_MonthlyReport` | AML CDD monthly report | Critical — BSA |
| `Analytics_sp_DMT_AMLCDD_PeriodicReview` | CDD periodic review | Critical — BSA |
| `Analytics_sp_CFPB_Update` | CFPB reporting | High — CFPB supervision |
| `sp_FRAUD_REPORT_124` | Chargebacks previous day | High — Reg E |
| `sp_FRAUD_REPORT_125` | Chargeback claim type/status | High — Reg E |
| `sp_FRAUD_REPORT_127` | Chargebacks closed previous day | High |
| `sp_FRAUD_REPORT_133` | Chargebacks closed previous month | High |
| `sp_FRAUD_REPORT_134` | Cases received previous month | High |
| `sp_FRAUD_REPORT_139` | Oldest open case | High |
| `sp_FRAUD_REPORT_140` | Cases closed previous day | High |
| `sp_FRAUD_REPORT_142` | Cases under $200 | Medium |
| `sp_FRAUD_REPORT_163` | Pending cases previous day | High |
| `sp_FRAUD_REPORT_165` | Pending/Closed/Open totals | High |
| `sp_FRAUD_REPORT_173` | Past-due cases | High — SLA compliance |
| `sp_NOC_Transform_Combine_NOCFiles` | NOC file processing | High — NACHA |
| `sp_Get_DDA_From_Card_Number` | DDA lookup by card number | Sensitive — PAN/DDA linkage |
| `sp_Get_DDA_From_Card_PUID` | DDA lookup by PUID | Sensitive |
| `sp_Get_DDA_From_Check_Number` | DDA lookup by check number | Sensitive |
| `EUC_DMT_CASE_AgentAssignment_Fraud` | Auto-assign fraud cases to agents | High |
| `EUC_DMT_CASE_AgentAssignment_ACH` | Auto-assign ACH cases | High |
| `EUC_DMT_CASE_AgentAssignment_Dispute` | Auto-assign dispute cases | High |
| `EUC_DMT_AMLCase_DATAUPDATE` | Update AML case data | Critical |
| `EUC_DMT_AMLCDD_DATAUPDATE` | Update AML CDD data | Critical |
| `EUC_DMT_Subpoena_DATAUPDATE` | Update subpoena records | Critical — Legal |

### 2.2 String-Matching Functions (Jaro-Winkler components)

| Function | Purpose |
|---|---|
| `fn_calculateCommon` | Calculate common characters (Jaro component) |
| `fn_calculateCommon2` | Variant |
| `fn_calculateMatchWindow` | Match window size calculation |
| `fn_calculatePrefixLength` | Common prefix length |
| `fn_calculateTranspositions` | Transposition count |
| `fn_GetCommonCharacters` | Extract common characters |

These implement fuzzy name matching used for AML/sanctions screening name comparison.

---

## 3. Dynamic SQL Risk

`sp_Get_DDA_From_Card_Number`, `sp_Get_DDA_From_Card_PUID`, and `sp_Get_DDA_From_Check_Number` perform lookups that could involve dynamic SQL if card numbers or PUIDs are used to construct queries. These require a **security review** to confirm they are properly parameterised. Injection into a procedure that returns DDA numbers would be a critical vulnerability.

---

## 4. Remediation Priority Table

| Priority | Item | Effort | Regulation |
|---|---|---|---|
| P0 | Verify/replace hardcoded AML case owner | Low (hours) | BSA |
| P0 | Engage Compliance re: batch OFAC screening adequacy | Low (immediate) | OFAC |
| P1 | Review AML threshold (currently 0) | Low | BSA |
| P1 | Audit ad-hoc tables for sensitive content | Medium | Privacy, PCI |
| P1 | Review PII in monitor_ach_detail necessity | Low | Privacy |
| P1 | Security review of sp_Get_DDA_* procedures | Low | PCI DSS |
| P2 | Implement CI/CD for compliance-critical DB | Medium | PCI Req 6 |
| P2 | Replace hardcoded business rules with reference tables | Medium | Maintainability |
| P2 | Evaluate real-time OFAC screening implementation | Very High | OFAC/BSA |
| P3 | Refactor EAV case model for AML data | Very High | Maintainability |
| P3 | Decommission/archive Mantas objects | Low | Housekeeping |

---

## 5. Compliance Gap Summary

| Regulation | Gap | Severity |
|---|---|---|
| BSA/AML | Hardcoded case owner — cases may go unreviewed | Critical |
| OFAC | Batch-only screening — 24-hour window gap | Critical |
| BSA | AML threshold 0 — all accounts flagged, risk of analyst overload masking genuine SAR cases | High |
| Reg E | No visible automated escalation for past-due disputes | Medium |
| CCPA/GDPR | PII in monitor_ach_detail without governance | High |
| PCI DSS Req 6 | No CI/CD — unvalidated changes to compliance-critical database | High |
| NIST CSF | Ad-hoc tables with potentially sensitive data | Medium |
