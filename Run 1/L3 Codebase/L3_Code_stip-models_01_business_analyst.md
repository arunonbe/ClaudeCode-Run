# stip-models — Business Analyst View

## Business Purpose
`stip-models` is the Stand-In Processing (STIP) domain model definitions repository. It is intended to house the canonical model/schema definitions that describe the data structures, contracts, and entities for the STIP capability. In the pattern typical for Onbe's generated-code architecture, `stip-models` is the upstream source from which `stip-generated` is produced.

STIP (Stand-In Processing) allows prepaid card transactions to be authorised using pre-loaded rules when the primary authorisation system is unavailable — a tier-1 resilience mechanism for the payments platform.

## Observed State
**The repository contains only a `.git/` directory with standard git hook sample files. No source files, model definitions, schema files, documentation, or build configuration are present.** The working tree is entirely empty of content.

## Capabilities (Intended vs. Observed)
| Intended Capability | Observed Evidence |
|---|---|
| STIP domain model/schema definitions | None — repository is empty |
| Source for code generation to stip-generated | No schema files (OpenAPI, XSD, Protobuf, JAXB, JSON Schema) present |
| Canonical STIP entity definitions | None |

## Business Entities (Intended)
Based on the STIP domain context, expected model definitions would describe:
- Transaction Authorization Request (card identifier, amount, merchant, MCC)
- Transaction Authorization Response (approve/decline, response code, reason)
- Stand-In Rule Set (velocity limits, BIN-level controls, merchant restrictions)
- Card Profile Snapshot (account status, available balance/credit, flags)
- Stand-In Decision Record (for reconciliation audit)
- Fallback Criteria Parameters

## Business Rules
None codified. No model definitions from which rules could be derived.

## Business Flows
None implemented.

## Compliance Relevance
Same as `stip-generated`:
- PCI DSS Requirements 3, 4, 10 — cardholder data handling, transmission security, audit logging
- Visa/Mastercard network stand-in processing rules
- Reg E — consumer protection for stand-in-processed transactions
- FFIEC business continuity — STIP is a resilience control

## Risks
| Risk | Severity | Notes |
|---|---|---|
| Repository is empty | Critical | STIP model definitions do not exist — upstream of generated code is absent |
| No canonical STIP domain model | Critical | Services implementing STIP have no authoritative contract to build against |
| Business continuity gap | Critical | Without models → no generated code → no STIP capability |
| No ownership / maintainer visible | High | Empty repository with no README, no contributors identified |
