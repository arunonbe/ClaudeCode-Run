# aml-name-screening_LIB — Enterprise Architect View

## Platform Generation (Gen-1/Gen-2/Gen-3)

**Generation: Gen-1 (legacy/pre-Onbe)**

Evidence:
- Package namespace `com.citi.prepaid` (Citi Prepaid branding, pre-Wirecard acquisition era).
- Authored June 2015 by TCS; no subsequent functional commits visible.
- Database host `ppamwdcpisql1b1.nam.nsroot.net` uses `nsroot.net` — the Citibank internal DNS domain — not an Onbe or Wirecard domain.
- Spring Framework 2.5.6 (released 2008) and Java 1.6 (released 2006) are Gen-1 vintage dependency choices.
- No REST API, no microservice packaging, no containerization — characteristics of pre-Gen-2 standalone batch tools.
- Maven `settings.xml` references both Wirecard Nexus (`wirecard.sys`) and Onbe GitHub Packages, suggesting the repo was carried forward through the Wirecard acquisition but never modernized.
- Artifact version remains `1.0.0-SNAPSHOT` — never formally released, consistent with a prototype or internal utility that never graduated to a production release cycle.

## Business Domain

**AML / Compliance — Cardholder Name Screening**

This library belongs to the **Risk & Compliance** subdomain within the Prepaid Payments platform. Its function — matching cardholder names against a watchlist — is a BSA/AML regulatory obligation. However, as noted in the BA view, the implementation performs internal database lookup only and does not integrate with a true OFAC/AML watchlist provider.

Within Onbe's current domain model, this function would logically reside in a **Compliance Services** capability alongside OFAC screening, SAR filing support, and transaction monitoring.

## Role in Platform

- **Type**: Standalone batch utility (JAR with `main` method), not a shared library despite the `_LIB` suffix in the repository name.
- **Consumers**: Unknown — no callers documented in the repository. Likely invoked manually or via a scheduled job on a Windows server by a compliance operations team.
- **Producers**: Reads from the `Ecountcore` SQL Server database, which is the core cardholder data store for the Gen-1 prepaid platform.
- **Integration point**: Direct SQL Server JDBC connection — no service layer, no messaging, no API gateway.
- **Criticality assessment**: The tool appears to be a compliance operations aid used by analysts, not a real-time control in the payment flow. Its failure does not directly block transactions.

## Dependencies

### Upstream (what this service depends on)
| Dependency | Type | Notes |
|-----------|------|-------|
| `Ecountcore` SQL Server (`fdr_dda_account_registration`) | Database | Citi/Wirecard-era cardholder DB, `nsroot.net` hostname |
| `NameScreening.properties` file | File system | Must exist at `C:\c-base\config\namescreening\` on the execution host |
| Input XLS file | File system | Operator-supplied, no SLA or format validation |
| Wirecard Nexus (`wirecard.sys`) | Artifact repository | Likely decommissioned |

### Downstream (what depends on this service)
- No programmatic consumers identified.
- Output is a file consumed manually by compliance analysts.

### Shared Libraries Consumed
| Library | Version | Onbe Standard? |
|---------|---------|---------------|
| Spring Framework | 2.5.6 | No (Onbe standard is Spring Boot 2.x/3.x) |
| Log4j 1.x | 1.2.15 | No (EOL, CVE-affected) |
| jTDS JDBC | 1.2.2 | No (deprecated; Microsoft JDBC driver is standard) |
| Jakarta POI | 3.0.1 | No (current standard is Apache POI 5.x) |
| Commons DBCP | 1.2.2 | No (superseded by HikariCP or DBCP2) |

## Integration Patterns

- **Pattern in use**: Batch file processing with direct JDBC database access. No messaging, no events, no APIs.
- **Antipatterns observed**:
  - Dynamic SQL construction via string concatenation — SQL injection risk and no use of prepared statements.
  - Direct `DriverManagerDataSource` (no connection pooling) — one connection per row.
  - Fat JAR with all dependencies bundled — dependency isolation is zero; any dependency conflict must be resolved at build time.
  - In-place file mutation — reads and overwrites the same XLS file; no atomic swap.
- **Gen-3 pattern gap**: Gen-3 expects REST microservices, event-driven integration (Kafka/messaging), and containerized deployment. This library uses none of these patterns.

## Strategic Status

**Status: Candidate for Decommission or Full Replacement**

Rationale:
1. The Ecountcore SQL Server (`nsroot.net`) is almost certainly not accessible in the current Onbe infrastructure environment, meaning the tool may already be non-functional.
2. The tool was never formally released (SNAPSHOT version, no release tag in git history visible).
3. A true AML name screening function requires integration with an external watchlist provider (e.g., Refinitiv World-Check, LexisNexis Bridger, Dow Jones Risk & Compliance). This tool provides none of that.
4. All dependencies are severely EOL and carry critical CVEs.
5. No tests, no CI build pipeline, no containerization — the tool cannot be safely operated or maintained in a modern platform.

If the compliance screening function is still needed, it must be rebuilt from scratch against a certified watchlist API with proper PII controls, audit logging, and case management integration.

## Migration Blockers

| Blocker | Description | Severity |
|---------|------------|----------|
| Defunct database host | `ppamwdcpisql1b1.nam.nsroot.net` is a Citi-era hostname, not resolvable in Onbe network | Critical |
| Java 1.6 compilation target | Cannot run on any modern JRE without compatibility flags; unsupported | Critical |
| No external watchlist integration | Tool does not satisfy the AML screening requirement it purports to fulfill | Critical |
| Hardcoded Windows path (`C:\c-base\`) | Cannot run in a Linux container without code changes | High |
| Credentials in source code | Must be removed and externalized before any production use | High |
| EOL Spring 2.5.6 | No security patches available; incompatible with Spring Boot 3.x migration | High |
| HSSF `.xls` format | Old binary Excel format; modern replacements use `.xlsx` (XSSF) or avoid Excel entirely | Medium |
| No unit tests | Cannot validate behavior during migration | Medium |
| No Docker/K8s packaging | Cannot deploy to Onbe's container platform without full repackaging | Medium |
