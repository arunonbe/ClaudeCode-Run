# DS_DB_acctgwf — Enterprise Architect Report

## 1. Platform Generation Classification

**Generation: Gen-2 (Wirecard/Northlane era, transitioning to Gen-3)**

Evidence:
- The database project targets `Sql100DatabaseSchemaProvider` (SQL Server 2008 schema model), which places it in the Gen-2 era infrastructure timeline.
- Cross-database references to `ATLYS_E` and `eCountBankTransactions` (an eCount/Citi legacy view name) indicate this database bridges Gen-1 GL system data (Microsoft Dynamics GP + eCount) with the Gen-2 Atlys workflow platform.
- The `NAM\` Active Directory login convention and the Northlane/Wirecard-era team login patterns (`NAM_GTS_gpatmon`, `NAM_ICG_DBA_Default`, `NAM_ISA_SQL_SECADMIN`) are consistent with the pre-Onbe organisational structure.
- The `ACCTGWF_APP_GRP` application group and the presence of `FortiDBRptRole` suggest this is operational in a regulated production environment.

## 2. Role in the Payments Architecture

`acctgwf` is a **Finance Operations Support** database, not a transaction processing or cardholder data system. It sits in the **management plane** of the Atlys platform, providing:

1. **Control evidence layer** for SOC 1/SOC 2 audits (workpapers with 4-signature workflow)
2. **Operational task orchestration** for Finance team recurring processes
3. **GL reconciliation bridge** between the Atlys reporting databases and Microsoft Dynamics GP (the ERP)
4. **User lifecycle management** integration (password management delegated to `ATLYS_E`)

In the Atlys stack, this database is positioned as:

```
[ATLYS_E (entity/core)] ← identity/auth
        |
[acctgwf] ← workflow/finance ops         [atlys_rv_nca / fc_nca / fc_nus] ← revenue/fee calculation
        |
[Microsoft Dynamics GP] ← ERP/GL (external)
```

## 3. Dependencies

### Upstream (acctgwf reads from)
| System | Type | Purpose |
|---|---|---|
| `ATLYS_E` | Cross-database SQL | User authentication and session validation |
| `[GlDbName]` (e.g., company GP database) | Cross-database dynamic SQL | GL account lists, unposted entries, bank transactions |
| `ATLYS_RvCR` (implied by prefix range function cross-reference) | Cross-database | Program prefix validation |

### Downstream (systems reading from acctgwf)
| System | Type | Purpose |
|---|---|---|
| Atlys web application | Application layer | Workflow UI (task completion, workpaper management) |
| EMEA_ATLYS login | SQL login | Automated task completion from EMEA processing system |

## 4. Architectural Patterns

- **State-based schema**: SSDT declarative model. No migration scripts — deployment drift between environments is a risk.
- **Multi-company tenancy**: All major tables include `CompanyId` as a discriminator, enabling multiple client entities within a single database instance.
- **Delegation pattern**: Authentication and user management are delegated upstream to `ATLYS_E` (`sys_user` cross-database call in `acctgwf.sys_user` line 66), reducing duplication but creating a hard runtime dependency.
- **Dynamic SQL abstraction**: GL queries are encapsulated in scalar functions (`sys_strGLAccts`, `sys_strGLAcctActive`, etc.) that return SQL string fragments. This is an older architectural pattern predating ORM layers — maintainable but opaque to static analysis tools.

## 5. Migration Complexity Assessment

**Migration Complexity: MEDIUM**

Factors increasing complexity:
- **Cross-database dependencies**: Cannot be migrated in isolation. `ATLYS_E` must be co-migrated or a compatibility API layer provided.
- **GP linked server dependency**: The GL account bridge relies on dynamic SQL targeting company-specific database names. Migrating to Azure SQL (which does not support cross-database queries the same way) requires refactoring.
- **SHA-1 password hashing**: Must be re-hashed with a modern algorithm (bcrypt/Argon2) before migration, requiring a coordinated password reset campaign.
- **`tblAW_WPs` compound PK + separate clustered index pattern**: Non-standard and may require schema adjustment for cloud-native databases.

Factors reducing complexity:
- **No PAN/CVV data**: No CDE migration concerns.
- **Relatively small object count**: 33 tables, 26 views, 14 SPs, 12 functions.
- **Self-contained workflow logic**: Most business logic is in stored procedures within this database.

## 6. Strategic Observations

- The **workpaper workflow** is a genuine compliance asset. Before any migration or re-platforming, the WP workflow's current state should be assessed against what Gen-3 tooling (e.g., ServiceNow GRC, Workiva, or AuditBoard) provides natively.
- The **EMEA_ATLYS special login** (hardcoded bypass for task completion in `sys_tasks.sql` lines 19 and 393) is an architectural smell. This system account has elevated trust that bypasses the normal RBAC check — this should be converted to a proper service account with limited, explicitly-granted permissions.
- The `GlDbName` field in `tblAWCompanies` (stores database name as a string) is a **configuration-as-data anti-pattern**. In a cloud-native architecture, this should be externalised to a configuration service.
- **No environment separation in schema**: The same database structure is deployed to PROD and UAT. There is no schema-level differentiation. This is standard for state-based SSDT projects but should be paired with environment-specific publish profiles (which are not present in this repo).

## 7. Regulatory Architecture Alignment

| Framework | Current State | Gap |
|---|---|---|
| PCI DSS v4.0.1 | Out of CDE scope. No cardholder data. | FortiDB present for DAM. TDE not enabled. |
| SOC 1 / SOC 2 | Workpaper workflow directly supports control evidence. | Password hashing (SHA-1) is a control weakness. |
| GLBA | GL reconciliation workflow supports financial data integrity. | No encryption at rest. |
| GDPR / CCPA | Employee PII (email, name) in `tblAWUsers`. | No data retention/purge mechanism. No column-level encryption on email. |
