# DS_RPT_ecount-report-services — Enterprise Architect View

## Platform Generation
**Gen-1 / Gen-2** — SQL Server Reporting Services (SSRS 2008/2010 schema), Visual Studio 2010 solution, SQL Server 2012-era infrastructure. The platform is eCount's legacy reporting layer. Reports are XML-based RDL (text-readable, diffable), making this more maintainable than the Crystal Reports repos, but the underlying infrastructure is still Gen-1.

## Business Domain
**Operations Analytics & Client Reporting — eCount Prepaid Platform**
- Transactional reporting for all prepaid card operations (US and Canada)
- Sub-domains: Compliance, Risk/AML, Finance, Customer Service, IT Operations, Client Deliverables
- Serves: Internal Operations, Finance, Risk, Compliance, IT, and external clients (program sponsors)

## Architectural Role
The **reporting layer** of the eCount prepaid platform. This is the primary reporting surface for operational data stored in `cf_report`, `EcountCore`, `Prepaid_Warehouse`, `RiskDB`, and related databases. Reports are the primary mechanism for:
- Client-facing program performance visibility
- Internal operational monitoring
- Compliance evidence (UDAAP fee monitoring, AML)
- Reg E dispute support (transaction history)

```
[EcountCore DB] [cf_report DB] [Prepaid_Warehouse] [RiskDB] [ECNT/ECAN]
         |              |                |               |        |
    [SSRS Report Server — eCount Reports]
         |
    [Internal users: Finance, Risk, CS, IT, Compliance]
    [External users: Program clients (sponsor portals)]
```

## Integration Patterns
- **Pull-based reporting** (SSRS executes T-SQL / stored procs against source DBs on demand)
- **Shared data sources** (`.rds` files define named connections; multiple reports reuse same connection)
- **Stored procedure encapsulation** — reports call named SPs in `cf_report` rather than inline SQL (e.g., `rpt_Repetitive_Fees`)
- **SSRS folder-based access control** — Secured Reports folder implies role-based row-level security at the SSRS layer
- **Client-external reports** — External Report hierarchy suggests a portal or scheduled delivery to program sponsors

## External System Dependencies
| System | Role |
|---|---|
| cf_report DB (p-db06) | Primary report data store |
| EcountCore (db02) | Core transaction engine |
| Prepaid_Warehouse (db03) | Analytical warehouse |
| RiskDB | AML/fraud risk data |
| Cbaseapp | CBase application data |
| ecountcore_rollback | Rollback state data |
| ECAN | Canadian eCount data |
| ECNT | Finance eCount data |
| RS2008 | SSRS server monitoring |

## Strategic Status
- **Active legacy** — this is a living repo with active report development (50+ projects, hundreds of reports). It cannot be decommissioned until eCount platform is replaced.
- eCount is the legacy prepaid issuing platform; migration to Gen-3 (Onbe's modern platform) will obsolete this entire reporting layer.
- Some reports are already in `Retired Reports` — indicating ongoing rationalization.
- Client-specific reports (Grifols, Maritz, Subaru, TXU, Enservio, Electrolux, T-Mobile, AT&T, RealPage, etc.) represent contractual obligations that must be replicated in any successor platform.

## Migration Blockers
1. **cf_report stored procedures not in this repo** — the DB objects powering reports are a separate artefact; migration requires capturing that DDL separately.
2. **Client-specific reports with contractual obligations** — migration timeline must align with client contract renewals or require contractual amendments.
3. **Reg E compliance reports** — transaction history reports are regulatory obligations; gap in availability is not acceptable.
4. **SSRS folder security** — Secured Reports access control must be replicated in any replacement platform.
5. **SSRS schema versions (2008/2010)** — reports would need to be reauthored or converted for modern reporting tools (Power BI Paginated Reports, SSRS 2019).
6. **Volume** — hundreds of `.rdl` files across 50+ projects; migration is a significant effort.
7. **No automated test suite** — no regression tests for report output; migration validation requires manual QA.
