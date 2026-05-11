# Enterprise Architect Report — windows-scripts

## Platform Generation

**Gen-1 (eCount/Citi)**. The scripts operate exclusively within the Gen-1 eCount Core runtime:
- `ECountService.Connection` COM object — the J2COM bridge to eCount Core Java services.
- `ECountService.Connection_j2com` — the newer J2COM variant.
- `ECountCore.eMember.UpdateSecureProfile` — Gen-1 service interface names.
- `ECountService.DataEnvironment.Execute` — Gen-1 data layer interface.
- `ABAT_JOBNAME` — ABAT job scheduler environment variable (Gen-1 batch orchestration).
- FDR (First Data Resources) report processing — Gen-1 processor relationship.
- `d-na-stk01.nam.wirecard.sys` style server names in the BCP format file paths — Gen-1/Gen-2 Wirecard era.

## Integration Patterns

- **XML-RPC via J2COM**: VBScript creates COM objects (`ECountService.Connection`) that internally marshal RPC calls to the eCount Core XML-RPC servlet layer. This is the primary Gen-1 inter-process communication pattern.
- **Stored procedure invocation**: `data-exec.vbs` and `data-exec-ignore-pk.vbs` invoke SQL Server stored procedures via the `ECountService.DataEnvironment` interface, providing a VBScript-to-stored-procedure bridge.
- **Flat file ETL**: Perl scripts parse fixed-format bank settlement reports and load them into SQL Server via BCP or direct inserts.
- **BCP bulk operations**: SQL Server BCP format files govern bulk import/export of financial data between the database and flat file formats required by banks and processors.

## External Dependencies

- **FDR (First Data Resources)**: Primary card processor; settlement reports parsed by Perl scripts.
- **Citi bank**: ACH/NACHA file exchange; CPS (Card Payment Services) check processing.
- **MetaBank (MB)** and **Sunrise Bank**: ACH origination/returns, check issuance.
- **Peoples Bank**: ACH origination.
- **ArrowEye**: Card fulfillment vendor; order confirmation, return mail, shipping confirmation.
- **Personix**: Card fulfillment vendor; inventory, return mail, transaction monitoring.
- **BNY Mellon (Mellon)**: Custodial bank settlement reports.
- **GXS (IBM Sterling)**: EDI/file exchange for client data feeds.
- **NDM (Network Data Mover)**: File transfer between internal systems and bank partners.
- **jIntegra**: J2COM bridge product (now effectively abandoned).

## Position in the Broader Platform

These scripts are the **operational glue** of the Gen-1 platform. They bridge the gap between:
- External bank/processor file formats and the eCount Core database.
- The ABAT job scheduler and eCount Core Java services.
- Manual operator interventions (SSN corrections, DOB updates) and the eCount Core data model.

Without these scripts, the Gen-1 batch processing layer cannot function. They are not documented as part of any formal application architecture and are not covered by any automated test suite.

## Migration Blockers

1. **jIntegra J2COM dependency**: The COM-to-Java bridge is the core dependency. Migrating off J2COM requires rewriting all VBScript operational scripts in a language that can invoke eCount Core or Gen-3 services directly (REST, gRPC, or similar).
2. **VBScript deprecation**: Windows is removing VBScript; all scripts must be rewritten before OS upgrades.
3. **Bank file format lock-in**: BCP format files and Perl parsers are tightly coupled to specific bank report formats. Changes to processor reporting formats require immediate script updates.
4. **ABAT job scheduler**: The ABAT job scheduler is a legacy Windows-based batch orchestration system. Migrating to a modern scheduler (e.g., Azure Batch, Apache Airflow) requires re-mapping all job definitions.

## Strategic Status

**Critical operational dependency — urgent modernization required.** The VBScript/J2COM/Perl stack is the most operationally fragile component of the Gen-1 platform. The combination of VBScript deprecation, J2COM abandonment, and manual deployment creates unacceptable operational risk. The immediate priorities are:
- Inventory all scripts and map each to a Gen-3 equivalent workflow.
- Migrate SSN/DOB manipulation scripts to audited Gen-3 admin APIs with proper RBAC.
- Replace Perl parsers with structured ETL pipelines in the Gen-3 data platform.
- Replace BCP flat-file operations with API-based data exchange where possible.
