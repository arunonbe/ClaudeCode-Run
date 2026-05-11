# Business Analyst Report — DS_ETL_atmcardtronics

## Repository Identity

**Repository:** DS_ETL_atmcardtronics  
**Classification:** ETL Pipeline — ATM Cardtronics Integration  
**Technology:** Microsoft SQL Server Integration Services (SSIS) — SQL Server 2012 (SSIS 11.0.7001.0)  
**Package count:** 13 SSIS packages (.dtsx files)  
**Project created:** November 2018 (WIRECARD\nick.doan on workstation PF0WXHBU)

---

## Business Purpose

DS_ETL_atmcardtronics is the **SSIS-based ETL pipeline** for processing data feeds from **ATM Cardtronics** (now Cardtronics/Allpoint), a major independent ATM network operator. Onbe (then Wirecard NAM) operates a fleet of ATMs through a Cardtronics partnership, providing cash access for prepaid cardholders.

The ETL pipeline ingests data files delivered by Cardtronics (CSV, flat files, Excel) and loads them into the `cf_report` SQL Server database for operational reporting, reconciliation, and partner billing.

---

## ATM Business Context

Cardtronics is one of the largest ATM operators in the world. Onbe's relationship with Cardtronics enables prepaid cardholders to withdraw cash at Allpoint ATM network terminals. The ETL pipeline processes the following operational data feeds:

1. **Daily Dispense** — cash dispensed per terminal per day
2. **Dispense Detail** — granular dispense transaction records
3. **Interchange** — interchange fee settlements between Cardtronics and Onbe
4. **Surcharge** — surcharge fee records per transaction
5. **Switch Balance** — ATM switch balancing data
6. **Replenishment** — cash cassette replenishment events
7. **Electronic Journal** — ATM electronic journal records (transaction audit trail)
8. **Daily Report** — consolidated daily operational summary
9. **Device Performance** — ATM terminal uptime/performance metrics
10. **TACTDIST Import** — TACT (Transaction) distribution file from Cardtronics' settlement system
11. **Partner Monthly Account Statement** — monthly financial reconciliation with Cardtronics partners
12. **Adjustment Email** — automated email notifications for ATM adjustment records
13. **Dispensed** — total dispensed amounts summary

---

## Data Flow Summary

The ETL follows a consistent pattern across all packages:
```
[Cardtronics FTP/File Delivery] → [C:\ETL\In\Cardtronics\] → [SSIS Package] → [cf_report database]
                                                                              → [C:\ETL\In\CardtronicsArchive\]
```

Files are delivered to a local staging path (`C:\ETL\In\Cardtronics\`) where SSIS packages pick them up. Processed files are archived to `C:\ETL\In\CardtronicsArchive\`.

---

## Key Process Details

### Cash Dispense Reconciliation
The `ATMCardtronics_DailyDispense.dtsx` package processes files with columns:
- `TID` (Terminal ID)
- `Currency`
- `sod_balance` (Start-of-Day balance)
- `disp_before_replen` (Dispensed before replenishment)
- `END_Residual`
- `load_amt`
- `disp_after_replen`
- `EOD_balance` (End-of-Day balance)
- `total_20`, `total_50`, `total_100` (denomination breakdowns)
- `total_disp`

These fields enable cash position reconciliation per ATM terminal — critical for ensuring Onbe's cash liability is correctly accounted for.

### TACTDIST Settlement Import
The `ATMCardtronics_TACTDIST_Import.dtsx` package imports `TACTDIST` files (settlement distribution files from the Cardtronics TACT system), including Excel-formatted activity files (`WirecardATM_FISSettlementBalancing*.xlsx`). This is the primary settlement reconciliation feed for the Cardtronics partnership.

### Adjustment Email Notifications
The `ATMCardtronics_AdjustmentEmail.dtsx` package sends automated email notifications to configured recipients when adjustment records are identified. Email recipients are configured via project parameters (`EmailTo`, `EmailCC`, `EmailFrom`).

---

## Schedule and Operational Cadence

The packages are designed to run on a **daily schedule**:
- Daily packages: `ATMCardtronics_DailyDispense`, `ATMCardtronics_DailyRpt`, `ATMCardtronics_ElectronicJournal`
- Monthly packages: `ATMCardtronics_PartnerMonthlyAcctStat`
- On-demand: `ATMCardtronics_AdjustmentEmail`

The scheduling mechanism is not visible in this repository — packages are executed by SQL Server Agent jobs on the host server, configured separately.

---

## Regulatory Relevance

### PCI DSS
ATM dispensing activity feeds relate to **cash withdrawals by prepaid cardholders**. Terminal IDs (TIDs) link to card network terminals. While this data does not directly contain PANs, the combination of TID + transaction amounts + timing data is **card-adjacent** and should be scoped in the CDE boundary assessment.

The TACTDIST file imports settlement data that reconciles financial positions between card networks, which falls under PCI DSS Req 9 (physical security of media containing cardholder data) for file handling and Req 10 (logging and monitoring) for access to settlement files.

### NACHA / ACH
Not directly applicable — ATM cash dispensing uses card networks (Allpoint/Mastercard), not ACH.

### Reg E
ATM transactions involving prepaid cardholders are subject to Reg E dispute resolution requirements. The Electronic Journal data in this ETL is critical for Reg E dispute investigation — it provides the transaction-level audit trail.

### GLBA
ATM cash transaction data constitutes consumer financial transaction data subject to GLBA protection obligations.
