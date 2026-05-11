# Data Architect View — xml-converter_LIB

## Data Stores
| Store | Type | Location | Description |
|---|---|---|---|
| `*.Northlane` files | Flat text | Local filesystem (working directory) | Column-to-field mapping templates |
| `*.settings` files | INI flat text | Local filesystem (working directory) | Per-template config including passwords |
| `fields.txt` | Flat text | Local filesystem (working directory) | Master field definitions (parent, name, type, length, required) |
| `compare.txt` | Flat text (generated) | Local filesystem (working directory) | Intermediate comparison file built at runtime |
| `settings.ini` | INI flat text | Local filesystem (working directory) | User UI preferences (window state, directory, format options) |
| Generated XML files | XML | Local filesystem (working directory) | Output request files submitted to job service |

## Schema / Field Definitions
Fields are defined in `fields.txt` as pipe-delimited records:
`parent | field_name | original_name | char_count | friendly_name | required | type`

Key XML segments and their PII/sensitive fields:
| Segment | Sensitive Fields |
|---|---|
| `registration` | firstname, lastname, middlename, suffixname, email, address1, address2, city, state, postal, country, homephone, businessphone, mobilephone |
| `secureprofileaddenda` | federaltaxid (SSN/TIN), dateofbirth, driverslicensenumber, driverslicensestate |
| `createaccountrequest` | notificationcode, accesslevel, plasticonly, onlineregistrationrequired |
| `addfundsrequest` | amount, taxableflag, partnerpaymentid, directclaimflag |
| `updateaccountrequest` | newpartneruserid, reissuecode, blockcard, cardactivation |
| `withdrawrequest` | amount, withdrawtype, primarypayeename, secondarypayeename |

## Sensitive Data Inventory
| Data Element | Classification | Location |
|---|---|---|
| Social Security Number / Federal Tax ID | PII / potential SAD-adjacent | `secureprofileaddenda` XML element; present in generated XML output files |
| Date of Birth | PII | `secureprofileaddenda` XML element |
| Driver's Licence Number and State | PII | `secureprofileaddenda` XML element |
| Cardholder full name | PII | `registration` XML element |
| Full address | PII | `registration` XML element |
| Phone numbers | PII | `registration` XML element |
| Email address | PII | `registration` XML element |
| File password / Batch password | Credential | `*.settings` plaintext file |
| Amount | Financial | `addfundsrequest` / `withdrawrequest` XML element |

## Encryption
- No encryption of data at rest is applied by this tool to generated XML files or template files
- File passwords and batch passwords stored in `*.settings` are plaintext — they likely represent PGP or similar encryption keys used downstream when transferring the generated file, but they are not protected locally
- No TLS or transport security is applied within this tool (desktop app; no network calls)

## Data Flow
```
Clipboard CSV data
      |
      v
WinForms Grid (in-memory)
      |
      v
Template mapping (*.Northlane)
      |
      v
XML generation (FormMain.cs)
      |
      v
*.xml output file (local filesystem)
      |
      v
[External] Job Service submission (out of scope for this repo)
```

## Data Quality and Retention
- No input validation beyond field-type and character-count enforcement at template definition time
- No retention policy — generated XML files persist indefinitely on the local operator workstation
- No data lineage or audit trail; no record of which operator generated which file

## Compliance Gaps
- Generated files containing SSN (`federaltaxid`) and DOB are unencrypted at rest on operator workstations — violates PCI DSS Req 3 (protect stored account data) and GLBA Safeguards Rule
- No access controls on generated files or template definitions beyond OS-level file system permissions
- No data masking applied to sensitive fields within the tool UI or generated output
- No log of data processed — hampers CCPA right-of-access and GDPR audit requirements
