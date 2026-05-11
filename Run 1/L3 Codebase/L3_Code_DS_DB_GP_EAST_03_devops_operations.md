# DS_DB_GP_EAST — DevOps / Operations View

## 1. Build System

**No build system artefacts are present.** There is no `.sqlproj` file, no solution file, and no source SQL scripts. The repository cannot be built, tested, or deployed from source.

---

## 2. CI/CD Pipeline

**No CI/CD pipeline configuration is present.** No `.gitlab-ci.yml`, `Jenkinsfile`, Azure Pipelines YAML, or equivalent was found.

---

## 3. Database Change Management

**No change management artefacts are present.** Because there are no SQL objects in the repository:
- There are no migration scripts.
- There are no DACPAC baselines.
- There is no schema versioning.

Any changes made to the production EAST region GP database are made directly on the server without version-controlled source representation. This is a **significant operational and compliance risk**.

---

## 4. Git History

The git log shows a `main` branch with a single commit (based on the packed-refs file referencing a single object in the `.promisor` pack). The repository was likely created and given a README in a single commit, with no subsequent content additions.

---

## 5. Operational Risks

| Risk | Severity | Detail |
|------|----------|--------|
| No source control for production database objects | Critical | Any procedures, views, or custom schema on the production EAST GP database have no version-controlled representation. Incident response, rollback, and audit are impossible without manual server access. |
| No CI/CD pipeline | High | Even if objects were added to the repo, there is no automated deployment mechanism. |
| Schema drift | High | Production database state is unknown from this repo alone. |
| No documentation beyond a one-line README | Medium | No information about deployment target, environment URLs, or responsible team. |
| Repository creates false sense of coverage | Medium | The existence of this repo may mislead auditors or team members into believing EAST-region GP customisations are under source control when they are not. |

---

## 6. Immediate Actions Required

1. **Conduct a schema comparison** between the production EAST-region GP company database and the sibling repos (ECAN, ECNT). Identify all custom objects (views, stored procedures, functions, triggers, tables) unique to EAST.
2. **Commit all custom objects** to this repository with appropriate SSDT project structure (matching ECAN/ECNT patterns).
3. **Create a `.sqlproj` file** using SSDT and organise objects by schema and type.
4. **Define a CI/CD pipeline** (or extend the existing GP pipeline pattern from ECAN/ECNT if one exists).
5. **Document the intended scope** — clarify whether EAST is a separate company database or an alias for ECAN+ECNT combined views.
