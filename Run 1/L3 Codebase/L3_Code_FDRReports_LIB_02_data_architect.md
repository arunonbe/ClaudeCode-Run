# Data Architect View — FDRReports_LIB

## Technology Stack

- **Language**: C# (.NET Framework 4.0 Client Profile)
- **Project Type**: Console Application (executable `.exe`)
- **Target Platform**: x86 (32-bit)
- **Database Access**: ADO.NET (`System.Data.SqlClient`)
- **File Parsing**: Manual string-based line processing (no library)
- **Target Database**: Microsoft SQL Server (`ECNT` database on `PPAMWDCPISQL3A1\PPAMWDCPISQL3A1` in production)

## Source Data: FDR RMS28 File

The application reads fixed-width text files in FDR's RMS28 format. Files are obtained from a network share (historical paths: `\\ppamwdcpdsql5\DynamicsGP\FDRReport\`, `T:\GCouto\FDRReport\`). The file path is read from the `Banker.dbo.SSISJobConfigurations` table at runtime (XML `ReportPath` element).

**File Format**: Fixed-width text, one record per line. Each line begins with a report identifier prefix (e.g., `1VS-110`, `1DD-441`, `1SD-018`). The application switches parsing mode when it detects a new report section header.

## Target Database Schema

**Database**: `ECNT` (Microsoft Dynamics GP database, hosted on Great Plains SQL Server)  
**Connection pattern**: `Server=<server>\<instance>; Database=ECNT; User ID=gplain; Password=Ecount99!`

The data is loaded into DataTable structures in memory, then bulk-inserted into the `ECNT` database. The exact target table names for each report type are determined at runtime from the `Banker.dbo.SSISJobConfigurations` table XML parameters.

## DataTable Structures (In-Memory Representations)

### VS110 Report
- **Header** (`VS110Header`): ID, SystemNo, ReportTitle, CompanyName, FBDate, RunDate, RunTime, ReportingFor, ProcessDate, RollupTo, ReportDate, FundXferEntity, SettledCurrency
- **Detail** (`VS110Detail`): ID, ReportHeaderID (FK), ColCategory, ColName, ColQuantity, CreditAmount, DebitAmount, TotalAmount

### VS115 Report
- **Header**: same as VS110
- **Detail**: ID, ReportHeaderID, ColCategory, ColName, CreditQuantity, CreditAmount, DebitQuantity, DebitAmount, TotalQuantity, TotalAmount

### CD523 Report (Currency Conversion)
- **Header**: ID, SystemNo, ReportTitle, CompanyName, FBDate, RunDate, RunTime, ConversionDate, ConversionRateMid, ConversionRateBuy, ConversionRateSell
- **Detail**: ID, ReportHeaderID, SectionTitle, **MemID** (Member ID), **TransID** (Transaction ID), SubTitle, CurrCD, LineColumnCount, ColName, ColQuantity, ColAmount, ColFee

### CD025 / CD525 Reports (Currency Conversion Detail variants)
- **Header**: SystemNo, ReportTitle, CompanyName, FBDate, RunDate, RunTime
- **Detail**: SectionTitle, **MemID**, **TransID**, SubTitle, CurrCD, LineColumnCount, ColName, ColQuantity, ColAmount, ColFee

### DD441 Report — SENSITIVE DATA PRESENT
- **Header**: SystemNo, ReportTitle, CompanyName, FBDate, RunDate, RunTime, ReportNumber, FromCompanyName, ReportDate, ReportTime, FullCompanyName, SettlementDate, ProcessorName, ConversionFeeNoOfCharges, ConversionVisaPlusFeeTotal, ConversionMCCirrusCCATotal, ConversionMCCirrusXBDRTotal
- **Detail**: ID, ReportHeaderID, **AccountNumber**, Trace, TrxDate, TrxTime, **CardNumber**, TranCode, TTLXActionAmtSettled, CurrencyFee, ColFC, CrossBorder, Col2FC, TerminalNumber, FeeSource, AcctQual, ColRI

**SENSITIVE DATA FLAG**: The `CardNumber` column in `DD441Detail` is populated from the DD-441 report detail. In Fiserv RMS28 format, DD-441 detail lines contain card numbers (typically truncated/masked per Fiserv's PAN protection settings, but the application does not perform any masking). The `AccountNumber` field may be a DDA account reference.

**PCI DSS**: If `CardNumber` contains any form of PAN (even truncated), the `ECNT` database hosting this table falls within PCI DSS scope. Requirement 3.3 states that SAD must not be stored after authorization. Requirement 3.4 requires that PAN be rendered unreadable (hashed, truncated, tokenized, or encrypted) anywhere it is stored. The `ECNT` database and this data pipeline must be formally assessed by Onbe's QSA.

### SD018 Report (MC Settlement)
- **Header**: SystemNo, ReportTitle, FBDate, RunDate, RunTime
- **Detail**: SectionTitle, GroupName, Category, MerchantCount, MerchantAmount, MerchantFee, CardholderCount, CardholderAmount, CardholderFee

### VS120 Report (Visa Clearing)
- **Header**: SystemNo, ReportTitle, CompanyName, FBDate, RunDate, RunTime, ReportingFor, ProcessDate, RollupTo, ReportDate, FundXferEntity, SettledCurrency, ClearingCurrency
- **Detail**: ColCategory, ColSubCategory, ColName, ColCount, ClearingAmount, ValueCredits, ValueDebits

### VS130 Report (Visa Interchange)
- **Header**: SystemNo, ReportTitle, CompanyName, FBDate, RunDate, RunTime, ReportingFor, ProcDate, RollupTo, ReportDate, FundXferEntity, SettledCurrency
- **Detail**: ColCategory, ColSubCategory1, ColSubCategory2, ColSubCategory3, ColName, ColCount, InterchangeAmount, FeeCredits, FeeDebits

## Configuration Architecture

The application reads its runtime configuration (database server, report file path, email settings) from the `Banker.dbo.SSISJobConfigurations` SQL table, specifically the `ProcessLoopParameters` and `JobParameters` columns (XML format). Two environments are hard-coded:
- ID 39: Production (`PPAMWDCPISQL3A1\PPAMWDCPISQL3A1`)
- ID 41: UAT (`ppamwdcUIgp1A1\ppamwdcUIgp1A1`)

The application deliberately processes UAT first, then production (`FDRReports.cs` line 401, `ConfigurationArray = new int[] { 41, 39 }`), as a safety mechanism.

## Sensitive Data Summary

| Field | Report | Risk Level | Notes |
|-------|--------|-----------|-------|
| `CardNumber` | DD-441 Detail | CRITICAL | Card number from FDR file — PCI DSS scope |
| `AccountNumber` | DD-441 Detail | HIGH | DDA/account reference — confirm whether full account number |
| `MemID` | CD-523, CD-025, CD-525 | MEDIUM | Member identifier — linked to cardholder identity |
| `TransID` | CD-523, CD-025, CD-525 | MEDIUM | Transaction identifier — part of card transaction audit trail |
| DB Password | `FDRReports.cs` lines 413, 418 | CRITICAL | Hardcoded in source code: `Password=Ecount99!` and `Password=r3p0rt1ng` |
