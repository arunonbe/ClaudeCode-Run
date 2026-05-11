# Enterprise Architect Analysis — issuing-classic-selfservice_WAPP

## 1. Platform Generation and Classification

`issuing-classic-selfservice_WAPP` is a **Generation 2 (Gen-2) internal operations portal**, representing a modernisation step relative to the legacy Perl/PHP or Classic ASP era tooling it likely replaced. It is built on Django 2.1 (Python), uses relational SQL Server databases via ODBC, and features structured JSON logging. However, it relies heavily on **legacy Gen-1 data stores** (`ecountcore`, `cbaseapp`, `jobsvc` databases) whose schemas it cannot control (`managed = False` ORM models).

The Northlane branding in static assets (`portal/static/portal/images/Logos/Northlane_*.png`) confirms this was built during the Northlane era of Onbe's predecessor, likely 2018–2020 based on migration timestamps (earliest: `0001_initial.py` for block_global_deposit around 2019-01-07; latest: `0006_auto_20200728_1630.py` for generate_emboss_code).

## 2. Role in Enterprise Architecture

This portal sits at the **Tier 2 / Internal Operations** layer of the Issuing Classic platform:

```
Cardholders
    ↓
Classic Web Portal (cardholder-facing, separate repo)
    ↓ (reads same DBs)
issuing-classic-selfservice_WAPP  ← Internal operations portal (THIS REPO)
    ↓
ecountcore DB | cbaseapp DB | jobsvc DB
    ↓
Legacy eCount Core Platform (Gen-1)
```

It provides staff-initiated mutations that bypass the normal transactional service layer — writing directly to `fdr_dda_account_journal` and `core_device` tables. This **direct DB mutation pattern** creates a significant architectural coupling risk: changes to the DB schema in ecountcore can silently break the portal, and the portal bypasses any business logic or audit controls embedded in the eCount Core service tier.

## 3. Integration Touchpoints

| Integration | Direction | Protocol | Risk Level |
|---|---|---|---|
| ecountcore DB | Read/Write | SQL Server ODBC | HIGH — direct DB access bypasses service layer |
| cbaseapp DB | Read/Write | SQL Server ODBC | HIGH — touches authentication tables |
| jobsvc DB | Read/Write | SQL Server ODBC | MEDIUM — card inventory operations |
| ProdSupportPortal DB | Write | SQL Server ODBC | LOW — portal's own audit DB |

There are no REST or SOAP API integrations in this portal — all data access is direct database. This is architecturally problematic from a service-layer encapsulation standpoint.

## 4. Dependency on Legacy Infrastructure

The portal is tightly coupled to the "Classic" (Northlane Gen-1) platform:
- **`ecountcore` database** — the Gen-1 eCount Core ledger. Django models reflect Gen-1 table structures (`core_device`, `fdr_dda_account_balance`, etc.).
- **`cbaseapp` database** — the Gen-1 cardholder authentication database. The portal's `change_usernames` function updates cardholder credentials directly.
- **`jobsvc` database** — the Gen-1 job service database for instant-issue card orders.

When Onbe migrates the Classic program to a new platform (e.g., nexpay-based stack visible elsewhere in the repo inventory), this portal will require a full rewrite or significant adaptation, as its data model is entirely built around Gen-1 table structures.

## 5. Architectural Risks

### 5.1 Direct Database Mutation
The portal writes directly to `fdr_dda_account_journal` (ledger entries), `core_device` (device block codes), `user_validation_information` (usernames), and `instant_issue_card` (card status). These writes do not go through any service API, meaning:
- No service-layer validation is applied.
- No event sourcing / audit trail at the service layer.
- Schema changes in target DBs break the portal silently.

### 5.2 Shared Database Credentials
All four databases share the same `database_user` and `database_password` (`settings.py` lines 63–65). A credential compromise affects all four databases simultaneously.

### 5.3 No API Gateway / Service Mesh
The portal is entirely self-contained with no observable API calls outward. In a zero-trust / service-mesh architecture, this is an anti-pattern.

### 5.4 Single-Instance, Stateful Deployment
No load balancing configuration is visible. Session storage uses Django's default DB-backed sessions. The rotating file logger implies single-node deployment. This creates availability risk.

## 6. Migration Complexity Assessment

**Estimated migration complexity: HIGH**

To migrate this portal to a modern microservices/API-first architecture:
1. Each Django module (issue_checks, block_global_deposit, etc.) needs to be replaced by calls to a domain API rather than direct DB writes.
2. The ecountcore, cbaseapp, and jobsvc read models need to be backed by REST APIs from the respective microservices.
3. Django 2.1 → Django 4.2/5.x upgrade is required (breaking changes in auth, ORM, and URL routing).
4. Authentication needs to move from Django's local model to Onbe's identity provider (Azure AD or equivalent, consistent with the newer nexpay/oneplatform stack).

A phased approach is recommended: first upgrade Django while keeping DB-direct access, then introduce API abstraction layers module-by-module.

## 7. Compliance Architecture Observations

- The portal is a **PCI DSS in-scope system** due to its access to `dda_number` (cardholder data), `core_device_protected.verification_code`, and `fdr_dda_account_*` financial tables.
- As an internal admin tool that can block accounts, issue checks, and void cards, it must be subject to **privileged access management (PAM)** controls per PCI DSS Requirement 7 and 8.
- The `django-axes` lockout is a partial control, but MFA for privileged staff is likely required under current PCI DSS v4.0.1 Requirement 8.4.
