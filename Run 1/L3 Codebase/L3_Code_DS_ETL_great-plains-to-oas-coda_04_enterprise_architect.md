# DS_ETL_great-plains-to-oas-coda — Enterprise Architect View

## Platform Generation
**Gen-1** — Visual Studio 2010 SSIS solution, SQL Server 2012 package format, legacy SQLNCLI11.1 driver, Citigroup-era VB.NET script component (copyright 2012). No cloud-native, containerized, or API-based components.

## Business Domain
**Finance — General Ledger Integration / Financial Reconciliation**
- Extracts Great Plains (Dynamics GP) financial data for posting to CODA accounting system.
- Processes refund check records into the OAS/CODA pipeline.
- Serves: Finance / Accounting teams.

## Architectural Role
A **point-to-point ETL bridge** between the Great Plains ERP (source) and the CODA financial ledger (target). It occupies the Finance data integration layer and was explicitly designed as a temporary solution.

```
[Microsoft Great Plains / Dynamics GP]
     (ATLYS_RvCR database — q-db04)
           |
    [SSIS_CODA_GPFeed.dtsx]
           |
    [Date-stamped flat files on UNC share]
           |
    [CODA / OAS Finance System]

[C:\GIT\rfcks.csv — Refund Check CSV]
           |
    [SSIS_RfCks.dtsx]
           |
    [ODS (q-db03) or downstream system]
```

## Integration Patterns
- **Batch file extract** (stored proc → SSIS → flat file) — classic Gen-1 ERP integration pattern
- **Scheduled date-loop iteration** — sequential daily processing via SSIS For Loop container
- **Flat file intermediary** — CSV/text files as the handoff mechanism between Finance systems (no API, no message bus)
- **ADO.NET + OLEDB dual connection** to same database (both ATLYS_RvCR connectors point to same server/DB) — unusual; likely developer testing artifact

## External System Dependencies
| System | Role | Connection |
|---|---|---|
| Microsoft Great Plains (Dynamics GP) | ERP source | ATLYS_RvCR database on q-db04 |
| CODA (Accounting/Ledger) | Financial posting target | Flat file delivery |
| OAS (Order Accounting System) | Secondary target | Not directly connected in SSIS; downstream of flat files |
| ODS | Operational Data Store | q-db03; used by RfCks package |

## Strategic Status
- **Decommission candidate** — explicitly labelled "temporary" in README. Created January 2019 by a Wirecard employee; no evidence of current ownership or active maintenance.
- Great Plains is a legacy ERP. Onbe's Gen-3 strategy likely uses a modern financial integration (API-based or Kafka/event-driven) rather than scheduled file extract.
- No successor system or migration plan is documented in this repo.
- CODA is also a legacy financial system; if Onbe has migrated to a modern ERP, this pipeline may already be dead.

## Migration Blockers
1. **Unknown operational status** — unclear if this package runs in production or has been superseded. Must be confirmed before decommission.
2. **Dependency on ATLYS_RvCR** — if Great Plains data is still needed by CODA, a replacement integration must be built before decommission.
3. **Undocumented `sys_interface` stored procedure** — the SP in ATLYS_RvCR is not in this repo; its schema and logic are unknown.
4. **`C:\GIT\rfcks.csv` dependency** — refund check processing has no automated data source; operationally broken unless someone manually places this file.
5. **No formal ownership** — no current Onbe team member identified as accountable; discovery needed before any migration or decommission action.
