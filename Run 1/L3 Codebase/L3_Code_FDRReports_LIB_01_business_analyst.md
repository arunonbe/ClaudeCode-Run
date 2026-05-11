# Business Analyst View — FDRReports_LIB

## Repository Overview

**FDRReports_LIB** is a Gen-1 C# console application (not a reusable library despite its `_LIB` suffix) that parses FDR RMS28 report files from Fiserv and imports the data into Microsoft SQL Server databases. The README states: _"C# console application to import specified reports from FDR RMS28 file. Visual Studio Code to be used to compile, until conversion to ETL/ELT process."_

This is the **first-stage FDR integration component** — it reads the raw Fiserv flat files and parses them into structured SQL Server data. The downstream `fdr-batch-reports-processing_LIB` then reads from those tables for further processing.

## FDR Report Types Processed

The application processes **9 distinct Fiserv/FDR report formats** from the RMS28 report file. Each report type has a defined Header+Detail table structure parsed from the fixed-width text file.

### Report 1: VS-110 — Visa Settlement Summary
**Business Purpose**: Visa settlement totals — the net settlement between Onbe/ecount and Visa for a processing period.  
**Header Fields**: SystemNo, ReportTitle, CompanyName, FBDate, RunDate, RunTime, ReportingFor, ProcessDate, RollupTo, ReportDate, FundXferEntity, SettledCurrency  
**Detail Fields**: ColCategory, ColName, ColQuantity, CreditAmount, DebitAmount, TotalAmount  
**Business Use**: Reconciliation of Visa-settled card transactions. Confirms debits/credits for the settlement period.

### Report 2: VS-115 — Visa Settlement by Currency
**Business Purpose**: Visa settlement broken down by credit/debit transaction quantities and amounts.  
**Header Fields**: Same as VS-110  
**Detail Fields**: ColCategory, ColName, CreditQuantity, CreditAmount, DebitQuantity, DebitAmount, TotalQuantity, TotalAmount  
**Business Use**: Multi-currency settlement reconciliation for Visa network transactions.

### Report 3: CD-523 — Currency Conversion Report
**Business Purpose**: Foreign currency conversion transactions processed through the card network.  
**Header Fields**: SystemNo, ReportTitle, CompanyName, FBDate, RunDate, RunTime, ConversionDate, ConversionRateMid, ConversionRateBuy, ConversionRateSell  
**Detail Fields**: SectionTitle, MemID, TransID, SubTitle, CurrCD, LineColumnCount, ColName, ColQuantity, ColAmount, ColFee  
**Business Use**: Tracks cross-border transactions requiring currency conversion. `MemID` (Member ID) and `TransID` (Transaction ID) are key identifiers.

### Report 4: CD-025 — Currency Conversion Detail
**Business Purpose**: Detailed per-transaction currency conversion data.  
**Header/Detail Fields**: Similar structure to CD-523 with SectionTitle, MemID, TransID, SubTitle, CurrCD, ColName, ColQuantity, ColAmount, ColFee.  
**Business Use**: Granular cross-border transaction reconciliation.

### Report 5: CD-525 — Currency Conversion Summary (alternate)
**Business Purpose**: Additional currency conversion summary variant.  
**Fields**: Same structure as CD-025.

### Report 6: DD-441 — Currency Conversion Fee Detail
**Business Purpose**: Detailed fee breakdown for currency conversion transactions. This is one of the most data-rich reports.  
**Header Fields**: SystemNo, ReportTitle, CompanyName, FBDate, RunDate, RunTime, ReportNumber, FromCompanyName, ReportDate, ReportTime, FullCompanyName, SettlementDate, ProcessorName, ConversionFeeNoOfCharges, ConversionVisaPlusFeeTotal, ConversionMCCirrusCCATotal, ConversionMCCirrusXBDRTotal  
**Detail Fields**: **AccountNumber**, Trace, TrxDate, TrxTime, **CardNumber**, TranCode, TTLXActionAmtSettled, CurrencyFee, ColFC, CrossBorder, Col2FC, TerminalNumber, FeeSource, AcctQual, ColRI  
**Business Use**: Transaction-level fee attribution for cross-border processing. **CardNumber** in the detail represents a masked or truncated card number — see sensitive data flag below.

### Report 7: SD-018 — Mastercard Settlement Summary
**Business Purpose**: Mastercard (MC) / Cirrus settlement totals by merchant and cardholder categories.  
**Detail Fields**: SectionTitle, GroupName, Category, MerchantCount, MerchantAmount, MerchantFee, CardholderCount, CardholderAmount, CardholderFee  
**Business Use**: MC network settlement reconciliation — net amounts owed to/from the Mastercard network.

### Report 8: VS-120 — Visa Clearing Detail
**Business Purpose**: Visa clearing transaction detail (distinct from settlement — clearing precedes settlement).  
**Detail Fields**: ColCategory, ColSubCategory, ColName, ColCount, ClearingAmount, ValueCredits, ValueDebits  
**Business Use**: Visa clearing reconciliation to confirm transactions in the clearing pipeline.

### Report 9: VS-130 — Visa Interchange Detail
**Business Purpose**: Visa interchange fee breakdown.  
**Detail Fields**: ColCategory, ColSubCategory1, ColSubCategory2, ColSubCategory3, ColName, ColCount, InterchangeAmount, FeeCredits, FeeDebits  
**Business Use**: Interchange fee analysis for Visa transactions — a key cost component of card processing.

## Sensitive Data Flag — CRITICAL

**FLAG: The DD-441 report contains `CardNumber` in the detail records.**

The `DD441Detail` DataTable (FDRReports.cs line 222) includes a `CardNumber` column. In Fiserv RMS28 reports, the CardNumber field in DD-441 detail records typically contains a masked PAN (first 6 / last 4) or a truncated card number — but the exact masking depends on the Fiserv configuration and contract. This must be confirmed with Onbe's Fiserv account team and verified against PCI DSS Requirement 3.4 (render PAN unreadable anywhere it is stored).

Even truncated or masked PANs are subject to PCI DSS scoping considerations if combined with other card-related data (AccountNumber, TransactionID, CardNumber together could re-identify a card).

The `AccountNumber` field in DD-441 is likely a DDA or internal account reference, not a full PAN, but must be confirmed.

## Operational Context

This application reads the daily RMS28 file delivered by Fiserv to Onbe's network share (multiple commented-out file paths in `FDRReports.cs` lines 346–358 reveal historical file locations: `\\ppamwdcpdsql5\DynamicsGP\FDRReport\`, `T:\GCouto\FDRReport\`). The parsed data is loaded into SQL Server tables via ADO.NET (SqlClient). The data then feeds the Great Plains (Microsoft Dynamics GP) finance system and the `fdr-batch-reports-processing_LIB` downstream processing pipeline.

The comment at line 355 references `GP_UAT_Testing` directories, confirming integration with the Microsoft Dynamics GP financial system used by Onbe's finance team.
