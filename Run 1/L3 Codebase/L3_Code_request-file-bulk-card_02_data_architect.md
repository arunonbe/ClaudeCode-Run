# 02 Data Architect — request-file-bulk-card

## Data Stores
| Store | Technology | Purpose |
|---|---|---|
| jobsvc SQL Server DB | Microsoft SQL Server | Job service data source (instant-issue order tracking) |
| cbase / ecount backend | cbase API (XML-RPC/SOAP) | Programme profile retrieval, member context |
| Input CSV file | Flat file (file system) | Source of location requests |
| Output request file | Flat file (file system) | Payment request file consumed by inventory/card systems |

Config properties loaded from:
- `D:/c-base/config/requestfile-bulk-card-gen/requestfile-bulk-card-gen.properties`
- `D:/c-base/config/jobsvc-ds.properties`

## Schema / Tables
Inferred from code:
- **instant_issue_order** (jobsvc DB) — updated with `request_file_id` via `updRequestFileIdInInstantIssueOrder(orderId, requestFileId)`; exact table/procedure name in `InstantIssueRequestFileBuilder` (external library `inventory-mgmt 2013.2.1`)
- Payment request file schema is defined by `PaymentRequestFile` / `RequestFileBuilder` in `requestfile-impl 1.0.2` (external library)

Input CSV columns (positional, 0-indexed):
| Index | Field | Notes |
|---|---|---|
| 0 | numberOfCards | Integer |
| 1 | firstname | PII |
| 2 | lastname | PII |
| 3 | address1 | PII |
| 4 | address2 | PII |
| 5 | city | PII |
| 6 | state | PII |
| 7 | postal | PII |
| 8 | country | Optional; defaults to "US" |
| 9 | remark | Optional |
| 10 | locationCode | Optional |

## Sensitive Data
| Data Element | Classification | Risk |
|---|---|---|
| First name, last name | PII (GLBA/CCPA) | In input file and output request file |
| Address (street, city, state, postal) | PII | In input file and output request file |
| memberId (operator) | Internal | CLI arg; not logged with masking |
| jobsvc DB password | Credential | Plain-text in properties file |

No PAN, CVV, or card track data in the input schema.

## Encryption
- No application-level encryption of the input or output CSV/request files
- `DriverManagerDataSource` used for JDBC (no connection pool); no SSL/TLS enforcement visible in the JDBC URL configuration
- Properties files with credentials stored unencrypted on the Windows file system (`D:/c-base/config/`)
- File system security relies entirely on OS-level ACLs

## Data Flow
```
Input CSV (file system)
  --> RequestfileBulkCardGenClient.processFile()
      --> DelimitedRecordParser --> InstantIssueLocationRequest list
      --> AppProgramInstantIssueProfileClass.retrieve() (cbase API)
      --> AppProgramUserManagementProfileClass.retrieve() (cbase API)
      --> InstantIssueRequestFileBuilder.buildPaymentRequestFile()
          --> PaymentRequestFile.constructRequestFile()
              --> Output request file (file system)
      --> InstantIssueRequestFileBuilder.updRequestFileIdInInstantIssueOrder()
          --> jobsvc SQL Server DB (order update)
```

## Quality / Retention
- No input file validation beyond field-count and integer parsing; bad data causes `RuntimeException`
- No output file integrity check (hash/checksum)
- No retention policy for input or output files; dependent on OS-level file management
- No duplicate-request detection (same input file could be reprocessed if `request_file_id` env var is not set)

## Compliance Gaps
- PII (name, address) in flat files without encryption at rest — GLBA / CCPA / PCI DSS Req. 3 gap
- DB credentials in plain-text properties file — PCI DSS Req. 8 gap
- No audit trail of which operator ran the job and what output file was produced (only Log4j file logging)
- No data-lineage controls; output file can be freely copied or forwarded without tracking
