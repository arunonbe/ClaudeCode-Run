# Data Architect — wirecard_nam-bank-agent_LIB

## Clone Completeness Note
Partial clone — event-persistence module (which contains Liquibase schema and JPA entities) may have missing files due to Windows long-path issue. Schema details below are inferred from batch job DTO classes and SFTP config classes.

## Data Stores
| Store | Type | Notes |
|---|---|---|
| Oracle DB | RDBMS | Primary store; ojdbc8; two-schema pattern assumed (consistent with FTC sibling) |
| H2 in-memory | RDBMS | Dev/test only (runtime dependency declared in root build.gradle) |
| Sunrise Bank SFTP | File system (remote) | ACH/wire/check files exchanged via SFTP; config prefix `sftp.srb` |
| PDS SFTP | File system (remote) | Check file exchange; `PdsSftpConfig` observed |
| Local filesystem | File system | Batch job staging directories: input, processed, failed, archive, output |
| EventHub (ActiveMQ) | Messaging | Internal event bus for CCP/platform integration |

## Inferred Schema (from DTO and batch config classes)

### ACH Inbound Direct Deposit File (NACHA format)
| Field | NACHA Record Type |
|---|---|
| FileHeaderRecord | File-level header (routing, creation date, file ID) |
| BatchHeaderRecord | Batch-level header (company name, effective date, SEC code) |
| EntryDetailRecord | Transaction entry (routing number, account number, amount, individual name) |
| BatchControlRecord | Batch-level balancing totals |
| FileControlRecord | File-level totals |
| CompanyBatch | Container for batch + entries |
| DirectDepositFile | Root container for the full NACHA file |

### ACH Origination / Drawdown Records
| Class | Purpose |
|---|---|
| `AchDrawdownRecord` | DB query result for wire drawdown file generation |
| `WireDrawdownRecord` | DB query result for wire drawdown file generation |
| `EntryDetailRecord` (achout) | Outbound origination entry detail |
| `CompanyBatchRecord` (achout) | Outbound batch record |

### Direct Deposit Reject File DTOs
| Class | Purpose |
|---|---|
| `QueryRecord` | Source DB record for reject file |
| `EntryDetailRecord` (reject) | NACHA entry for reject |
| `CompanyBatchRecord` (reject) | NACHA batch record |
| `FileHeaderRecord` / `FileControlRecord` | File envelope records |

## Sensitive Data Classification
| Field | Classification | Location |
|---|---|---|
| Bank routing number (ABA) | Sensitive financial | ACH EntryDetailRecord, wire drawdown |
| Bank account number | Sensitive financial — PCI DSS SAD-adjacent | ACH EntryDetailRecord |
| Individual name | PII | ACH EntryDetailRecord (NACHA "Individual Name" field) |
| Customer data | PII | CustomerBrandPartitioner, customer import/export jobs |
| Company name / SEC code | Financial | BatchHeaderRecord |
| Check MICR data | Sensitive financial | Check issuance file |

**Note**: ACH EntryDetailRecord contains DFI account number and routing number — these are sensitive financial identifiers governed by NACHA rules and PCI DSS scope (if prepaid card account numbers are involved).

## Encryption
- Database TLS: consistent with FTC sibling (ojdbc8, JKS truststore expected in env config)
- SFTP authentication: **private key authentication** observed (`SunriseSftpConfig.privateKey` property) — key loaded from application property at runtime
- No column-level encryption observed in available source
- SFTP `setAllowUnknownKeys(true)` in `BatchCommonChannelConfig.java:38` — **disables host key verification**, removing a key MITM protection for SFTP connections

## Data Flow
```
Sunrise Bank SFTP
  │
  ├── SFTP Download (ImportSftpDownloadTasklet / sftp-common-utilities)
  │         │
  │    Local filesystem (input dir)
  │         │
  │    Spring Batch reader/processor/writer
  │         │
  │    Oracle DB (nam-bank-agent schema)
  │         │
  │    EventHub (ActiveMQ) → CCP / platform events
  │
  ├── Spring Batch reader (Oracle DB query)
  │         │
  │    File writer (NACHA/check format)
  │         │
  │    Local filesystem (output dir)
  │         │
  │    SFTP Upload (PublishSftpUploadTasklet)
  │         │
  │    Sunrise Bank SFTP / PDS SFTP
  │
  └── Archive dir (post-upload file retention)
```

## Data Quality / Retention
- Batch jobs move files: input → processed (success) or input → failed (failure)
- Archive directory stores uploaded files post-SFTP-upload
- No database retention/purge policy visible in available source
- NACHA file balancing totals in BatchControlRecord / FileControlRecord ensure financial reconciliation
- DirectDepositFileHeaderValidator validates file header before processing

## Compliance Gaps
1. `setAllowUnknownKeys(true)` in SFTP session factory — removes host key verification, enabling MITM on SFTP connections; violates PCI DSS Requirement 4.2 (secure transmission)
2. ACH EntryDetailRecord contains bank account numbers and routing numbers — these must be encrypted at rest and in transit per NACHA Operating Rules and PCI DSS
3. Partial clone prevents full assessment of event-persistence encryption and entity-level data handling
4. No observed encryption of staging files on local filesystem (input/output/archive directories)
5. StepExceptionEmailListener may include sensitive data in exception emails
6. SFTP private key loaded from application property — key management process not auditable from source alone; must be verified in operations
