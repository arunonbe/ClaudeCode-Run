# DS_DP_db01 — Business Analyst Report

## Repository Overview

**Repo name:** DS_DP_db01  
**Server instance (inferred):** P-DB01 / C-DB01 (Production / Cold-standby pair)  
**Path evidence:** `G:\MSSQL11.DB01\MSSQL\Data\` (file `20200124_NAMDATASVC-1454_C-DB01 add tempdb files.sql`, line 3)  
**Active date range of change scripts:** October 2019 – December 2020  
**Branching model:** Single `master` branch only

---

## Business Purpose

DB01 is one of the numbered Data Processing database server nodes in the Onbe (formerly Wirecard/NorthLane) prepaid card platform. The scripts in this repository do **not** create application databases from scratch. Instead they represent a series of operational change scripts applied to a pre-existing SQL Server instance that already hosts the following logical databases:

| Database name | Business role observed in scripts |
|---|---|
| `Repositorysvc` | Repository file service — stores card-program documents, uploaded files, enrollment assets |
| `Repositorysvc_rollback` | Archive/rollback shadow of Repositorysvc |
| `Jobsvc` | Job / task scheduling service database |
| `Ordersvc` | Order management service database |
| `DBAdmin` | Instance-level administration and security audit database |
| `master` (SQL Server system) | Server-level trigger and configuration |

The primary business operations visible in DB01 change scripts are:

1. **Repository file lifecycle management** — Archiving and pruning old records from the `Repositorysvc` file tables (files created before August 2019 were systematically archived to `Repositorysvc_rollback` in October–December 2019 via NATS-5942, NATS-6026). This is a data retention and performance housekeeping operation applicable to card program documents (enrollment forms, uploaded identification documents, etc.).

2. **ACH transfer data correction** — A targeted one-row update (`20191210_NATS-6125_update_ach_transfer_detail.sql`) that resets a failed ACH transfer record (`id = 199660523`) in the `ach_transfer_detail` table back to status_code=1. This indicates DB01 hosts or has cross-database access to an ACH funds movement processing table, making it directly relevant to **NACHA compliance** (Reg E and NACHA Operating Rules for ACH entries).

3. **Instance-level IP access control** — The `TR_check_ip_address_functional_user` server-level logon trigger (WDNAMCBTS-517, 2020) blocks functional user logins originating from non-approved IP addresses. This is a CDE network access control directly relevant to **PCI DSS Requirement 7** (restrict access) and **Requirement 8** (identify and authenticate access).

4. **Auditor access provisioning and deprovisioning** — NAMDATASVC-2399 and SQ-261 grant/revoke `db_datareader` access on `jobsvc` and `ordersvc` to `NAM\BakerTilly_Auditors`. BakerTilly is a known third-party audit firm. These scripts represent the formal audit access lifecycle, relevant to **PCI DSS Requirement 12.3** and SOC 2 Type II evidence.

5. **SQL Agent job maintenance** — Agent operator email addresses were updated from wirecard.com domain to northlane.com domain (SQ-1114, November 2020), reflecting the corporate rebranding from Wirecard to NorthLane/Onbe. Job alerts go to `DataServicesGroup-Operator`.

---

## Data Stored on DB01

Based on cross-database references in the scripts, DB01 hosts or accesses:

- **`repo_file`** — file metadata records; fields include `file_id` (GUID), `file_name`, `file_version_number`, `file_type_id`, `program_id`, `submission_channel_id`, `encryption_code`
- **`repo_file_attributes`** — attribute key-value pairs on repository files (potential cardholder document metadata)
- **`repo_file_audit`** — audit trail of file actions (member, action_code, date, host)
- **`ach_transfer_detail`** — ACH transfer rows with `status_code`, `transfer_id`, `result_code`, `result_message` — **NACHA-regulated data**
- **`Audit_blocked_ip_user`** (DBAdmin schema) — security audit log of blocked login attempts (IP_Address, Host_Name, Original_Login, Program_Name)
- **`ValidIPAddress`** / **`usernames_functional_accounts`** (master schema, referenced in trigger) — IP allowlist and functional account registry

---

## Regulatory Relevance

| Regulation | Relevance | Evidence |
|---|---|---|
| PCI DSS v4.0.1 Req 7 | Access control to CDE | IP allowlist trigger (`WDNAMCBTS-517_002`, line 14–63) |
| PCI DSS v4.0.1 Req 8 | Logon authentication controls | Server-level trigger with ROLLBACK on invalid IP |
| PCI DSS v4.0.1 Req 10 | Audit logging | `Audit_blocked_ip_user` table + cleanup job; `repo_file_audit` |
| PCI DSS v4.0.1 Req 12.3 | Third-party access | BakerTilly auditor grant/revoke pattern |
| NACHA / Reg E | ACH entry data corrections | `ach_transfer_detail` update script |
| GLBA | Non-public financial data in repository | Enrollment files in `Repositorysvc` |

---

## Key Business Process Events (Chronological)

| Date | Ticket | Business event |
|---|---|---|
| 2019-11-22 | NATS-5942 | Repo file archival (pre-Aug 2019 records purged) |
| 2019-12-03 | NATS-6026 | Final repo cleanup with rollback safety |
| 2019-12-10 | NATS-6125 | ACH transfer detail status reset |
| 2019-12-30 | NAMDATASVC-1642 | Automated weekly pruning job deployed |
| 2020-01-24 | NAMDATASVC-1454 | TempDB expanded to 8 files (performance) |
| 2020-08-13 | NAMDATASVC-2399 | BakerTilly audit access granted |
| 2020-08-21 | WDNAMCBTS-343 | Dev user (NAM\nikhil.sapre) VIEW ANY DEFINITION granted |
| 2020-09-17 | WDNAMCBTS-517 | IP-based logon security trigger deployed |
| 2020-11-13 | SQ-1114 | Email domain migrated wirecard.com → northlane.com |
| 2020-12-01 | SQ-261/SQ-1448 | Audit access revoked; developer access revoked |

---

## Summary Assessment

DB01 is a **general-purpose application node** hosting the Repositorysvc document management database and the Ordersvc/Jobsvc microservice databases. It participates in both the **cardholder data environment** (through repository files that may contain KYC/enrollment documents) and the **ACH processing chain** (ach_transfer_detail). The change history is sparse compared to DB02 and DB04 — only 13 scripts spanning 14 months — suggesting it is a lower-churn node, potentially serving a limited set of programs or acting as a supplementary node in the DB02/DB04 cluster.
