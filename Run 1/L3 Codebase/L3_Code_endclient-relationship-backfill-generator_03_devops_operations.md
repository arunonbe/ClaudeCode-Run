# DevOps & Operations Analysis — endclient-relationship-backfill-generator

## Repository Overview

**Repo:** `endclient-relationship-backfill-generator`
**Build system:** Maven (`pom.xml`), artifact `RelationshipBackfillScriptGenerator` v1.0-SNAPSHOT
**Runtime:** Java 21 (`maven.compiler.source/target = 21`, `pom.xml` lines 12–13)
**CI/CD:** No pipeline configuration file detected (no `Jenkinsfile`, `.gitlab-ci.yml`, `.github/workflows/`).

---

## Build and Package

### Maven Build
The project is a standard single-module Maven project. The only runtime dependency is `commons-cli:commons-cli:1.3.1` for command-line argument parsing (`pom.xml` line 16–24).

There is no `<build>` section in `pom.xml` that defines a fat JAR or executable JAR plugin. This means the standard `mvn package` produces a thin JAR without bundled dependencies. To execute, the operator must either:
- Build a fat JAR manually (e.g., add `maven-assembly-plugin` or `maven-shade-plugin`), or
- Provide `commons-cli` on the classpath separately.

This is an **operational gap** — the tool is not runnable as-is from a fresh `mvn package` without additional setup.

### Recommended build command
```bash
mvn clean package
java -cp target/RelationshipBackfillScriptGenerator-1.0-SNAPSHOT.jar:~/.m2/repository/commons-cli/commons-cli/1.3.1/commons-cli-1.3.1.jar EndClientRelationshipScriptGenerator -i input.csv -o output.sql
```

---

## CI/CD Pipeline

**No CI/CD pipeline is defined.** There is no:
- `Jenkinsfile`
- `.gitlab-ci.yml`
- `.github/workflows/` directory

The `.idea/` directory (IntelliJ IDEA project files) indicates local developer use only. This is consistent with the tool's classification as a one-off operational utility rather than a production service.

### Risk
Without a pipeline:
- No automated build verification on commit.
- No artifact versioning or publishing to a shared artefact registry.
- Engineers must build and distribute the JAR manually.

---

## Execution Model

The tool is a **synchronous CLI process**:
1. Takes `-i` (input CSV path) and `-o` (output SQL path) as required arguments.
2. Reads the entire input file sequentially.
3. Writes the output file.
4. Exits with code `0` on success or `1` on failure (`System.exit(endStatus)` not explicitly present here — errors are written to `System.err` and the process exits naturally).

### Runtime Requirements
| Requirement | Detail |
|-------------|--------|
| JRE | Java 21+ |
| Memory | Minimal; processes line-by-line |
| Disk | Proportional to input file size (output SQL ≈ input size × 5) |
| Network | None (purely local file I/O) |
| Database | None at runtime; SQL is generated offline |

---

## Operational Runbook

### Typical Run Procedure
1. Prepare CSV mapping file: `program_id,relationship_id` per line.
2. Build the JAR (if not already distributed).
3. Execute: `java -jar <jar> -i mapping.csv -o backfill.sql`
4. Review `backfill.sql` for correctness (spot-check sample entries).
5. Obtain DBA approval.
6. Execute `backfill.sql` in a maintenance window against the target database.
7. Verify row counts in `dbo.program_relationship_map` and `dbo.programs` match expectations.
8. Store the executed script and the input CSV in the change management system.

### Error Handling
- Invalid arguments (missing `-i` or `-o`): `ParseException` thrown, error printed to `stderr`, process exits with `System.exit(1)` at line 17.
- File I/O errors (file not found, permission denied): `IOException` caught at line 62, message printed to `stderr`. Process continues, which means the output file may be partially written.

### Partial-write risk
If an `IOException` occurs mid-processing (e.g., disk full), the output file will contain partial SQL. There is no cleanup or truncation of the output file on error. The operator must check for this condition manually.

---

## Security and Hardening Considerations

| Item | Finding | Recommendation |
|------|---------|----------------|
| Input CSV sourcing | No controls on who provides the CSV | Restrict to authorised change management tickets |
| SQL output review | No automated review step | Add a review gate before execution in any automation |
| Privilege | Script is executed with DBA credentials | Use a dedicated restricted role that can only INSERT into the specific tables |
| File permissions | Output SQL file inherits OS defaults | Set restrictive umask before running; treat output as sensitive if programme IDs are confidential |
| Dependency age | `commons-cli:1.3.1` (2015 release) | Upgrade to 1.6.x; check for CVEs via `mvn dependency-check:check` |

---

## Observability

There is no structured logging, metrics, or alerting. The tool prints minimal progress to standard output/error. For operational accountability, consider:
- Logging input line count, output statement count, and a SHA-256 hash of the input file to an audit log.
- Integrating with the corporate change management system to record execution evidence.

---

## Conclusion

This is a low-complexity utility with no CI/CD, no automated testing (no `src/test`), and no fat-JAR packaging. It is appropriate for a controlled, manual execution model but should be wrapped with process controls (change ticket, DBA sign-off, post-execution verification) before any production use. The absence of transaction wrapping in the generated SQL is the single highest operational risk.
