# jobservice-integration_LIB — Solution Architect View

## Summary

The technical architecture, API surface, security posture, technical debt inventory, and code-level risks for `jobservice-integration_LIB` are **identical to `jobserviceintegration_LIB`**.

See `E:\OnbeEast363\analysis\per-repo\jobserviceintegration_LIB\05_solution_architect.md` for the full analysis.

## Technical Architecture

Same as sibling:
- Java 1.6, no framework, Apache Commons Logging
- `BatchFile` fixed-width record writer
- Per-client converter modules with `main(String[] args)` entry points
- `Hashtable` / `Vector` data structures
- Filesystem I/O only

## API Surface

Identical to `jobserviceintegration_LIB` — `BatchFile` write methods, `ChryslerFileConverter.processFile()`, and `main()` entry points per client module.

## Security Posture

Identical to `jobserviceintegration_LIB`:
- No authentication or authorisation
- No encryption
- Log4j 1.2.15 binary JAR present (CVE-2019-17571 — critical)
- Hibernate 3.2.0.cr5, Acegi Security 1.0.3 JARs in BulkCardGen

## Technical Debt

Identical to `jobserviceintegration_LIB`. Key items:
- Java 1.6 EOL (Critical)
- Log4j 1.x binary in SCM (Critical)
- Binary JARs (Critical)
- `System.exit()` in library code (High)
- Off-by-one substring bugs in `BatchFile.java` (Medium)
- Copy-paste bug: `otherAreaCode` reads same field as home area code (Medium)
- SNAPSHOT version, no unit tests (High)

## Duplicate Artifact Risk (Additional Technical Debt)

Both this repo and `jobserviceintegration_LIB` define:
```xml
<groupId>com.ecount.service</groupId>
<artifactId>jobserviceintegration</artifactId>
<version>1.0.1-SNAPSHOT</version>
```
Publishing both to the same Maven repository results in one overwriting the other non-deterministically.

## Gen-3 Migration Requirements

Same as `jobserviceintegration_LIB`. Priority action: consolidate with `jobserviceintegration_LIB` before any migration work begins.

## Code-Level Risks (File:Line References)

Same as `jobserviceintegration_LIB`:

| Risk | File | Line |
|---|---|---|
| `System.exit(-1)` in library code | `chrysler/src/main/java/com/ecount/fileconversion/chrysler/ChryslerFileConverter.java` | 116 |
| `System.exit(1)` in library code | `chrysler/src/main/java/com/ecount/fileconversion/chrysler/ChryslerFileConverter.java` | 81 |
| Off-by-one `substring(16)` | `Common/src/main/java/com/ecount/jobintegration/common/BatchFile.java` | 143 |
| Log4j 1.2.15 CVE JAR | `alg/common/log4j-1.2.15.jar` | N/A — binary |
| Copy-paste bug: `otherAreaCode` = `FIELD_CONTACT_HOMEAREACODE` | `chrysler/src/main/java/com/ecount/fileconversion/chrysler/ChryslerFileConverter.java` | 469 |
