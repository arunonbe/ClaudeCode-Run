# Business Analyst — ieft-cp2e_LIB

## Overview

`ieft-cp2e_LIB` is a Java batch library that generates **CP2E (Citibank Payment-to-Enterprise) formatted wire-transfer instruction files** for Onbe's Interbank Electronic Fund Transfer (IEFT) payment rail. It is a foundational payment-disbursement component serving the eCount/Onbe prepaid card platform.

## Business Purpose

The library's sole responsibility is to extract pending outbound payment records from the eCount core database, enrich them with sensitive banking details retrieved from the StrongBox secure vault, and produce a fixed-length 128-character-per-record CP2E flat file that is submitted to Citibank for wire execution.

### Two Transfer Modes

| Mode | Parameter | Description |
|------|-----------|-------------|
| AutoClaim (ACH / domestic wire) | `wl_transfer_type = 0` | Processes all pending claim records up to the current timestamp; anti-concurrency cutoff prevents duplicate processing of live loads. |
| One-Time Transfer (OTT) | `wl_transfer_type = 1` | Processes a single batch identified by `request_file_id`; supports status recovery when a previous OTT extraction failed (exit code 888/777 guard logic in `Cp2eExtractFile.java` lines 100–108). |

### Supported Payment Corridors

The template (`cp2eTemplate.xml`) and business logic in `Cp2eWriter.java` handle multi-currency, multi-country payouts including:
- Domestic ACH / wire (USD)
- South Africa (ZAR) — special routing number sourced from `bank_detail4`
- United Kingdom (GBP) — routing number prefixed with `SC`
- Indonesia (IDR) — address appended with `SKN/1/1/50/2` when address is blank
- India (INR) — RBI Payment Purpose Code P1401 ("Compensation of employees") automatically inserted
- Sweden (SEK) — RTGS code word `UTL` appended after `CCT` for wire
- Costa Rica, Kazakhstan — country-specific field transformations

### CP2E File Structure

The generated file contains a fixed-format header (record type `0`), one-to-many transaction lines (record types `01`–`08`, each with sub-record IDs `01`–`16`), and a footer (record type `9`) with total record count, transaction count, and total amount. Each line is exactly **128 characters**; the writer validates this (`Cp2eWriter.java` line 402–409).

### Process Flow

1. Batch job starts; `Cp2eExtractFile.main()` is invoked with output file path and optional parameters.
2. Spring context loaded from `cp2eExtract.xml`; datasource resolved via Director service.
3. Stored procedure `ieft_cfx_process_check_last_OTT_status` checked for failure state.
4. `ieft_cfx_process_generate_file_sequence` generates a unique `request_file_id`.
5. `ieft_cfx_process_batch_extract` (AutoClaim) or `ieft_cfx_process_batch_extract_ott` (OTT) streams rows to `Cp2eDbRowProcessor`.
6. Each row is placed on a configurable thread pool (default 20 threads) as a `StrongBoxLookupHelper` task.
7. StrongBox vault call resolves bank account number, routing number, currency, country, and payment-purpose details for the IEFT account reference.
8. `Cp2eWriter.writeRecord()` (synchronized) formats the row to the file.
9. Footer written; on OTT success, `ieft_cfx_process_upd_file_gen_flag` marks the batch complete.

## Regulatory and Compliance Context

- **Wire payments** are subject to OFAC sanctions screening, which is expected upstream of this component.
- **Reg E** applies to any consumer ACH disbursements flowing through this file.
- The component itself does not apply screening; it is a file-generation utility. Upstream pipeline must ensure compliance before records reach this queue.
- The **India INR corridor** hardcodes payment purpose code P1401 (`PaymentPurposeCodes.java` line 4/486), which aligns with RBI cross-border remittance reporting requirements under FEMA.

## Stakeholders

| Role | Interest |
|------|----------|
| Treasury / Payments Operations | Confirms daily file generation, monitors exit codes |
| Finance ERP (Citibank integration) | Consumes generated CP2E files |
| Compliance | Verifies OFAC pre-screening before file generation |
| Engineering | Maintains extract stored procedures and template XML |

## Version and Technology Baseline

- **Maven artifact**: `CP2E_creator:IEFT_CP2E:2019.4.5` (pom.xml line 6) — artifact last versioned in 2019.
- **Java source/target**: 1.6 (pom.xml lines 70–71) — critically outdated; Java 6 reached end-of-life in February 2013.
- **Spring**: 2.x (ClassPathXmlApplicationContext from XML DTD spring-beans).
- **StrongBox integration**: XML-RPC client (`strongboxClient:1.0.2`, `strong-box-client:1.1.1-SNAPSHOT`).
