# DS_DB_nexpay_claimable — Data Architect Report

## 1. Database Object Inventory

| Object Type | Count | Notes |
|-------------|-------|-------|
| Tables | **0** | No tables — pure view layer |
| Views | **4** | All cross-database views over EcountCore |
| Stored Procedures | **0** | None |
| Functions | **0** | None |
| Indexes | **0** | Views are non-indexed; NOLOCK hints used |
| Defaults | **0** | None |
| Migrations / DeltaSql | **0** | No migration history |

This is the smallest database schema in the analysis set. All data resides in `EcountCore`.

## 2. View Definitions — Complete Specification

### 2.1 `dbo.claimable_payment`
**File**: `dbo/Views/claimable_payment.sql`

```sql
CREATE VIEW [dbo].[claimable_payment] AS
SELECT p.*, r.first_name, r.middle_name, r.last_name
FROM EcountCore..claimable_payment p WITH (NOLOCK)
INNER JOIN EcountCore..core_member m WITH (NOLOCK) ON p.owner_id = m.id
INNER JOIN EcountCore..core_registration_basic r WITH (NOLOCK) ON m.registration_id = r.id
```

**Source Tables**:
| EcountCore Table | Join | Purpose |
|-----------------|------|---------|
| `claimable_payment` | Root | Payment records, claim tokens, amounts, status |
| `core_member` | INNER JOIN on `p.owner_id = m.id` | Links payment to member |
| `core_registration_basic` | INNER JOIN on `m.registration_id = r.id` | Recipient name fields |

**Projected Columns**:
- `p.*` — All columns of `EcountCore..claimable_payment` (schema-dependent; see note below)
- `r.first_name` — **PII: Recipient first name**
- `r.middle_name` — **PII: Recipient middle name**
- `r.last_name` — **PII: Recipient last name**

**PII/Sensitivity Flag**: HIGH — name + payment data combined

**Note on `SELECT p.*`**: The wildcard projection means this view's column set is dynamic — it will automatically include any new columns added to `EcountCore..claimable_payment`. If a column containing a PAN, account number, or other sensitive data is added to the EcountCore table, it would be automatically exposed by this view. **Recommendation**: Replace `p.*` with an explicit column list.

### 2.2 `dbo.recipient_registration`
**File**: `dbo/Views/recipient_registration.sql`

**Source Tables**:
| EcountCore Table | Join | Purpose |
|-----------------|------|---------|
| `core_member` A | Root | Member record (provides `id`) |
| `core_registration` B | INNER JOIN | Registration root (links registration sub-tables) |
| `core_registration1` C | INNER JOIN | Name fields and email addresses |
| `core_registration2` D | LEFT OUTER JOIN | Primary address and phone fields |
| `core_registration_extended_address` E | LEFT OUTER JOIN (type=1) | Fallback address |
| `core_registration_extended_phone` F | LEFT OUTER JOIN (type=1) | Fallback home phone |
| `core_registration_extended_phone` G | LEFT OUTER JOIN (type=2) | Fallback business phone |
| `core_registration_extended_phone` H | LEFT OUTER JOIN (type=3) | Fallback mobile phone |

**Projected Columns with PII Classification**:

| Column | Source | PII Flag |
|--------|--------|----------|
| `id` | `core_member.id` | Internal identifier |
| `first_name` | `core_registration1.first_name` | **HIGH PII** |
| `middle_name` | `core_registration1.middle_name` | **HIGH PII** |
| `last_name` | `core_registration1.last_name` | **HIGH PII** |
| `suffix_name` | `core_registration1.suffix_name` | **LOW PII** |
| `email_address` / `home_email` | `core_registration1.home_email` | **HIGH PII / TCPA** |
| `business_email` | `core_registration1.business_email` | **HIGH PII** |
| `mobile_email` | `core_registration1.mobile_email` | **HIGH PII** |
| `address1` | `COALESCE(reg2.address1, ext_addr.address1)` | **MEDIUM PII** |
| `address2` | `COALESCE(reg2.address2, ext_addr.address2)` | **MEDIUM PII** |
| `attention_line` | `COALESCE(reg2.attention_line, ext_addr.address3)` | **MEDIUM PII** |
| `company_name` | `COALESCE(reg2.company_name, ext_addr.address4)` | **LOW PII** |
| `city` | `COALESCE(reg2.city, ext_addr.city)` | **MEDIUM PII** |
| `state` | `COALESCE(reg2.state, ext_addr.state)` | **MEDIUM PII** |
| `postal` | `COALESCE(reg2.postal, ext_addr.postal)` | **MEDIUM PII** |
| `country` | `COALESCE(reg2.country, ext_addr.country)` | **MEDIUM PII** |
| `phone` / `home_phone` | `COALESCE(reg2.home_phone, F.phone_country_code + F.phone_area_code + F.phone_number)` | **HIGH PII / TCPA** |
| `business_phone` | `COALESCE(reg2.business_phone, G.phone...)` | **HIGH PII** |
| `mobile_phone` | `COALESCE(reg2.mobile_phone, H.phone...)` | **HIGH PII / TCPA** |

**Total PII columns**: 20 out of 21 projected columns contain or derive from PII.

### 2.3 `dbo.claimable_payment_modality`
**File**: `dbo/Views/claimable_payment_modality.sql`

```sql
CREATE VIEW [dbo].[claimable_payment_modality] AS
SELECT * FROM EcountCore..claimable_payment_modality
```

**Purpose**: Reference data — payment modality options (ACH, card, check, etc.)  
**PII Flag**: No (reference/lookup data)  
**Risk**: `SELECT *` wildcard — same concern as `claimable_payment`

### 2.4 `dbo.claimable_payment_status`
**File**: `dbo/Views/claimable_payment_status.sql`

```sql
CREATE VIEW [dbo].[claimable_payment_status] AS
SELECT * FROM EcountCore..claimable_payment_status
```

**Purpose**: Reference data — payment status codes  
**PII Flag**: No (reference/lookup data)  
**Risk**: `SELECT *` wildcard

## 3. Cross-Database Dependency Map

All views depend on `EcountCore` database being:
- Present on the same SQL Server instance
- Accessible to the `nexpay_claimable` database's connection context
- Schema-compatible (no breaking changes to joined tables)

```
nexpay_claimable database
├── claimable_payment VIEW
│   ├── EcountCore..claimable_payment    ← CRITICAL dependency
│   ├── EcountCore..core_member           ← CRITICAL dependency
│   └── EcountCore..core_registration_basic ← CRITICAL dependency
├── recipient_registration VIEW
│   ├── EcountCore..core_member           ← CRITICAL dependency
│   ├── EcountCore..core_registration     ← CRITICAL dependency
│   ├── EcountCore..core_registration1    ← CRITICAL dependency
│   ├── EcountCore..core_registration2    ← IMPORTANT dependency
│   ├── EcountCore..core_registration_extended_address ← FALLBACK dependency
│   └── EcountCore..core_registration_extended_phone (×3) ← FALLBACK dependency
├── claimable_payment_modality VIEW
│   └── EcountCore..claimable_payment_modality ← CRITICAL dependency
└── claimable_payment_status VIEW
    └── EcountCore..claimable_payment_status ← CRITICAL dependency
```

**Risk**: Any schema change to `EcountCore` tables (`ALTER TABLE ... DROP COLUMN`) will break views silently at query time. No view-validation check is deployed.

## 4. PCI DSS CDE Scope Assessment

**Assessment: POTENTIALLY IN CDE SCOPE — REQUIRES INVESTIGATION**

The `claimable_payment` view exposes all columns of `EcountCore..claimable_payment` via `SELECT p.*`. The claim token or claim code stored in this table must be evaluated:

**Scenario 1 — Token is non-PAN**: If the claim token is a GUID or random alphanumeric value that does not resolve directly to a PAN, the database is **out of CDE scope**. The Claimable Choice product design implies this is the expected case.

**Scenario 2 — Token is a pseudo-PAN**: If the claim token follows a PAN-format (16-digit) or links directly to a card number in the same query result, this view is **in CDE scope**.

**Recommendation**: Query `EcountCore..claimable_payment` production data to determine the format of the claim token column. Confirm with the NexPay architecture team.

## 5. NOLOCK Usage Assessment

All four views use `WITH (NOLOCK)`:
- **Benefit**: No shared locks; non-blocking reads in high-concurrency environment.
- **Risk**: Dirty reads possible — may return uncommitted data or miss recently committed rows.
- **Assessment**: Acceptable for read-heavy claim portal operations where eventual consistency is tolerable (e.g., checking payment status), but should not be used for security-critical operations (e.g., confirming OFAC clearance or payment authorisation).

## 6. Data Retention

No retention policy is implemented in this database (no tables, no archival logic). Retention for claimable payment data is governed by EcountCore. Typical retention requirements:
- Claimable payment records: 7 years (financial records retention)
- Recipient PII: Per GLBA/CCPA/GDPR — subject to data subject deletion rights
- After deletion from EcountCore, these views automatically return no data for deleted records

## 7. Wildcard SELECT Risk Summary

Two of four views use `SELECT *` or `SELECT p.*`:

| View | Wildcard | Risk |
|------|----------|------|
| `claimable_payment` | `SELECT p.*` | **HIGH** — exposes all EcountCore claimable_payment columns |
| `claimable_payment_modality` | `SELECT *` | **LOW** — reference data only |
| `claimable_payment_status` | `SELECT *` | **LOW** — reference data only |
| `recipient_registration` | Explicit columns | **Best practice** — explicit column list |

**Recommendation**: Replace `p.*` in `claimable_payment` with an explicit column list documenting each projected field's purpose and sensitivity.
