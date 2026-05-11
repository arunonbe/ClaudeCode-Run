# 04 Enterprise Architect — request-file-bulk-card

## Platform Generation
Gen-1 / Legacy. Java 5 compile target, Spring 2.0.4, Subversion SCM (ecount internal), Windows file-system paths hard-coded (`D:/c-base/`), plain-text JDBC credentials in properties files, cbase API integration. Dates from 2013.

## Business Domain
Card Inventory / Instant Issuance. Bridges operator bulk-order input (CSV) and the card inventory management system request-file format.

## Role
Standalone batch process executable. Not a library; not a service. Invoked on demand by operations staff or a scheduler to produce bulk instant-issue card order files for a specific programme.

## Dependencies
| Dependency | Direction | Coupling |
|---|---|---|
| cbase API (`RequestContext`, `Member`, `AppProgramInstantIssueProfileClass`) | Outbound | Hard — profile retrieval |
| `requestfile-impl 1.0.2` | Compile | Hard — `PaymentRequestFile`, `RequestFileStatus` |
| `inventory-mgmt 2013.2.1` | Compile | Hard — `InstantIssueRequestFileBuilder`, `InstantIssueLocationRequest` |
| `fileconversion 1.0.0` | Compile | Hard — `DelimitedRecordParser` |
| `xPlatform 2.5.24` | Compile | Hard — xPlatform system bootstrap |
| jobsvc SQL Server DB | Outbound | Hard — order record updates |
| File system (`D:/c-base/`) | Runtime | Hard — config, input, output |

## Integration Patterns
- **Batch CLI process**: triggered by Windows Task Scheduler or operator command line
- **File-based integration**: consumes CSV, produces proprietary request file
- **JDBC direct**: plain `DriverManagerDataSource` for jobsvc DB access
- **cbase API (legacy RPC)**: profile data retrieved via cbase platform library calls

## Strategic Status
**Sunset candidate.** Frozen at 2013 vintage (version 2013.2.1, Subversion history). The capability (bulk instant-issue card ordering from a CSV) is a narrow operational workflow that should be replaced by a modern REST API-driven order intake flow in the Gen-3 platform. No active development observed; likely kept running for legacy programme support.

## Migration Blockers
- Hard dependency on cbase `RequestContext` / `AppProgramInstantIssueProfileClass` — Gen-3 equivalent must expose programme profile data via an accessible API
- `inventory-mgmt 2013.2.1` library is an opaque internal dependency; its replacement must be confirmed with the inventory management team
- File-based input/output contract must be maintained or replaced with a documented API; downstream systems consuming the request file must be surveyed
- No automated tests beyond a stub test class (`RequestfileBulkCardGenClientTest`); any migration requires test authorship first
