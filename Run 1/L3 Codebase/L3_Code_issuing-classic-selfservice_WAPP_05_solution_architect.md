# Solution Architect Analysis — issuing-classic-selfservice_WAPP

## 1. Technical Debt Inventory

### 1.1 Critical Technical Debt

| Item | Location | Severity | Notes |
|---|---|---|---|
| Django 2.1.11 (EOL) | `requirements.txt` line 2 | CRITICAL | No security patches since April 2021 |
| `DEBUG = True` hardcoded | `portal/settings.py` line 27 | CRITICAL | Manual production override required; risk of debug mode in prod |
| Direct DB writes to legacy tables | All module signal handlers | HIGH | Bypasses service-layer validation |
| Shared single DB credential for 4 databases | `settings.py` lines 63–65 | HIGH | Blast radius on credential leak |
| No MFA visible | `accounts/` app | HIGH | PCI DSS v4.0.1 Req 8.4 |
| `numpy==1.17.1`, `urllib3==1.25.3` EOL | `requirements.txt` | HIGH | Known CVEs |
| No Dockerfile / container deployment | Repo root | MEDIUM | Manual deployments likely |
| `django-debug-toolbar` in production middleware | `settings.py` line 87, 114 | MEDIUM | Must confirm it is disabled in prod |

### 1.2 Medium Technical Debt

- No Content Security Policy (CSP) header configured.
- `STATIC_ROOT` only set when `DEBUG is False` — static file serving in production via Apache/IIS assumed but not documented.
- `django-debug-toolbar` is in `INSTALLED_APPS` (line 93) — must be disabled in production.
- Test coverage tooling present but no CI pipeline to enforce coverage thresholds.
- `portal/settings.py` comment: `# %%%% <DEV OPS NOTIFICATION>: DELETE THE FOLLOWING LINES DURING PRODUCTION DEPLOYMENT %%%%` — manual step, easily overlooked.

## 2. Security Vulnerability Analysis

### 2.1 Authentication and Session Management

**Risk: Brute-force lockout only, no MFA**

`axes.middleware.AxesMiddleware` (settings.py line 129) provides lockout after failed attempts with a 12-hour cooldown (line 145: `AXES_COOLOFF_TIME = 12`). No second factor is implemented. Given the portal's ability to issue checks, block accounts, and void card inventory, PCI DSS v4.0.1 Requirement 8.4 mandates MFA for all administrative access to the CDE.

**Risk: Session cookie security conditional on DEBUG=False**

`SESSION_COOKIE_SECURE = True` (settings.py line 48) is only set when `DEBUG is False`. If DEBUG is accidentally True in production, session cookies are transmitted over HTTP.

### 2.2 Direct Database Mutation Without Service-Layer Authorization

`block_global_deposit/models.py` signal handler (line 49–57) calls `CoreDeviceQuery.update_core_records_to_block_all_beneficiary_accounts(dda_number)` directly. There is no service-layer re-validation of the user's authority to block that particular DDA or confirmation that the DDA belongs to the expected program. A staff user with portal access could potentially block any DDA by constructing the correct form input.

Similarly, `change_usernames/models.py` (line 30) calls `q.update_username(old_username, new_username)` with no server-side validation that the `old_username` actually belongs to the `dda_number` provided. These are IDOR (Insecure Direct Object Reference) risks.

### 2.3 `core_device_protected.verification_code` in Scope

`ecountcore/models.py` line 104: `verification_code = models.CharField(max_length=32, blank=True, null=True)` in `CoreDeviceProtected`. The field name strongly suggests it stores a card verification value. If this is CVV/CVC or PIN offset data, storage is prohibited under PCI DSS Requirement 3.3 (SAD must not be stored after authorisation). The portal ORM model reads this table, pulling the `verification_code` into the application memory. **This requires immediate investigation and data classification.**

### 2.4 Django Debug Toolbar in Middleware

`debug_toolbar.middleware.DebugToolbarMiddleware` is listed as **the first middleware** in the stack (settings.py line 114). If `DEBUG` is accidentally True in production, the debug toolbar will be active and expose SQL queries, template context, request data, and environment variables to any authenticated (and potentially unauthenticated, depending on `INTERNAL_IPS` config) user.

### 2.5 Emboss Code Generation — Information Sensitivity

`generate_emboss_code/models.py` stores `emboss_codes_generated` (up to 1200 chars) in the `ProdSupportPortal` database. Emboss codes are used to control card fulfilment/personalisation. If these codes are predictable or reused, they could be exploited to generate fraudulent cards.

## 3. Key Classes and Methods

| Class / Function | File | Purpose |
|---|---|---|
| `Profile` | `accounts/models.py:8` | User profile model extending Django User |
| `create_user_profile` / `save_user_profile` | `accounts/models.py:16–23` | Signal handlers to sync Profile with User |
| `IssueCheck` | `issue_checks/models.py:17` | Audit record for check issuance |
| `update_fdr_dda_account_journal` | `issue_checks/models.py:39` | Post-save signal — writes ledger entry |
| `BlockGlobalDeposit` | `block_global_deposit/models.py:12` | Audit record for account blocking |
| `update_core_device` | `block_global_deposit/models.py:48` | Post-save signal — mutates core_device |
| `BlockGlobalDepositRollback` | `block_global_deposit/models.py:28` | Rollback state tracker |
| `VoidCardInventory` | `void_card_inventory/models.py:13` | Audit record for card voiding |
| `update_instant_issue_card` | `void_card_inventory/models.py:35` | Post-save signal — voids cards in jobsvc |
| `TraceIp` | `trace_ip/models.py:8` | IP lookup audit record |
| `ChangeUsername` | `change_usernames/models.py:12` | Username change audit record |
| `update_user_validation_information` | `change_usernames/models.py:25` | Post-save signal — updates cbaseapp username |
| `update_core_member_addenda` | `change_usernames/models.py:33` | Post-save signal — updates ecountcore addenda |
| `GenerateEmbossCode` | `generate_emboss_code/models.py:9` | Emboss code generation audit record |
| `FdrDdaAccountBalance` | `ecountcore/models.py:17` | View-backed balance model (ecountcore DB) |
| `FdrDdaAccountJournal` | `ecountcore/models.py:32` | Ledger journal model (ecountcore DB) |
| `CoreDeviceProtected` | `ecountcore/models.py:94` | Protected device model with verification_code |
| `LoginHistory` | `cbaseapp/models.py:4` | Cardholder login audit log (cbaseapp DB) |
| `UserValidationInformation` | `cbaseapp/models.py:20` | Cardholder credentials table (cbaseapp DB) |
| `HomeTemplateView` / `LogoutSuccess` | `portal/views.py` | Base portal views |
| `PrefixValidator` / `NumericValidator` / `BlankValidator` | `portal/models_tools/validators.py` | DDA number field validators |

## 4. Remediation Priorities

| Priority | Item | Recommended Action |
|---|---|---|
| P0 | Django 2.1.11 EOL | Upgrade to Django 4.2 LTS immediately |
| P0 | `DEBUG = True` hardcoded | Replace with environment variable; add deployment validation script |
| P0 | Classify `CoreDeviceProtected.verification_code` | Engage data steward; if SAD, remove field from ORM and confirm DB-level protection |
| P1 | No MFA | Implement MFA via Onbe identity provider (Azure AD MFA or TOTP) |
| P1 | IDOR risk in block/change-username | Add server-side ownership validation before DB mutation |
| P1 | Shared DB credentials | Implement per-database least-privilege service accounts |
| P2 | Upgrade numpy, urllib3, other EOL packages | Update `requirements.txt` and re-test |
| P2 | Add CI/CD build + test pipeline | Add GitHub Actions workflow for automated testing and deployment |
| P2 | CSP headers | Configure `django-csp` package |
| P3 | Remove debug_toolbar from production | Conditional installation only in dev environments |
| P3 | Container-based deployment | Add `Dockerfile` and `docker-compose.yml` for consistent deployment |
