# Enterprise Architect Report — DS_CCP_ods

## Platform Generation Classification

**Generation: Gen-2 (Wirecard/Northlane — transitional ODS layer)**

Evidence of generation:
- SSDT project creator context embedded in project file structure reflects Wirecard-era development
- The `FIS` prefix on all report tables reflects FIS (Fidelity National Information Services) as the card processor — a Gen-2 processing relationship
- Sunrise Banks as the issuing bank partner (`@BankName = 'Sunrise Banks'` hardcoded as default in `RptNetworkSettlementReport`) is a Gen-2 bank arrangement
- The CCP Oracle DWH connection (referenced by job orchestration in DS_CCP_db09) is a Gen-2 system
- The comment `-- 2020-07-31 Van Nguyen - Removed validation logic due to shutdown of CCP` in `spVerifyImport` marks the beginning of the Gen-2 to Gen-3 transition at Northlane

The ODS is a **transitional layer** — it was built to serve the WIRED reporting product during the Wirecard/Northlane era and is being superseded as Onbe builds Gen-3 cloud-native reporting. It has elements of both Gen-1 (FIS batch file processing patterns) and Gen-2 (SSDT project, some stored procedure organisation quality).

## Role in Overall Payments Architecture

The ODS plays the **analytical staging and reconciliation hub** role within the CCP data domain:

```
┌──────────────────────────────────────────────────────────────────────┐
│                    PAYMENTS DATA ARCHITECTURE                        │
│                                                                      │
│  CARD NETWORK LAYER                                                  │
│  Mastercard Settlement Files ──► ODS.RptNetworkImport               │
│  (NAM_*_TT140 format)            RptNetworkSettlementData            │
│                                                                      │
│  PROCESSOR LAYER                                                     │
│  FIS Daily Files (*.STL,         ODS.FISRptCardholderActivity        │
│  *.IXS.csv) ────────────────►   ODS.FISRptDailyFee                  │
│                                  ODS.FISRptProcessorSettlement        │
│                                                                      │
│  LEGACY ORACLE LAYER                                                 │
│  CCP Oracle DWH ────────────►   ODS.RptNetworkAgg                   │
│  (AWS SSH tunnel)                                                     │
│                                                                      │
│  DOWNSTREAM CONSUMERS                                                │
│  ODS ────────────────────────►  WIRED DB (report caching)           │
│  ODS ────────────────────────►  OAS exports via SFTP                │
│                                  (Sunrise Banks reconciliation)       │
└──────────────────────────────────────────────────────────────────────┘
```

The ODS has three distinct roles:
1. **Settlement reconciliation layer**: Reconciles Mastercard network settlement against internal records.
2. **Bank partner reporting layer**: Produces daily/weekly reports for Sunrise Banks (issuing bank).
3. **Processor reconciliation layer**: Reconciles FIS processor fees and settlement against programme expectations.

## Dependencies on Other Repos/Services

| Dependency | Type | Notes |
|---|---|---|
| DS_CCP_db09 | Operational | SQL Agent jobs that execute ODS procedures |
| DS_CCP_ccp-import | SSIS project | Populates `RptNetworkAgg` from Oracle CCP DWH |
| DS_CCP_ccp-export | SSIS project | Reads from ODS `FISRpt*` tables to produce OAS export files |
| DS_CCP_sftp | SSIS project | Generic SFTP component used in OAS exports |
| DS_CCP_wired | Database | WIRED DB reads from ODS via `RptNetworkSettlementReport` and related procs |
| DS_CCP_wired-caching | SSIS project | Reads ODS for certain cache refresh operations |
| FIS (external) | Data feed | Source of all `FISRpt*` data via flat files |
| Mastercard (external) | Data feed | Source of `RptNetworkImport` data |
| Oracle CCP DWH (external) | Database | Source of `RptNetworkAgg` data |
| Sunrise Banks (external) | Client/bank | Consumer of OAS reconciliation exports |

## Architectural Assessment

### Strengths
1. The staging/production/archive pattern for FIS tables is sound and provides a clear ETL lineage.
2. The `FileIOLog` audit mechanism is a well-designed operational control.
3. SSDT project management is more maintainable than raw ad-hoc SQL scripts.
4. Separation of ODS concerns (staging, production, archive, reference) is logical.

### Weaknesses
1. **Monolithic stored procedures**: `RptNetworkSettlementReport` is a 238-line multi-mode procedure with three different report outputs controlled by a `@report` parameter (`'n'`, `'1'`, `'y'`, `'p'`). This is difficult to test, maintain, and debug.
2. **Tightly coupled to FIS file format**: The staging tables mirror the raw FIS flat file layout. Any FIS format change requires schema changes.
3. **Single-bank assumption**: `RptNetworkSettlementReport` defaults to `@BankName = 'Sunrise Banks'` — the schema was designed for single-bank operation and would require refactoring for multi-bank scalability.
4. **No API layer**: The ODS is accessed directly by SSIS packages via SQL connections. There is no service API, making the schema a shared mutable dependency for all consumers.

## Migration Complexity and Blockers

### Complexity: HIGH

1. **PAN data migration**: Moving the ODS to a new platform (Azure SQL, Synapse) requires a careful data migration plan for PAN-bearing tables that complies with PCI DSS. Data in transit must be encrypted; destination must be CDE-scoped.

2. **FIS flat file dependency**: The ODS is built around FIS batch file processing. Migration to event-driven or API-based FIS data consumption requires a complete redesign of the `FISRpt*` table family.

3. **Sunrise Banks bank reporting dependency**: The `RptNetworkSettlementReport` procedure directly serves Sunrise Banks reconciliation. Any ODS migration must maintain service continuity for this bank partner reporting.

4. **Oracle DWH decommission prerequisite**: `RptNetworkAgg` depends on the Oracle CCP DWH being populated. Until an alternative source of network aggregation data is established, the ODS migration is blocked.

5. **DDM vs. true encryption migration**: Migrating PAN columns to column-level encryption (Always Encrypted or similar) will break all existing stored procedures that select PAN data, requiring a full procedure rewrite.

### Migration Blockers
- Active bank partner (Sunrise Banks) reporting dependency
- Oracle CCP DWH data feed still active (or needing formal EOL)
- PAN column encryption remediation (PCI DSS compliance requirement before any cloud migration)
- No API abstraction layer to decouple consumers from ODS schema changes
