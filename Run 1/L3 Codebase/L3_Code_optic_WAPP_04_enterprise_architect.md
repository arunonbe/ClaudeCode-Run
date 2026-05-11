# Enterprise Architect Report — optic_WAPP

## Platform Generation

**Gen-2 (Wirecard/Northlane) — operational legacy tool.** The Confluence documentation is hosted at `northlane.atlassian.net`, confirming this is a Northlane-era tool that has persisted into the Onbe organization post-acquisition. The application is an Excel VBA macro workbook connected to a SQL backend called "RiskDB," with no relationship to the Gen-3 Spring Boot / Azure / Dapr / Kotlin technology stack.

This is not a microservice, not a containerized workload, and not a Spring Boot application. It is a desktop business intelligence / data management application built on Microsoft Excel VBA — a pattern common in financial operations teams from the Gen-1/Gen-2 era.

## Integration Patterns

- **Direct SQL (ADO/ODBC):** OPTIC connects directly to the RiskDB SQL Server database using ADO/ODBC from VBA. There is no API layer, no service mesh, no Dapr, and no event-driven integration. Data access is via raw SQL queries embedded in VBA code.
- **File-based distribution:** The link file mechanism is a proprietary file-distribution pattern — not a standard deployment pattern from any generation of the Onbe platform.
- **No API surface:** OPTIC exposes no HTTP endpoints, no message queues, and no integration points consumable by other systems. It is a terminal node in the data flow — data goes in (SQL queries to RiskDB), visualization goes out (Excel cells on screen).

## External Dependencies

| Dependency | Purpose |
|---|---|
| Microsoft Excel | Runtime host for VBA and UI |
| RiskDB SQL Server | Data source for all OPTIC data |
| Corporate network / VPN | Required for RiskDB connectivity |
| Corporate workstation | Execution environment |

No cloud dependencies, no Azure services, no modern API dependencies.

## Position in Broader Platform

OPTIC sits entirely outside the Gen-3 platform stack. It is an isolated operational tool used by internal Onbe business users (operations, risk management teams) to query and view data from RiskDB. Its position in the platform:

```
[RiskDB (SQL Server — Gen-2 era)]
    --> [OPTIC Excel VBA Application (user workstation)]
        --> [Internal business users]

(No connection to Gen-3 platform, Azure, Dapr, or API Management)
```

## Migration Blockers

For migrating OPTIC to a modern platform (Power Apps, internal web application, or a Gen-3 React/Spring Boot BI tool):
1. **Unknown business requirements:** VBA business logic is embedded in binary `.xlsm` files and must be extracted and documented before migration can be planned.
2. **RiskDB schema unknown:** The target data model for a migration cannot be designed without knowledge of the RiskDB schema, stored procedures, and permissions model.
3. **User access control model:** SQL firewall-based data partitioning is sophisticated and must be replicated in any replacement system.
4. **User adoption:** Business users familiar with the Excel interface may resist migration to a web or Power Apps interface.
5. **Ownership and resourcing:** The development contacts (`Pat.Brown@onbe.com`, `Micheal.Gevaryahu@onbe.com`) are the only known subject matter experts. Bus factor of 2.

## Strategic Status

**Legacy operational tool — migration candidate.** OPTIC is not strategically aligned with Onbe's Gen-3 platform. It carries significant technical and security risks (see 05_solution_architect.md for details). The recommended strategic path is:

1. **Short-term:** Conduct a VBA code audit to identify and remediate credential and data exposure risks.
2. **Medium-term:** Define a migration roadmap to replace OPTIC with a modern internal tool (Power BI for reporting, Power Apps for data entry, or a Gen-3 internal API + React frontend for custom use cases).
3. **Long-term:** Decommission OPTIC and RiskDB once replacement capabilities are operational and user adoption is confirmed.

The risk of leaving OPTIC in its current state (no SDLC controls, potential credential embedding, binary VBA code, no security scanning) is high for a PCI DSS Level 1 payments company. A single compromised `.xlsm` file distributed via the server share would execute arbitrary VBA code on every OPTIC user's workstation.
