# sql-validator — Business Analyst View

## Business Purpose
`sql-validator` (`com.onbe.sqlvalidator:sql-validator:1.0-SNAPSHOT`) is a Java library designed to safely validate raw SQL queries before execution. Its primary purpose is to prevent SQL injection attacks and to enforce a read-only, safe query contract. This library is intended to be used wherever Onbe systems accept SQL input (e.g., reporting tools, AI-generated queries, MCP-integrated data access) and need to confirm that input cannot damage the database or exfiltrate sensitive data.

The URL `https://github.com/onbe/sql-validator` and package root `com.onbe.sqlmcp` (MCP = Model Context Protocol) suggest this library was created in the context of an AI/LLM integration layer where an AI agent generates SQL queries that need to be validated before execution against Onbe's databases.

## Capabilities
| Capability | Analyzer Class | Description |
|---|---|---|
| Unicode normalisation | `SecureInputAnalyzer` | NFKC normalisation + Levenshtein distance check to detect Unicode obfuscation attacks |
| Control character blocking | `SecureInputAnalyzer` | Rejects null bytes and ISO control characters in SQL input |
| Multi-statement blocking | `SecureInputAnalyzer` | Rejects SQL containing semicolons (prevents stacked queries) |
| SELECT-only enforcement | `SqlQueryValidator` | Rejects any statement that is not a SELECT (INSERT, UPDATE, DELETE, DROP, TRUNCATE, etc. all blocked) |
| Table allowlisting | `TablesAnalyzer` | Enforces that only explicitly permitted tables can appear in the query |
| Protected table/schema blocking | `TablesAnalyzer`, `SqlSafetyConfig` | Blocks access to `information_schema`, `sys`, `pg_catalog`, `users`, `passwords`, `sessions`, `tokens`, `keys`, `secrets`, `admin`, etc. |
| Sensitive column blocking | `ColumnAnalyzer` | Blocks queries referencing columns named `password`, `secret`, `token`, `key`, `hash`, `salt` |
| SQL injection pattern detection | `SecurityAnalyzer`, `ExpressionAnalyzer` | AST-based detection of tautology expressions (1=1, 'a'='a'), OR TRUE patterns, suspicious LIKE patterns, dangerous operators in WHERE clauses and string literals |
| Dangerous function blocking | `FunctionAnalyzer` | Blocks `xp_cmdshell`, `sp_oacreate`, `openrowset`, `pg_read_file`, `pg_ls_dir`, etc.; enforces an allowlist of safe aggregate/string/date functions |
| Complexity limiting | `ComplexityAnalyzer` | Limits query complexity (max score 50), nesting depth (5), join count (5), table count (10) |
| String literal length limiting | `StringsAnalyzer` | Rejects string literals longer than 4,000 characters |
| Hex value blocking | `ExpressionAnalyzer` | Rejects hexadecimal literals |
| Large numeric value blocking | `ExpressionAnalyzer` | Rejects numeric literals exceeding 1,000,000,000 |
| Obfuscation detection | `SecurityAnalyzer` | Detects character-by-character concatenation used to spell sensitive words (e.g., `'p'||'a'||'s'||'s'...`) |
| Multi-DB support | `SqlSafetyConfig.DatabaseType` | Separate allowed/disallowed function sets for SQL Server and PostgreSQL |

## Key Entities
- `SqlSafetyConfig` — Static configuration hub: allowedFunctions, dangerousKeywords, disallowedFunctions, PROTECTED_TABLES, PROTECTED_COLUMNS, PROTECTED_SCHEMAS, SUSPICIOUS_PATTERNS, DANGEROUS_OPERATORS, MAX_STRING_LITERAL_LENGTH (4000), MAX_COMPLEXITY_SCORE (50), MAX_JOINS (5), MAX_NESTED_DEPTH (5), MAX_TABLES_ALLOWED (10).
- `ValidationResult` — Result wrapper (valid: boolean, errorMessage: String) — currently unused by `SqlQueryValidator.validateQuerySecurely()` which throws `AnalyzeException` instead.
- `AnalyzeException` — Unchecked exception thrown on any validation failure.

## Business Rules
1. Only SELECT statements are permitted — all DML and DDL is rejected.
2. Only tables in the caller-supplied allowlist may be accessed (unless allowlist is empty, in which case all non-protected tables are permitted).
3. Protected schemas and tables (system tables, credential tables) are always blocked regardless of allowlist.
4. Queries must not reference sensitive column names (password, secret, token, key, hash, salt).
5. Known SQL injection patterns must be detected and blocked at the AST level.
6. Query complexity must not exceed defined thresholds to prevent resource exhaustion or bypass via complexity.
7. Input is Unicode-normalised first to prevent lookalike character attacks.

## Business Flows
1. Caller passes raw SQL string + database type + allowed tables list to `SqlQueryValidator.validateQuerySecurely()`.
2. Input normalisation and pre-parse checks run (`SecureInputAnalyzer`).
3. SQL is parsed to AST by JSQLParser.
4. All analysers traverse the AST; any `AnalyzeException` propagates to caller as a hard rejection.
5. If no exception: query is safe to execute.

## Compliance Relevance
- Directly supports PCI DSS Requirement 6.2.4 (secure development — input validation, SQL injection prevention).
- Supports OWASP Top 10 A03:2021 Injection prevention.
- The PROTECTED_TABLES and PROTECTED_COLUMNS sets explicitly protect credential storage tables — relevant to PCI DSS Requirement 8 (identity management).
- Relevant to any AI/LLM integration at Onbe where generated SQL must be sanitised before execution.

## Risks
| Risk | Severity | Notes |
|---|---|---|
| `ValidationResult` class is defined but not returned | Medium | `validateQuerySecurely()` throws exception rather than returning `ValidationResult` — the class is dead code; API is inconsistent |
| Allowlist bypass when list is empty | Medium | `TablesAnalyzer` skips table checks if `tableNames.isEmpty()` — callers must always pass a non-empty allowlist for protected deployments |
| `SELECT *` allowed | Low | Column-level restrictions only block named columns; `SELECT *` from an allowed table may still return sensitive columns at runtime |
| Complexity limits may block legitimate reporting queries | Low | `MAX_JOINS=5`, `MAX_COMPLEXITY_SCORE=50` may be too restrictive for complex analytical queries |
