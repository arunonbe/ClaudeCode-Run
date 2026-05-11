# Data Architect Report — GP-RSM-Customization

## 1. Repository Content

The `GP-RSM-Customization` repository contains only a `README.md` file. No source code, schema definitions, configuration files, or data models are present. All data architecture analysis in this document is inferred from:

- The repository README: "East Campus Dynamics GP .NET GP Addin. Originally in Dex, converted to .NET by Crestwood"
- The Dynamics GP RSM (Report Scheduler Manager) product documentation
- Data schemas observed in the sibling repository `finance-webservice_API`
- Standard GP Add-in patterns for the Microsoft Dynamics GP 2010–2018 era

---

## 2. Data Sources (Inferred)

A GP RSM customization typically reads from and writes to the following Dynamics GP databases:

### 2.1 GP Company Database (e.g., `ECNT`, `ECAN`, `EMXN`)

Based on the multi-entity routing observed in `finance-webservice_API` (`GPDBHelper.cs`), the GP company databases are named by 4-character BIN prefix codes:
- `ECNT` — eCount North America (US entity)
- `ECAN` — eCount Canada
- `EMXN` — eCount Mexico

Relevant tables a GP RSM add-in would access:

| Table | Description |
|---|---|
| `SOP10100` / `SOP10200` | Sales Order Processing (SOP) header and line detail — sales transactions created by `finance-webservice_API` |
| `GL10000` / `GL20000` | General Ledger transaction work and history |
| `SY60500` | Report List (RSM report catalogue) |
| `SY60100` | Report Scheduler schedules |
| `SY60200` | Report Scheduler destinations (email recipients, file paths) |
| `SY60300` | Report Scheduler filter settings |
| `GL40200` | Chart of Accounts |
| `RM00101` / `RM20101` | Receivables master and transaction history |

### 2.2 GP System Database (`DYNAMICS`)

The GP DYNAMICS database stores cross-company configuration:

| Table | Description |
|---|---|
| `SY01500` | Company master (lists all company databases including `ECNT`, `ECAN`, `EMXN`) |
| `SY03300` | User security settings |
| `SY40500` | GP add-in registration |

### 2.3 Audit Database (`so.FWSAuditTable`)

The `finance-webservice_API` repository (`AuditDBHelper.cs`) uses a stored procedure `so.FWSAuditTable` in a shared audit database. RSM reports may join against this audit trail to produce reconciliation reports correlating GP transactions with the `finance-webservice_API` transaction lifecycle.

---

## 3. Data Entities (Inferred)

### 3.1 Report Schedule Entity

A GP RSM customization would work with report schedule entities containing:

| Field | Description |
|---|---|
| Schedule ID | Unique identifier for the report schedule |
| Report Name | GP report ID from `SY60500` |
| Frequency | Daily / Weekly / Monthly / Period-end |
| Company | Entity code (`ECNT`, `ECAN`, `EMXN`) |
| Distribution | Email recipients, network path, or printer |
| Filter Criteria | Date range, GL account range, BIN range |
| Last Run Time | Timestamp of last successful execution |
| Status | Active / Inactive / Error |

### 3.2 Report Output Artifacts

RSM reports generate output artifacts that may be subject to data governance:

| Output Type | Sensitivity | Retention |
|---|---|---|
| PDF financial summaries | HIGH — revenue figures | SOX: 7 years |
| Excel reconciliation sheets | HIGH — transaction-level data | SOX: 7 years |
| CSV export feeds | MEDIUM — aggregated program data | Business: 1 year |
| Email distributions | HIGH — sent to finance team | Email retention policy |

---

## 4. Sensitive Data Assessment

### 4.1 Financial Data in Reports

GP RSM reports generated for Onbe finance operations would contain:

- **Program-level revenue figures**: Revenue from prepaid card fee income, disbursement fees, FX conversion margins
- **Settlement totals**: Daily and period-end settlement figures by card network and program
- **Reconciliation data**: GP journal entries reconciling with external settlement files
- **Cardholder program data**: Aggregated (not individual) cardholder metrics by BIN range

This data is sensitive under:
- **SOX**: Revenue recognition and period-end close data; must be accurate and complete
- **GLBA**: Financial institution data subject to Safeguards Rule
- **CCPA/GDPR**: If reports include any cardholder-linked data, privacy obligations apply

### 4.2 Distribution Risk

Email-distributed financial reports represent a data loss vector. A misconfigured distribution list in the RSM customization could result in sensitive financial data being sent to unintended recipients. Without access to the source code, it is impossible to audit the current distribution configuration.

### 4.3 Absence of Source Code Governance

The lack of source code in the repository means:
- No code review process exists for changes to report distribution logic
- No audit trail for modifications to report filter criteria (e.g., which accounts are included/excluded from reports)
- PCI DSS Requirement 6.4 (change management) and SOX ITGC change management controls cannot be satisfied for this component

---

## 5. Data Flow (Inferred)

```
[GP Company DB (ECNT/ECAN/EMXN)]
    |
    | SQL queries via GP Add-in / Dexterity bridge
    v
[GP RSM Engine]
    |
    | Custom .NET add-in logic (GP-RSM-Customization)
    |   - Custom report schedules
    |   - Custom distribution rules
    |   - Custom filter criteria
    v
[Report Output (PDF / Excel / CSV)]
    |
    +--→ [Email: Finance team distribution list]
    +--→ [File share: Network path for archival]
    +--→ [Printer: Physical copies for period-end close]
```

---

## 6. Recommendations

1. **Source Code Recovery**: Locate the deployed `.dll` files on the GP production server (`p-na-app31`) and either decompile or request source code from Crestwood. Commit to this repository.

2. **Data Lineage Documentation**: Document which GP tables are queried by the RSM customization and what filters are applied, to ensure SOX report completeness and accuracy controls can be validated.

3. **Distribution List Audit**: Review the currently configured email distribution lists in GP RSM to confirm reports are only reaching authorized recipients.

4. **PCI DSS Review**: Confirm that no full PANs or sensitive authentication data appear in any scheduled report output. Any report referencing card data should use masked values (first 6 / last 4).
