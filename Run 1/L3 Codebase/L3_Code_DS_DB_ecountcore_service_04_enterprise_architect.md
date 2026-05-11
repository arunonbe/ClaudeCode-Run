# DS_DB_ecountcore_service — Enterprise Architect View

## 1. Platform Generation

This database was first authored circa **2007–2009** based on author dates in procedure headers (JWu 2007-03-21, Rem 2009-02-18). It has been maintained incrementally through 2020. The technology stack is:
- **SQL Server 2012+** (DSP `Sql110` schema provider target)
- **SQL Server Service Broker** — a messaging feature introduced in SQL Server 2005
- **SQL-CLR** (EcountUtility.dll) — introduced in SQL Server 2005
- **SSDT project format** — current (Visual Studio database project tooling)

This is a **second-generation prepaid platform component**, consistent with the broader EcountCore architecture which dates from the mid-2000s Euronet/eCount era before Onbe's formation.

---

## 2. Architectural Role

`ecountcore_service` occupies the **batch-orchestration / async dispatch tier** in the EcountCore stack:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Onbe Prepaid Platform                        │
│                                                                 │
│  ┌─────────────────┐     ┌──────────────────────────────────┐   │
│  │  Application    │     │         SQL Server               │   │
│  │  Services       │     │                                  │   │
│  │  (NAM_PPA_PRD_*)│────►│  ecountcore_service              │   │
│  │                 │     │  (Service Broker dispatch bus)   │   │
│  └─────────────────┘     │         │                        │   │
│                          │         ▼                        │   │
│                          │  ecountcore (CDE)               │   │
│                          │  (accounts, fee processing,     │   │
│                          │   escheatment)                  │   │
│                          │         │                        │   │
│                          │         ▼                        │   │
│                          │  ecountcore_process              │   │
│                          │  (DCAF staging, open-auth data) │   │
│                          └──────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

The database is **not a microservice** — it is tightly coupled to `ecountcore` and `ecountcore_process` via hard-coded three-part names. It cannot operate independently. It is better characterised as a **sub-schema** of the EcountCore database cluster that was split out to provide a clean messaging boundary for long-running batch jobs.

---

## 3. Dependencies

### 3.1 Upstream Callers
- **SQL Agent Jobs** — invoke the `app_task_manager_*` procedures on schedule.
- **Application services** (`NAM_PPA_PRD_ECORESVC`, `NAM_PPA_PRD_SCHSVC`, etc.) — may call manager procedures directly for on-demand batch triggers.
- **Operations team** (`emer_*` logins) — emergency manual execution.

### 3.2 Downstream Dependencies
| Dependency | Type | Coupling |
|------------|------|---------|
| `ecountcore` | SQL database (same instance) | Hard — three-part name references throughout all SPs |
| `ecountcore_process` | SQL database (same instance) | Hard — three-part name TRUNCATE/INSERT in maintenance fee SP |
| `EcountUtility.dll` | CLR assembly | Binary deployed alongside DACPAC |

### 3.3 GP Repos / Banker SVC
No direct dependency exists between `ecountcore_service` and the GP databases (DS_DB_GP_*) or the Banker API. The GP databases are consumed by the Finance service layer; this database serves the card operations layer.

---

## 4. Migration Complexity Assessment

| Factor | Assessment |
|--------|-----------|
| Schema complexity | Low — 1 table, 10 SPs, 3 functions, 6 Service Broker objects |
| Business logic complexity | High — Service Broker activation pattern with dynamic SQL execution, CLR assembly, complex cross-database joins |
| Dependency coupling | High — hard-coded three-part references to two other databases on the same instance |
| Data volume | Low — TaskLog is an operational log, not a transactional ledger |
| Technology currency | Medium — SQL Server Service Broker is stable but not cloud-native; would require re-architecture for migration to Azure SQL / PaaS |

**Migration path to Azure SQL Managed Instance**: Feasible with moderate effort. Service Broker is supported on Azure SQL MI. CLR assemblies require re-validation. Cross-database references require all three databases to be on the same MI or refactored to linked servers / elastic queries.

**Migration path to Azure SQL Database (single)**: Complex. Service Broker is not supported on single Azure SQL Database. The activation pattern would need to be replaced with an Azure Service Bus / Azure Functions pattern.

---

## 5. Governance and Ownership

- No `CODEOWNERS` file or team assignment in the repository.
- The `development` branch is the only observed branch; no feature branching, pull-request, or merge policy is visible.
- Author references in SP comments name individuals (JWu, Rem/RZG, BillT, Colint, Somesh/Monali, MichaelG) but no current team ownership is documented.

---

## 6. Modernisation Recommendations

1. **Replace Service Broker activation with Azure Service Bus + Azure Functions** if migrating to PaaS — this eliminates the `sp_executesql` code-injection risk and provides better observability.
2. **Refactor cross-database dependencies** to stored procedure interfaces or microservice APIs to enable independent deployment.
3. **Externalise CLR assembly** — the `programCount` function should either be replaced with pure T-SQL or maintained as a versioned NuGet package with source code in the repository.
4. **Introduce pipeline definition** and automated DACPAC deployment to eliminate manual change management.
5. **Consolidate emergency access logins** into time-boxed, AD-managed groups with MFA.
