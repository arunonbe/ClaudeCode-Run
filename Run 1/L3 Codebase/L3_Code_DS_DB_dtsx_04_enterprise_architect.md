# DS_DB_dtsx — Enterprise Architect View

## Platform Generation

This repository represents **first-generation on-premises batch ETL infrastructure** for the Wirecard North America / Onbe prepaid card platform. The packages target SQL Server Integration Services 2012 (package format version 6, `LastModifiedProductVersion="11.0.7001.0"`). The platform generation is legacy-tier: no cloud connectivity, no API-based integration, entirely file and database-to-database with NDM (IBM Sterling Connect:Direct) for secure file transport.

---

## Role in the Payments Architecture

`DS_DB_dtsx` occupies the **Integration and Compliance Data Pipeline** tier of the Onbe platform architecture:

```
[Core Prepaid Platform]         [External Partners / Compliance]
  EcountCore DB (p-db02)  ─────> SSIS ETL (p-na-bat03) ─────> Oracle Mantas (AML)
  EcountCore_Process_SS   ─────> SSIS ETL               ─────> FDR Settlement
  Great Plains (p-db08)   ─────> SSIS ETL               ─────> Citi NAOT (card ship)
  cf_report               ─────> SSIS ETL               ─────> Fiserv (card ship)
                                                         ─────> Sunrise Bank (reconciliation)
```

The batch server `p-na-bat03` is therefore an integration hub between the core CDE and multiple external regulated entities. It sits within the PCI DSS CDE boundary.

---

## System Dependencies

| Dependency | Type | Criticality | Notes |
|---|---|---|---|
| `p-db02.nam.wirecard.sys\db02` — EcountCore | Database (SQL Server) | Critical | Source for cardholder data, returned checks |
| `p-db06-ha.nam.wirecard.sys\db06` — Ecountcore_Process_SS | Database (SQL Server) | Critical | Source for AML Mantas feeds |
| `p-db08-ha.nam.wirecard.sys\db08` — DYNAMICS / ecnt | Database (SQL Server) | High | Great Plains ERP data for AML |
| `PPAMWDCUDSQL1C1\PPAMWDCUDSQL1C1` — cf_report | Database (SQL Server) | High | Reporting database source |
| Oracle Mantas | External AML system | Critical (compliance) | Receives flat file feeds |
| Citi NAOT | External partner | High | NDM file transfer |
| Fiserv/Personix | External partner | High | NDM file transfer |
| Sunrise Bank | Banking partner | High | Reconciliation files |
| NDM / Connect:Direct | File transfer middleware | Critical | Delivers external partner files to batch server |
| SQL Server Agent | Job scheduler | Critical | Executes all SSIS packages |
| `smtp.nam.wirecard.sys` | SMTP relay | Medium | Alert emails |

---

## Integration Patterns

1. **Database-to-File (Outbound)**: Queries against SQL Server → flat file output → NDM pickup → external system (Mantas).
2. **File-to-Database (Inbound)**: NDM delivers file from external partner → SSIS reads file → SQL Server staging table.
3. **Database-to-Database**: Direct OLE DB connections between SQL Server instances on the same internal network.

All integration is **synchronous batch** — no streaming, no message queue, no event-driven architecture. This is consistent with prepaid card batch processing architectures of the 2005–2015 era.

---

## Migration Complexity

| Dimension | Assessment |
|---|---|
| Cloud migration readiness | Low — all connections reference on-premises SQL Server instances and internal DNS; no environment variable injection or parameter-based configuration |
| SSIS version compatibility | Medium — SSIS 2012 packages can be upgraded to SSIS 2019 with tooling, but connection managers and some components need validation |
| NDM dependency | High complexity — NDM Connect:Direct requires separate migration plan; replacing with SFTP or Azure Data Factory pipelines requires significant re-engineering |
| Oracle Mantas AML feed | High complexity — Mantas expects specific flat-file formats with exact column positions; any ETL replacement must produce identical output |
| Secrets management | Critical remediation needed before cloud migration — all passwords must be externalised to a vault (Azure Key Vault, HashiCorp Vault) before any pipeline modernisation |
| Monitoring modernisation | Medium — SQL Server Agent logs need replacement with observability tooling (Azure Monitor, Datadog) |

---

## Architectural Concerns

1. **Single point of failure**: All ETL runs on a single batch server (`p-na-bat03`). There is no HA/DR configuration for the ETL tier itself — the databases have HA aliases (`-ha.`) but the batch server does not.
2. **No separation of concerns**: The same batch server handles AML compliance feeds, FDR financial settlement, card inventory, and returned checks — unrelated business domains tightly coupled on shared infrastructure.
3. **Credential sprawl**: The `report` SQL login is shared across all ETL packages for all purposes (AML, reconciliation, BIN mapping) — violating the principle of least privilege.
4. **Wirecard-era architecture**: The domain naming convention (`NAM\*` AD accounts, `*.wirecard.sys` DNS) indicates this infrastructure was built during the Wirecard North America period and has been carried forward into Onbe. A full infrastructure audit and renaming is warranted.
5. **No data lineage**: There is no automated data lineage tracking — it is not possible from this repository alone to determine the full column-level provenance of data flowing to Oracle Mantas.

---

## Strategic Recommendations

1. **Modernise to Azure Data Factory or Databricks** for cloud-native ETL, replacing SSIS packages with parameterised pipelines.
2. **Externalise secrets** to Azure Key Vault immediately — this is a PCI DSS and security prerequisite for any migration.
3. **Implement NDM replacement** with Azure Blob Storage or SFTP for external file exchange.
4. **Separate batch server functions** — AML compliance, financial settlement, and card operations should be independent pipelines.
5. **Onboard to SSIS Catalog** as an interim step if migration to cloud is deferred, providing centralised execution monitoring and parameterisation.
