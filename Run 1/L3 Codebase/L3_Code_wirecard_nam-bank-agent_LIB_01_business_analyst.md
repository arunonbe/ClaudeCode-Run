# Business Analyst — wirecard_nam-bank-agent_LIB

## Clone Completeness Note
This repository was flagged as a **partial clone** due to Windows long-path limitations. Analysis is based on files successfully cloned, which include all batch configuration classes, job definitions, and structural files. Deep source files in some sub-modules (event-consumer, event-service, event-persistence, config) may be missing. All findings are explicitly sourced from available files.

## Business Purpose
The NAM Bank Agent is the North American banking integration hub for the Wirecard/Northlane platform. It handles all structured file-based communication with NAM-affiliated banks (primary bank partner referenced as "Sunrise" throughout the code), orchestrating ACH inbound/outbound, wire drawdown, check issuance/return, and customer data synchronisation via batch jobs and event-driven consumers.

## Capabilities

### External Bank Communication (Sunrise Bank SFTP)
- Import inbound ACH direct deposit files from Sunrise bank (NACHA format parsing)
- Import inbound ACH return files from Sunrise bank
- Import client fund posting files from Sunrise bank
- Publish outbound ACH origination files to Sunrise bank
- Publish outbound ACH drawdown files to Sunrise bank
- Publish outbound wire drawdown files to Sunrise bank
- Publish outbound direct deposit reject files to Sunrise bank
- Import/publish check-related files (check issuance, check void, check return, undelivered checks)
- Check files exchanged with both Sunrise and PDS (another bank/processor partner)

### Internal CCP/Platform Communication
- Import new wire transfer out transactions from platform EventHub
- Import wire transfer out status updates
- Import wire transfer out notifications of change (NOC)
- Import cancel wire transfer out transactions
- Import check transactions (from platform)
- Import void check transactions
- Import new drawdown transactions
- Import wire transfer in status updates
- Import customers from CCP
- Publish customer data to platform
- Publish check status updates to platform
- Monitor drawdowns (DrawdownMonitorConfig)
- Publish wire transfer in events to platform
- Publish wire transfer out status updates and NOC to platform

## Key Entities
- Customer / cardholder records
- ACH direct deposit transactions (NACHA file records: File Header, Batch Header, Entry Detail, Batch Control)
- ACH origination / drawdown records
- Wire drawdown records
- Check issuance / void / return records
- Undelivered check records
- Wire transfer in / out status updates
- Notification of change (NOC) records

## Business Rules
1. NACHA file format compliance: FileHeaderRecord, BatchHeaderRecord, EntryDetailRecord, BatchControlRecord, FileControlRecord (observed in DirectDepositFile DTOs)
2. Files are downloaded from SFTP, processed, and moved to processed/failed directories
3. Chunk-based processing (`BatchJobConstants.CHUNK_SIZE`) for all batch steps
4. Customer data partitioned by brand (`CustomerBrandPartitioner`)
5. Files in directory processed in parallel partitions (`FilesInDirectoryPartitioner`)
6. Step exception emails sent on batch job failure (`StepExceptionEmailListener`)
7. Files moved to appropriate directory on step completion (`MoveFileStepExecutionListener`)
8. 90% minimum Jacoco code coverage enforced at build time

## Business Flows
1. **ACH Inbound**: Sunrise SFTP → SFTP download tasklet → NACHA file parser → CCP event publish
2. **ACH Outbound**: CCP EventHub → batch reader from Oracle DB → NACHA file writer → SFTP upload to Sunrise
3. **Check Issuance**: CCP platform → batch job → check file generation → SFTP upload to Sunrise and PDS
4. **Wire Drawdown**: EventHub wire-transfer-in event → batch build wire drawdown file → SFTP upload to Sunrise
5. **Customer Sync**: CCP customer data → batch export → internal event publish

## Compliance Relevance
- NACHA compliance: file format, batch balancing, ABA routing numbers in ACH files
- ACH return processing: NACHA return reason codes handled
- Notification of Change (NOC) processing: NACHA NOC codes (`AchNotificationOfChangeCode`)
- Wire transfer communication: potential Fedwire / CHIPS-format messages to bank
- Check issuance: MICR / ANSI X9 compliance implied for check files
- Reg E applicability: ACH direct deposit and return flows are Reg E-governed consumer transactions
- Customer data synchronisation: GLBA/CCPA sensitive data exchange with bank partner

## Risks
1. Partial clone — event-consumer, event-service, and event-persistence modules may have incomplete files; analysis cannot confirm all service-layer business logic
2. Sunrise bank partner credentials (SFTP private key, username, host) are in application properties — not visible in source but must be in environment config
3. StepExceptionEmailListener sends exception details via email — potential data leakage if stack traces contain account data
4. No dead-letter handling observed for batch job failures beyond the failed-directory mechanism
