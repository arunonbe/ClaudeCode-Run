# Data Architect Analysis: repository_LIB

## Data Stores
| Store | Type | Purpose |
|---|---|---|
| SQL Server (cbaseapp database) | Relational DB | Stores Report, ReportCategory, ProgramReport entities; accessed via Hibernate 5 |
| Repository Service (XML-RPC) | Remote service | File storage and retrieval; accessed via `XmlRpcReportManagerClient` and `RPCWrapper` |
| FTP server | File transfer | Referenced in `FTPUtil`; used for file retrieval operations |

## Schema / Tables
The library owns/reads the following tables (inferred from Hibernate entities and DAO queries):

### report
| Column | Type | Notes |
|---|---|---|
| reportId (inferred) | Integer PK | Report identifier |
| name | VARCHAR | Report name; used in `getReportByName()` query |
| reportCategory.id | FK | Foreign key to report_category |

### report_category
| Column | Type | Notes |
|---|---|---|
| id | Integer PK | Category identifier |
| (other columns) | Unknown | Entity class is present but columns not visible without reading full entity |

### program_report
| Column | Type | Notes |
|---|---|---|
| (join table or mapping table) | Unknown | Maps programs to reports; accessed via `ProgramReportDAO` |

Database dialect: SQL Server (confirmed by commented-out Hibernate config in `repositoryContext.xml:88`).

Session factory and transaction manager are wired externally via Spring (`spring-dbctx-container`), not configured within this library.

## Sensitive Data Handled
- Report metadata (names, categories, program associations) — internal operational data; moderate sensitivity.
- Files retrieved/stored are opaque byte arrays from this library's perspective; actual content sensitivity depends on the calling context (may include batch files with PII or financial data).
- `FTPUtil` handles file transfer operations; FTP credentials are external to this library.

## Encryption
- No encryption implemented within this library.
- File content is handled as raw bytes/streams without encryption at this layer.
- Transport encryption depends on the XML-RPC client and FTP client configuration provided externally.
- SQL Server connection encryption depends on the JDBC datasource configuration (injected externally via `spring-dbctx-container`).

## Data Flow
```
Caller (service/webapp)
  |
  |--> RepositoryManager.getFile() / storeFile()
  |       --> RepositoryManagerImpl
  |               --> XmlRpcReportManagerClient (repository-client module)
  |                       --> XML-RPC over HTTP --> repository-service_SVC
  |
  |--> ReportManager.getReport() / getReportsByCategory()
  |       --> ReportManagerImpl
  |               --> ReportDAO (Hibernate) --> SQL Server (cbaseapp DB)
```

## Data Quality / Retention
- No data quality validation within the library; callers are responsible for valid inputs.
- Date-range filtering is provided but retention policy is not enforced at this layer.
- No soft-delete or audit trail logic visible in this library's DAO classes.

## Compliance Gaps
1. **FTP usage** (`FTPUtil`): Plain FTP transfers files without encryption in transit; violates PCI DSS Requirement 4.2 (protect cardholder data in transit) if any file content includes PANs.
2. **No access logging** at the library layer: file access operations are not audited within this library; depends on callers.
3. **Opaque file content**: Library does not validate that files containing PANs are encrypted before storage; this responsibility is delegated entirely to callers and the repository service.
4. **Hibernate 5 session factory** wired via Spring XML context: no connection-level encryption settings visible; depends on external datasource configuration.
