# Enterprise Architect Report — DS_ETL_atmcardtronics

## Repository Identity

**Repository:** DS_ETL_atmcardtronics  
**Platform Generation:** Legacy SSIS ETL (Generation 1) — SQL Server 2012 era  
**Role in Architecture:** ATM network data ingestion pipeline — connects Cardtronics ATM network data to the cf_report reporting database

---

## Position in Onbe's Data Architecture

DS_ETL_atmcardtronics sits at the **external data ingestion boundary** of Onbe's data platform:

```
[Cardtronics/Allpoint ATM Network]
    ↓ File delivery (FTP/SFTP/manual)
[Local file system: C:\ETL\In\]
    ↓ SSIS packages (this repo)
[cf_report database on q-db03.nam.wirecard.sys\db03]
    ↓ Cross-database queries
[RiskDB ATM Cash Forecast — DS_DP_db15]
    ↓ Reporting application
[ATM Management Dashboard]
```

The pipeline is a **one-way data ingestion channel** — data flows from Cardtronics into Onbe's reporting infrastructure. There is no reverse flow (Onbe data back to Cardtronics via this pipeline).

---

## External Partner Dependency

The pipeline depends on **Cardtronics** (now Cardtronics International, rebranded to Allpoint Network) for data delivery. Key enterprise considerations:

1. **Partner data format ownership:** Cardtronics controls the flat file formats. Any format change on the Cardtronics side requires SSIS package updates on the Onbe side. There is no schema registry or format versioning mechanism.

2. **File delivery SLA:** The delivery mechanism and timing are not documented in the repository. If Cardtronics is late delivering files, the daily ETL jobs will either fail (if mandatory) or produce stale data (if optional file handling is implemented).

3. **Data reconciliation:** The settlement reconciliation between Cardtronics and Onbe is done through the TACTDIST files and monthly account statements. Any discrepancy between Cardtronics' records and Onbe's processing data needs investigation capability — the Electronic Journal data is key to this.

---

## Technology Generation Assessment

| Technology | Version | Support Status |
|---|---|---|
| SSIS | 11.0.7001.0 (SQL Server 2012 SP4) | Extended support ended July 2022 |
| SQLNCLI11.1 | SQL Server Native Client 11 | Deprecated (replaced by MSOLEDBSQL) |
| ACE OLEDB 12.0 | Microsoft Access Database Engine | Current (regularly updated with Office) |
| SSIS Package format version | 6 | Compatible with SQL Server 2012–2019 |

**SQL Server 2012 reached end of extended support in July 2022.** The SSIS packages were built on SQL Server 2012 SSIS tooling. While SSIS packages created on SQL Server 2012 are generally forward-compatible with SQL Server 2016/2017/2019, the package format version (6) and the `LastModifiedProductVersion=11.0.7001.0` metadata confirm the packages have not been updated or re-saved in a newer SSIS version.

---

## Integration Architecture Assessment

### Pull Pattern (File-Based)
The pipeline uses a **file-based pull pattern**: SSIS picks up files from a local directory. This is a common legacy ETL pattern with the following implications:
- No real-time processing capability
- Daily batch window creates a 24-hour data lag for ATM operations insights
- Files must be available at job execution time (no retry/queue mechanism)
- Local disk dependency — if the ETL server disk fills, all pipelines stop

### Single Destination Database (cf_report)
All 13 SSIS packages write to a single destination database (`cf_report`). This creates:
- A single point of contention for concurrent package execution
- cf_report as a critical dependency — downtime of `q-db03` stops all ATM data ingestion
- Table name conflicts are possible if packages write to overlapping tables without coordination

### No API Integration
The pipeline predates API-based data exchange. Modern ATM network data integrations typically use REST APIs or event streams (e.g., Kafka topics) rather than flat files. A modernisation path would involve:
1. Replacing Cardtronics flat file delivery with API calls (if Cardtronics provides an API)
2. Or replacing SSIS with Azure Data Factory or a Python/Spark ETL that provides better monitoring, retry, and scalability

---

## Naming and Identity

The packages were created by `WIRECARD\nick.doan` on workstation `PF0WXHBU` in November 2018. The design-time file paths contain `Wirecard` in file names (`WirecardDispenseDetail*.csv`, `WirecardATM_FISSettlementBalancing*.xlsx`). This confirms:
- The pipeline was built during the Wirecard era and has not been fully rebranded
- Cardtronics may still deliver files with `Wirecard` in the filename — or the file naming convention has been updated and only the SSIS design-time path retains the old name

---

## Migration Complexity Assessment

| Migration Concern | Complexity | Notes |
|---|---|---|
| Replacing SSIS with Azure Data Factory | MEDIUM | 13 packages; ADF has a SSIS lift-and-shift option |
| Migrating from SQLNCLI11 to MSOLEDBSQL | LOW | Connection string update only |
| Removing Excel source dependency (ACE) | MEDIUM | Requires Cardtronics to change TACTDIST delivery format |
| Introducing API-based Cardtronics integration | HIGH | Depends on Cardtronics API availability and partnership agreement |
| Centralising file landing zone to Azure Blob Storage | LOW | ADF supports blob triggers natively |
| Improving SMTP to use TLS | LOW | Configuration change only |
