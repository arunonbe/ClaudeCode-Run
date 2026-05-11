# Enterprise Architect View — DS_CCP_ccp-export

## Platform Generation
**Generation 2 (Gen-2) data platform.** SSIS-based ETL using SQL Server 2017 and Oracle DWH as sources. Represents the "CCP" (Card/Cardholder Program) data domain that was introduced as Wirecard/Ecount moved toward a more structured data platform. Predates any cloud-native or API-first architecture.

## Domain Placement
- **Domain:** Data Platform — CCP Outbound Data Delivery
- **Subdomain:** Cardholder Data Export / Bank Partner Integration
- **Product context:** CCP prepaid card program — Sunrise Banks as issuing bank partner

## Role in the Ecosystem
CCP-Export is the **outbound data delivery** component of the CCP pipeline:

```
[ccp-import] → [ODS SQL Server] → [ccp-export] → [Sunrise Banks SFTP]
                [DWH Oracle]   → [ccp-export] → [Finance Copy SFTP]
                                               → [OAS SFTP]
```

It feeds:
- **Sunrise Banks** — issuing bank partner receives account, transaction, balance, card status, interchange, and settlement data
- **Finance team** — receives billing audit and FVD data for revenue reconciliation (see also `ccp-export-to-legacy`)
- **OAS** — Oracle Application Server or similar intermediary for daily fees and settlement

## Key External Interfaces
| Partner | Data Type | Frequency | Format |
|---------|-----------|-----------|--------|
| Sunrise Banks (`ftp.sunrisebanks.com`) | Account, Transaction, Balance, Card Status, Interchange, Settlement, Recon | Daily | Pipe-delimited `.txt` |
| Finance (internal SFTP) | Billing audit, FVD, OAS fees/settlement | Daily | CSV / pipe-delimited |
| OAS | Daily fees, settlement | Daily | (format per package) |

## Architectural Patterns
- **Batch ETL** — scheduled daily extracts; no streaming or real-time capability
- **SSIS Project Deployment Model** — packages share project-level connection managers and parameters
- **Push delivery** — data is pushed to partners via SFTP; no pull/API model
- **Flat file interchange** — file-based integration with bank partners; no EDI or API

## Current Status
Active operational pipeline. Created 2019 by WIRECARD\adam.fortuno and WIRECARD\van.nguyen2. Last SSDT version `14.0.3002.113` (SQL Server 2017 era). No evidence of recent structural changes; the pipeline appears stable but ageing.

## Migration Blockers
1. **Oracle Client dependency** — Oracle Client 12 is required on the SSIS host; cloud-hosted SSIS (Azure-SSIS IR) can support this but adds complexity.
2. **Flat-file bank protocol** — Sunrise Banks receives data via SFTP/pipe-delimited files; any migration requires bank agreement to accept a new delivery method (API/SFTP retained).
3. **DPAPI secrets** — must be migrated to a proper secrets manager before any server migration.
4. **ODS/DWH dependency** — both source databases must remain accessible or be migrated concurrently.
5. **No unit tests for SSIS packages** — no automated validation of extract logic.
