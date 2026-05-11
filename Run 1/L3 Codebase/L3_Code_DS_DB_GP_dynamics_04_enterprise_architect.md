# DS_DB_GP_dynamics — Enterprise Architect View

## 1. Platform Generation

Microsoft Dynamics GP (Great Plains) is a **legacy ERP platform** — GP 18.x is the current version as of 2024, but the codebase and database architecture date from the 1990s (Great Plains Software) and early 2000s (Microsoft acquisition). The `Sql100` DSP target suggests the schema was last baseline-captured against SQL Server 2008 R2, likely GP version 10.x or later.

At Onbe, GP serves as the **financial ERP backbone** for operational finance — accounts payable, accounts receivable, GL, payroll, and budget management. It is deployed in a **multi-company** configuration (DYNAMICS system database + ECAN, ECNT, EMEAM, EAST company databases).

**Microsoft has announced GP will reach end of mainstream support in 2025 and extended support in 2029**, making migration planning a near-term enterprise architecture priority.

---

## 2. Architectural Role

```
┌──────────────────────────────────────────────────────────────────┐
│                  Onbe Finance Architecture                       │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │           Microsoft Dynamics GP Cluster                     │ │
│  │                                                             │ │
│  │  ┌──────────────┐   Authentication   ┌──────────────────┐  │ │
│  │  │   DYNAMICS   │◄──────────────────►│  ECAN / ECNT /   │  │ │
│  │  │  (this repo) │   Company lookup   │  EMEAM / EAST    │  │ │
│  │  └──────────────┘                   └──────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────┘ │
│         │                          │                             │
│         ▼                          ▼                             │
│  Finance WebService API      Banker API                          │
│  (finance-webservice_API)    (banker_API)                        │
│         │                          │                             │
│         ▼                          ▼                             │
│  DS_ETL_finance-gp           EcountCore (prepaid platform)      │
│  DS_ETL_great-plains                                             │
│  DS_WH_ecount-warehouse                                          │
└──────────────────────────────────────────────────────────────────┘
```

The DYNAMICS database is the **security and configuration hub** of the GP cluster. It has no direct financial transaction data but controls who can access what in every regional company database.

---

## 3. Dependencies

### 3.1 Upstream Systems
- **GP Client Application (desktop)** — connects to DYNAMICS for user authentication, then opens company databases.
- **RSM Customizations** (`GP-RSM-Customization` repo) — ISV add-on that extends GP with custom forms and reports; creates dependencies on custom tables in the company databases.
- **eConnect** (`eConnectOut` procedures) — middleware for integrating GP with external systems (order management, Banker).

### 3.2 Downstream Consumers
| Consumer | Access Pattern |
|----------|---------------|
| `banker_API` | Reads ECAN/ECNT/EMEAM via `BankerProgram`, `BankerAllSOView` views; authenticated via DYNGRP role; DYNAMICS provides user session validation |
| `finance-webservice_API` | Financial reporting queries against GP company databases |
| `DS_ETL_finance-gp` / `DS_ETL_great-plains` | ETL extraction of GL, AP, AR, payroll data for data warehouse |
| `DS_ETL_great-plains-to-oas-coda` | GP to OAS/Coda financial system ETL |
| `accounting-workflow_WAPP` | Finance workflow application consuming GP data |
| `Atlys` (`DS_DB_ATL_*`) | Atlys integration via `ATLYS_APP_GRP` role |

---

## 4. GP Multi-Company Architecture

The DYNAMICS database hosts a shared security and system layer used by all GP company databases. The `SY01500` company master table defines each registered company (ECAN, ECNT, EMEAM, EAST, etc.) with a numeric `CMPANYID`. GP client applications authenticate against DYNAMICS and then connect to the specific company database identified by `INTERID` (5-character company code).

This shared architecture means:
- A security breach of the DYNAMICS database grants access to **all regional GP companies**.
- Schema changes to DYNAMICS must be tested against all regional company databases.
- The `amAutoGrant` procedure in DYNAMICS is called during GP table deployment to grant access across all configured companies.

---

## 5. Migration Complexity Assessment

| Factor | Assessment |
|--------|-----------|
| Schema complexity | Very high — 300+ tables, full GP standard schema plus customisations |
| Business logic complexity | High — GP application layer handles most logic; database layer has targeted custom SPs |
| Vendor dependency | Very high — GP schema is proprietary; most tables cannot be renamed or restructured without breaking the GP application |
| Multi-company coupling | High — DYNAMICS security model is shared by ECAN, ECNT, EMEAM, EAST |
| End-of-life risk | High — GP mainstream support ends 2025 |
| Cloud migration path | Moderate — Azure SQL MI supports GP on SQL Server; full cloud-native ERP migration would require replacement (D365 Business Central or similar) |

**Recommended migration path**: Evaluate Microsoft Dynamics 365 Business Central as the GP successor (Microsoft's own recommended migration target). This is a multi-year programme requiring parallel operation, data migration, and process re-engineering. The ETL repos (`DS_ETL_finance-gp`, `DS_ETL_great-plains-to-oas-coda`) indicate some migration groundwork may already be in progress.

---

## 6. SOX Control Implications

The DYNAMICS database directly supports the following SOX IT General Controls (ITGCs):
- **User Access Management** — `SY01400` (users), `SY10500` (role assignments), `zAuditGPUserSec` audit trail.
- **Change Management** — DACPAC-based deployment; manual process creates SOX change-management risk without automated audit trail.
- **Logical Access Controls** — `DYNGRP`, `RAPIDGRP`, `DYNWORKFLOWGRP` roles define access boundaries; GP security tasks/roles in SY07xxx tables enforce least privilege within GP.

The audit triggers (`AuditGPUserCreateUpdateDelete` etc.) are essential SOX controls and must be maintained as non-bypassable. Any DACPAC deployment that drops or disables these triggers would constitute a SOX control failure.
