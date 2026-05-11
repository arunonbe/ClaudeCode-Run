# Business Analyst View — xml-converter_LIB

## Business Purpose
XML Converter is a Windows desktop (WinForms) operator-facing tool that allows internal staff and clients to generate XML request files for submission to the eCount job service. It is used to batch-create or fund prepaid card accounts without requiring manual XML authoring.

## Capabilities
- Load client-specific CSV/spreadsheet data from clipboard or file and map columns to eCount XML field schema
- Generate XML request files for the following transaction types:
  - `registration` / `updateregistration` — cardholder registration and profile updates
  - `createaccountrequest` — prepaid card account creation
  - `addfundsrequest` — add funds / disbursement to a card
  - `addfundscertrequest` / `addfundscertmemorequest` — certificate-based fund loads
  - `updateaccountrequest` — account attribute changes (block card, reissue code, access level, etc.)
  - `secureprofileaddenda` — PII secure profile fields (DOB, SSN, drivers licence)
  - `withdrawrequest` — withdrawal transactions
- Manage reusable templates (`.Northlane` files) that define column-to-field mappings for each client
- Auto-migrate legacy `.Wirecard` template files to `.Northlane` on startup
- Support fixed values, mapped values, and addenda assignments in templates
- Generate HTML field-layout documentation for clients
- Configurable per-run settings (partner ID, program code, file password, batch password, PUID merging)

## Entities
| Entity | Description |
|---|---|
| Template | Named `.Northlane` file defining column-to-XML field mapping for a client |
| Field | XML element within a specific request segment (e.g. `<registration><firstname>`) |
| Addenda | Extensible data slots (numbered 151–170) carried as passthrough in nightly files |
| Registration | Cardholder name, address, phone, email |
| Account | Prepaid card identified by PUID / eCount DDA number |
| Payment | Funds disbursement or certificate load event |
| Settings | Per-template config stored in `*.settings` INI file (program, partner, promo, passwords) |

## Business Rules
- XML element ordering is fixed and enforced by hardcoded sort arrays (`regSort`, `fundsSort`, etc.) to comply with North Lane processor schema requirements
- Wirecard-branded files are auto-renamed to Northlane on load (migration rule)
- `secureprofileaddenda` fields (DOB, SSN, drivers licence state) require explicit field type assignment
- Amount fields may be expressed in dollars (whole) or pennies — toggle controlled by user setting
- State validation uses a hardcoded US state list including military APO codes
- PUID merging: when enabled, multiple payment rows sharing a PUID are combined into one XML request
- File and batch passwords are persisted in the `.settings` file in plaintext

## Process Flows
1. Operator selects or creates a template (field mapping)
2. Operator pastes CSV data from clipboard into the grid
3. Tool maps each column to the configured XML field using the template
4. Tool generates a validated XML file in the working directory
5. XML file is submitted externally to the eCount job service

## Compliance Relevance
- Generates XML requests containing cardholder PII (name, address, DOB, SSN, DL number) — PCI DSS / GLBA / CCPA data handling obligations apply to the generated files
- `secureprofileaddenda` fields include `federaltaxid` (SSN/TIN) and `dateofbirth` — SAD-adjacent sensitive data
- Password fields for file and batch encryption are stored in plaintext in `*.settings` files on the local filesystem

## Risks
- Passwords stored in plaintext `.settings` files — no encryption at rest
- Tool runs as a local Windows desktop app with no authentication layer beyond Windows identity check (`!lblUser.Text.Contains("INT")`)
- No audit log of what XML files were generated, by whom, or what data was included
- Operator error in column mapping could produce malformed or incorrectly assigned PII/payment data
- `.Northlane` template files and `fields.txt` field definitions are stored as unprotected local files
