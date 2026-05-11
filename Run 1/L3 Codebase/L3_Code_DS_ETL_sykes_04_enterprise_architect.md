# DS_ETL_sykes — Enterprise Architect Perspective

## Position in the Enterprise Architecture

`DS_ETL_sykes` occupies the **Vendor Data Integration** layer of Onbe's data architecture. It sits between the Sykes Enterprises file-delivery mechanism (external) and the `cf_report` SQL Server operational reporting database (internal). This repository is one of several ETL projects in the `DS_ETL_*` family — alongside `DS_ETL_warehouse` — that together populate the data stores consumed by the `DS_RPT_ecount-report-services` reporting tier.

```
[Sykes Enterprises] -- Excel files --> [Drop Zone: C:\ETL\In\SykesReports\]
                                                    |
                                         [DS_ETL_sykes SSIS packages]
                                                    |
                                         [cf_report SQL Server DB]
                                         d-na-db01.nam.wirecard.sys,2232
                                                    |
                                    [DS_RPT_ecount-report-services SSRS]
```

## Technology Stack Assessment

| Layer | Technology | Version | Status |
|---|---|---|---|
| ETL Runtime | SQL Server Integration Services | 2012 SP4 CU (11.0.7001.0) | End-of-Life |
| Source Format | Microsoft Excel via ACE OLEDB | 12.0 (Office 2010+) | Current |
| Target Database | SQL Server (`cf_report`) | Unknown version | Active |
| IDE | SQL Server Data Tools | 2012 | End-of-Life |
| OLE DB Provider | SQLNCLI11.1 | SQL Server 2012 | End-of-Life |
| OS Integration | Windows DPAPI (EncryptSensitiveWithUserKey) | Windows | Risk |

The entire SSIS runtime is built on SQL Server 2012 tooling, which reached end of extended support in July 2022. Running ETL workloads on unsupported infrastructure is a PCI DSS Requirement 6.3.3 concern (all software components protected from known vulnerabilities).

## Integration Patterns

### Pattern 1: Batch File Ingestion (Push Model)
Sykes delivers Excel files to a local filesystem path. The ETL then polls that directory. This is a push/pull hybrid — Sykes pushes, SSIS pulls. There is no acknowledgement handshake or delivery confirmation mechanism visible in the repository. This is the oldest and least resilient integration pattern; it provides no guarantee of exactly-once delivery.

### Pattern 2: Fixed-Schema Excel Mapping
Each package has hardcoded assumptions about Sykes's Excel report layouts (row ranges, sheet names, column order). This creates a tight coupling between Onbe's ETL and Sykes's report format — any Sykes-side Excel template change requires corresponding ETL modification and redeployment.

### Pattern 3: Shared Reporting Database as Integration Point
All Sykes data lands in the `cf_report` database, which is also the source for SSRS reports and (historically) Crystal Reports. This shared-database integration pattern creates implicit dependencies — a Sykes ETL failure does not cause a hard error in the reporting tier but instead causes stale data to be reported to clients.

## Vendor Management Architecture

The presence of programme-specific packages (Grifols, Verizon, TXU, T-Mobile, Biolife) within a single Sykes ETL project suggests Sykes operates a multi-client queue on behalf of Onbe. This is architecturally significant: Onbe's data architecture must accommodate both the Sykes vendor relationship and the end-client relationships simultaneously. The ETL project functions as an intermediary that disaggregates Sykes's consolidated reporting into client-level data feeds.

## Enterprise Risk and Compliance

### PCI DSS Scope Assessment
Based on the file contents analysed, the Sykes ETL does not process Primary Account Numbers (PAN), card verification values, or track data. The packages process call-centre operational metrics. However:

- The `cf_report` database is within scope for reporting on cardholder activity (see `DS_RPT_ecount-report-services`). Any compromise of the ETL pipeline that allows injection of fraudulent records into `cf_report` could affect the integrity of compliance reports.
- The SSIS runtime machine (`C:\ETL\In\SykesReports\` implies a Windows server) must be assessed for PCI DSS Requirement 2.2 (system configuration standards) and Requirement 6.3 (patch management), particularly given the use of end-of-life SSIS 2012.

### GDPR/CCPA Considerations
Call-centre performance data (handle times, call volumes by programme) is operational metadata and generally does not constitute personal data. However, any package that might capture agent IDs or cardholder callback data would require privacy impact assessment. No such fields are visible in the package parameter definitions reviewed.

### Third-Party Vendor Risk
Sykes (now Concentrix following the 2021 acquisition) is a third-party service provider. Under PCI DSS Requirement 12.8/12.9, Onbe must maintain a list of service providers and monitor their PCI compliance. The data exchange mechanism (plaintext Excel files on a network share) should be assessed as part of that vendor risk review — file-in-transit encryption is not implemented at the ETL layer.

## Architectural Debt

1. **No API-based integration**: The industry standard for vendor operational data exchange has shifted to REST APIs with JSON payloads. Continuing to use Excel file drops creates operational fragility.
2. **Monolithic project**: Eight logically distinct data feeds are combined in one SSIS project. Separation of concerns would be better served by individual micro-ETL deployments per feed, enabling independent versioning and failure isolation.
3. **No master data management**: Programme names and client identifiers (Grifols, Verizon, TXU) are embedded in file patterns rather than resolved through a master data catalogue. This creates referential fragility.
4. **Legacy domain name**: The server FQDN `d-na-db01.nam.wirecard.sys` reflects the former Wirecard North America domain. Post-acquisition rebranding to Onbe/NorthLane should have included infrastructure renaming; the persistence of `wirecard.sys` hostnames in source code represents organisational and potentially contractual risk.

## Strategic Recommendations

1. **Modernise integration**: Evaluate whether Sykes/Concentrix can deliver data via a managed API or SFTP with PGP encryption rather than plaintext Excel drops.
2. **Migrate ETL platform**: Move from SSIS 2012 to Azure Data Factory or SSIS 2019 on current infrastructure.
3. **Rename infrastructure**: Remove `wirecard.sys` references from all connection strings; align with current corporate DNS namespace.
4. **Implement data contracts**: Define formal schemas for each Sykes data feed and validate incoming files against those schemas before processing.
5. **Add observability**: Integrate with a centralised monitoring platform to capture ETL execution metrics, latency, and failure rates.
