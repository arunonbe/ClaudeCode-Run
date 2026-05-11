# Business Analyst Analysis — endclient-relationship-backfill-generator

## Repository Overview

**Repo name:** `endclient-relationship-backfill-generator`
**Type:** Internal data-migration CLI utility
**Primary language:** Java 21
**Build tool:** Maven (artifact `RelationshipBackfillScriptGenerator` v1.0-SNAPSHOT, `pom.xml` line 8)
**README summary (README.md line 1):** "A simple Java CLI to generate a SQL script that will backfill existing promotions with a relationship ID."

---

## Business Purpose

This tool exists to solve a specific one-time (or periodic) operational problem: legacy promotion records in the Onbe prepaid platform were created before the concept of an **end-client relationship ID** was introduced into the data model. To retroactively associate promotions with their owning relationship, an operations engineer provides a CSV mapping file of `program_id,relationship_id` pairs, and the tool generates a SQL script that inserts the necessary rows into `dbo.program_relationship_map` and marks programs as shared in `dbo.programs`.

### Business Trigger

The tool is required when:
- A new end-client relationship concept is introduced and existing programmes need to be migrated.
- A client's programme portfolio is reorganised under a new relationship ID.
- Bulk rectification is needed after a data-quality audit.

### Business Workflow

1. A data steward or operations engineer prepares a flat CSV file where each line contains `programId,relationshipId` (inferred from `EndClientRelationshipScriptGenerator.java` lines 46–51).
2. The engineer runs the CLI: `java -jar ... -i <input.csv> -o <output.sql>`.
3. The tool reads each CSV row and writes two SQL statements per pair:
   - An `INSERT` into `dbo.program_relationship_map` that selects all existing promotions for the programme and stamps them with the provided `relationship_ext_id`, `start_date` as `GETUTCDATE()`, and `end_date` as `NULL` (lines 25–36).
   - An `INSERT` into `dbo.programs` marking the programme as shared (line 40).
4. The generated `.sql` file is reviewed by a DBA and executed against the target SQL Server database.

### Business Entities Affected

| Entity | Table | Operation |
|--------|-------|-----------|
| Programme | `dbo.programs` | INSERT (shared flag set to 0) |
| Programme Promotion | `dbo.program_promotion` | READ (source of promotions per programme) |
| Relationship Map | `dbo.program_relationship_map` | INSERT (new relationship binding) |

### Known Business Limitations (flagged in source code TODOs)

- **No duplicate prevention** — the tool does not check whether a relationship has already been backfilled (`EndClientRelationshipScriptGenerator.java` line 26: "TODO ensure this doesn't overwrite existing relationships or attempt to insert dupes").
- **No input validation** — programme IDs and relationship IDs are not validated against known formats (line 49).
- **No transactional wrapping** — each pair of inserts is not wrapped in a SQL transaction (line 50), creating a risk of partial updates if execution is interrupted.
- **No row-count check** — input parsing assumes exactly two comma-separated values per line (line 50).

### Compliance and Regulatory Relevance

Because this tool modifies tables that govern which end-clients are associated with which prepaid programmes, it touches data lineage that is relevant to:
- **PCI DSS v4.0.1 Req 12.5.2** – change management traceability for the cardholder data environment.
- **Audit trail** – the generated SQL does not include audit columns (no `UPDATED_BY`, no timestamp beyond `GETUTCDATE()`), which may be insufficient for SOC 1 / SOC 2 change-evidence requirements.

### Stakeholders

| Role | Concern |
|------|---------|
| Operations / DBA | Executes the generated script; responsible for reviewing output before applying |
| Product / Programme Management | Provides the CSV input mapping |
| Compliance / Audit | Requires evidence of what was changed and when |
| Engineering | Maintains and enhances the tool |

---

## Gaps and Recommendations

1. **Idempotency guard** — add a `WHERE NOT EXISTS` clause to each INSERT to prevent re-runs from inserting duplicate relationship mappings.
2. **Transaction wrapping** — wrap each programme's pair of inserts in `BEGIN TRANSACTION … COMMIT` / `ROLLBACK` to ensure atomicity.
3. **Input validation** — validate that `programId` and `relationshipId` match expected formats before emitting SQL.
4. **Audit columns** — consider emitting `INSERTED_BY` and `INSERTED_AT` populated from a command-line argument to satisfy SOC 2 change-evidence requirements.
5. **Dry-run mode** — add a `--dry-run` flag that prints expected row counts without generating SQL, allowing the data steward to verify scope before execution.
