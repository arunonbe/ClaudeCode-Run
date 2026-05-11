# Data Architect Analysis — issuing-classic-selfservice_WAPP

## 1. Database Architecture

The portal connects to **four Microsoft SQL Server databases** configured in `portal/settings.py` (lines 171–212). In test mode the engine falls back to SQLite in-memory.

| Django DB alias | SQL Server Database Name | Purpose |
|---|---|---|
| `default` | `ProdSupportPortal` | Portal audit/action tables |
| `ecountcore` | `Ecountcore` | Legacy eCount core ledger and device tables |
| `cbaseapp` | `cbaseapp` | Cardholder authentication and login history |
| `jobsvc` | `jobsvc` | Job service for instant-issue card processing |

Connection credentials are shared across all four databases (`database_user`, `database_password` from config). No per-database least-privilege credentials are visible.

## 2. Data Entities and Table Mapping

### 2.1 Portal Audit Tables (ProdSupportPortal DB)

These are Django-managed tables:

| Django Model | Table Name | Sensitive Fields |
|---|---|---|
| `Profile` | `accounts_profile` | user FK, dept |
| `IssueCheck` | `issue_checks_issuecheck` | `dda_number` (16-char), `amount`, `fdr_dda_account_journal_entry_id` |
| `BlockGlobalDeposit` | `block_global_deposit_blockglobaldeposit` | `dda_number` |
| `BlockGlobalDepositRollback` | `block_global_deposit_blockglobaldepositrollback` | `beneficiary_id_blocked`, `previous_block_code` |
| `VoidCardInventory` | `void_card_inventory_voidcardinventory` | `dda_number`, `puid`, `affiliate_id` |
| `TraceIp` | `trace_ip_traceip` | `ip_address` |
| `ChangeUsername` | `change_usernames_changeusername` | `dda_number`, `old_username`, `new_username` |
| `GenerateEmbossCode` | `generate_emboss_code_generateembosscode` | `program_id`, `emboss_codes_generated` |

**PCI/Sensitive Data Flag**: `dda_number` appears in `IssueCheck`, `BlockGlobalDeposit`, `VoidCardInventory`, and `ChangeUsername` models. The DDA number is a 16-character account identifier that may correspond to or be derivable from a card PAN; it must be treated as cardholder data under PCI DSS. It is stored in plain text in the audit tables.

### 2.2 Ecountcore DB (Legacy, unmanaged ORM models)

File: `ecountcore/models.py`

| Model | Table | Notable Sensitive Fields |
|---|---|---|
| `FdrDdaAccountBalance` | `fdr_dda_account_balance` | `dda_number` (PK, 16 chars), `amount_available`, `amount_pending` — **FINANCIAL** |
| `FdrDdaAccountJournal` | `fdr_dda_account_journal` | `dda_number`, `amount`, `fee`, transaction phase/status — **FINANCIAL LEDGER** |
| `CoreDevice` | `core_device` | `owner_id`, `block_code` |
| `CoreDeviceDda` | `core_device_dda` | `dda_number` (stored with dot in column name: `dda.number`) |
| `CoreDeviceProtected` | `core_device_protected` | `verification_code` (max 32), `block_code` — **SENSITIVE: verification_code may be a PIN-derived or CVV value** |
| `CoreMemberAddenda` | `core_member_addenda` | `value` (up to 40 chars) — stores username/member addenda |
| `CoreCardAccountEmbossHistory` | `core_card_account_emboss_history` | `exp_date`, `tracking_number`, `pin_requested` (bool) — **SENSITIVE: expiry date and PIN request flag** |
| `CoreProfileFulfillment` | `core_profile_fulfillment` | `emboss_code` (32 chars) |

**PCI/Sensitive Data Flags**:
- `CoreDeviceProtected.verification_code` — field name implies this could hold a CVV, PIN offset, or verification value. Must be classified and confirmed with the data steward. If it is a CVV2/CVC2 equivalent this is **prohibited from storage** under PCI DSS Requirement 3.3.
- `CoreCardAccountEmbossHistory.pin_requested` — records whether a PIN was requested. If PIN data flows through this table it requires HSM-based storage.
- `FdrDdaAccountBalance` and `FdrDdaAccountJournal` — contain account balances and transaction amounts linked to cardholder DDA numbers. These are in scope for PCI DSS and Reg E.

### 2.3 Cbaseapp DB (Legacy, unmanaged ORM models)

File: `cbaseapp/models.py`

| Model | Table | Notes |
|---|---|---|
| `LoginHistory` | `login_history` | `username`, `ip_address`, `result_code`, `affiliate_id` — authentication audit log |
| `UserValidationInformation` | `user_validation_information` | `username` — **Note**: `password`, `password_type`, `secret_question`, `secret_answer` fields are **commented out** in the model (lines 24–30) indicating they exist in the database but are intentionally excluded from Django ORM access |
| `CbaseUser` | `cbase_user` | base cardholder user record |

**PCI/Sensitive Data Flags**: The commented-out password and secret-question fields in `user_validation_information` indicate that authentication credentials exist in this database. The portal intentionally avoids reading them, but the columns remain in the underlying table and could be accessible via direct database access.

### 2.4 Jobsvc DB

Accessed via `jobsvc/queries.py` (models in `jobsvc/models.py`). Stores instant-issue card orders and card records. Contains `InstantIssueCard` and `InstantIssueOrder` entities. The `VoidCardInventory` module writes against this database.

## 3. Data Flow

```
Staff Browser
    → Django Portal (ProdSupportPortal DB — audit log written)
        → ecountcore DB (core_device, fdr_dda_account_journal — mutated)
        → cbaseapp DB (user_validation_information — updated on username change)
        → jobsvc DB (instant_issue_card — voided on void card inventory)
```

## 4. PCI DSS Data Classification Summary

| Data Element | Location | PCI Classification | Risk |
|---|---|---|---|
| `dda_number` (16-char) | Multiple tables | Likely PAN or PAN-derived — CHD | **CRITICAL** — stored plaintext |
| `verification_code` | `core_device_protected` | Possible SAD (CVV/verification) | **CRITICAL** — must confirm; if SAD, storage prohibited |
| `exp_date` | `core_card_account_emboss_history` | SAD if full expiry stored | HIGH |
| Account balance / journal | `fdr_dda_account_*` | Financial cardholder data | HIGH |
| `username` | `user_validation_information`, `core_member_addenda` | PII | MEDIUM |
| `ip_address` | `login_history`, `trace_ip` | PII | MEDIUM |
| `pin_requested` flag | `core_card_account_emboss_history` | PIN-adjacent | MEDIUM — confirm if PIN value stored elsewhere |

## 5. Database Migrations

Django migration files are present for all portal-owned tables (e.g., `issue_checks/migrations/0001_initial.py` through `0008`). Legacy tables (`ecountcore`, `cbaseapp`, `jobsvc`) use `managed = False` throughout, meaning Django does not control their schema.
