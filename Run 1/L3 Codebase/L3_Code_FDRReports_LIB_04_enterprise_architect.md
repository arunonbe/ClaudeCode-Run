# Enterprise Architect View — FDRReports_LIB

## Platform Generation and Role

**Platform Generation**: Gen-1 (legacy on-premises, pre-cloud)  
**Language Ecosystem**: .NET Framework 4.0 / C# (distinct from all other Onbe repositories which are Java)  
**Integration Target**: Fiserv (FDR) RMS28 batch report files + Microsoft Dynamics GP (ECNT database)  
**Role**: First-stage FDR report parser — the entry point for Fiserv financial data into Onbe's systems

## Unique Architectural Position

This is the **only C# / .NET repository** identified in the batch of 6 repos, and likely one of the very few C# repositories in Onbe's overall portfolio (which is predominantly Java). This signals its origin as a one-off utility tool, probably developed by a finance or operations team rather than the core engineering organization, and not subject to Onbe's standard engineering practices.

The README's statement "until conversion to ETL/ELT process" indicates that this was always intended to be temporary but has likely remained in production for years, accruing risk with each passing year as the .NET Framework 4.0 platform ages.

## Integration Architecture Position

```
[Fiserv / FDR Card Processor]
    |
    | Daily RMS28 flat file delivery
    | (via SFTP or secure file transfer to network share)
    v
[Network Share: \\ppamwdcpdsql5\DynamicsGP\FDRReport\]
    |
    | FDRReports.exe (this application)
    | - Reads all files in directory
    | - Parses 9 report types
    | - Inserts into ECNT (Great Plains DB)
    v
[ECNT Database on PPAMWDCPISQL3A1]
    |
    | Microsoft Dynamics GP (Finance System)
    | - Settlement reconciliation
    | - Fee accounting
    | - Interchange tracking
    v
[Finance Team Reporting / General Ledger]
```

## Relationship to Other Repositories

| Repository | Relationship |
|-----------|-------------|
| `fdr-batch-reports-processing_LIB` | Downstream Java processor that reads from different FDR staging tables (EcountCore, not ECNT). The two repos target different databases — FDRReports_LIB feeds the GP finance system; fdr-batch-reports-processing_LIB feeds the job service. |
| `DS_DB_GP_EAST` / `DS_DB_GP_ecnt` | Database schema repositories for the ECNT (Great Plains) database that this application writes to. |
| `DS_ETL_finance` / `DS_ETL_finance-gp` | ETL repositories that may represent the planned replacement for this application. |

## Finance System Integration

The `ECNT` database is Microsoft Dynamics GP (Great Plains) — Onbe's ERP/Finance system. By writing Fiserv settlement and fee data directly into GP tables, this application enables:
- Automatic general ledger entries for card processing fees (interchange, currency conversion).
- Settlement reconciliation between card processor and Onbe's books.
- Currency conversion tracking for international card transactions.

This is a **finance-critical integration**. Errors in parsing or data loading directly affect Onbe's financial reporting and could result in material misstatements.

## FDR / Fiserv Context

FDR (First Data Resources) was acquired by Fiserv in 2019. The RMS28 file format is a Fiserv standard for delivering batch settlement and fee reports to card issuers and program managers. The report codes (VS-110, VS-115, VS-120, VS-130 for Visa; CD-023, CD-025, CD-525 for currency conversion; SD-018 for Mastercard; DD-441 for fee detail) are standard FDR report identifiers. This format is unlikely to change frequently as it is part of Fiserv's stable reporting infrastructure.

## Compliance Architecture Assessment

This application represents significant PCI DSS compliance risk:

1. **CardNumber in DD-441**: The presence of card number data (even truncated) in a .NET Framework 4.0 application with no encryption, no access controls, and hardcoded credentials is a PCI DSS scope expansion risk. The `ECNT` database and the servers running this application must be assessed as part of the CDE if card data is present.

2. **Hardcoded credentials in source code** (`FDRReports.cs` lines 413, 418): `Password=Ecount99!` (production) and `Password=r3p0rt1ng` (UAT) are committed to version control. Anyone with access to this repository has production database credentials.

3. **No TLS enforcement**: ADO.NET connections use `Integrated Security=False` with SQL Authentication — the default TLS behavior of SQL Server 2012-era installations may not enforce TLS 1.2+.

4. **No audit logging**: There is no log of which files were processed, when, and what records were inserted. This violates PCI DSS Requirement 10 (log and monitor all access to system components and cardholder data).

## Migration Priority

**Migration Priority: HIGH**

Given that:
- This is the only C# application in an otherwise Java environment.
- It contains hardcoded production credentials.
- It may process card-related data (DD-441 CardNumber).
- .NET Framework 4.0 is end-of-life.
- The README explicitly identifies this as a transitional tool.

**Recommended migration path**: Replace with Azure Data Factory or SSIS (SQL Server Integration Services) pipeline to ingest FDR RMS28 files, using Azure Key Vault for credentials, with proper PCI DSS controls around card data handling.
