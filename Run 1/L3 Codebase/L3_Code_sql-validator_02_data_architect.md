# sql-validator — Data Architect View

## Data Stores
`sql-validator` does not own or connect to any data store. It is a pure validation library. It operates on SQL strings in memory only and never executes queries or connects to a database.

## Schema / Tables
None owned. The library maintains static reference sets of protected/blocked table names:

### Protected Tables (always blocked, from `SqlSafetyConfig.PROTECTED_TABLES`)
`users`, `passwords`, `sessions`, `tokens`, `keys`, `secrets`, `admin`, `configuration`, `settings`, `logs`, `audit`, `password`, `secret`, `token`, `key`, `hash`, `salt`, `concat`, `substring`, `cast`, `decode`

### Protected Schemas (always blocked, from `SqlSafetyConfig.PROTECTED_SCHEMAS`)
`information_schema`, `sys`, `mysql`, `performance_schema`, `pg_catalog`, `pg_toast`, `pg_temp`

### Protected Columns (always blocked, from `SqlSafetyConfig.PROTECTED_COLUMNS`)
`password`, `secret`, `token`, `key`, `hash`, `salt`

## Sensitive Data
The library itself does not process or store sensitive data. It processes SQL query strings, which may theoretically contain embedded data values in WHERE clauses or string literals. The `StringsAnalyzer` inspects string literal values for suspicious patterns from `SUSPICIOUS_PATTERNS` which includes words like `password`, `user`, `username`, `admin`, `root`. Detection of these in string values causes rejection.

## Encryption
None. The library operates entirely in memory on string/AST representations.

## Data Flow
```
Caller: raw SQL string
         |
         v
SecureInputAnalyzer.validateAndNormalizeInput()
  → Unicode NFKC normalization
  → Levenshtein distance check (≤10% change allowed)
  → Control character scan
  → Semicolon count check (multi-statement rejection)
         |
         v
CCJSqlParserUtil.parse() → Statement AST
         |
         v
instanceof Select check (non-SELECT rejected)
         |
         v
TraverseAll (visitor orchestrator)
  → ColumnAnalyzer: visits Column nodes
  → ComplexityAnalyzer: visits PlainSelect, WithItem, FromQuery nodes
  → ExpressionAnalyzer: visits PlainSelect WHERE, StringValue, HexValue, LongValue
  → FunctionAnalyzer: visits Function nodes
  → StringsAnalyzer: visits StringValue nodes
  → TablesAnalyzer: visits Table nodes
  → SecurityAnalyzer: visits Concat, AndExpression, OrExpression, EqualsTo, LikeExpression
         |
         v
If no AnalyzeException: caller may proceed to execute query
If AnalyzeException thrown: caller must reject the input
```

## Data Quality / Retention
Not applicable — no persistent data. The library is stateless.

## Compliance Gaps
| Gap | Standard | Notes |
|---|---|---|
| No logging of rejected queries | PCI DSS Req 10, SOC 2 CC7 | Blocked SQL injection attempts should be logged as security events. The library throws an exception but does not log. Callers must implement audit logging of rejections. |
| `ValidationResult` class unused | API design | The `ValidationResult` wrapper is defined but `validateQuerySecurely()` voids it by throwing instead of returning — callers cannot distinguish validation failures from runtime errors without catching `AnalyzeException` |
| Empty allowlist bypass | PCI DSS Req 7 (least privilege) | Empty `allowedTables` list disables table restriction — callers must always pass an explicit, minimal allowlist |
| `SELECT *` allows all columns in allowed tables | PCI DSS Req 3 | Column-level blocking only applies to explicitly named columns; `SELECT *` bypasses column protection for allowed tables |
