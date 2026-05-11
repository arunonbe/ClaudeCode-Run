# Solution Architect Analysis — endclient-relationship-backfill-generator

## Repository Overview

**Repo:** `endclient-relationship-backfill-generator`
**Primary source file:** `src/main/java/EndClientRelationshipScriptGenerator.java`
**Java version:** 21 (`pom.xml` lines 12–13)
**Runtime dependency:** `commons-cli:1.3.1`

---

## Solution Design

### Problem Being Solved

The solution addresses a **data backfill gap** in Onbe's prepaid programme data model: existing promotions in `dbo.program_promotion` lack a `relationship_ext_id` binding. The tool generates a SQL script that a DBA executes to close this gap by inserting rows into `dbo.program_relationship_map` and flagging affected programmes in `dbo.programs`.

### Chosen Approach

The solution uses a **code-generation pattern**: rather than connecting to the database and executing SQL directly, it produces a SQL script as output. This is a deliberate engineering choice that provides:
- Human-readable output for DBA review before execution.
- No database credentials required at tool-execution time.
- A reviewable artefact for change management.

### Architecture Components

```
[CSV Input File]
      |
      v
[EndClientRelationshipScriptGenerator.java]
  - parseArgs() : Command-line parsing via commons-cli
  - main()      : File I/O loop + SQL template substitution
      |
      v
[Generated SQL Script Output File]
      |
      v
[DBA Manual Execution -> SQL Server Database]
```

---

## Security Risks

### 1. SQL Injection via CSV Input (HIGH)
**Location:** `EndClientRelationshipScriptGenerator.java` lines 55–58
**Description:** Both `programId` and `relationshipId` are interpolated directly into SQL strings using `String.format()`. No escaping or sanitisation is performed. If a CSV value contains a single quote (`'`), the generated SQL will be syntactically invalid or could be used to inject additional SQL statements.
**Recommendation:** Escape single quotes in both values (`value.replace("'", "''")`), or switch to a SQL builder that uses parameterised placeholders. Since the output is a reviewed script, minimal escaping is the pragmatic fix.

### 2. Positional INSERT (MEDIUM)
**Location:** Line 40 — `insert dbo.programs values ('%s', 0)`
**Description:** The INSERT does not specify column names. If the `dbo.programs` table is altered (column added, column reordered), this statement will silently insert data into the wrong columns or fail at execution time.
**Recommendation:** Use explicit column list: `INSERT dbo.programs (program_id, shared_flag) VALUES ('%s', 0)`.

### 3. No Idempotency Guard (HIGH)
**Location:** Lines 25–40
**Description:** Neither INSERT checks for pre-existing records. Re-running the tool against the same input will produce duplicate rows in `dbo.program_relationship_map` and a primary-key / uniqueness violation in `dbo.programs` (depending on the table's constraints).
**Recommendation:** Wrap each INSERT in a conditional: `IF NOT EXISTS (SELECT 1 FROM dbo.program_relationship_map WHERE program_id = ... AND relationship_ext_id = ...) INSERT ...`.

### 4. No Atomic Transaction (HIGH)
**Location:** Lines 25–40 (no `BEGIN TRANSACTION`)
**Description:** The two SQL statements per programme (program_shared_insert and program_relationship_insert) are not wrapped in a transaction. If the script is interrupted between the two statements, `dbo.programs` will be updated but `dbo.program_relationship_map` will be missing rows.
**Recommendation:** Wrap each pair in `BEGIN TRANSACTION; ... COMMIT;` with a `ROLLBACK` on error.

### 5. No Input File Integrity Verification (LOW)
**Description:** There is no checksum or signature verification on the input CSV. An attacker or accidental modification could inject rows with different programme or relationship IDs.
**Recommendation:** Log the SHA-256 hash of the input file in the output script header comment. Verify the hash matches the expected value from the change ticket before execution.

---

## Technical Debt

| Item | Description | Severity |
|------|-------------|----------|
| No test coverage | There is no `src/test` directory. `EndClientRelationshipScriptGenerator.java` has no unit tests for `parseArgs()` or the SQL generation logic. | High |
| Outdated dependency | `commons-cli:1.3.1` (2015). Latest is 1.6.x. | Low |
| No fat-JAR build config | `pom.xml` has no assembly/shade plugin; the tool cannot be run as a self-contained JAR. | Medium |
| No logging framework | Output goes only to `System.err` / `System.out`. No structured log, no log level control. | Low |
| Hardcoded table names | `dbo.program_relationship_map`, `dbo.program_promotion`, `dbo.programs` are hardcoded strings. | Low |
| No version stamp in output | Generated SQL has no comment identifying the tool version or input file name, making audit reconstruction harder. | Medium |

---

## Compliance Mapping

| PCI DSS / Regulatory Requirement | Relevance | Status |
|-----------------------------------|-----------|--------|
| PCI DSS v4.0.1 Req 6.3 – Bespoke software security | SQL injection risk in generated output | Not addressed |
| PCI DSS v4.0.1 Req 10.3 – Audit log events | No audit log of execution | Not addressed |
| PCI DSS v4.0.1 Req 12.5.2 – Change management | Manual process; change ticket required | Partially addressed (operational) |
| SOC 1 / SOC 2 – Change evidence | No automated evidence generation | Not addressed |

---

## Improvement Roadmap

### Immediate (before next execution)
1. Add `WHERE NOT EXISTS` guards to both INSERT statements.
2. Add explicit column list to `insert dbo.programs`.
3. Wrap each programme block in `BEGIN TRANSACTION … COMMIT`.
4. Add header comment to output SQL: tool version, input file name, operator ID, timestamp.

### Short-term (next sprint)
5. Add unit tests for `parseArgs()` and SQL generation logic.
6. Upgrade `commons-cli` to 1.6.x.
7. Add `maven-shade-plugin` to build a self-contained executable JAR.
8. Add single-quote escaping for `programId` and `relationshipId`.

### Medium-term (if tool is to be reused)
9. Refactor as a Spring Batch job with direct JDBC connection, parameterised SQL, idempotency, and structured audit logging — consistent with the Gen-3 `cross-border-transfer-service-batch` pattern.
