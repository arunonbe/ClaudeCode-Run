# DS_DB_ecountcore_process — Enterprise Architect View

## Platform Generation

`Ecountcore_Process` is a **purpose-built staging and integration database** for the Onbe prepaid card platform. It represents a deliberate architectural separation of concerns: inbound file processing, data staging, and reconciliation are isolated from the authoritative operational database (`Ecountcore`). This is a sound enterprise architecture pattern for payment processing systems — it reduces the blast radius of integration failures and allows files to be processed and validated before affecting the CDE.

The use of SQL Server table partitioning for high-volume FDR files, and the partition switch architecture for archival, indicates thoughtful performance engineering. The database is SQL Server 2016 target, consistent with the EcountCore platform.

---

## Role in the Payments Architecture

`Ecountcore_Process` occupies the **Integration Staging tier** between external payment partners and the core CDE:

```
[External Partners / Processors]
  FDR (First Data Resources) ──> DD031, DCAF, NACHA, ATM/ACH STAR files
  Citi NAOT                  ──> Plastic shipping, return mail, NACHA files
  Fiserv                     ──> Card ship status files
  Arroweye                   ──> Order/ship confirmation files
  Paypoint                   ──> Encashment settlement files
  ALTO / PACS                ──> Bulk ACH load files
  Citi WorldLink (IEFT)      ──> FX rate, payment files
  IVR System                 ──> Card activation files
        ↓
  [Ecountcore_Process DB] ← THIS REPO
  (staging, validation, status tracking, partition management)
        ↓
  [Ecountcore DB] (posting, financial updates, cardholder records)
        ↓
  [Ecountcore_Process_Archive DB] (historical data beyond retention window)
```

The database also serves as the **source for the AML Mantas ETL** (`AMLMantasETLNAM.dtsx` connects to `Ecountcore_Process_SS`), meaning it is a data source for compliance surveillance.

---

## System Dependencies

### Upstream Producers
| System | Data Produced | Interface |
|---|---|---|
| FDR (First Data Resources) | DD031, DCAF, NACHA, CD011/052/061 | NDM/Connect:Direct → filesystem → SSIS |
| Citi NAOT | Plastic shipping, return mail, NACHA | NDM → filesystem → SSIS |
| Fiserv | Card ship status | NDM → filesystem → SSIS |
| Arroweye | Order/shipment confirmations | SFTP/file |
| Paypoint | Encashment settlement | File |
| ALTO/PACS | Bulk ACH loads | File/batch |
| Citi WorldLink | FX rates, payment files | File |
| IVR system | Card activation records | Direct insert or file |

### Downstream Consumers
| System | What it reads | Interface |
|---|---|---|
| `Ecountcore` | Posted transaction data (via cross-database queries) | Direct SQL (cross-db) |
| Oracle Mantas (AML) | Account/transaction data | SSIS ETL reads from this DB |
| Batch processing services | Processing status, queue records | Stored procedure calls |
| `Ecountcore_Process_Archive` | Archived partition data | Partition switch (T-SQL) |

---

## Architectural Patterns

### Partition Switch Pattern
The "switch table" pattern (`*_switch` alongside main `*` tables) is a SQL Server high-performance bulk load technique:
1. Data is loaded into the switch table (heap, no constraints)
2. Constraints are validated on the switch table
3. `ALTER TABLE SWITCH PARTITION` atomically moves data into the main table's partition
4. This avoids index maintenance during bulk load, dramatically improving throughput

### File-Based Integration
All external data enters through files delivered via NDM/Connect:Direct. This reflects the legacy payment industry standard of batch file interchange. Each file type has dedicated staging tables with file_status tracking.

### Cross-Database Reference Pattern
Procedures in this database reference `[ecountcore].[dbo].[core_card_master]` and other EcountCore tables directly via three-part names (as seen in `fdr_process_dd031_import.sql`). This tight cross-database coupling means both databases must be on the same SQL Server instance (or linked server).

---

## Migration Complexity

| Dimension | Assessment |
|---|---|
| File-based integration | High complexity — replacing NDM with cloud-native file ingestion (Azure Event Grid + Blob Storage) requires re-architecting 15+ file processing workflows |
| Cross-database dependencies | High — cross-database T-SQL references (`[ecountcore].[dbo].*`) must be replaced with API calls or event streaming in a decomposed architecture |
| Partition architecture | Medium — partition switch can be replaced with Azure SQL Hyperscale or Azure Table partitioning, but requires storage redesign |
| FDR/Citi/Fiserv file formats | High — proprietary binary/fixed-width file formats require maintained parsers in any migration |
| CVV remediation before migration | Critical blocker — CVV columns must be removed before any cloud migration to reduce scope for cloud PCI assessment |

---

## Recommendations

1. **Remediate CVV columns immediately** before any migration or scope assessment activities.
2. **Replace NDM with cloud-native file transfer** (Azure Blob Storage + Azure Data Factory) as a first migration step — this does not require changing the database schema.
3. **Evaluate API-based FDR integration** — First Data (now Fiserv) offers API-based settlement reporting that could replace DD031 file processing.
4. **Maintain partition architecture** — the partition switch pattern is well-designed and should be preserved (or replaced with equivalent Azure SQL Hyperscale auto-partitioning) in any migration.
