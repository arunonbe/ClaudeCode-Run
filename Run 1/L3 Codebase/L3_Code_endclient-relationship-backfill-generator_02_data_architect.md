# Data Architect Analysis — endclient-relationship-backfill-generator

## Repository Overview

**Repo:** `endclient-relationship-backfill-generator`
**Source file analysed:** `src/main/java/EndClientRelationshipScriptGenerator.java`
**Build descriptor:** `pom.xml`

---

## Data Architecture Role

This tool operates as a **SQL generation utility** — it does not connect to a database itself but instead produces a SQL script for offline DBA review and execution. The underlying data architecture it targets is a SQL Server relational database (Microsoft T-SQL dialect, evidenced by `GETUTCDATE()` and the `dbo` schema prefix at lines 25–36).

---

## Target Database Schema

### Tables Referenced

#### `dbo.program_promotion`
- **Purpose:** Master mapping of promotions to programmes.
- **Columns consumed by tool:** `program_id`, `promotion_code`
- **Access mode:** `SELECT` (read source)
- **Role:** Provides the set of promotions that will receive relationship bindings.

#### `dbo.program_relationship_map`
- **Purpose:** Many-to-one mapping between promotions and end-client relationship IDs.
- **Columns inserted:**
  - `program_id` — sourced from `program_promotion.program_id`
  - `promotion_code` — sourced from `program_promotion.promotion_code`
  - `relationship_ext_id` — provided via the CSV input file
  - `start_date` — set to `GETUTCDATE()` at time of SQL execution
  - `end_date` — set to `NULL` (open-ended relationship)
- **Access mode:** `INSERT`
- **Primary key / uniqueness:** Not enforced by the generated SQL; no `WHERE NOT EXISTS` guard (`EndClientRelationshipScriptGenerator.java` line 26 TODO).

#### `dbo.programs`
- **Purpose:** Programme master, with a shared-flag column.
- **Columns inserted:** `program_id`, `0` (shared flag)
- **Access mode:** `INSERT`
- **Generated SQL (`programSharedInsert`, line 40):** `insert dbo.programs values ('%s', 0);`
  - This is a positional INSERT with no explicit column list, which is fragile if the `dbo.programs` table schema ever changes (additional columns, column reorder).

### Entity-Relationship Summary

```
dbo.program_promotion (program_id, promotion_code)
    |
    +--> [backfill tool reads]
    |
    v
dbo.program_relationship_map (program_id, promotion_code, relationship_ext_id, start_date, end_date)

CSV Input (program_id, relationship_id)
    |
    +--> dbo.programs (program_id, shared_flag=0)
```

---

## Data Flow

### Input Data
- **Format:** Plain text CSV, one record per line, two fields: `programId,relationshipId`.
- **Source:** Operator-prepared mapping file (no schema validation in code — lines 46–51 of `EndClientRelationshipScriptGenerator.java`).
- **Risk:** No type checking, no length validation, no sanitisation. A malformed CSV line with more than two columns will produce an `ArrayIndexOutOfBoundsException` silently or write incorrect SQL.

### Processing
1. `BufferedReader` reads the input CSV line by line (line 42).
2. Each line is split on comma (line 47): `String[] values = line.split(",")`.
3. Values are trimmed (line 51–52) but not further validated.
4. String format substitution populates two SQL template strings (lines 55–58).
5. Combined SQL is written to the output file via `BufferedWriter`.

### Output Data
- **Format:** Plain T-SQL script, no transactions, no `GO` batch separators.
- **Recipient:** DBA for manual review and execution.

---

## Data Quality Concerns

| Concern | Severity | Notes |
|---------|----------|-------|
| No duplicate detection | High | Re-running the tool on the same input will produce duplicate rows in `dbo.program_relationship_map` |
| Positional INSERT into `dbo.programs` (line 40) | High | Breaking if schema changes; missing column list |
| SQL injection via CSV input | Medium | Values are string-formatted directly into SQL (`%s` substitution); a malicious or malformed CSV could inject SQL |
| No NULL/empty value guard | Medium | Empty `programId` or `relationshipId` results in syntactically valid but semantically wrong SQL |
| No referential integrity check | Low | Tool does not verify that `program_id` values exist in the database before generating INSERT statements |

---

## SQL Injection Risk

The tool uses `String.format(programRelationshipInsert, relationshipId, programId)` at line 57 and `String.format(programSharedInsert, programId)` at line 55. These are direct string interpolations into SQL. If the CSV file is sourced from an untrusted party or contains special characters (single quotes, semicolons), it could generate malformed or malicious SQL. As this is an offline tool that generates a script for DBA review, the risk is mitigated operationally, but the code should use parameterised output or escaping as a defence-in-depth measure.

---

## Recommendations for Data Architecture

1. **Parameterised output** — Use SQL parameters (`@programId`, `@relationshipId`) or at minimum escape single quotes in both values before substitution.
2. **Explicit column list** — Change `insert dbo.programs values (...)` to `INSERT dbo.programs (program_id, shared_flag) VALUES (...)`.
3. **Idempotency guard** — Wrap each INSERT into `program_relationship_map` with a `WHERE NOT EXISTS (SELECT 1 FROM dbo.program_relationship_map WHERE program_id = '%s' AND relationship_ext_id = '%s')`.
4. **Transaction blocks** — Add `BEGIN TRANSACTION; … COMMIT;` per programme pair.
5. **Audit columns** — Emit `INSERTED_BY` and `INSERTED_AT` columns to satisfy change-data-capture and audit requirements.
6. **Schema version guard** — Consider emitting a header comment block that records the schema version the script was generated for, to prevent accidental execution against a mismatched database version.
