# Business Analyst View — drawdown-data-manager_LIB

## Business Purpose
The Drawdown Data Manager is a Java command-line library used by the legacy Citi/Ecount prepaid-card platform to provision and retrieve bank-account reference data for ACH drawdown (pull-payment) operations. When a cardholder or program needs a linked external bank account on file, this tool reads a CSV input file, validates the data, writes the bank-account record into the StrongBox secrets-vault service, and then persists the resulting vault reference ID back into the GreatPlains (GP) SQL database via a stored procedure (`DrawdownReferenceUpdateSP`). A secondary read-back mode accepts vault reference IDs as command-line arguments and prints the stored bank-account fields.

## Capabilities
| # | Capability | Trigger |
|---|-----------|---------|
| 1 | Bulk-load bank account records from CSV into StrongBox vault | CLI with no args triggers PUT mode |
| 2 | Retrieve and print vault-stored bank account record | CLI with reference-ID arg triggers GET mode |
| 3 | Validate routing/institution/transit numbers and account numbers before writing | Always inline |
| 4 | Persist StrongBox reference IDs to GP database | After successful write |

## Key Business Entities
- **Program** — identified by 8-digit numeric Program ID
- **Promotion** — 1–9 digit numeric ID linking a program to a funding arrangement
- **Bank Account** — routing number (composed from institution + transit numbers), account number, account type, country, bank name
- **StrongBox Reference** — opaque vault reference returned after writing; replaces the raw account number in downstream systems
- **GreatPlains Record** — finance-system row updated with ProgramID, PromotionID, and vault reference

## Business Rules
1. Program ID must be exactly 8 numeric digits.
2. Promotion ID must be numeric, length 1–9.
3. Institution number must be exactly 3 digits.
4. Transit number must be exactly 5 digits.
5. Bank account number must be numeric, 4–17 digits.
6. Client bank name must be 2–30 characters.
7. Any validation failure returns null and prints an error; no partial writes occur.

## Process Flow
```
CSV file → Java validation → StrongBox XMLRPC write → vault reference returned
           ↓ on failure: abort with error message
           ↓ on success: GP stored procedure called to persist (ProgramID, PromotionID, reference)
```

## Compliance Relevance
- Stores bank account numbers in an encrypted vault (StrongBox) rather than in plain SQL — partially aligned with PCI DSS Requirement 3 (protect stored data) and GLBA (financial data protection).
- Account numbers appear in the CSV input file in plaintext; no evidence of file-at-rest encryption.
- No audit trail beyond console println() and GP database update.

## Risks
- CSV input file contains plaintext account numbers; if the file persists on disk it is a GLBA / PCI DSS exposure.
- Spring 2.5.4 and Log4j 1.2.15 are severely outdated (EOL); Log4j 1.x has known critical CVEs.
- Credentials (Director URL, GP DB credentials) stored in flat `.properties` files on `D:\c-base\config\`; no injection-safe secret management at config level.
- No automated test coverage (JUnit 4.4 dependency present but no test classes found).
- `StrongBoxClientException` and `URISyntaxException` are caught and stack-traced only — no structured error handling or alerting.
