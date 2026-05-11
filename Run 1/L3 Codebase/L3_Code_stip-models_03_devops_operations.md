# stip-models — DevOps / Operations View

## Build System
None. No build files are present. The repository contains only a `.git/` directory with standard git hook sample files.

## CI/CD Pipeline
None. No workflow files, pipeline definitions, schema validation scripts, or code generation triggers are present.

## Deployment
Not applicable — no content to deploy or publish.

## Configuration Management
Not applicable.

## Observability
Not applicable.

## Infra Dependencies
None defined.

## Expected Pipeline Architecture (When Implemented)
For a models repository in a generated-code pattern, the expected CI/CD pipeline would be:

```
stip-models change (commit/PR)
    |
    v
Schema validation (linting, breaking-change detection)
    |
    v
Code generation (OpenAPI Generator / protoc / xjc)
    |
    v (option A: commit generated code)
Commit generated artifacts → stip-generated repository
    |
    v (option B: publish directly)
Publish generated JAR to Maven registry
    |
    v
Dependent services rebuild and test
```

## Operational Risks
| Risk | Severity | Notes |
|---|---|---|
| Repository is empty — no model definitions | Critical | STIP models do not exist; entire STIP code generation pipeline is blocked |
| No schema versioning strategy | High | Breaking schema changes with no versioning will break all consumers |
| No schema validation | High | Invalid schemas can silently generate broken code |
| No generation trigger | High | Even if models were added, no pipeline exists to generate `stip-generated` |

## Recommendations
1. Determine responsible team for STIP domain and assign ownership.
2. Define schema format decision (OpenAPI, Protobuf, XSD, JSON Schema) aligned with Gen-3 platform standards.
3. Implement a GitHub Actions workflow that:
   - Validates schema on PR
   - Runs breaking-change detection (e.g., `openapi-diff`, `buf breaking`)
   - Triggers code generation to `stip-generated` on merge to main
4. Add Dependabot or equivalent for generator tooling version management.
