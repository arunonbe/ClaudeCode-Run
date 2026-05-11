# DS_DB_ecountcore_process_archive — Enterprise Architect View

## Platform Generation

`Ecountcore_Process_Archive` is the **long-term retention tier** of the Onbe prepaid card processing platform. It was purpose-built in August 2021 to receive time-expired partition data from `Ecountcore_Process`, fulfilling regulatory retention obligations without degrading the performance of the active processing database.

The database reflects a deliberate, staged data lifecycle architecture — active processing in `Ecountcore_Process`, regulated retention in `Ecountcore_Process_Archive`, and final secure deletion when the archive retention period expires. This is an appropriate enterprise pattern for a PCI DSS Level 1 payments processor operating under multiple concurrent regulatory regimes.

---

## Role in the Payments Architecture

`Ecountcore_Process_Archive` sits at the end of the data lifecycle pipeline for EcountCore staging data:

```
[External Partners / Processors]
  FDR, Citi NAOT, Fiserv, Arroweye, Paypoint, ALTO/PACS, IVR
        ↓
[Ecountcore_Process DB]
  Active processing: staging, validation, status tracking
  Data retained for online_months (short-term operational window)
        ↓ (partition switch when online_months exceeded)
[Ecountcore_Process_Archive DB] ← THIS REPO
  Regulated retention: NACHA 2yr, Reg E 24mo, state law 5-7yr
  Final deletion when archive online_months exceeded
        ↓ (truncate — data permanently deleted)
[End of lifecycle]
```

The archive is also implicitly within scope for:
- **PCI DSS CDE** — it holds FDR cardholder data and (critically) the `cvv_in` column from DCAF auth data
- **AML surveillance** — Oracle Mantas reads from `Ecountcore_Process`; historical archive data may be referenced during investigation follow-up
- **SOC 1 / SOC 2 audit evidence** — archived settlement records support SOC 1 audit assertions about payment processing controls

---

## System Dependencies

### Upstream Producers

| System | Interface | Notes |
|---|---|---|
| `Ecountcore_Process` DB | Partition switch (`ALTER TABLE SWITCH PARTITION`) + INSERT via `ecountcore_process_partition_maintain` SP | The archive DB receives data exclusively from the process DB's maintenance procedure |

The archive database has **no direct external data producers**. All data enters through the partition switch mechanism from `Ecountcore_Process`. This means:
- If the `Ecountcore_Process` maintenance job fails, no data reaches the archive
- The archive schema must stay synchronised with the source tables in `Ecountcore_Process` — any column addition to a source table requires the same column to be added to the archive table

### Downstream Consumers

| System | What it reads | Interface |
|---|---|---|
| Regulatory / audit personnel | Historical NACHA, FDR, settlement records | Ad-hoc SELECT queries via `ecountcore_process_archive_Select` role |
| AML investigation support | Historical transaction records for aged accounts | Direct SQL reads |
| Dispute/chargeback processing | Archived FDR auth and ticket data | Stored procedure calls or direct query |
| Partition maintenance job | `ecountcore_process_archive_partition_control` | Called by SQL Server Agent |

---

## Architectural Patterns

### Partition Switch Receive Pattern

The archive database is the **destination** of partition switch operations initiated in `Ecountcore_Process`. The pattern:

1. In `Ecountcore_Process`, partition-switch expired data into the `*_switch` table (zero-copy, metadata operation)
2. In `Ecountcore_Process`, INSERT from `*_switch` into the corresponding archive table
3. In `Ecountcore_Process`, TRUNCATE the `*_switch` table
4. In `Ecountcore_Process_Archive`, the corresponding `*_switch` tables exist to allow further re-partitioning within the archive if needed

This pattern ensures that the archive insert is a bulk operation (efficient) and that the data is removed from the process DB atomically.

### Schema Synchronisation Dependency

Because the archive tables mirror the process tables column-for-column, any schema change to a source table in `Ecountcore_Process` requires a **co-ordinated migration** across both databases. There is no foreign key or schema enforcement linking the two — synchronisation is purely convention-based. A schema drift between the two databases would cause the INSERT step in the maintenance procedure to fail at runtime.

### Compliance-Driven Retention Architecture

Unlike standard database archiving (which simply moves data to cheaper storage), this archive serves as the **system of record for regulatory compliance**. The `ecountcore_process_archive_partition_control.online_months` values are not performance parameters — they are compliance parameters. Any change requires sign-off from Legal, Compliance, and potentially the QSA.

---

## Migration Complexity

| Dimension | Assessment |
|---|---|
| Data sensitivity | Critical — contains archived FDR CHD data, NACHA records, and `cvv_in` column (PCI violation) |
| Regulatory coupling | High — retention periods are regulated by NACHA, Reg E, state law; cannot be changed without legal review |
| Schema dependency on source DB | High — archive schema must stay aligned with `Ecountcore_Process` tables; independent migration is not possible |
| Partition architecture | Medium — partition switch can be replaced with Azure SQL Hyperscale or Azure Data Factory archival flows, but requires redesign of the maintenance procedure |
| CVV remediation blocker | Critical — `cvv_in` in `fdr_process_dcaf_auth_data` (and potentially populated rows) must be purged before any cloud migration |
| Storage on [PRIMARY] | Low-Medium — re-architecting to dedicated filegroups improves cloud migration options (Azure SQL Hyperscale supports named filegroups) |

---

## Recommendations

1. **Remediate `cvv_in` immediately.** The `fdr_process_dcaf_auth_data.cvv_in` column in the archive database contains data migrated from the process database. Any CVV values archived here are in violation of PCI DSS Requirement 3.3.1. This must be purged before any cloud migration assessment and before the next QSA audit cycle.

2. **Formalise retention period governance.** The `online_months` values in `ecountcore_process_archive_partition_control` are compliance-critical parameters. Implement a formal change control process: Legal/Compliance approval required for any modification, with audit trail.

3. **Add dedicated filegroups in cloud migration.** When migrating to Azure SQL, introduce separate filegroups (or separate databases) for cold archive tiers. Azure SQL Hyperscale supports filegroup separation and read-scale replicas that can serve audit queries without impacting the write path.

4. **Synchronise schema migration with source DB.** Establish a process requiring that any schema change to `Ecountcore_Process` tables that are archived also generates a corresponding migration script for `Ecountcore_Process_Archive`. This should be part of the story definition of done for any table alteration.

5. **Consider event-driven archival as a migration target.** The current batch partition switch could be replaced with an event-driven archival pipeline (Azure Event Hub + Azure Data Factory) in a cloud migration, eliminating the cross-database dependency and enabling independent scaling of the archive tier.

6. **Evaluate archive DB separation from CDE scope.** If the CVV data is purged and cardholder data is tokenised or removed from the archive, it may be possible to move the archive database outside the CDE scope for certain archived tables — reducing PCI audit surface.
