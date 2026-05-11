# Business Analyst Report — GP-RSM-Customization

## 1. Executive Summary

`GP-RSM-Customization` is a near-empty repository whose entire content is a two-line `README.md` file. The README states: "East Campus Dynamics GP .NET GP Addin. Originally in Dex, converted to .NET by Crestwood." No source code, project files, build scripts, or configuration files are present in the repository.

Despite the absence of code, the repository name and README provide sufficient context to understand the business purpose. "RSM" in the Dynamics GP ecosystem refers to **Report Scheduler and Manager** — the GP subsystem responsible for scheduling, generating, and distributing financial reports. This repository almost certainly contained .NET customizations to GP's report scheduling and management functionality, specific to the East Campus operational environment.

---

## 2. Business Purpose (Inferred)

### 2.1 Great Plains Report Scheduler Manager (RSM)

Microsoft Dynamics GP (formerly Great Plains) includes a Report Scheduler component that allows finance teams to automate the generation and distribution of financial reports. Common RSM customizations include:

- Custom report triggers based on business events (e.g., end-of-period close)
- Custom distribution logic (email delivery of financial summaries to specific recipients)
- Report filtering by entity, BIN range, or program
- Integration with GP's Modifier/Report Writer tooling
- Automated reconciliation report generation tied to the `finance-webservice_API` transaction processing workflow

For Onbe's operations, such customizations would support:
- Daily, weekly, and monthly reconciliation reports across the prepaid card portfolio
- Program-level disbursement and settlement summaries
- Chargeback and dispute reporting fed from the Cambridge CBTS / global deposit batch processes
- Finance team distribution lists for SOX-relevant reports

### 2.2 Original Dex / Sanscript Implementation

The README notes the customization was "originally in Dex." Dex (short for Dexterity) is Great Plains' proprietary scripting language (also called Sanscript), used to build and modify GP forms, reports, and business logic. Dex-based customizations are compiled into `.cnk` (chunk) files that extend the GP dictionary at runtime.

The conversion from Dex to .NET indicates a modernization initiative, likely executed by **Crestwood** (a Microsoft Dynamics GP consulting partner specializing in GP customization and migration). This migration to .NET GP Add-ins (using the `Microsoft.Dexterity.Bridge` namespace) was a common upgrade path during the 2010–2018 era as Dex-based development declined.

### 2.3 East Campus Designation

"East Campus" appears throughout the Onbe/eCount system (e.g., `global-deposit-batch_LIB` Nexus URL references `d-na-stk01.nam.wirecard.sys`). This likely refers to Onbe's East data center or US entity. The East Campus designation in this GP add-in context suggests the RSM customization was specific to the US operations entity (`ECNT` — eCount North America).

---

## 3. Relationship to Other Repositories

`GP-RSM-Customization` is part of the broader Onbe Great Plains integration layer:

| Repository | Relationship |
|---|---|
| `finance-webservice_API` | The primary GP integration; creates and voids sales transactions via eConnect. RSM customizations likely generate reports derived from the same GP sales transaction data. |
| `global-deposit-batch_LIB` | Processes cross-border deposits that ultimately settle as GP transactions. RSM reports may reconcile deposit volumes against GP ledger entries. |
| `GP-RSM-Customization` | Report scheduling and distribution layer on top of the GP data managed by the above services. |

The three repositories together represent the complete GP integration stack: transaction creation (`finance-webservice_API`), batch deposit processing (`global-deposit-batch_LIB`), and financial report automation (`GP-RSM-Customization`).

---

## 4. Regulatory Relevance

### 4.1 SOX — Sarbanes-Oxley Act

Financial report generation is directly in scope for SOX IT General Controls (ITGCs):
- **Change Management (CC6.1 / SOX ITGC)**: Customizations to financial report generation systems must be tracked, tested, and approved before deployment
- **Completeness and Accuracy**: Reports distributed to finance teams for period-end close must reconcile with underlying GL entries; any customization defect in report filtering or aggregation could result in materially incorrect financial statements
- **Access Controls**: The GP Add-in's distribution logic controls who receives which financial reports; unauthorized modification could result in restricted financial data being sent to unintended recipients

### 4.2 GLBA / CCPA

Reports generated from GP may contain cardholder program-level financial data. Distribution of such reports requires appropriate data handling controls under GLBA and CCPA.

### 4.3 PCI DSS

GP sales transaction data (from `finance-webservice_API`) may reference cardholder account ranges. Report outputs must not include full PANs or sensitive authentication data. RSM report templates and distribution outputs should be reviewed for PCI DSS Requirement 3.3 compliance (protection of stored account data).

---

## 5. Repository State Assessment

The repository currently contains **no deployable or reviewable artifacts**:

| Artifact | Present | Notes |
|---|---|---|
| Source code (.cs, .vb, .dex) | No | Not committed to repository |
| Project files (.csproj, .sln) | No | Not committed |
| Build configuration | No | No `pom.xml`, `build.gradle`, `.sln`, or Makefile |
| CI/CD pipeline | No | No `.gitlab-ci.yml` or `.github/workflows/` |
| Test files | No | None present |
| Configuration files | No | None present |
| Binary artifacts | No | No `.cnk`, `.dll`, or `.zip` files |

Possible explanations for the empty state:
1. Source code was never migrated from the original SCM system (likely GitLab or TFS) when the repository was created on GitHub
2. The customization was deployed directly to the GP server without being committed to version control (a common pattern for Dex/GP Add-in development)
3. The code was intentionally removed or is maintained in a different branch not visible here

---

## 6. Impact Assessment

The business impact of losing this customization depends entirely on what the RSM reports covered. In the absence of source code:

- It is impossible to determine which reports were automated, who received them, or what business decisions they supported
- Finance teams relying on scheduled GP reports may be unaware the automation source is untracked in version control
- Any re-implementation would require GP expertise and knowledge of the original Dex logic
- If the Crestwood-delivered .NET add-in is the only copy of this logic, it represents a **single point of failure with no disaster recovery capability**

**Recommendation**: Locate the .NET `.dll` or `.cnk` files currently deployed on the GP production server (`p-na-app31` based on the finance-webservice README), reverse-engineer or recover the source code, and commit it to this repository.
