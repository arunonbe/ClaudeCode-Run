# Enterprise Architect — INIT1400-GPScribe

## Platform Generation

`INIT1400-GPScribe` is a **Generation 1 / legacy integration** component. Evidence:

- The integration replaces **Scribe 1.2**, a third-party ETL product that was already a legacy tool (Scribe was discontinued in favor of Scribe Online/TIBCO). Initiative 1400 re-implemented Scribe's behavior in native T-SQL rather than migrating to a modern integration platform.
- Microsoft Dynamics GP (Great Plains) is itself a **legacy ERP platform**. Microsoft announced the end of mainstream support for Dynamics GP and encourages migration to Dynamics 365 Business Central. The eConnect API (`taSopLineIvcInsert`, `taSopHdrIvcInsert`) is the GP-era integration mechanism, predating modern GP extensions and D365 APIs.
- The linked server pattern (`OPENQUERY` to an IP address) is a 1990s-era SQL Server data integration technique. Modern integrations use REST APIs, message queues (Service Bus, Kafka), or data integration platforms (Azure Data Factory, Logic Apps).
- Database name `Dev_Swiftgift_CRM` and the "Swiftgift" brand suggest this is part of the **Swiftgift acquisition** or a legacy business unit predating Onbe's current brand identity.
- The GP `USER2ENT` field is set to `'ScribeWest'` — a reference to the Scribe integration it replaced, demonstrating that this component carries the operational identity of its predecessor.

## Position in Onbe Architecture

```
Swiftgift CRM                           GP Server
[Dev_Swiftgift_CRM DB]                  [P-AZ-GPSQL-VM01]
10.10.150.7                             SWIFT database
─────────────────────────────────────────────────────────
CRM_Invoice_Report               SQL Agent Job: INIT1400
  (daily sales invoices)         │
       │                         │  Step 1: DYNO_Scribe_West_DataImport
       │  OPENQUERY (Linked Svr) │  ─► Fetch unprocessed CRM records
       ├────────────────────────►│  ─► Populate CA_tblStg_ScribeInvoice
       │                         │  ─► Mark source as Processed via linked SP
       │                         │
       │                         │  Step 2: DYNO_Scribe_West_InvoiceImport
       │                         │  ─► eConnect: taSopLineIvcInsert (per line)
       │                         │  ─► eConnect: taSopHdrIvcInsert (per invoice)
       │                         │  ─► Log errors to CA_tblScribeInvoice_ErrorLog
       │                         │  ─► Delete partial GP records on failure
       │                         ▼
                         DYNAMICS GP ERP
                         ─────────────────
                         SOP10100/SOP10200  (Sales Orders/Invoices)
                         RM00101            (Customers)
                         IV00101            (Inventory Items)
                            │
                            ▼
                     Finance / AR team review
                     Revenue ledger posting
```

## Upstream Dependencies

| Dependency | Location | Risk |
|-----------|----------|------|
| `Dev_Swiftgift_CRM` database | 10.10.150.7 | IP-based linked server; IP change = silent breakage |
| SQL Server Linked Server credentials | GP server credential store | Credential not in Key Vault; manual rotation |
| `INTI1400_UpdateProcessedFlag` SP | 10.10.150.7 (CRM server) | Must be deployed to CRM server separately; out-of-sync risk |
| `seeStringToTable` function | SWIFT DB | Must be pre-deployed; InvoiceImport depends on it via DataImport |
| eConnect stored procedures (`taSopLineIvcInsert`, `taSopHdrIvcInsert`) | SWIFT DB | Installed by GP eConnect module; version-locked to GP installation |
| `OASIS_Exclusion` table | SWIFT DB | Managed externally; incorrect exclusions silently drop invoices |
| `IV00101`, `RM00101` | SWIFT DB | GP master data tables; `TOP 1000` / `TOP 10000` hard limits risk data truncation |

## Downstream Dependencies

| Consumer | Dependency |
|---------|-----------|
| Finance / Accounts Receivable | Daily GP invoices for revenue recognition; without import, GL is incomplete |
| Month-end close process | GP SOP data feeds into financial reporting; missing data causes close delays |
| GP reporting (Crystal Reports, SQL queries) | SOP10100/SOP10200 data feeds standard GP reports |

## Cross-cutting Concerns

### Business Entity Scope

The "West" designation in both stored procedure names (`DYNO_Scribe_West_*`) and the `'ScribeWest'` USER2ENT value suggests this is the **West region** or **West entity** integration. It is likely that a separate `DYNO_Scribe_East_*` or similar integration exists for other regional entities, though no such scripts are present in this repository. The complete revenue integration picture requires examining all regional variants.

### eConnect Coupling

The eConnect API is a stored-procedure-based integration layer installed on the GP SQL Server. It:
- Enforces GP business logic (currency validation, batch creation, customer validation).
- Returns integer error codes that must be cross-referenced against `DYNAMICS..taErrorCode`.
- Has no versioning semantics — a GP version upgrade may change eConnect SP signatures or behavior, silently breaking the import.

The tight coupling to eConnect means any migration away from Dynamics GP requires a complete rewrite of Step 2, not just a configuration change.

### Architectural Maturity Assessment

| Dimension | Score (1=poor, 5=excellent) | Notes |
|-----------|---------------------------|-------|
| Modularity | 2 | Two stored procedures; no abstraction layers |
| Testability | 1 | No test environment, no test data, no automated tests |
| Operability | 2 | Error log table only; no active monitoring or alerting |
| Security | 2 | Linked server to IP; bidirectional write access; no CMK encryption |
| Maintainability | 2 | Wide-char encoded file; hardcoded IPs; requires SP code modification for recovery |
| Compliance readiness | 3 | No cardholder data processed; financial data adequately isolated |

## Modernization Roadmap

### Short-term (0–3 months)
- Enable DB Mail alerting for import failures.
- Change job owner to a service account.
- Add parameterized re-run capability to `DYNO_Scribe_West_InvoiceImport`.
- Clarify and (if needed) rename `Dev_Swiftgift_CRM`.

### Medium-term (3–12 months)
- Migrate the linked server pattern to a REST API call (if the CRM system exposes an API) or Azure Data Factory pipeline.
- Replace the hardcoded IP linked server with a DNS-registered hostname and managed credentials.
- Implement Azure Monitor alerting on the SQL Agent job.
- Add environment separation (Dev/QA/Prod configuration profiles).

### Long-term (12–36 months)
- Evaluate migrating from Dynamics GP to Dynamics 365 Business Central, which provides a modern REST-based integration API (`taSopHdrIvcInsert` equivalent in D365 would be the Sales Invoice API or a Power Automate connector).
- Replace the batch daily job with an event-driven integration pattern: CRM emits an event on invoice creation; GP subscription processes in near-real-time using Azure Service Bus and Logic Apps.
- Evaluate whether the "West" and (presumed) other regional integrations can be consolidated into a single parameterized pipeline managed through Azure Data Factory.
