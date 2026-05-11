# Enterprise Architect Analysis — endclient-relationship-backfill-generator

## Repository Overview

**Repo:** `endclient-relationship-backfill-generator`
**Classification:** Internal operational tooling — data migration / backfill utility
**Platform generation:** Pre-Gen-3 (supports legacy relational model; no microservice, no REST, no event streaming)

---

## Platform Generation and Architectural Positioning

This repository sits firmly in what Onbe's platform evolution would classify as **Gen-1 / legacy operational tooling**. It is a single-class Java CLI that directly manipulates SQL Server tables — the same `dbo.program_promotion` and `dbo.program_relationship_map` tables that are part of the legacy prepaid promotion data model managed by older Struts/Spring-XML applications.

Its existence reflects the **seam between platform generations**: a new concept (end-client relationship ID) has been introduced into the data model, but historical records pre-date this concept and must be retroactively migrated. This is a classical data-layer backfill pattern in enterprise platform transitions.

### Platform Generation Matrix

| Attribute | This Repo | Gen-2 Target | Gen-3 Target |
|-----------|-----------|--------------|--------------|
| Architecture style | CLI utility | Spring Boot REST | Spring Boot + Dapr sidecar |
| Deployment | Manual JAR execution | WAR / containerised | Kubernetes pod |
| Data access | Offline SQL generation | JPA / Spring Data | JPA + event sourcing |
| Testing | None | JUnit | JUnit + Cucumber BDD |
| CI/CD | None | Jenkins / GitLab | GitHub Actions / CodeQL |

---

## Enterprise Architecture Concerns

### 1. Data Model Governance

The tool directly targets `dbo.program_relationship_map`, a table that represents a core business concept — the binding of promotions to end-client relationships. Any tool that manipulates this table without transactional integrity controls or audit trail is a **data governance risk**. In an enterprise with SOC 1 / SOC 2 obligations, all changes to this kind of master-reference data should be:
- Tracked in a change management system (e.g., ServiceNow).
- Subject to peer review.
- Executed in a controlled maintenance window.
- Verified by automated row-count checks post-execution.

This tool provides none of these controls natively.

### 2. Cross-System Dependency

The tables targeted (`dbo.program_promotion`, `dbo.program_relationship_map`, `dbo.programs`) are shared with the legacy enrollment and promotion management systems. Any schema change in these tables — such as adding a `NOT NULL` column — will break the positional INSERT at line 40 of `EndClientRelationshipScriptGenerator.java` silently (by generating syntactically valid but semantically wrong SQL). Enterprise architecture should enforce a **schema registry** or migration-management tool (e.g., Liquibase, as used in the Gen-3 exemplar services) to version-control these tables.

### 3. Placement in Application Landscape

| Layer | Component |
|-------|-----------|
| Data layer | SQL Server (`dbo.*` tables — legacy prepaid schema) |
| Processing | `EndClientRelationshipScriptGenerator.java` (this repo) |
| Downstream consumers | Enrollment extract process, promotion management APIs |

The tool is a **point-in-time operational utility**, not a reusable service. It should be catalogued in the enterprise application inventory as a "runbook tool" rather than a managed service.

### 4. Technology Lifespan

- **Java 21** — Current LTS; appropriate.
- **Maven + `commons-cli`** — Minimal, appropriate for a CLI tool.
- **No Spring, no ORM** — Intentional simplicity; appropriate for a one-shot tool.
- **No fat-JAR configuration** — Operational gap (see DevOps analysis).

### 5. Alignment with Onbe's Strategic Direction

Onbe's Gen-3 architecture (as evidenced by `exemplar-customer-service_WAPP` and `exemplar-cross-border-transfer-service_WAPP`) moves towards:
- Event-driven microservices with Dapr.
- Kubernetes deployment.
- Liquibase-managed schema migrations.
- Automated test coverage enforcement (JaCoCo thresholds).

This tool predates and is architecturally inconsistent with Gen-3 patterns. In the Gen-3 world, the equivalent operation would be a **Liquibase changeset** or a **Spring Batch job** with idempotency guards and audit logging, not a hand-crafted SQL generator.

---

## Recommendations

1. **Retire the tool** — once the backfill is complete and verified, archive this repository. Document the final execution artifact in the change management system.
2. **If repeated use is needed** — refactor as a Spring Batch step that connects directly to the database, uses parameterised SQL, enforces idempotency, and writes to the corporate audit log. This would align with the `cross-border-transfer-service-batch` pattern.
3. **Schema governance** — register the target tables in Liquibase so any future schema change is tracked and downstream tools can be notified.
4. **Document data lineage** — in the enterprise data catalogue, record that `dbo.program_relationship_map` was backfilled by this tool, including the date and version of the input CSV.

---

## Risk Summary

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Duplicate inserts on re-run | High | High | Add `WHERE NOT EXISTS` guard |
| Schema drift breaks positional INSERT | Medium | High | Add explicit column list; register table in Liquibase |
| Unauthorised execution | Low | Critical | Gate behind change management ticket |
| PCI scope data exposed in CSV | Low | High | Verify CSV contains no cardholder data (programme IDs are not PANs) |
