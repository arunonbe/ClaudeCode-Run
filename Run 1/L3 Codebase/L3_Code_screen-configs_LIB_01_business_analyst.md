# Business Analyst View — screen-configs_LIB

## Business Purpose

screen-configs_LIB (`com.ecount.service.screenconfigs:screenconfigs:2016.2.1`) is a Gen-1 eCount service library that manages per-program configuration of the Instant Issue Customer Zone (CZ) setup screens. It enables client program managers (via an administrative interface) to configure which screens, fields, payment reasons, reversal reasons, and display defaults appear on the instant-issue card issuance workflow used by Customer Service Agents (CSAs).

This library is a configuration-as-data layer: rather than hard-coding screen layouts and business rules per program, it stores them in SQL Server and exposes a typed API for retrieval and mutation.

## Capabilities Provided

- **Reversal reason configuration**: retrieves program-specific list of reversal reasons for card transaction reversal screens; filters to active (`A`) reversal type (`R`) entries only
- **Payment reason configuration**: retrieves program-specific payment reason codes and associated amounts for payment screens
- **Screen driver flags**: retrieves named configuration flags that control which screen sections/fields are rendered (e.g., `dspCHInfoFld`, `dspPmtRevFld`, `dspActBalFld`, `dspUpdProfFld`, `dspHidePIIFld`)
- **Display defaults data**: retrieves default values for configurable screen fields (telephone number defaults, location selection, account suspension thresholds)
- **O-account details**: retrieves account type listings for instant-issue screens
- **CC Admin layout**: assembles the complete call-center admin screen layout from screen driver flags and reversal reasons
- **Sections layout**: assembles the complete sections layout (Collapse Sections, Default Data, Payment Details) for a program
- **Account suspension parameters**: retrieves account suspension configuration (inactive account suspension threshold)
- **Save operations**: persists payment reason settings, display default data, display settings, and o-account details back to SQL Server

## Client/Cardholder Impact

This library indirectly affects cardholders by controlling what CSA agents see when processing instant-issue card requests. Misconfiguration (e.g., incorrect payment reasons, wrong PII display flags) can cause:

- CSAs to inadvertently expose cardholder PII that should be hidden (`dspHidePIIFld`)
- Payment reversals to be processed with incorrect reason codes, creating compliance and audit trail issues
- Instant-issue workflows to fail if required screen fields are misconfigured

The `dspHidePIIFld` flag is particularly significant: it controls whether PII is shown to CSAs, directly touching GLBA and PCI DSS cardholder data minimization obligations.

## Business Rules Found in Code

- Reversal reasons are filtered to only active (`Column2 = 'A'`) and reversal-type (`Column3 = 'R'`) entries; inactive or non-reversal entries are silently excluded
- Payment reasons include both reason code and amount — the amount field is part of the screen configuration, suggesting preset amounts for payment types
- Screen driver flags are keyed by identifier strings (e.g., `dspHidePIIFld`, `addressInCSec`, `contactsInCSec`) that are matched by string comparison — any typo in a calling application would silently produce an empty result with no error
- The sections layout assembly is deterministic: flags are always assembled into "Collapse Sections", "Default Data", and "Payment Details" groupings
- Account suspension is configurable per program (not global), allowing different inactivity thresholds per client program

## Regulatory Obligations

- **PCI DSS**: The `dspHidePIIFld` flag, if incorrectly configured, could expose cardholder PII to unauthorized CSA agents. Configuration of this flag is in scope for PCI DSS Requirement 7 (restrict access to system components and cardholder data to only those individuals whose job requires it).
- **GLBA**: Program-level control over PII display to agents is a GLBA safeguard control. Misconfiguration is a safeguard failure.
- **CCPA**: If programs serve California cardholders, the PII display configuration must enforce data minimization obligations.

## Key Business Risks Found in Code

- **No input validation**: The `programid` parameter is passed directly to the DAO layer without validation (null check or format check). A null program ID will likely cause a SQL Server exception that propagates unchecked.
- **Silent empty returns**: Most inquiry methods return null or an empty collection when no results are found, with no logging. Misconfigured programs will silently show no screen elements rather than surfacing an error.
- **String-based flag key matching using `==` on string literals**: The code uses `0=="dspHidePIIFld".compareTo(key.trim())` for string equality — while functionally correct, this pattern is confusing and error-prone. The `dspHidePIIFld` flag controlling PII visibility is particularly sensitive to such logic errors.
- **Version freeze**: Library version `2016.2.1` indicates this code has not been substantively updated since 2016. Spring 2.0.4 and JUnit 3.8.1 dependencies are severely EOL.
- **No audit trail for save operations**: `savePaymentReasonSettings`, `saveInstIssueDisplayDefaultData`, and `saveInstIssueDisplaySettings` do not log what changed, who changed it, or when — required for PCI DSS Requirement 10.2 compliance.
