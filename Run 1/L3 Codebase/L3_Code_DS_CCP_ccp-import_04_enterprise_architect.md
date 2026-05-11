# Enterprise Architect View — DS_CCP_ccp-import

## Platform Generation
**Generation 2 (Gen-2) data platform.** SSIS-based ETL ingesting from three external financial network partners. Represents the inbound half of the CCP data pipeline architecture.

## Domain Placement
- **Domain:** Data Platform — CCP Inbound Data Ingestion
- **Subdomain:** Network Settlement and Fee Data Ingestion
- **Processors covered:** FIS (Fidelity Information Services), Mastercard, WDP (Wirecard Data Platform / wire transfer processor)

## Role in the Ecosystem
CCP-Import is the **source of truth population** step for the ODS. Without it, no downstream CCP processes have fresh data:

```
[FIS SFTP]         ──► ccp-import ──► ODS ──► ccp-export (to Sunrise)
[Mastercard SFTP]  ──►             ──►     ──► ccp-export-to-legacy (to Ecount)
[WDP SFTP]         ──►             ──►     ──► ccp-report-services (SSRS reports)
[DWH Oracle]       ──────────────────────────► ccp_import_aggnetworksettlement
```

**CCP-Import is the most upstream component of the entire CCP data pipeline. Any import failure cascades to all downstream consumers.**

## External Partner Interfaces
| Partner | Data Type | Frequency | Format | Encryption |
|---------|-----------|-----------|--------|-----------|
| FIS (Wirecard/FIS) | Daily fee, daily report, ISA fee | Daily | CSV with header | SFTP (SSH) |
| Mastercard | Daily settlement summary | Daily | Fixed-width (no header) | SFTP (SSH) |
| WDP | Unposted transactions | Daily | PGP-encrypted file via SFTP | SFTP + PGP |

## Aggregation Layer
`ccp_import_aggnetworksettlement.dtsx` is notable as the only package that reads from ODS/DWH after import to produce aggregated views. It is parameterised by:
- `p_financial_institution` — defaults to `SRB` (Sunrise Banks); can be run for other FIs
- `T_minus` — number of days offset (default 1 = yesterday)

This makes it the reconciliation anchor for the daily settlement cycle.

## Architectural Patterns
- **Staged ingest** — files land on SFTP server, are downloaded to local staging, then imported to ODS
- **Per-processor modular packages** — FIS, MC, WDP each have dedicated import packages
- **Post-ingest aggregation** — `ccp_import_aggnetworksettlement` runs after raw import to produce consolidated views
- **PGP at-rest protection** for WDP files (vendor requirement)

## Current Status
Active daily operational pipeline. Dependencies on `t-phl-db01.wirecard.lan` (Wirecard-era server) and `sftp-qa.nam.wirecard.com` suggest legacy infrastructure is still referenced in configuration.

## Migration Blockers
1. **FIS/MC/WDP SFTP partner contracts** — partner SFTP endpoints and credentials must be re-provisioned under Onbe naming after migration.
2. **WDP PGP key management** — PGP keys are file-system-resident on the SSIS host; must be migrated to a secrets manager.
3. **ODS dependency** — ODS SQL Server is the central destination; any ODS migration must be coordinated.
4. **Mastercard fixed-width format** — proprietary format with no schema documentation in the repository; format changes require code changes.
5. **No automated tests** — no validation that import record counts match expected values from source.
