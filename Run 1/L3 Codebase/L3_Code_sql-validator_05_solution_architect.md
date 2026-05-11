# sql-validator — Solution Architect View

## Technical Architecture
Pure Java 17 library with JPMS module declaration. Stateless — all validation runs in a single synchronous call with no shared mutable state.

```
SqlQueryValidator.validateQuerySecurely(sql, dbType, allowedTables)
    │
    ├─ SecureInputAnalyzer.validateAndNormalizeInput(sql)
    │      Unicode NFKC normalization → Levenshtein distance check → control chars → semicolons
    │
    ├─ CCJSqlParserUtil.parse(normalizedSql) → Statement AST
    │
    ├─ instanceof Select check
    │
    ├─ TraverseAll(analyzers).select.accept(director)
    │      ├─ ColumnAnalyzer         — Column nodes
    │      ├─ ComplexityAnalyzer     — PlainSelect, WithItem, FromQuery
    │      ├─ ExpressionAnalyzer     — PlainSelect WHERE, StringValue, HexValue, LongValue
    │      ├─ FunctionAnalyzer       — Function nodes (allowlist + blocklist + system fn check)
    │      ├─ StringsAnalyzer        — StringValue nodes (length + suspicious patterns)
    │      ├─ TablesAnalyzer         — Table nodes (allowlist + protected tables/schemas)
    │      └─ SecurityAnalyzer       — Concat, And/Or, EqualsTo, LikeExpression
    │
    └─ void return (no exception = valid)
         AnalyzeException thrown (unchecked) = invalid
```

## API Surface
Single public entry point (JPMS exports `com.onbe.sqlvalidator` and `com.onbe.sqlvalidator.analyzers`):

```java
// module-info.java: exports com.onbe.sqlvalidator; exports com.onbe.sqlvalidator.analyzers
public class SqlQueryValidator {
    public static void validateQuerySecurely(
        String sql,
        SqlSafetyConfig.DatabaseType dbType,   // SQL_SERVER | POSTGRESQL
        List<String> allowedTables             // null/empty = no table restriction
    ) throws AnalyzeException;
}
```

`ValidationResult` is exported but not returned by the API — it is dead code in the current implementation.

## Security Posture

### SQL Injection Prevention
The library implements defence-in-depth:
1. **Pre-parse**: Unicode normalisation, control character removal, multi-statement blocking
2. **Parse**: JSQLParser strict parsing — malformed SQL is rejected
3. **AST analysis**: Structural pattern detection that cannot be bypassed by encoding tricks that survive parsing

**Gap**: String-based pattern matching in `ExpressionAnalyzer.visit(PlainSelect)` (`whereStr.contains(pattern)`) is a secondary check performed alongside AST checks. If the AST-based checks cover the same patterns, the string-based check is redundant. If not, it may produce false positives on legitimate queries containing substrings like `"select"` in column values.

**Gap**: `TablesAnalyzer` with empty `tableNames` list allows all tables except protected ones. Callers must always pass an explicit allowlist.

### Authentication
Not applicable — library, no network access.

### Cryptography
Not applicable.

### Secrets Management
No secrets. No credentials. No external connectivity.

### Known CVE Concerns
| Component | Version | Risk |
|---|---|---|
| `jsqlparser:5.3` | 5.3 (current as of analysis) | No known CVEs at analysis time; monitor JSQLParser GitHub for security advisories |
| `slf4j-simple:1.7.36` | 1.7.36 | Outdated — SLF4J 2.x is current. No critical CVEs in 1.7.36 itself but using it as a library dependency is an anti-pattern that can break consumer logging |

## Technical Debt
| Item | File | Line | Notes |
|---|---|---|---|
| `System.out.println` debug output | `TraverseAll.java` | 55, 56, 127, 130, 145, 147, 170, 175, 190, 194, 207, 212, 229, 270, 285, 305, 323, 342, 362, 381, 397, 409, 534 | Every AST node visit prints to stdout — must be removed before production use |
| `ValidationResult` unused | `ValidationResult.java` | entire file | Defined, exported, but never returned by the only public method |
| `slf4j-simple` as library dependency | `pom.xml:33` | — | Anti-pattern: forces SLF4J binding on consumers |
| `1.0-SNAPSHOT` version | `pom.xml:9` | — | Unstable; no release published |
| No CI/CD pipeline | — | — | No workflow files present |
| String-based WHERE scan | `ExpressionAnalyzer.java:16–23` | — | `whereStr.contains(pattern)` for patterns including `"select"` will false-positive on queries with string values containing "select" |
| `SUSPICIOUS_PATTERNS` includes common SQL keywords | `SqlSafetyConfig.java:62–67` | — | `"select"`, `"from"`, `"where"`, `"join"` in `SUSPICIOUS_PATTERNS` will block any string literal containing these words (e.g., `WHERE description = 'please select'`) |

## Gen-3 Migration Requirements
This library is already Gen-3. Hardening actions needed before production use:
1. Remove all `System.out.println` statements from `TraverseAll.java`.
2. Replace `slf4j-simple` with `slf4j-api` only.
3. Add logging of rejected queries at WARN level (without the SQL content if it may contain sensitive data — log the rejection reason and a hash of the input).
4. Release version `1.0.0` (remove SNAPSHOT).
5. Publish to Onbe GitHub Packages Maven registry.
6. Add GitHub Actions workflow for CI, CodeQL, and publish.
7. Review `SUSPICIOUS_PATTERNS` to remove common SQL keywords that will cause false positives in string literals.
8. Address the empty-allowlist bypass: consider making a non-empty allowlist mandatory (throw on empty list rather than skipping the check).
9. Consider returning `ValidationResult` instead of throwing, or at minimum document the exception-based contract clearly.

## Code-Level Risks
| Risk | File | Line | Notes |
|---|---|---|---|
| stdout noise in production | `TraverseAll.java` | 55 et al. | `System.out.println("Visiting PlainSelect")` — every query parse produces many lines of stdout |
| Empty allowlist bypasses table restriction | `TablesAnalyzer.java` | 48–50 | `if (tableNames.isEmpty()) return;` — all non-protected tables accessible |
| False positives from SUSPICIOUS_PATTERNS | `StringsAnalyzer.java` | 22–29 + `SqlSafetyConfig.java:62` | Pattern `"select"` in `SUSPICIOUS_PATTERNS` rejects string literals containing "select" |
| `SELECT *` bypasses column protection | `ColumnAnalyzer.java` | 8–14 | Column-level blocking requires explicit column names; wildcard evades it |
