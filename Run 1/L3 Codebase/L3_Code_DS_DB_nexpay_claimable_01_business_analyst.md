# DS_DB_nexpay_claimable — Business Analyst Report

## 1. Repository Identity

| Attribute | Value |
|-----------|-------|
| Repo name | DS_DB_nexpay_claimable |
| Internal alias | NexPay Claimable / Claimable Choice |
| Total source files | 5 |
| Object types | Views only (cross-database) |
| README | Comprehensive (84 lines — best-documented in this set) |
| Related service | `nexpay-claim-code-svc` |
| Data source | `EcountCore` database (cross-database queries) |

## 2. Business Purpose

`DS_DB_nexpay_claimable` is a **thin read-only view layer** exposing NexPay's Claimable Choice payment data to the `nexpay-claim-code-svc` Spring Boot microservice. Unlike the other databases in this analysis set, it contains **no tables of its own** — all data originates from the `EcountCore` database and is surfaced via SQL Server cross-database views.

**Claimable Choice** is Onbe's product that allows disbursement recipients to **choose their preferred payment method** from a menu of options (ACH direct deposit, virtual card, physical check, push-to-card, etc.). The workflow is:
1. Client submits a disbursement with `claimable=true`
2. EcountCore creates a `claimable_payment` record with a tokenised claim code
3. The recipient receives a notification with a link to the claim portal
4. The recipient authenticates and selects a payment modality
5. `nexpay-claim-code-svc` queries this database's views to retrieve payment and recipient data
6. The chosen payment is executed via the NexPay payment rail

## 3. Views Provided

The database exposes four views, all using `WITH (NOLOCK)` hints for non-blocking reads:

### 3.1 `dbo.claimable_payment`
```sql
-- File: dbo/Views/claimable_payment.sql
SELECT p.*, r.first_name, r.middle_name, r.last_name
FROM EcountCore..claimable_payment p
INNER JOIN EcountCore..core_member m ON p.owner_id = m.id
INNER JOIN EcountCore..core_registration_basic r ON m.registration_id = r.id
```
**Purpose**: Returns claimable payment records enriched with recipient name from the registration tables. This view is the primary query interface for the claim-code service to retrieve payment details and verify recipient identity.

**PII Exposure**: `first_name`, `middle_name`, `last_name` from `core_registration_basic` — cardholder identity data associated with a claimable payment. This constitutes GLBA-protected consumer financial information.

**Security Note**: `SELECT p.*` exposes all columns of `EcountCore..claimable_payment`, including payment amounts, claim tokens, status codes, and any internal identifiers. This is a broad projection — the specific columns of `claimable_payment` determine the full PII/compliance exposure.

### 3.2 `dbo.recipient_registration`
```sql
-- File: dbo/Views/recipient_registration.sql
SELECT A.id, C.first_name, C.middle_name, C.last_name, C.suffix_name,
       C.home_email, C.business_email, C.mobile_email,
       D/E.address1/2, D/E.city/state/postal/country,
       COALESCE(D.home_phone, phones) AS home_phone,
       COALESCE(D.business_phone, phones) AS business_phone,
       COALESCE(D.mobile_phone, phones) AS mobile_phone
FROM EcountCore..core_member A
[with 6 joins across core_registration tables]
```
**Purpose**: Provides a denormalised recipient profile combining name, email addresses (home, business, mobile), postal address, and phone numbers (home, business, mobile). Used by `nexpay-claim-code-svc` to populate the claim portal UI with pre-filled recipient information and to send verification communications.

**PII Exposure**: 
- Full name (first, middle, last, suffix) — **HIGH PII**
- Three email addresses (home, business, mobile) — **HIGH PII / TCPA**
- Three phone numbers (home, business, mobile) — **HIGH PII / TCPA**
- Full postal address (address1/2, city, state, postal, country) — **MEDIUM PII**

### 3.3 `dbo.claimable_payment_modality`
```sql
-- File: dbo/Views/claimable_payment_modality.sql
SELECT * FROM EcountCore..claimable_payment_modality
```
**Purpose**: Reference data — exposes the available payment modalities (ACH, virtual card, check, push-to-card, etc.) that a recipient can select for their claimable payment. Used to populate the payment selection dropdown in the claim portal.

**PII Exposure**: Likely a reference/lookup table; no direct PII expected. However, `SELECT *` means any future PII columns added to `claimable_payment_modality` in EcountCore would automatically be exposed.

### 3.4 `dbo.claimable_payment_status`
```sql
-- File: dbo/Views/claimable_payment_status.sql
SELECT * FROM EcountCore..claimable_payment_status
```
**Purpose**: Reference data — exposes payment status codes (pending, claimed, expired, cancelled, etc.) for the claimable payment workflow. Used by the claim-code service for status filtering and display.

**PII Exposure**: Lookup table, no PII expected.

## 4. Data Flows

```
Client Disbursement (claimable=true)
        ↓
EcountCore..claimable_payment [created]
        ↓
nexpay_claimable..claimable_payment VIEW ←── nexpay-claim-code-svc (reads)
        ↓
Recipient notification (claim URL + token)
        ↓
Recipient accesses claim portal
        ↓
nexpay_claimable..recipient_registration VIEW ←── claim portal pre-fill
        ↓
Recipient selects modality
        ↓
nexpay_claimable..claimable_payment_modality VIEW ←── modality dropdown
        ↓
NexPay payment execution (ACH/card/check)
        ↓
nexpay_claimable..claimable_payment_status VIEW ←── status polling
```

## 5. Regulatory Relevance

### PCI DSS
The `claimable_payment` view exposes all columns of `EcountCore..claimable_payment`. If the claimable_payment table in EcountCore stores payment card numbers or claim tokens that function as PANs, this view would be in PCI CDE scope. The token/claim-code value stored in claimable_payment must be assessed:
- If it is a tokenised reference (not a PAN) — **out of CDE scope**
- If it resolves to a PAN without additional security steps — **in CDE scope**

The Claimable Choice product is designed to allow recipients to select their payment rail; the token is the claim identifier, not the card number itself. Most likely out of CDE scope, but requires confirmation.

### NACHA / Regulation E
When a recipient selects ACH as their payment modality, the subsequent ACH transaction is Reg E-governed. The `nexpay_claimable` database itself does not store ACH account or routing numbers — it only stores the modality selection. The actual ACH execution happens downstream via NexPay's payment services.

### TCPA (Telephone Consumer Protection Act)
The `recipient_registration` view exposes mobile phone numbers used for claim notifications. TCPA requires prior express consent for automated/SMS notifications. Onbe must maintain consent records for these phone numbers (stored in the NotificationSvc consent tables, not here).

### GDPR / CCPA
Recipient PII (name, email, phone, address) in the `recipient_registration` view qualifies as personal data under GDPR (if EU recipients) and personal information under CCPA (if California residents). Data subject access and deletion rights must be supported. Because this is a view over EcountCore, deletion requests must be actioned in EcountCore tables.

## 6. Business Process Integration

| Upstream System | Role |
|-----------------|------|
| EcountCore | Authoritative source for all data |
| `jobservice` (job_action_add_funds.claim_code) | Creates claimable payment records |
| NexPay order orchestrator | Initiates payment execution |

| Downstream System | Role |
|------------------|------|
| `nexpay-claim-code-svc` | Primary consumer of all 4 views |
| Recipient self-service portal | Presents claim options to recipients |
| NexPay payment rails | Executes chosen payment |

## 7. Unique Characteristics

This is the **simplest and best-documented** database in the six-repo set:
- Only 4 SQL files (all views)
- Comprehensive README documenting all views, prerequisites, and deployment
- Clear `WITH (NOLOCK)` usage policy
- Explicit cross-database dependency declaration
- License noted as "Proprietary - Onbe East"

The simplicity is by design — the database exists purely to provide an abstraction layer that insulates `nexpay-claim-code-svc` from changes to EcountCore's internal table structure. If EcountCore is refactored, only these 4 view files need updating rather than the microservice's query logic.
