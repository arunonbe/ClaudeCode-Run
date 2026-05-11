# DS_DB_jobsvc — Enterprise Architect Report

## 1. Platform Generation Assessment

`DS_DB_jobsvc` is a **Generation 2 (Core Platform)** database. It bridges the legacy batch file processing world (client partner files via SFTP) with the modern microservices payment platform. The SQL Server 2012 target places it in Onbe's second generation of platform services, newer than GP (SQL 2008) but older than the NexPay microservices (SQL 2016+).

The Quartz 1.x scheduler schema embedded in this database is particularly significant — it indicates the Java batch processing layer was built using Spring/Quartz infrastructure from the mid-2000s to early-2010s era, and has not been migrated to modern scheduling frameworks.

## 2. Role in Onbe's Architecture

`DS_DB_jobsvc` is the **central operational hub** for Onbe's batch disbursement platform:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    BATCH DISBURSEMENT PIPELINE                       │
├─────────────────┬───────────────────────────────────────────────────┤
│  FILE INGESTION │  JOB ORCHESTRATION         │  PAYMENT EXECUTION  │
│                 │                            │                     │
│  Client SFTP    │  DS_DB_jobsvc              │  EcountCore         │
│  Partner Files  │  ├── job_file              │  ├── card issuance  │
│       ↓         │  ├── job_record            │  ├── fund loading   │
│  autofile_job   │  ├── job_action_*          │  └── registration   │
│       ↓         │  ├── work_instance         │                     │
│  job_file       │  ├── QRTZ_*               │  DS_DB_ordersvc     │
│                 │  └── instant_issue_*       │  └── order tracking │
└─────────────────┴────────────────────────────┴─────────────────────┘
```

No other database in the Onbe platform has this breadth of dependency — jobsvc is consumed by:
- The Spring Batch / Quartz job service (`jobservice_SVC`)
- The batch library (`batch_LIB`)
- The job scheduler service (`job-scheduler_SVC`)
- The job service integration libraries (`jobservice-integration_LIB`, `jobserviceintegration_LIB`)
- The ecore batch library (`ecore-batch_LIB`)

## 3. Upstream and Downstream Dependencies

### 3.1 Upstream
| System | Data Flow | Notes |
|--------|-----------|-------|
| Client partners (SFTP) | Raw instruction files | Files land in `job_file`, rows in `job_record` |
| `DS_DB_ordersvc` | Order creation triggers job actions | Order status drives job processing |
| `autofile_SVC` | Automated file routing | Feeds `autofile_job` table |
| Scheduler (`job-scheduler_SVC`) | Quartz trigger management | Writes to `QRTZ_*` tables |

### 3.2 Downstream
| System | Data Flow | Notes |
|--------|-----------|-------|
| EcountCore (`ecountcore` DB) | Card operations execution | Job actions drive ecount card/account operations |
| `DS_DB_notificationsvc` | Notification dispatch | `job_action_send_notification` triggers |
| `DS_DB_nexpay_claimable` | Claimable payment tokens | `claim_code` in `job_action_add_funds` |
| Strongbox vault | Secure field storage | `field_secure_ref` in `job_action_memo_secure` |
| ACH payment rail | ACH disbursements | `ach_transfer_detail` tracks ACH events |
| GP databases | Financial accounting | ETL extracts job totals to GP journals |

## 4. Critical Architecture Observations

### 4.1 PAN Storage — CDE Scope Concern
The `instant_issue_card.card_number` column (CHAR(16)) is the most architecturally significant finding in this database. If this column contains full PANs:
- jobsvc database becomes PCI CDE in-scope
- All connected systems must be assessed for network segmentation
- Access controls, encryption, key management, and monitoring must meet PCI DSS Level 1 requirements
- The `jobservice_SVC` application tier becomes a CDE-connected component

**Architecture action**: If card numbers are needed for instant issue workflows, they should be stored as:
1. Tokens (referenced to a PCI-compliant vault such as the Onbe Strongbox)
2. Truncated values (first 6 / last 4 only)
3. Encrypted using AES-256 with key management separate from data

### 4.2 Quartz 1.x End-of-Life
The presence of Quartz 1.x-era table columns (`IS_VOLATILE`, `IS_STATEFUL`) in `QRTZ_JOB_DETAILS` indicates a very old scheduler runtime. Quartz 1.x was replaced by Quartz 2.x around 2011–2012. The implications:
- Security vulnerabilities in the Quartz library may not be patched
- Java serialisation in `QRTZ_JOB_DETAILS.JOB_DATA` (IMAGE type) is a deserialization attack surface
- Modern replacements (Spring Batch with `spring-batch-metadata` tables, Quartz 2.x, or Spring Scheduler) should be evaluated

### 4.3 `zzz_` Table Legacy Layer
Six deprecated `zzz_` prefixed tables exist in the schema:
- `zzz_job_work_item`, `zzz_work_instance_log_old`, `zzz_work_item`, `zzz_work_item_history`, `zzz_work_item_state`, `zzz_work_item_state_machine`, `zzz_work_item_type`

These represent a previous generation of the work orchestration model (work_item-based) that was superseded by the current `work_instance`/`work_process` model. They should be archived and removed.

### 4.4 Spring Batch Metadata Integration
While the database does not contain Spring Batch's standard `BATCH_JOB_INSTANCE`, `BATCH_JOB_EXECUTION`, `BATCH_STEP_EXECUTION` tables, the `work_instance`, `work_process`, and `work_process_step` tables serve an equivalent function for Onbe's custom batch framework. The ACH transfer tracking in `ach_transfer_detail` is a domain-specific batch metadata pattern.

## 5. Integration Architecture

### 5.1 Strongbox Vault Integration
`job_action_memo_secure.field_secure_ref` stores a reference token (VARCHAR(40)) pointing to a value stored in the Onbe Strongbox vault (`DS_DB_strongbox` / `strongbox-lib_LIB`). This is the tokenisation mechanism for sensitive data that would otherwise be stored in action memos. The vault integration is architecturally sound but requires:
- Vault availability for job execution (availability dependency)
- Token rotation policy documentation
- Vault access monitoring

### 5.2 CDC Tables
Six `CDC_*_bk` tables present in the Tables folder are backup snapshots of SQL Server CDC system tables (change tracking) taken at a point in time. This indicates CDC was enabled on the database at some point (possibly for migration or auditing) and these snapshots were preserved. This is not a concern but should be cleaned up.

## 6. Migration Complexity

### 6.1 Complexity Score: HIGH

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| Schema size | 3/5 | ~155 tables, 287 SPs — manageable |
| PCI scope | 5/5 | Potential PAN in instant_issue_card |
| Integration surface | 5/5 | Central hub — connected to all major platform services |
| Quartz dependency | 4/5 | Embedded scheduler; migration requires app changes |
| PII sensitivity | 4/5 | Cardholder names, emails, phones in job_action tables |
| Business criticality | 5/5 | All batch disbursements depend on this database |

### 6.2 Migration Path Considerations
1. **PAN remediation must precede** any other migration work — determine card_number content and implement tokenisation.
2. Quartz migration requires coordination with `jobservice_SVC` Java application team.
3. `zzz_` tables can be safely dropped after confirming no active queries reference them.
4. CDC backup tables (`CDC_*_bk`) can be safely dropped after confirming they are reference-only.

## 7. Regulatory Architecture Position

jobsvc sits at the intersection of:
- **PCI DSS**: Potential CDE scope (card_number)
- **NACHA / Reg E**: ACH transfer tracking (ach_transfer_detail)
- **TCPA**: Phone number storage for notification targeting
- **GLBA**: Cardholder PII (name, email, address, phone)
- **OFAC**: `recipient_screening_status` in `job_action_register_user` suggests AML/OFAC screening results are stored — a compliance-critical field

The OFAC screening status (`recipient_screening_status`) is particularly important: this field links the cardholder registration action to the AML screening outcome. If populated with "BLOCKED" or similar, the action should not complete. Auditors will look for this control's effectiveness in SOC 2 and OFAC compliance reviews.
