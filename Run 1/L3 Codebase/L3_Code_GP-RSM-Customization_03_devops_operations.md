# DevOps & Operations Report — GP-RSM-Customization

## 1. Repository State

The `GP-RSM-Customization` repository contains a single file:

```
GP-RSM-Customization/
  README.md
```

README content: "East Campus Dynamics GP .NET GP Addin. Originally in Dex, converted to .NET by Crestwood"

There are **no build scripts, CI/CD pipelines, test files, configuration files, or source code** present. All DevOps and operational analysis in this document is therefore based on inference from the README, the sibling `finance-webservice_API` repository, and standard Microsoft Dynamics GP Add-in development and deployment practices.

---

## 2. Build System (Inferred)

### 2.1 .NET GP Add-in Build

A Microsoft Dynamics GP .NET Add-in is a Windows class library that compiles to a `.dll` assembly. The standard build toolchain for the Wirecard/eCount era (2010–2018) would be:

| Component | Tool |
|---|---|
| Language | C# or VB.NET |
| IDE | Visual Studio 2010–2019 |
| Build | MSBuild via Visual Studio or command line |
| Target Framework | .NET Framework 4.0–4.8 (same as `finance-webservice_API` which targets .NET 4.0) |
| Output | `GPRSMCustomization.dll` (or similar name) |
| GP Integration | `Microsoft.Dexterity.Bridge.dll` and `Microsoft.Dexterity.Shell.dll` from the GP installation |

The `finance-webservice_API` README documents the same build process for its GP component:
```
"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\msbuild.exe" FinanceWS.sln /t:Build /p:Configuration=Release
```

The GP RSM customization would use an identical build process.

### 2.2 Dex-to-.NET Migration by Crestwood

The original Dex (Sanscript) customization would have been:
- Compiled into a `.cnk` (Dynamics GP chunk) file using the Dexterity compiler
- Deployed to GP clients by placing the `.cnk` in the GP application directory

The Crestwood-migrated .NET version replaces this with:
- A `.dll` registered in `Dynamics.set` (GP's add-in manifest file) or via the GP Add-in framework
- Deployed to the GP server/client installation directory

---

## 3. CI/CD Pipeline

**No CI/CD pipeline exists.** There are no:
- `.gitlab-ci.yml` files
- `.github/workflows/` directory or YAML files
- Makefile or deployment scripts

This means all builds and deployments are performed manually, directly on the GP server. This is consistent with traditional on-premise GP Add-in deployment practices but represents a significant gap against modern DevOps standards and SOX ITGC change management requirements.

---

## 4. Deployment

### 4.1 Deployment Model

Based on the `finance-webservice_API` README, Onbe's GP servers are:
- **QA**: `q-na-app01`
- **Production**: `p-na-app31`

A GP .NET Add-in is deployed by:
1. Copying the compiled `.dll` to the GP installation directory on the server
2. Registering the add-in in `Dynamics.set` (GP's launch file that lists add-ins to load)
3. Restarting the Dynamics GP service or GP client sessions to load the new add-in
4. Verifying report schedules are correctly configured in the RSM module

### 4.2 Environment Configuration

Without source code, the environment-specific configuration (database connection strings, report distribution email addresses, file share paths) is unknown. These configurations would typically be stored in:
- A `.config` or `.ini` file alongside the `.dll`
- Directly in the GP RSM schedule configuration in the `SY60200` table
- Hardcoded in the add-in assembly (common but not recommended)

### 4.3 Operational Risk

The absence of version-controlled source code and automated deployment creates several operational risks:

| Risk | Description | Severity |
|---|---|---|
| No rollback capability | Without source code, reverting to a previous version of the RSM customization requires restoring from a server backup or requesting the prior version from Crestwood | HIGH |
| Single point of failure | If the `p-na-app31` server is lost, the RSM customization logic cannot be recreated from source control | HIGH |
| Undocumented changes | Any changes made directly on the GP server leave no audit trail in version control | HIGH |
| SOX ITGC violation | Changes to financial report generation logic with no code review, testing, or change management process | HIGH |

---

## 5. Testing

**No test projects or test files are present in the repository.**

For GP Add-ins, testing is typically performed:
- Manually in the GP client on the QA server (`q-na-app01`)
- By GP consultants (Crestwood) verifying report output matches expected results
- No automated unit testing or integration testing framework exists

The absence of automated tests, combined with no version control of source code, means there is no safety net for changes to the RSM customization.

---

## 6. Monitoring and Observability

### 6.1 GP RSM Execution Logging

Dynamics GP logs report scheduler execution results in:
- The Windows Event Log on the GP application server
- GP's internal report history tables (`SY60600`)
- The GP Activity Log (if enabled in GP system settings)

### 6.2 Alerting

There is no evidence of automated alerting for:
- Report schedule failures
- Distribution delivery failures (bounced emails)
- Report generation errors

In production, a failed RSM schedule would only be discovered if a finance team member noticed a missing report.

---

## 7. Remediation Recommendations

1. **Source Code Recovery (IMMEDIATE)**: Obtain the source `.cs` or `.vb` files from Crestwood and commit them to this repository
2. **Add MSBuild/GitHub Actions pipeline**: Even for a GP Add-in, automated build verification ensures the code compiles against the GP assemblies
3. **Document deployment procedure**: Add a README section describing how to deploy to `q-na-app01` and `p-na-app31`
4. **Add change management gates**: Require code review and QA verification before deploying RSM changes to production (SOX ITGC requirement)
5. **Implement monitoring**: Add Windows Event Log alerting for RSM schedule failures
