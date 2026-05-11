# DS_DP_db04 — Enterprise Architect Report

## Platform Role

DB04 is the **portal content management and cardholder session security** node in the DS_DP cluster. It has a dual role:

1. **Production portal content server** — The `cbaseapp` database powers the cardholder-facing portal (ClientZone / OnePortal) with all UI content, brand skins, notification templates, and customer service configuration
2. **QA proxy for card processing** — DB04 hosts a QA instance of EcountCore/EcountCore_Process, functioning as the development/QA counterpart of DB02's production processing

---

## Technology Stack

| Attribute | Value |
|---|---|
| Database engine | Microsoft SQL Server (named instance, port 2232) |
| Instance name pattern | `P-DB04` (production), `q-db04.nam.wirecard.sys\db04,2232` (QA) |
| Maintenance framework | Ola Hallengren SQL Server Maintenance Solution (deployed Dec 2019) |
| Partition scheme | `cbaseapp_process_monthly_scheme` — monthly partitioning for security audit data |
| BioCatch integration | External behavioral biometrics API (2023 addition) |
| xcontent system | Content versioning system v1.0.12–1.0.35+ |

---

## Architectural Position

```
┌─────────────────────────────────────────────────────────┐
│                DB04 Architecture Role                    │
│                                                         │
│  Cardholder     ──►  Portal UI  ──►  cbaseapp           │
│  Browser                           (copy tags, skins)   │
│                                                         │
│  CSA Agent      ──►  CSA Tool  ──►  cbaseapp            │
│                                    (inquiry types,      │
│                                     security roles)     │
│                                                         │
│  Cardholder     ──►  Login Session  ──►  cbaseapp       │
│  Login                              security_audit_     │
│                                     device_user_data    │
│                                                         │
│  BioCatch API   ──►  Fraud Score  ──►  biocatch_        │
│                                        api_audit        │
│                                                         │
│  xcontent CMS   ──►  Brand Skins  ──►  Skin tables      │
│                                                         │
│  QA Team        ──►  EcountCore QA  ──►  EcountCore     │
│                      (q-db04 proxy)                     │
└─────────────────────────────────────────────────────────┘
```

---

## Dependencies

### Upstream (writes to DB04)
- **Portal application servers** — Write cardholder session events to `security_audit_device_user_data`
- **BioCatch API** — External behavioral biometrics scores written via `insert_biocatch_api_response` SP
- **Content management team** — Copy tag and skin deployments via manual SQL scripts
- **Notification service** — Template configuration

### Downstream (DB04 feeds)
- **Cardholder portal** — Reads copy tags, skins, notification templates from `cbaseapp`
- **CSA application** — Reads inquiry type configuration from `cbaseapp`
- **QA environment** — EcountCore QA data used by development teams

---

## Unique Architectural Features

### Monthly Partition Maintenance Pattern
DB04's `cbaseapp_process_monthly_partition` is the only place in the DS_DP repositories where a **full partition lifecycle with a control table** is documented:
- `cbaseapp_process_partition_control.online_months` controls how many months of partitions to maintain
- The partition addition script dynamically computes boundary values
- The switch table (`security_audit_device_user_data_switch`) enables partition switching

This is architecturally superior to DB02's simpler compression-only approach and provides a template for the broader platform's data lifecycle management.

### BioCatch Integration (2023)
The addition of behavioral biometrics scoring in 2023 represents the platform's investment in **behavioral fraud prevention**. Key architectural observations:
- `biocatch_api_audit` is in `cbaseapp` — not in a dedicated fraud database
- The stored procedure `insert_biocatch_api_response` uses simple parameterized inserts (no dynamic SQL)
- `data_points` (varchar 8000) stores a large payload — likely JSON or pipe-delimited BioCatch output
- No encryption of the `data_points` field is observed

### xcontent as a Content Delivery System
The xcontent versioning system (v1.0.12 → v1.0.35+) represents a structured approach to portal white-labeling. The `createskin_cbaseapp` scripts create new skin records for each client brand. With 50+ client programs visible in the copy tags, DB04 effectively manages a **multi-tenant content delivery system** within a single SQL Server database.

---

## Migration Complexity

| Factor | Assessment |
|---|---|
| Schema complexity | MEDIUM — `cbaseapp` content tables + partition scheme |
| QA proxy dual role | HIGH — Cannot migrate production and QA independently |
| Content volume | HIGH — 100+ xcontent versions, thousands of copy tags |
| BioCatch integration | MEDIUM — External API dependency requires parallel migration |
| Downstream portal coupling | HIGH — Any cbaseapp schema change breaks the live portal |
| Partition migration | MEDIUM — Monthly scheme requires careful cutover |

---

## Corporate Transition Evidence

DB04 shows clear evidence of the Wirecard → NorthLane → Onbe transition:
- November 2020 (`SQ-234`): `20201104_SQ-234_payday_update_database_copytags_for_wirecard.sql` — updated copy tags to remove Wirecard branding for the Payday program
- November 2020 (`SQ-1114`): Email domain migration to northlane.com
- xcontent v1.0.12+ (Nov 2021 onward): Likely reflects new Onbe-era brand templates

The xcontent version 1.0.12 appearing in November 2021 — 9 months after the Wirecard acquisition — suggests the content management platform was also re-platformed during this period.

---

## Strategic Recommendations

1. **Separate QA and production roles** — DB04 serving both production portal content and QA card processing creates operational and compliance risk. Dedicated QA infrastructure should be provisioned.
2. **Automate xcontent deployments** — The 30+ manual skin deployment scripts should be replaced with a CI/CD pipeline that deploys xcontent skins from a version-controlled content repository.
3. **Audit `biocatch_api_audit`** — Review data minimization, retention policy, and encryption for behavioral biometric data (CCPA compliance).
4. **Standardize date prefix format** — Multiple scripts with invalid date prefixes (month 15–24) create operational sorting issues.
5. **Implement copy tag change tracking** — Current model has no rollback mechanism for content changes; consider maintaining a `_previous` value column or a separate change log table.
