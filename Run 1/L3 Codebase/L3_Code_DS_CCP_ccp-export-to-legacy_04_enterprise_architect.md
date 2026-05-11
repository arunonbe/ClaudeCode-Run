# Enterprise Architect View — DS_CCP_ccp-export-to-legacy

## Platform Generation
**Gen-2 transitional bridge.** This project is explicitly a migration bridge — it exists to feed the Gen-1 legacy Ecount platform with data produced by the Gen-2 CCP system. It will become obsolete when the legacy Ecount platform is fully decommissioned. It is the most obviously temporary artefact in the CCP suite.

## Domain Placement
- **Domain:** Data Platform — CCP Legacy Integration / Migration Bridge
- **Subdomain:** Financial Reconciliation Data Feed (legacy)
- **Lifecycle stage:** Transitional — scheduled for decommission when Ecount legacy is retired

## Role in the Ecosystem
```
[ccp-import] → [ODS] ──► [ccp-export-to-legacy] ──► [Legacy Ecount SFTP]
[DWH Oracle] ──────────►                                    │
                                                             ▼
                                              Legacy Ecount (billing, FVD, reconciliation)
```

This project is the only component in the CCP suite that writes **back** to the legacy platform. All other CCP components read from legacy or deliver to external partners.

## Dependency Chain
| Upstream | This project | Downstream |
|----------|-------------|------------|
| ccp-import (populates ODS) | ccp-export-to-legacy (reads ODS, writes to legacy SFTP) | Legacy Ecount billing/recon processes |

## Key Risk: Decommission Timing
If this project is decommissioned before legacy Ecount processes are migrated, the following legacy functions will break:
- Billing audit reporting
- FVD revenue recognition in legacy systems
- Billing detail reconciliation
- Single-load FVD accounting

Recommended: maintain this project in a monitored but frozen state until legacy Ecount retirement is confirmed.

## Architectural Patterns
- **Anti-corruption layer** — translates CCP data model to legacy Ecount file format
- **Batch SFTP push** — scheduled daily flat-file delivery
- **Archive-after-delivery** — file lifecycle management via `Archive_Processed_Files.dtsx`

## Current Status
Active but transitional. Mixed SSDT versions (14 and 15) suggest it has been maintained through at least two SQL Server upgrade cycles. No evidence of recent data-model changes.

## Migration / Decommission Blockers
1. Legacy Ecount must be fully decommissioned or re-platformed before this project can be retired.
2. Finance and operations teams dependent on billing audit and FVD data must be onboarded to a Gen-3 reporting solution.
3. No documentation of which legacy Ecount processes consume these files — a full consumer inventory is needed before decommission.
