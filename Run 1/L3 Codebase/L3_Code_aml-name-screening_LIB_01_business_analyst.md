# aml-name-screening_LIB — Business Analyst View

## Business Purpose

This library implements an **AML (Anti-Money Laundering) Name Screening** batch process. Its sole function is to accept a list of person names from an Excel input file, query the Ecountcore prepaid card account registration database for matching cardholder records, and write the matched results back into the same Excel workbook. The process was authored in June 2015 by TCS (Tata Consultancy Services) under the Citi Prepaid (`com.citi.prepaid`) brand, which later became part of the Onbe platform.

The library is packaged as a standalone runnable JAR and is not a web service or API — it is a command-line batch tool intended to be scheduled or triggered by an operator.

## Business Capabilities

1. **Name ingestion** — Reads an XLS workbook (legacy HSSF/BIFF8 format) from a configured directory. The first sheet contains a list of names; rows beyond row 1 (header) are treated as subjects. Each row is expected to supply first name, middle name, and last name in the first three columns (pipe-delimited after in-memory parse).
2. **Fuzzy name match via SQL LIKE** — For each subject, issues a `LIKE '%firstName%middleName%lastName%'` query against `fdr_dda_account_registration` in the Ecountcore SQL Server database. Partial / substring matches are returned.
3. **Result enrichment** — Returns 13 cardholder attributes per match: FIRSTNAME, MIDDLENAME, LASTNAME, DDA (demand deposit account number), CARDID, CREATED (date), CITY, STATE, POSTAL, COUNTRY, ADDRESS, EMAIL, CONTACT (phone).
4. **Output to Excel** — Writes results into a second sheet named `amlResultSheet` within the same workbook. If no match is found for a row, writes the sentinel string `"No Possible Outcomes"` in each result column.
5. **Exit code signalling** — Returns OS exit code `0` for success and `1` for any failure, enabling integration into batch scheduling pipelines.

## Business Entities

| Entity | Source | Description |
|--------|--------|-------------|
| Subject Name | XLS input file | First, middle, last name of person to screen |
| `fdr_dda_account_registration` row | Ecountcore SQL Server | Cardholder registration record |
| DDA Number | DB column `dda_number` | Demand Deposit Account identifier linked to a prepaid card |
| Card ID | DB column `card_id` | Physical or virtual prepaid card identifier |
| PII fields | DB columns | `home_email`, `home_phone`, `address1`, `city`, `state`, `postal`, `country` |
| AML Result | Output XLS sheet `amlResultSheet` | All matched cardholder rows for a given subject |

## Business Rules & Validations

- **Row iteration starts at row 2** (`NameScreeningImpl.java` line 39: `for(int i = 2; i <= hm.size(); i++)`), treating row 1 as a header — there is no explicit header validation.
- **Column count is fixed at row 0** (`NameScreeningHelper.java` line 73: `numberOfCells = row.getPhysicalNumberOfCells()`). Subsequent rows are iterated only up to that count; this means a row with fewer columns than the header silently produces empty name segments.
- **Apostrophe escaping** — Single quotes in name segments are escaped by doubling (`'` → `''`) before embedding in the SQL string (`NameScreeningDAO.java` lines 67–78). No other SQL sanitization is performed.
- **"No Possible Outcomes" sentinel** — When a result cell value is null or empty, the string `NameScreeningConstants.NO_POSSIBLE_OUTCOMES` is written (`NameScreeningHelper.java` line 205).
- **Mandatory input file argument** — `args[0]` must be supplied; absence is caught post-extraction and triggers `System.exit(1)` (`NameScreeningMain.java` lines 56–63). Note: the length check occurs _after_ `args[0]` is already read, creating an `ArrayIndexOutOfBoundsException` risk when zero arguments are supplied.
- **Optional credential arguments** — DB credentials are passed as `USERNAME=<val> PASSWORD=<val>` CLI arguments. They must appear in exactly that order (`NameScreeningMain.java` lines 113–128).
- **Hardcoded fallback credentials** — `NameScreeningConstants.java` defines `USERNAME = "report"` and `PASSWORD = "[REDACTED — rotate immediately]"` as compile-time constants (lines 25–26), though these are not automatically used by the DAO if CLI arguments are present. A commented-out alternate pair (`[REDACTED — rotate immediately]`/`[REDACTED — rotate immediately]`) also exists (lines 28–29).

## Business Flows

```
Operator invokes JAR:
  java -jar NameScreening-1.0.0-SNAPSHOT-jar-with-dependencies.jar <inputFile> USERNAME=<u> PASSWORD=<p>
        |
        v
NameScreeningMain.main()
  --> Loads Spring context (applicationContext.xml)
  --> Resolves NameScreeningImpl bean
  --> calls processNameScreening(inputFileParam, commandLineInputParams)
        |
        v
NameScreeningImpl.processNameScreening()
  --> NameScreeningHelper.loadInputFile(xlsPath)
      Reads XLS sheet[0], row[1..n], returns HashMap<rowIndex, pipe-delimited StringBuilder>
        |
        v
  --> For each row i=2..n:
        Parse firstName, middleName, lastName from pipe-delimited string
        --> NameScreeningDAO.execute(first, middle, last, params)
            Opens JDBC connection to Ecountcore SQL Server
            Executes LIKE query against fdr_dda_account_registration
            Returns ArrayList<ArrayList<String>> of up to 13 columns per match
        --> NameScreeningHelper.updateWorkbook(result, xlsPath, rowIndex)
            Appends result rows to sheet "amlResultSheet"
            Writes "No Possible Outcomes" for empty cells
        |
        v
  Returns 0 (success) or 1 (failure)
  System.exit(status)
```

## Compliance & Regulatory Concerns

- **AML / BSA obligation** — The tool exists to screen prepaid cardholder names against a list of persons of interest, a core BSA/AML control. However, the implementation queries the _internal_ account database only (Ecountcore). There is no integration with any external OFAC SDN list, FinCEN database, Accuity/WorldCheck, or equivalent sanctions/PEP screening service. The "screening" is purely a fuzzy name lookup within Onbe's own cardholder population, not against a regulatory watchlist. This means the tool is an internal investigation aid, not a true OFAC/AML watchlist-screening control.
- **PII exposure** — The output XLS file contains cardholder PII: full name, address, email, phone, DDA number, and card ID. There is no encryption, masking, or access control on the output file. Any operator who can invoke the job can read the full PII dataset.
- **Credential handling** — Plaintext passwords exist in source code (`NameScreeningConstants.java` lines 25–26) and in the Maven `settings.xml` (multiple server passwords in `.mvn/wrapper/settings.xml`). This violates PCI DSS Requirement 8 (access control) and Requirement 3 (protect stored data).
- **Audit trail** — Log output (Log4j) records SQL queries including unmasked name values and DDA numbers (DAO lines 108–110). Log files may constitute an uncontrolled PII record.
- **No result disposition** — There is no workflow to flag, escalate, or disposition a matched record. The tool produces an Excel file; all subsequent action is manual and untracked.
- **GLBA / CCPA / GDPR** — The PII written to the output XLS file (email, phone, address) is subject to these regulations. No data minimization, retention, or deletion controls are present.

## Business Risks

1. **Not a true watchlist screen** — The tool does not check OFAC SDN, EU consolidated list, or any PEP/adverse media source. Relying on it as an AML control would leave Onbe exposed to regulatory sanctions.
2. **Manual, untracked process** — No case management, audit log of decisions, or SLA tracking exists. Regulators expect documented, repeatable AML screening workflows.
3. **PII leakage via XLS output** — Unprotected XLS files containing full cardholder PII can be forwarded, lost, or stolen.
4. **Orphaned tool** — Package namespace is `com.citi.prepaid`, indicating it was inherited from the Citi/Wirecard era. It has not been updated to Onbe's current platform standards and may be entirely retired or superseded.
5. **No input validation for XLS structure** — Malformed or unexpected column layouts silently produce incorrect screening results.
