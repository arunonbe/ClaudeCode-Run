# sql-validator — Enterprise Architect View

## Platform Generation
**Gen-3 / New tooling.** Evidence:
- Package root `com.onbe.sqlmcp` (`onbe` brand namespace, `mcp` = Model Context Protocol) — distinct from Gen-1/2 `com.citi.prepaid` namespace
- Java 17 with JPMS module system — modern Java
- `jspecify` null-safety annotations — modern API design practice
- JUnit Jupiter 5.10 — modern test framework
- Created in context of AI/LLM integration (MCP), not legacy Gen-2 service migration
- No Spring dependency, no JMS, no XStream

## Business Domain
Security tooling / AI safety layer. Specifically: SQL safety enforcement for AI-generated or user-supplied SQL queries in the context of Onbe's data access infrastructure.

The `com.onbe.sqlmcp` namespace strongly implies this is part of an MCP (Model Context Protocol) integration that allows AI agents to query Onbe databases. The validator is the security gate that stands between AI-generated SQL and database execution.

## Role in Ecosystem
| Role | Description |
|---|---|
| Security gate | Validates and blocks unsafe SQL before execution against Onbe databases |
| AI/LLM safety layer | Intercepts AI-generated SQL in MCP flows — prevents prompt injection leading to SQL injection |
| Compliance enabler | Enforces read-only, allowlisted table access — supports least-privilege principle for automated data access |
| Shared library | Designed to be consumed by multiple services/tools that expose SQL execution capability |

## Dependencies
| Dependency | Version | Notes |
|---|---|---|
| JSQLParser | 5.3 | Core SQL parsing engine — the library's most critical dependency; must be kept up-to-date |
| SLF4J Simple | 1.7.36 | Should be replaced with SLF4J API only for library distribution |
| JSpecify | 1.0.0 | Null safety annotations |

## Integration Patterns
| Pattern | Description |
|---|---|
| Library (JAR) | Synchronous Java method call — `SqlQueryValidator.validateQuerySecurely(sql, dbType, allowedTables)` |
| Exception-based rejection | `AnalyzeException` (unchecked) signals rejection — caller must catch and handle |
| Visitor pattern | Internal AST traversal uses visitor pattern (`TraverseAll` + `AnalyzerVisitor` implementations) |

## Strategic Status
| Dimension | Assessment |
|---|---|
| Maturity | Early — `1.0-SNAPSHOT`, no published release, no CI/CD |
| Strategic value | High — critical safety control for any AI/automated SQL execution at Onbe |
| Uniqueness | Bespoke implementation; alternatives exist (e.g., commercial SQL firewall tools, JSQLParser-based open source validators) |
| Recommended action | Stabilise (remove debug output, publish release), integrate into MCP data-access layer, add to security architecture review as a PCI DSS Req 6.2.4 control |

## Migration Blockers
None — this is new Gen-3 tooling. It is itself a migration enabler (guards Gen-3 AI data access patterns). No legacy dependencies to remove.
