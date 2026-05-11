# DS_Gitlab-Demo-Branching — Data Architect Perspective

## Data Architecture Assessment

From a data architecture standpoint, `DS_Gitlab-Demo-Branching` contains no data assets, no schema definitions, no ETL logic, no data models, and no database artefacts. The repository is entirely composed of placeholder text files created for a GitLab workflow demonstration. There is nothing to assess in terms of data lineage, data quality, schema design, or data governance.

## Repository Content Summary

All eight files in the repository have been reviewed:
- `README.md` (44 bytes): Contains only a heading and "Delete me please."
- `this is my dev work.txt` (14 bytes): "demo blah blah"
- `this is moar work.txt` (19 bytes): "Hey this is my fix!"
- `change2.txt` through `change5.txt` and `change101.txt`: All zero bytes, empty.

No SQL scripts, XML schemas, data dictionaries, ER diagrams, ETL configurations, SSIS packages, SSRS reports, or any other data artefacts are present.

## Architectural Context and Significance

Despite containing no data content, this repository has indirect architectural significance as evidence of the Onbe Data Services team's adoption of GitLab for source control. The existence of a branching-strategy demo repository signals that the team was in the process of establishing version control discipline — a foundational prerequisite for a mature data architecture practice.

### Branching Strategy Implications for the Data Architecture

The data repositories analysed in this review (`DS_ETL_sykes`, `DS_ETL_warehouse`, and others) contain complex SSIS projects and SQL artefacts that benefit significantly from controlled branching:

1. **SSIS package versioning**: SSIS `.dtsx` files are XML and can be diff'd in Git, but merging concurrent changes to large packages (e.g., `ClaimablePaymentHistory.dtsx` at 654 KB) requires careful branch management to avoid conflicts.
2. **Environment promotion**: A branch strategy that mirrors environments — `feature/*` branches for development, `develop` for integration/QA, `main` for production — directly supports the multi-environment architecture observed in `DS_ETL_warehouse` (packages with `p-` production vs. `q-` QA connection strings).
3. **Schema change management**: Any DDL changes to `Ecountcore_SS` or `Prepaid_Warehouse` that must be co-ordinated with SSIS package changes require atomic branch-and-merge workflows to prevent schema-package version mismatches.

### GitLab Feature Branch Model

The demo files suggest the team demonstrated the following Git workflow:

```
main branch ─────────────────────────────────────>
              \                    /
               feature/dev-work -->
                         \         \
                          fix/moar-work -->
```

Files `this is my dev work.txt` and `this is moar work.txt` simulate commits to feature and fix branches respectively. The `change2.txt` through `change101.txt` files simulate a sequence of iterative changes, possibly committed to `develop` to demonstrate fast-forward or squash merges.

## Data Governance Observations

The demo repository's continued presence in the active GitLab namespace, un-archived, with a README saying "Delete me please." is itself a data governance observation: the organisation lacks a repository lifecycle management policy. A mature data governance framework would include:

1. **Repository classification**: All repos tagged as PROD, QA, DEMO, ARCHIVE, or DEPRECATED.
2. **Retention policy**: Demo repositories auto-archived after 90 days of inactivity.
3. **Namespace governance**: Data Services repositories grouped under a GitLab sub-group with enforced naming conventions.
4. **Access controls**: Demo repositories restricted to a training group, not accessible to the same audience as production code.

## Recommendation

From a data architecture perspective, this repository should be:
1. Archived immediately to remove it from active discovery and scanning.
2. Used as the basis for documenting Onbe Data Services' official branching strategy — a formal `.md` file describing branch naming conventions, merge request templates, reviewer requirements, and pipeline triggers.
3. Referenced in onboarding documentation as a historical example of how NOT to manage training artefacts in a production namespace.

The architectural lesson from this repository is not in its content, but in its existence: data teams need repository lifecycle governance as much as they need data governance. Unmanaged repositories accumulate in namespaces, consuming index space in CI/CD systems and potentially appearing in security scans or compliance inventories as unexplained artefacts.
