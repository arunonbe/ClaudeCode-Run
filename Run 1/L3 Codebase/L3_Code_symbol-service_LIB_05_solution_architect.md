# Solution Architect View — symbol-service_LIB

## Technical Architecture
Two-module Maven library:
- `symbol-common`: Interface (`ISymbolService`), value objects (`Symbol`, `SymbolInput`, `SymbolOutput`), constants (`SymbolServiceConstants`), exception (`SymbolServiceException`).
- `symbol-svc`: Implementation (`SymbolServiceImpl`), library (`SymbolLibrary`), DAO (`SymbolServiceDAOJDBCImpl`), three stored procedure classes (`CreateSymbol`, `UpdateSymbol`, `RetrieveSymbolGroup`), Spring XML context.

Layer diagram:
```
ISymbolService (symbol-common)
        |
SymbolServiceImpl (symbol-svc)
        |
SymbolLibrary (symbol-svc)
        |
ISymbolServiceDAO / SymbolServiceDAOJDBCImpl (symbol-svc)
        |
CreateSymbol / UpdateSymbol / RetrieveSymbolGroup (stored procedures)
        |
SQL Server (symbol table, via JobSvcDataSourceSymbol)
```

## API Surface
Library — no HTTP endpoint. Public API:

| Method | Signature | Description |
|--------|-----------|-------------|
| `createSymbol` | `(SymbolInput) throws SymbolServiceException` | Insert a symbol |
| `updateSymbol` | `(SymbolInput) throws SymbolServiceException` | Update a symbol |
| `retrieveSymbolGroup` | `(SymbolInput) throws SymbolServiceException → SymbolOutput` | Retrieve all symbols in a group |

## Security Posture

### Authentication and Authorization
Not applicable — library; security is enforced by the consuming application.

### Cryptography
Not applicable — reference data only.

### Secrets Management
- Test datasource credentials (`b2ctest`/`b2ctest`) hardcoded in `applicationContext-symbol-datasource.xml` (test resources).
- Production DataSource is injected by the consuming application — no secrets in this library's main source.

### Known CVEs
| Library | Concern | Severity |
|---------|---------|---------|
| JTDS (test scope) | Not Microsoft's official driver; limited security update history | Medium |
| `commons-dbcp:1.x` (test scope, via parent) | EOL; DBCP2 is current | Medium |

No critical CVEs identified in the `symbol-svc` production code itself. The main risk vector is the consuming application's Spring context and JDBC driver configuration.

## Technical Debt
| Item | Location | Severity |
|------|----------|----------|
| `Symbol` implements raw `Comparator` (not `Comparator<Symbol>`) | `Symbol.java:12` | Low — raw type warning; unsafe cast in `compare()` |
| `RetrieveSymbolGroup` uses raw `RowMapper` (not `RowMapper<Symbol>`) | `RetrieveSymbolGroup.java:89` | Low — raw type warning |
| `@SuppressWarnings("unchecked")` on resultset cast | `RetrieveSymbolGroup.java:59` | Low |
| Exception logging via `log.get().info(...)` for exceptions (should be `error`) | `RetrieveSymbolGroup.java:77` | Low |
| `SYMBOL_SERVICE_DATA_ACCESS_FAILURE_CODE = 0` — zero as failure code | `SymbolServiceConstants.java:27` | Medium — callers may mistake 0 for success |
| Test credentials hardcoded in test XML | `applicationContext-symbol-datasource.xml:22-23` | High |
| Hardcoded Windows path `d:/c-base/config/` in test XML | `applicationContext-symbol-datasource.xml:8-11` | Medium |
| `maven-wrapper.jar` in VCS | `.mvn/wrapper/maven-wrapper.jar` | Medium |
| Duplicate workflow/dependabot configs in `.mvn/.github/` | `.mvn/.github/` directory | Low |
| DataSource name `JobSvcDataSourceSymbol` — tightly named to Job Service | `applicationContext-symbol.xml:31,36,40` | Medium (naming coupling) |

## Code-Level Risks
| Risk | Location | Description |
|------|----------|-------------|
| Raw `Comparator` with unsafe cast | `Symbol.java:89-112` | `compare(Object, Object)` casts to `Symbol` — will throw `ClassCastException` if a non-Symbol is passed. |
| Error code zero ambiguity | `SymbolServiceConstants.java:27` | `SYMBOL_SERVICE_DATA_ACCESS_FAILURE_CODE = 0` — any caller checking `code == 0` for "success" will misinterpret a data access failure. Recommend using a non-zero error code. |
| `Collections.sort(symbolList, new Symbol())` | `RetrieveSymbolGroup.java:70` | Creates a `new Symbol()` instance purely as a `Comparator` — an unusual pattern; `Symbol` should implement `Comparable<Symbol>` or a separate `SymbolComparator` class should be used. |
| Test requires live SQL Server | All test classes | Tests in `CreateSymbolTest`, `RetrieveSymbolTest`, `UpdateSymbolTest` cannot run without `eciflexsqldev:1433`. |

## Gen-3 Migration Requirements
1. Genericise `Comparator` and `RowMapper` to eliminate raw type warnings and unsafe casts.
2. Replace `SYMBOL_SERVICE_DATA_ACCESS_FAILURE_CODE = 0` with a non-zero error code.
3. Replace JTDS with Microsoft `mssql-jdbc` driver.
4. Replace stored procedures with Spring Data JPA or JOOQ for easier testing and migration.
5. Add self-contained integration tests using Testcontainers (SQL Server container) to eliminate live DB dependency.
6. Remove hardcoded test credentials and paths — use Testcontainers or environment variables.
7. Remove `.mvn/.github/` duplicate workflow directory.
8. Consider exposing as a REST microservice if many consumers need runtime symbol resolution.
