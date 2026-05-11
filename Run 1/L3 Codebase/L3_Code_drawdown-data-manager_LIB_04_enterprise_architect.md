# Enterprise Architect View — drawdown-data-manager_LIB

## Platform Generation
**Generation 1 (Gen-1) legacy.** Built on the original Citi/Ecount prepaid platform circa 2018–2019. Uses proprietary Citi/Ecount internal frameworks (`Core2`, `StrongBox`, `Director`). Spring 2.5.4 dates this artefact to pre-2010 framework vintage (though packaged later).

## Domain Placement
- **Domain:** Payments — ACH Drawdown / Linked Bank Account provisioning
- **Subdomain:** Cardholder Bank Account Reference Data Management
- **Consumer context:** Back-office operator or batch job that onboards bank accounts for drawdown-funded prepaid programs

## Role in the Ecosystem
This library sits between:
- **Upstream:** A CSV file produced by an operator or upstream system (identity of producer unknown from this repo)
- **StrongBox vault:** Encrypted storage of financial account data
- **GreatPlains (GP):** Onbe's finance/accounting system that references the vault-stored accounts for drawdown transactions

It is a **data provisioning utility**, not a real-time service. It does not expose an API.

## Key Dependencies
| Dependency | Version | Status |
|------------|---------|--------|
| Spring Framework | 2.5.4 | EOL — critical risk |
| Log4j | 1.2.15 | EOL — critical CVEs |
| Ecount Core2 (common, ecount-system) | 1.0.4 / 1.0.10 | Internal; unknown maintenance status |
| Ecount StrongBox client | 1.1.1-SNAPSHOT | Internal; SNAPSHOT = unstable |
| Ecount Director client | 1.0.11 | Internal |
| Ecount XMLRPC | 1.0.9 | Internal |
| commons-collections | 3.2.1 | EOL; Apache Security Advisory |

## Architectural Patterns
- **Command-line batch utility** (no HTTP server, no message queue)
- **CSV-to-vault ETL** micro-pattern
- **Stored-procedure integration** for downstream DB writes

## Current Status
Active but aging. The presence of Dependabot and CodeQL suggests it is still maintained at a security baseline level. No evidence of recent functional changes.

## Migration Blockers
1. Dependency on proprietary `Core2`/`StrongBox`/`Director` Citi/Ecount APIs — these must be replaced or wrapped before any Gen-3 migration.
2. Hardcoded configuration paths prevent containerisation without refactoring.
3. SNAPSHOT dependency on StrongBox client (`1.1.1-SNAPSHOT`) is unstable for production.
4. No unit or integration tests make safe refactoring difficult.
