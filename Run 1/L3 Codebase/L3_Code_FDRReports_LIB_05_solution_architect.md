# Solution Architect View — FDRReports_LIB

## Code Structure

The entire application is contained in a **single C# file**: `ConsoleApplication1/FDRReports.cs` (532 KB — approximately 13,000+ lines). There is one namespace (`ConsoleApplication1`) and one class (`Program`) with a single method (`Main`). This is a monolithic procedure, not an object-oriented design.

## Class/Method Inventory

### Namespace: `ConsoleApplication1`

**`Program`** — The only class in the application.

**`Main(string[] args)`** — The only method. This single method (approximately 13,000 lines) contains the entire application logic:
1. **DataTable initialization** (lines 24–343): Creates 18 DataTable objects (2 per report type × 9 report types) with all column definitions.
2. **Configuration initialization** (lines 382–494): Reads job configuration from `Banker.dbo.SSISJobConfigurations`, parses XML job parameters, constructs database connection strings.
3. **File iteration** (lines 496–end): For each file in the report directory, reads line by line, detects report type by 8-character prefix matching, parses each line, populates DataTables, bulk-inserts to SQL Server.

There are **no helper methods, no classes, no interfaces, no separation of concerns** beyond the DataTable structure.

## Security Vulnerabilities — CRITICAL

### VULN-1: Hardcoded Production Database Password (CRITICAL — P0)
**File**: `FDRReports.cs` line 413  
**Detail**: `Password=Ecount99!` embedded in the production connection string literal. This credential is committed to the Git repository and accessible to anyone with repository read access.  
**PCI DSS**: Violates Requirement 8.3.1 (protect individual non-consumer user authentication factors) and Requirement 8.2.1 (all user IDs and authentication factors must be kept confidential).  
**Remediation**: Immediately rotate the `gplain` account password. Move to Windows Integrated Security (`Integrated Security=SSPI`) or Azure Key Vault secret reference.  
**Priority**: P0 — Treat as a credential compromise incident.

### VULN-2: Hardcoded UAT Database Password (CRITICAL — P0)
**File**: `FDRReports.cs` line 418  
**Detail**: `Password=r3p0rt1ng` embedded in the UAT connection string literal.  
**Remediation**: Same as VULN-1.  
**Priority**: P0.

### VULN-3: Additional Hardcoded Credentials in Comments (HIGH)
**File**: `FDRReports.cs` lines 476, 484, 490–492  
**Detail**: Multiple commented-out connection strings contain the same hardcoded passwords. Even in comments, these represent committed secrets.  
**Remediation**: Remove commented-out connection strings with passwords. Use environment-specific configuration.  
**Priority**: P1.

### VULN-4: Card Number Data Without Encryption Controls (CRITICAL)
**File**: `FDRReports.cs` — DD-441 DataTable definition, `CardNumber` column  
**Detail**: The application parses and stores `CardNumber` from DD-441 report lines into a DataTable and then writes it to the `ECNT` SQL database. If this is a full or partial PAN, the ECNT database is in PCI DSS scope and must implement encryption at rest, TLS in transit, and access controls per Requirement 3.  
**PCI DSS**: Requires immediate formal assessment by Onbe's QSA.  
**Priority**: P0 — Requires compliance assessment.

### VULN-5: SQL Injection Risk (HIGH)
**File**: `FDRReports.cs` line 425–426  
**Detail**: Query string is built using direct string concatenation with `intParm.ToString()`. While `intParm` is an integer value (not user input), the pattern of string concatenation for SQL queries is a code quality risk if extended.  
**Priority**: P2 — Use parameterized queries throughout.

### VULN-6: .NET Framework 4.0 — End of Life (HIGH)
**File**: `FDRReportProject.csproj` line 13: `<TargetFrameworkVersion>v4.0</TargetFrameworkVersion>`  
**Detail**: .NET Framework 4.0 reached end-of-support in January 2016. No security patches have been released for over 8 years.  
**Priority**: P1.

## Technical Debt Assessment

| Category | Issue | Severity |
|----------|-------|---------|
| Architecture | 13,000+ line single method | Critical — unmaintainable |
| Architecture | No unit tests, no integration tests | Critical |
| Architecture | 9 report parsers in one method with boolean flags | High — error-prone state machine |
| Security | Two hardcoded production passwords | Critical |
| Security | CardNumber stored in DB without confirmed masking | Critical |
| Platform | .NET Framework 4.0 EOL | High |
| Build | No CI/CD, no automated testing | High |
| Reliability | No idempotency, no duplicate detection | High |
| Reliability | No retry logic | Medium |
| Reliability | No structured logging | Medium |
| Maintenance | C# in a Java-dominant environment | Medium |

## Refactoring Recommendations

If keeping this application (not recommended — migrate to ADF/SSIS instead):

1. **Decompose into classes**: Create a `ReportParser` interface with 9 implementations, one per report type.
2. **Extract connection management**: Create a `DatabaseConnectionFactory` that reads credentials from environment variables or secrets manager.
3. **Add idempotency**: Track processed files in a `file_processing_log` database table.
4. **Parameterize all SQL**: Replace string concatenation with `SqlCommand` parameters.
5. **Add structured logging**: Use NLog or Serilog to emit structured JSON logs.
6. **Target .NET 8**: Migrate from .NET Framework 4.0 to .NET 8 LTS.

## Immediate Actions Required

| Action | Owner | Timeline |
|--------|-------|---------|
| Rotate `gplain` password (PPAMWDCPISQL3A1) | Infrastructure/DBA | Immediate |
| Rotate `report` password (ppamwdcUIgp1A1) | Infrastructure/DBA | Immediate |
| Assess DD-441 CardNumber PCI scope | QSA / Security | 30 days |
| Remove committed passwords from git history | Engineering | 1 week (git filter-branch or BFG) |
| Plan migration to ADF/SSIS | Architecture | Next sprint planning |
