# Data Architect Report — optic_WAPP

## Data Models

The OPTIC application stores no data within the Excel files themselves. All data resides in the SQL backend called "RiskDB." The data model is defined at the database level and accessed dynamically by VBA SQL queries at runtime. The schema of RiskDB cannot be determined from the repository content.

The Excel files contain:
- VBA macro code (embedded in the `.xlsm` binary format, not visible as text in git)
- Excel workbook structure (sheets, named ranges, form controls) — also embedded in binary format
- No flat data, no CSV exports, no schema files, no ORM mappings

## Sensitive Data Handling

### Unknown Data Classification Risk

Because the VBA code is binary and the RiskDB schema is unknown, it is not possible to determine:
- Whether RiskDB contains CHD (PAN, CVV, expiry dates, track data)
- Whether RiskDB contains PII (SSN, full name, address, date of birth)
- Whether RiskDB contains DDA (bank account / routing numbers)
- What SQL queries OPTIC sends to RiskDB and what data is returned to the user's Excel session

This is a significant gap. If RiskDB is a risk management database for a payments company, it plausibly contains references to cardholder accounts, transaction amounts, merchant identifiers, and potentially truncated PANs or account references. Any such data returned to the Excel application would reside in the user's local memory and potentially in the Excel file's session data.

### Data in Excel Memory

When OPTIC fetches data from RiskDB and displays it in the Excel workbook:
- Data is loaded into Excel's in-memory data model and rendered in cells
- Users may be able to copy, export, or save that data locally
- Excel worksheets may cache data in the `.xlsm` file if saved
- This is a data leakage vector if sensitive data is displayed without masking

## Data Flows

```
[RiskDB Server (SQL Backend)]
    <--> [ODBC/ADO/SQL Server connection from VBA]
        <--> [OPTIC Excel Application (user desktop)]
            --> [User screen / local Excel memory]

[OPTIC Production Copy Link.xlsm (user desktop)]
    --> [HTTP/SMB file download from RiskDB server]
        --> [OPTIC - Production.xlsm (written to user disk or opened in memory)]
```

## Connection String / Credential Risks

VBA Excel applications typically connect to SQL Server via:
- ODBC Data Source Name (DSN) — credentials stored in Windows Registry or ODBC configuration
- ADO connection string embedded in VBA code — potentially including hardcoded username/password

Since VBA code is inside a binary `.xlsm` file and cannot be read from this repository, the connection method is unknown. If a hardcoded connection string with embedded credentials exists in the VBA code, it would be readable by anyone with access to the Excel file and VBA editor (Developer → Visual Basic). This is a PCI DSS Requirement 8 violation if the credentials are shared or embedded in the distributed application.

## Encryption Status

- **Data at rest (RiskDB):** Unknown — depends on SQL Server encryption configuration (TDE, column encryption). Not determinable from this repository.
- **Data in transit:** If the VBA → SQL Server connection uses an unencrypted ODBC connection, data (potentially including sensitive operational data) would be transmitted over the network in plaintext. SQL Server ODBC connections do not encrypt by default unless `Encrypt=yes` or `TrustServerCertificate=No; Encrypt=yes` is specified in the connection string.
- **File download:** The link file downloads the OPTIC application from the server. If this uses an SMB share or HTTP (not HTTPS), the file transfer is unencrypted and subject to man-in-the-middle attack.

## Retention Concerns

Excel-based applications inherently lack formal data retention controls:
- Users may save screenshots or printed exports of data displayed in OPTIC
- If data is cached in the `.xlsm` file by saving it, that data persists indefinitely on the user's device
- There is no automated data deletion mechanism in an Excel application

If RiskDB data includes financial records subject to retention requirements (GLBA: 6 years, PCI DSS: 12 months for audit logs), the absence of retention controls in the Excel layer is a compliance gap.

## PCI DSS Compliance Assessment

- Req 3 (Stored CHD): Risk exists that unmasked CHD could be displayed in and inadvertently cached by the Excel application. Assessment requires VBA code review.
- Req 4 (CHD in transit): SQL connection encryption status is unknown and potentially at risk.
- Req 7 (Access control): SQL firewall permissions provide database-level access control — appropriate if correctly maintained.
- Req 8 (Authentication): Shared VBA-embedded database credentials would be a critical violation. Must be verified.
- Gap: Binary `.xlsm` format prevents effective code review for embedded credential detection.
- Gap: No data masking capability in Excel VBA — if PANs or account numbers appear in query results, they would be displayed in full.
- **Recommended action:** Extract and review VBA code from both `.xlsm` files using the VBA editor or a VBA extraction tool, and audit the connection string and SQL queries for credential and data exposure risks.
