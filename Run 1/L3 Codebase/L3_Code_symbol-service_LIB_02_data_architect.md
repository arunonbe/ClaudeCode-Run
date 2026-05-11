# Data Architect View — symbol-service_LIB

## Data Stores
| Store | Type | Description |
|-------|------|-------------|
| `jobsvc_test` SQL Server | Microsoft SQL Server (JTDS driver) | Test database; hosts symbol tables. Alias `JobSvcDataSourceSymbol` in test context. Production datasource is `JobSvcDataSourceSymbol` (injected by container from external context). |

Test config: `jdbc:jtds:sqlserver://eciflexsqldev:1433/jobsvc_test`, user `b2ctest`, password `b2ctest` — hardcoded plaintext credentials in test resources.

## Schema / Tables
The service uses three stored procedures, implying a single symbol table:

| Stored Procedure | Operation | Parameters |
|-----------------|-----------|------------|
| `symbol_create` | INSERT | group, id, name, description |
| `symbol_update` | UPDATE | group, id, name, description |
| `symbol_retrieve_group` | SELECT (ResultSet) | group |

Implied table structure (from `Symbol` entity and stored procedure parameters):
| Column | Type | Notes |
|--------|------|-------|
| group | INTEGER | Grouping key |
| id | INTEGER | Symbol ID within group |
| name | VARCHAR | Symbol name |
| description | VARCHAR | Display description |
| visible | INTEGER | Visibility flag (0/1 or similar) |

Full DDL not present in this repository.

## Sensitive Data
None. Symbol records are reference/display data (e.g., currency symbols, locale characters). No PII, no financial account data, no cardholder data.

## Encryption
Not applicable — no sensitive data requiring encryption.

## Data Flow
```
Consuming service (e.g., UI, payment service)
    |
    | [ISymbolService.createSymbol / updateSymbol / retrieveSymbolGroup]
    v
SymbolServiceImpl --> SymbolLibrary --> SymbolServiceDAOJDBCImpl
    |
    | [JDBC stored procedure call]
    v
SQL Server (jobsvc_test / production symbol table)
```

## Data Quality and Retention
- No soft-delete; symbols are updated or remain permanently.
- No versioning or audit history.
- Results are sorted in Java (`Collections.sort`) after retrieval — no ORDER BY in the stored procedure.
- Error code `SYMBOL_SERVICE_DATA_ACCESS_FAILURE_CODE = 0` conflicts with a success code (`0` typically means OK) — potential ambiguity in error handling.

## Compliance Gaps
| Gap | Standard | Severity |
|-----|----------|----------|
| Hardcoded test credentials (`b2ctest`/`b2ctest`) in `applicationContext-symbol-datasource.xml` | PCI DSS Req 8 | High (test scope) |
| Hardcoded local config path (`d:/c-base/config/...`) in test datasource XML | Environment coupling | Medium |
| No audit log for symbol create/update operations | PCI DSS Req 10 | Low (reference data) |
