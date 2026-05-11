# Business Analyst Report — windows-scripts

## Business Purpose

`windows-scripts` is a repository of operational scripts — VBScript (VBS), Perl, and BCP format files — that run on the Windows-based batch processing servers (primarily `bat03` and `p-az-app12`) in the Gen-1 eCount/Citi and Wirecard/Northlane production environment. These scripts are the operational backbone of the Gen-1 batch processing layer, executing file ingestion, transformation, validation, financial reconciliation, and bank integration tasks.

The scripts operate within the jIntegra J2COM bridge environment, which provides a COM-to-Java interoperability layer allowing VBScript to invoke eCount Core Java services via the `ECountService.Connection` or `ECountService.Connection_j2com` COM object.

## Capabilities

### VBScript Operational Scripts
- **SSN/PII update scripts** (`1099_ssn_update.vbs`, `dob_update.vbs`): Direct invocation of `ECountCore.eMember.UpdateSecureProfile` to update Social Security Numbers and dates of birth for cardholders. These scripts accept member IDs and SSNs as arguments or hardcoded values.
- **RPC execution wrapper** (`RPC-EXEC.vbs`): Generic XML-RPC invocation script allowing any eCount interface/method to be called from the command line. Used for ad-hoc operational data corrections.
- **Data execution scripts** (`data-exec.vbs`, `data-exec-ignore-pk.vbs`): Invoke stored procedures in eCount databases via the `ECountService.DataEnvironment.Execute` interface. Used for batch data corrections and ETL.
- **ACH control total scripts** (`ach-orig-control-totals-*.vbs`, `ach-returns-control-totals-*.vbs`): Validate ACH origination and return file control totals per bank (MB/MetaBank, Sunrise Bank, Citi, Peoples Bank).
- **Check issuance scripts** (`Check-Issuance-totals-MB.vbs`, `CPSPreCheckReturns-totalchecks-*.vbs`): Validate check issuance totals and CPS (Card Payment Services) pre-check return totals.
- **PGP scripts** (`pgp.vbs`): Invoke PGP encryption/decryption operations for file transfer.
- **SFTP job failure email** (`SFTPjobfail_email.vbs`): Send email alerts on SFTP job failures.
- **Personix/card fulfilment scripts** (`INVENTORY_INDY.vbs`, `psxdownloadsweep.vbs`, `RETURN_MAIL_REPORT.vbs`, etc.): Integrate with Personix card fulfilment vendor for inventory management and return mail processing.

### Perl ETL Scripts
- **FDR report parsers** (`fdrReportParser.pl`, `fdrReportParserDAU30.pl`, etc.): Parse First Data Resources (FDR) processor reports (CD-series, DD-series, SD-series) including New Accounts Journal, Daily Embossing, Non-Monetary Entry, Monthly Invoice.
- **Citi report parser** (`citiReportParser.pl`): Parse Citi bank settlement reports.
- **Mellon report parser** (`mellonReportParser.pl`): Parse BNY Mellon custodial bank reports.
- **Personix report parsers** (`psxReportParser.pl`, `importPsxReport.pl`): Parse card fulfilment vendor reports.
- **NESSA parser** (`nessParser.pl`): Parse NESSA (National Electronic Settlement System?) report data.

### BCP Format Files
- SQL Server BCP (Bulk Copy Program) format files for ACH, NACHA, FDR, CPS check, cardholder data feed, IVR pre-check, and ArrowEye card fulfilment data import/export operations.

## Client and Cardholder Impact

These scripts are **production operational tools**. They directly manipulate cardholder PII (SSN, date of birth), trigger financial file processing (ACH, check, NACHA), and control card fulfilment. Errors in these scripts can result in:
- Incorrect SSNs associated with cardholder accounts (1099 reporting errors, identity risk).
- ACH origination/return mismatches causing NACHA file rejections.
- Card inventory discrepancies.
- Missed fraud alerts.

## Regulatory Obligations

- **NACHA**: ACH control total scripts validate NACHA file structure and settlement totals. Any deviation from NACHA rules must be detected and reported.
- **IRS/1099**: The SSN update script is explicitly tied to 1099 tax reporting corrections.
- **GLBA / PCI DSS Req. 3**: Scripts that update SSN and date of birth touch non-public personal information and cardholder data.
- **Reg E**: Scripts that affect ACH origination or return processing are subject to Reg E error resolution obligations.

## Key Business Risks

1. **Direct PII manipulation via command-line scripts with no audit trail**: The SSN and DOB update scripts can be run by any user with access to the server and the COM object, with no built-in logging or approval workflow.
2. **No access controls on script execution**: Scripts reside on production servers and can be executed by any user with Windows login access.
3. **Bank-specific hardcoded credentials**: Credential material was found in related repos; scripts here may reference environment-specific credentials through the jIntegra J2COM configuration.
