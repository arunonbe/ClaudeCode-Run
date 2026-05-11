# DS_DP_db04 — Solution Architect Report

## Critical Flags

### FLAG-01: BioCatch Behavioral Biometrics — CCPA Special Category
- **Severity:** HIGH
- **Regulation:** CCPA Section 1798.140(b) — "Biometric information" is sensitive personal information
- **Evidence:** `20230215_DB04_create_table_biocatch_api_audit.sql`, column `data_points varchar(8000)` and `risk_factors nvarchar(3500)` and `genuine_factors nvarchar(500)`
- **Risk:** If California cardholders' behavioral biometric data is stored in this table, Onbe must: (1) disclose collection in privacy notice; (2) honor deletion requests; (3) not sell/share without opt-in consent
- **Additional risk:** `data_points` varchar(8000) with no visible encryption stores potentially large behavioral fingerprint payloads
- **Remediation:** Privacy legal review; data minimization; retention policy; encryption-at-rest for biometric fields
- **Priority:** P0 — Legal/Compliance immediate review required

### FLAG-02: Invalid Date Prefixes in 2023 Scripts
- **Severity:** MEDIUM (operational)
- **Evidence:** Multiple 2023 scripts have impossible date values:
  - `20231505_` — month 15 (impossible)
  - `20231610_` — month 16
  - `20232009_` — month 20
  - `20232108_` — month 21
  - `20232407_` — month 24
  - `20232804_` — month 28
  - `20232806_` — month 28
  - `20233005_` — month 30
- **Root cause:** Day and month appear transposed (YYYYDDMM instead of YYYYMMDD). For example `20232009` = 2023, day 20, month 09 (September 20, 2023 = `20230920`)
- **Risk:** Lexicographic sort of filenames produces incorrect chronological ordering; incident response replay would execute scripts in wrong order
- **Remediation:** Rename all affected files to correct ISO 8601 format
- **Priority:** P2

### FLAG-03: Dynamic SQL in Partition Migration — Execute-as-String Pattern
- **Severity:** MEDIUM
- **Evidence:** `20191018_NAMDATASVC-1388_02-Partition_security_audit_device_user_data.sql`, lines 40–44:
  `EXEC (@SQL)` with `@sql VARCHAR(MAX)` constructed from `sys.indexes` catalog data
- **Context:** While the input is from a system catalog (not user-supplied), establishing this pattern in DBA scripts normalizes dynamic SQL execution
- **Remediation:** Document all occurrences; ensure no expansion of this pattern to user-supplied inputs
- **Priority:** P3

---

## Technical Debt Inventory

### TD-01: No Cleanup Job for `biocatch_api_audit`
- Table created February 2023 with no retention/cleanup job
- Unbounded growth on a varchar(8000) data_points column
- Priority: P1

### TD-02: No Copy Tag Rollback Mechanism
- Content changes (UPDATE on copy tag tables) have no reversal scripts
- Manual DBA action required for any production content rollback
- Priority: P2

### TD-03: xcontent Re-deployments Without Idempotency
- Multiple scripts for the same xcontent version (e.g., 1.0.24 deployed 4 times) suggest non-idempotent deployments
- Scripts may fail or create duplicate records if re-run
- Priority: P2

### TD-04: QA/Production Role Conflict
- DB04 hosts both production `cbaseapp` content and QA `EcountCore` processing
- Production content and QA workloads share instance resources (tempdb, max server memory, etc.)
- Priority: P1

### TD-05: Incomplete Partition Lifecycle
- Partition addition scripts are present (`01-CbaseappAddPartitions.sql`) but no partition archival/switch-out scripts visible
- Old monthly partitions may never be archived/removed, leading to unbounded partition growth
- Priority: P2

### TD-06: Loose Change Management for Content Scripts (2022–2023)
- ~100 content scripts lack consistent ticket references
- Does not satisfy PCI DSS Req 6.5 (change management documentation)
- Priority: P1

### TD-07: `PS_TECHAPI` User Permissions Not Reviewed
- `20210423-NATS-11158_Create_PS_TECHAPI_user_permissions.sql` creates a technical API user
- Permissions granted not visible in repository (script creates user, actual grant may be in another file)
- Principle of least privilege compliance unknown
- Priority: P2

---

## Complete Object Inventory

### `cbaseapp` Database
| Object | Type | Purpose |
|---|---|---|
| `dbo.security_audit_device_user_data` | Table (partitioned) | Cardholder device audit log — monthly partitions |
| `dbo.security_audit_device_user_data_switch` | Table | Partition switch staging |
| `dbo.cbaseapp_process_partition_control` | Table | Partition management metadata (online_months, process_order, enabled) |
| `cbaseapp_process_monthly_partition` | Partition Function | Monthly boundary partition function |
| `cbaseapp_process_monthly_scheme` | Partition Scheme | Maps monthly partition to [PRIMARY] filegroup |
| `dbo.biocatch_api_audit` | Table | BioCatch behavioral biometrics scoring log |
| `dbo.insert_biocatch_api_response` | Stored Procedure | Inserts BioCatch API response into audit table |
| `dbo.inquiry_types_category` | Table | CSA inquiry category reference |
| `dbo.Inquiry_types` | Table | CSA inquiry type reference |
| `dbo.inquiry_type_activity_xref` | Table | Inquiry-to-activity mapping |
| `dbo.security_role` | Table | Portal security role registry (ROLE_FILE_VIEW added SQ-1111) |
| `dbo.affiliate_fieldname` | Table | Affiliate portal field name configuration |
| `dbo.affiliate_field_lookup` | Table | Affiliate portal field value lookup |
| Copy tag tables (unnamed) | Tables | UI localized text strings (high-volume inserts/updates) |
| Skin/template tables (unnamed) | Tables | Brand visual theme definitions |
| Notification template tables (unnamed) | Tables | US + Canada notification message templates |
| `dbo.op_message` (inferred) | Table | OnePortal login message content |

### `master` Database (shared with all nodes)
| Object | Type | Purpose |
|---|---|---|
| `IndexOptimize_AgentWrapper` | Stored Procedure | Time-aware index maintenance wrapper |
| `TR_check_ip_address_functional_user` | Server Trigger | IP-based logon access control |

### `msdb` Database (SQL Agent)
| Object | Type | Purpose |
|---|---|---|
| `DBMP User Databases -- Index and stats reorg (custom)` | Job | Daily index maintenance |
| `DBMP User Databases -- Integrity Check (custom)` | Job | Weekly integrity check |
| Various disabled legacy jobs | Jobs | Disabled by NAMDATASVC-1879 (Feb 2020) |

---

## Schema Consistency vs. Other DS_DP Nodes

| Schema element | DB01 | DB02 | DB04 | DB05 | DB06 | DB07 |
|---|---|---|---|---|---|---|
| Monthly partition scheme | No | No | YES (cbaseapp) | No | No | No |
| Security audit trigger (master) | YES | YES | YES | YES | YES | YES |
| IndexOptimize_AgentWrapper | YES (implied) | YES | YES | YES | YES | No |
| EcountCore databases | No | YES (primary) | YES (QA proxy) | Unknown | Yes (ecountcore_ss) | No |
| `cbaseapp` database | No | No | YES (primary) | No | No | No |

DB04 is unique among the six nodes in hosting `cbaseapp` as a primary production database. No other node in this analysis set contains `cbaseapp` scripts.

---

## Remediation Priority Matrix

| Priority | Item | Effort | Compliance Impact |
|---|---|---|---|
| P0 | CCPA review of BioCatch biometrics data | HIGH | Privacy/Legal |
| P1 | Add cleanup job for biocatch_api_audit | LOW | Data hygiene |
| P1 | Separate QA from production instance | HIGH | Operational risk |
| P1 | Enforce change management tickets for content scripts | LOW | PCI Req 6.5 |
| P2 | Fix invalid date prefixes in 2023 scripts | LOW | Operational |
| P2 | Implement copy tag rollback mechanism | MEDIUM | Business continuity |
| P2 | Complete partition lifecycle (add archival/switch-out) | MEDIUM | Storage management |
| P3 | Document dynamic SQL pattern from partition migration | LOW | Code quality |
