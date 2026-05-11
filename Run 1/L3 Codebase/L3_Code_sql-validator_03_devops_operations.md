# sql-validator — DevOps / Operations View

## Build System
- **Build tool**: Apache Maven
- **POM**: `com.onbe.sqlmcp:sql-validator:1.0-SNAPSHOT`, packaging `jar`
- **Java version**: 17 (source/target)
- **Module system**: Java Platform Module System (JPMS) — `module-info.java` present
- **Dependencies**:
  - `com.github.jsqlparser:jsqlparser:5.3` — SQL parser
  - `org.slf4j:slf4j-simple:1.7.36` — logging
  - `org.jspecify:jspecify:1.0.0` — null-safety annotations
  - JUnit Jupiter 5.10.0 (test scope)

## CI/CD Pipeline
No CI/CD pipeline definitions (GitHub Actions, Jenkins, Azure DevOps) are present in the repository. The `docs/code-review-tasks-2023-11-15-14-00-00.md` file implies the repository was created with some code review activity in late 2023 but no automated pipeline was set up.

AI-assistant guidelines are present (`.ai/`, `.github/copilot-instructions.md`, `.junie/guidelines.md`), suggesting AI-assisted development tooling is configured for this repository.

## Deployment
JAR library (`1.0-SNAPSHOT`). Deployment mechanism not defined — no Maven repository publishing configuration in `pom.xml`. The version `1.0-SNAPSHOT` indicates it has never been formally released.

## Configuration Management
No external configuration. All behaviour is controlled by `SqlSafetyConfig` static constants. No property files, YAML, or environment variable references.

## Observability
- `slf4j-simple:1.7.36` is included as a runtime dependency. No logging calls are made within the library itself — all error reporting is via `AnalyzeException` throws.
- `TraverseAll.java` contains `System.out.println()` debug statements at every AST node visit (e.g., `"Visiting PlainSelect"`, `"Visiting Column: ..."`) — these will produce verbose stdout output in any environment where the library is used.

## Infra Dependencies
None. The library operates entirely in memory with no network or file system access.

## Operational Risks
| Risk | Severity | Notes |
|---|---|---|
| `System.out.println` debug output | High | `TraverseAll.java` prints to stdout for every AST node — significant log noise and performance overhead in production |
| `1.0-SNAPSHOT` version | Medium | SNAPSHOT artifacts are unstable by definition; callers may receive different behaviour from the same version string |
| No CI/CD pipeline | Medium | No automated build, test, or publish pipeline — quality gate not enforced |
| `slf4j-simple` in library | Low | Embedding `slf4j-simple` in a library is an anti-pattern — it takes over SLF4J binding for the consuming application |
| No Maven publish configuration | Medium | Library cannot be distributed to Onbe's internal Maven repository without adding distributionManagement |

## Recommendations
1. Remove or gate `System.out.println` statements in `TraverseAll.java` behind a logger with DEBUG level.
2. Replace `slf4j-simple` with `slf4j-api` only (no implementation) — let consuming applications choose their logger binding.
3. Bump version from `1.0-SNAPSHOT` to `1.0.0` and publish to Onbe's GitHub Packages Maven registry.
4. Add a GitHub Actions workflow matching the pattern in `spring-utils_LIB` (CodeQL + publish).
5. Add Dependabot configuration for automated CVE patching of jsqlparser.
