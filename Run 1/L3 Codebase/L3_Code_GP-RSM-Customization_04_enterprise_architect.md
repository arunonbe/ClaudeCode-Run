# Enterprise Architect Report — GP-RSM-Customization

## 1. Platform Generation Assessment

`GP-RSM-Customization` is a **first-generation, on-premise ERP customization** from the Citi/eCount era, subsequently maintained through the Wirecard acquisition and into the Onbe period. Based on the README alone, key generation indicators are inferred:

| Indicator | Evidence |
|---|---|
| Dynamics GP (.NET Add-in) | README: "Dynamics GP .NET GP Addin" |
| Originally Dex/Sanscript | README: "Originally in Dex" |
| Converted by Crestwood | README: "converted to .NET by Crestwood" |
| East Campus designation | Matches the `ECNT` entity pattern in `finance-webservice_API` |
| No cloud components | On-premise GP server at `p-na-app31` |
| No CI/CD pipeline | No `.github/workflows` or `.gitlab-ci.yml` |
| No source code in VCS | Pre-DevOps era deployment practice |

The Dex-to-.NET migration by Crestwood is characteristic of the **2012–2018 GP modernization wave** when Microsoft actively encouraged customers to migrate Dex customizations to the .NET Add-in framework ahead of Dynamics 365 Business Central migration paths. This places the original Dex code at approximately **2005–2015** vintage, and the .NET conversion at **2015–2020**.

This is **Generation 1** in Onbe's application portfolio — older than `file-transfer-service_LIB` (Gen 1, Java 1.6) and significantly older than `functionapptest` (Gen 3, Azure Functions + Java 17).

---

## 2. Role in Enterprise Architecture

### 2.1 Integration Position

`GP-RSM-Customization` sits at the **financial reporting layer** of Onbe's on-premise ERP architecture:

```
[Cambridge CBTS / ACH networks]
    |
    | Settlement files / NACHA ACH
    v
[global-deposit-batch_LIB] ← Batch processing
    |
    | JDBC to SQL Server
    v
[core_ieft_transaction_journal]
    |
    | eConnect API
    v
[finance-webservice_API] ← GP transaction creation
    |
    | eConnect / ODBC
    v
[Dynamics GP (SOP, GL)]
    |
    | GP RSM Add-in
    v
[GP-RSM-Customization] ← This repository
    |
    | Scheduled report generation
    v
[PDF/Excel reports → Finance team email distribution]
```

### 2.2 Relationship to Other Repositories

| Repository | Relationship | Direction |
|---|---|---|
| `finance-webservice_API` | Creates GP sales transactions that RSM reports aggregate | Upstream data producer |
| `global-deposit-batch_LIB` | Processes deposits that become GP transactions | Upstream (indirect) |
| `GP-RSM-Customization` | Consumes GP transaction data for reporting | Downstream consumer |

The GP RSM customization is a pure consumer — it reads data written by `finance-webservice_API` and presents it as scheduled reports to finance users. It does not write back to any operational system.

---

## 3. Architecture Patterns

### 3.1 GP Add-in Pattern (Microsoft.Dexterity.Bridge)

The .NET GP Add-in pattern uses:
- `Microsoft.Dexterity.Bridge` namespace for GP form/window manipulation
- `Microsoft.Dexterity.Shell` for startup registration and event subscription
- GP eConnect or direct ODBC/OLEDB for data access
- GP Report Writer or SSRS for report rendering

### 3.2 On-Premise ERP Pattern

This customization follows the classic on-premise ERP extension pattern:
- Tightly coupled to the GP installation on a specific server
- No API layer or service boundary
- Deployed as a binary registered in GP's launch configuration
- Configuration stored in GP system tables, not in external config files

This pattern contrasts sharply with Onbe's target architecture (Azure, Managed Identity, Key Vault, microservices).

---

## 4. Dependencies

### 4.1 Hard Dependencies

| Dependency | Risk Level | Notes |
|---|---|---|
| Microsoft Dynamics GP installation | CRITICAL | Add-in requires GP DLLs to compile and run |
| GP server `p-na-app31` | HIGH | No evidence of redundancy or failover |
| Windows Server on GP host | HIGH | .NET Framework 4.x requires Windows |
| Crestwood consulting relationship | HIGH | Source code may only exist with Crestwood |
| GP license from Microsoft | MEDIUM | Dynamics GP licensing required |
| `finance-webservice_API` data | MEDIUM | Reports are meaningless without upstream transactions |

### 4.2 Microsoft Dynamics GP End-of-Life

**CRITICAL RISK**: Microsoft announced that Dynamics GP will reach end of support on **September 30, 2029**, with mainstream support already limited. Microsoft's preferred migration path is to **Dynamics 365 Business Central** (cloud-based ERP). This means:

- The GP platform underpinning this customization has a defined sunset date
- All GP customizations including `GP-RSM-Customization` and `finance-webservice_API` will need to be migrated or replaced before 2029
- The on-premise deployment model will become unsupported

---

## 5. Fit / Gap Analysis Against Onbe Target Architecture

| Dimension | Current State | Target State Gap |
|---|---|---|
| Platform | Dynamics GP (on-premise) | Dynamics 365 Business Central or Azure-native |
| Deployment | Binary on Windows server | Container / Azure App Service |
| Source control | Not in VCS | GitHub with full CI/CD |
| Secrets/config | Unknown (hardcoded likely) | Azure Key Vault |
| Build | Manual (no pipeline) | GitHub Actions |
| Testing | Manual only | Automated unit/integration tests |
| Observability | GP logs only | Azure Application Insights |
| Hosting | `p-na-app31` (on-premise) | Azure (cloud) |

The gap between current state and target architecture is **CRITICAL** — not only is the technology stack misaligned, but the source code itself is absent from version control, making any migration planning impossible without first recovering the code from the production server or Crestwood.

---

## 6. Migration Complexity Assessment

Migration complexity is rated **HIGH** for the following reasons:

1. **Unknown source code**: Without source code, migration scope cannot be assessed or estimated. The first step is recovery.

2. **Dynamics GP EOL**: Any migration must account for the GP platform itself being retired by 2029. The RSM customization cannot be migrated to a newer version of GP — it must be re-implemented against Dynamics 365 Business Central or replaced with an Azure-native reporting solution (Azure Data Factory, Power BI, SSRS in Azure, etc.).

3. **Dex heritage**: The original Dex logic is likely embedded in the .NET migration in ways that are idiomatic to GP's Dexterity model (field references using GP internal field IDs, Sanscript event handlers ported to C# delegates). Understanding and re-implementing this logic requires GP domain expertise.

4. **Report output dependencies**: Finance teams have process dependencies on the specific report formats and email distribution schedules. Any re-implementation must maintain backward compatibility with existing report layouts to avoid disrupting close processes.

5. **SOX change management**: Changes to financial report generation logic require SOX change management approval, testing evidence, and UAT sign-off from the Finance Controller.

---

## 7. Lifecycle Recommendation

1. **Immediate**: Locate and recover source code from `p-na-app31` (decompile `.dll` if necessary) and commit to this repository. Without source code, the remaining steps cannot proceed.
2. **Short-term**: Add CI/CD pipeline (GitHub Actions) and establish change management process for GP customization deployments.
3. **Medium-term**: Evaluate replacement with Power BI + Azure SQL for report generation, removing the on-premise GP dependency.
4. **Long-term (pre-2029)**: Migrate from Dynamics GP to Dynamics 365 Business Central or equivalent, retiring this GP Add-in entirely.
