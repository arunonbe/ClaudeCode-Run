# Business Analyst Analysis — issuing-classic-selfservice_WAPP

## 1. System Overview

`issuing-classic-selfservice_WAPP` is an internal operations portal built with **Django 2.1.11** (Python). It is not a cardholder-facing application; it is an **internal Issuing Operations / Production Support portal** used by Northlane/Onbe staff to perform administrative actions on Classic prepaid card accounts. The portal was originally branded under Northlane (logos in `portal/static/portal/images/Logos/` confirm Northlane branding). The Django project entry point is `manage.py` (line 6: `os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'portal.settings')`).

## 2. Functional Modules

The portal is composed of eight Django applications wired together in `portal/settings.py` (`INSTALLED_APPS`, lines 86–110) and routed via `portal/urls.py`:

### 2.1 Accounts (`accounts/`)
Standard Django authentication layer. Provides login, logout, sign-up, password change, and user profile management. Templates: `login.html`, `change_password.html`, `profile.html`, `signup.html`, `update_profile.html`. The `Profile` model extends `django.contrib.auth.models.User` with a `dept` field (`accounts/models.py`, line 9). Brute-force login protection is provided by `django-axes` (12-hour lockout, `settings.py` line 145: `AXES_COOLOFF_TIME = 12`).

### 2.2 Issue Checks (`issue_checks/`)
Allows staff to issue a paper check (or cancel an already-issued check) against a cardholder DDA account. The `IssueCheck` model (`issue_checks/models.py`, lines 17–57) captures `dda_number`, `amount`, `action_type` (Issued/Canceled), and references `fdr_dda_account_journal_entry_id`. On save, a signal handler (`update_fdr_dda_account_journal`) inserts a new row into the `fdr_dda_account_journal` table via `FdrDdaAccountJournalQuery.insert_new_record()`, which automatically adjusts the available balance via SQL Server triggers. Supports bulk upload via `left_panel_bulk_upload.html`.

### 2.3 Block Global Deposit (`block_global_deposit/`)
Enables staff to block or cancel a block on all beneficiary accounts tied to a DDA number. The `BlockGlobalDeposit` model (`block_global_deposit/models.py`, lines 12–46) records the `dda_number`, `action_type` (Block/Canceled block), and a `portal_transaction_id`. A post-save signal calls `CoreDeviceQuery.update_core_records_to_block_all_beneficiary_accounts()`. A companion `BlockGlobalDepositRollback` model tracks rollback state with `previous_block_code` codes (active/closed/pending-correction/suspended/initialized). Supports bulk upload.

### 2.4 Void Card Inventory (`void_card_inventory/`)
Used to void (or reactivate) instant-issue card inventory at a delivery site. `VoidCardInventory` model (`void_card_inventory/models.py`) accepts `affiliate_id`, `delivery_site_id`, `all_or_subset` selector, `dda_number`, and a list of PUIDs (partner user IDs). Post-save logic calls `InstantIssueCardQuery.update_all_unused_cards()` or subset variants depending on the ONLY/EXCEPT flag. This is a high-impact operation — voiding cards can affect cardholder access.

### 2.5 Trace IP (`trace_ip/`)
Fraud investigation tool. Staff enter an IP address and a lookback window (1–168 hours) and the portal queries login history. `TraceIp` model (`trace_ip/models.py`) records `ip_address` and `lookback_hours`. Results are likely drawn from `LoginHistory` in cbaseapp DB.

### 2.6 Change Usernames (`change_usernames/`)
Allows staff to change a cardholder's username (used for cardholder web portal login). `ChangeUsername` model (`change_usernames/models.py`) captures `old_username`, `new_username`, and `dda_number`. Two post-save signals fire: one updates `UserValidationInformation.username` in cbaseapp DB; a second updates `core_member_addenda` in ecountcore DB. Supports bulk upload.

### 2.7 Generate Emboss Code (`generate_emboss_code/`)
Generates card emboss codes for fulfilment vendors (Arroweye, Fiserv Standard, Fiserv POD). The model captures `program_id`, `vendor`, `vertical` (16 verticals including Claims, Payroll, Refunds, Consumer Incentive), and the number of codes to generate (1–100). Verticals include regulated payment categories (Loan Disbursement, Public Sector, Passenger Compensation), which have compliance implications under Reg E.

### 2.8 Supporting Infrastructure Apps
- **`cbaseapp/`** — ORM models wrapping `login_history`, `user_validation_information`, and `cbase_user` tables (all `managed = False`, i.e., read from legacy SQL Server). Password fields are present but **commented out** in `cbaseapp/models.py` (lines 24–30 — passwords excluded from ORM).
- **`ecountcore/`** — ORM models for `core_device`, `core_device_dda`, `core_device_protected`, `core_member_addenda`, `fdr_dda_account_balance`, `fdr_dda_account_journal`, `core_card_account_emboss_history`, `core_profile_fulfillment`.
- **`jobsvc/`** — Wraps jobsvc database for instant-issue card and order queries.

## 3. Business Processes Supported

| Module | Business Process | Criticality |
|---|---|---|
| issue_checks | Disburse paper check from prepaid balance | High — financial transaction |
| block_global_deposit | Emergency block on all beneficiary accounts | Critical — fraud response |
| void_card_inventory | Void unused instant-issue cards at site | High — inventory management |
| trace_ip | Fraud investigation by IP lookup | Medium — investigation tool |
| change_usernames | Cardholder username correction | Medium — identity management |
| generate_emboss_code | Card personalisation trigger | Medium — fulfilment operations |

## 4. User Base

The portal uses Django's built-in user model extended with a `dept` field (`accounts/models.py`, line 10). Access is restricted to authenticated internal staff. Login lockout after repeated failures (django-axes). No multi-factor authentication is visible in the codebase.

## 5. Regulatory Relevance

- **Reg E / NACHA**: The `issue_checks` module writes financial journal entries that affect cardholder available balances — Reg E dispute handling applies.
- **PCI DSS**: The portal reads from `core_device_protected` (which includes `verification_code` — likely a card verification or PIN-related field), making this system potentially in scope for the CDE.
- **GLBA / CCPA**: The portal displays and modifies cardholder PII (username, DDA number, IP address) and is therefore subject to GLBA safeguards.
