# om-east-deploy — Enterprise Architect View

## Strategic Role in the Platform

`om-east-deploy` represents Onbe's transition from fragmented, per-service deployment scripts toward a centralized, policy-driven deployment platform. In enterprise architecture terms it is a **deployment capability layer** — a horizontal platform concern that decouples deployment mechanics from application build pipelines. This pattern is foundational for a regulated financial services organization needing consistent, auditable change management across multiple service teams.

## Architectural Patterns

### Pattern 1: Declarative Configuration-Driven Deployment
The service YAML files (`services/*.yml`) are the single source of truth for deployment topology. This implements the **Infrastructure as Code** principle at the deployment configuration level — not at the infrastructure provisioning level (which is handled by separate Terraform repos visible in the broader repository list, e.g., `nlroot-aws_INFRA_TF`, `nlutil-aws_INFRA_TF`).

The pattern separates:
- **What** (artifact coordinates, version) — supplied at dispatch time
- **Where** (server list, paths, service names) — declared in `services/*.yml`
- **How** (stop/copy/start mechanics) — encapsulated in `om-ci-setup` composite actions

This separation enables service teams to own deployment topology without understanding deployment mechanics, and operations teams to own mechanics without understanding service specifics.

### Pattern 2: Centralized Orchestrator with Federated Execution
The repository is an orchestrator, not an executor. Actual deployment mechanics live in `om-ci-setup` composite actions. This implements a **Facade** pattern: `om-east-deploy` presents a stable deployment interface while `om-ci-setup` can evolve deployment implementations independently.

The risk of this pattern is tight coupling to `@main` of `om-ci-setup` — documented in the DevOps view. Enterprise governance would require pinning to versioned releases.

### Pattern 3: Environment Gating via GitHub Environments
GitHub Environments (`uat`, `qa`, `prod`) with required reviewers implement a **Policy Enforcement Point** pattern. This maps to PCI DSS Requirement 6.5 (changes are authorized and controlled) and to standard ITIL Change Management practices.

## Current State vs. Target State

| Dimension | Current State | Target State (Phase 5) |
|---|---|---|
| Scope | UAT only, single example service | All OM services, UAT/QA/prod |
| Deployment style | Stop, copy, start (Phase 1) | Rolling with App Gateway drain (Phase 2) |
| Trigger | Manual only | Manual + auto-promote SNAPSHOT to QA |
| Rollback | Manual break-glass | Automated rollback on failed mid-flight deploy (Phase 3) |
| Governance coverage | Partial (services not yet migrated) | Full coverage via Phase 5 migration |

## Integration with Enterprise Governance

### Change Management
The workflow enforces a four-eyes principle: the person triggering the deploy is distinct from the required reviewer on the GitHub Environment (for UAT this is the East Deploy Team). For production, this will satisfy segregation-of-duties requirements.

### Artifact Governance
By requiring artifacts to exist in `maven.pkg.github.com/onbe/onbe_maven_releases` before deployment, the system ensures only built, tested artifacts reach environments. The registry is the control gate — unauthorized artifacts cannot be deployed through this workflow.

### PCI DSS Alignment

| PCI DSS Requirement | Alignment |
|---|---|
| 6.3.2 — Inventory of bespoke software | `services/*.yml` files serve as the inventory of deployed components |
| 6.5.1 — Security policies and procedures for deployment | Approval gates on GitHub Environments enforce authorization |
| 10.2.1 — Audit log entries for system access | GitHub Actions workflow logs provide immutable deployment records |
| 12.3.2 — Risk assessments for changes | Manual dispatch + approval gate supports this; automated risk assessment not implemented |

## Technology Choices and Rationale

### GitHub Actions (CI/CD Platform)
Chosen as the CI/CD platform aligning with the broader Onbe East engineering organization (observable from `.github/workflows/` directories across all analyzed repos). GitHub Actions provides native integration with GitHub Packages (artifact registry) and GitHub Environments (approval gates).

### yq for YAML Processing
`yq` v4.44.3 is used to parse service configs. It is a well-maintained YAML processor with a jq-style query language. The choice avoids shell-based YAML parsing (fragile) or requiring Python/Ruby on the runner. The runtime download pattern is operational debt — the runner image should include `yq`.

### Maven Dependency Plugin for Artifact Fetch
Using `maven-dependency-plugin:copy` for artifact retrieval is idiomatic for Maven-based artifact registries and avoids building a custom download mechanism. It correctly handles SNAPSHOT vs. release version semantics.

### Windows Tomcat Deployment Target
The deployment target is Windows-hosted Apache Tomcat — a traditional Java EE deployment pattern. This reflects the East-region platform's heritage as a Wirecard-era system. The presence of `nam.wirecard.sys` domain names in server configurations confirms this is legacy infrastructure. The roadmap phases suggest this model is being maintained and modernized (rolling deploys, Azure App Gateway) rather than containerized, which contrasts with the containerized deployment pattern visible in `om-payment-api` (Dockerfile, docker-compose.yml).

## Architectural Concerns and Recommendations

1. **Hybrid deployment model risk**: `om-payment-api` has a Dockerfile and Dapr components, suggesting containerization is underway for newer services. `om-east-deploy` targets traditional Tomcat on Windows. As the platform modernizes, a single deployment orchestrator will need to support both paradigms, or the architecture will bifurcate.

2. **No dependency graph management**: There is no mechanism to express or enforce service deployment ordering. If service A depends on service B's schema migration, deploying A before B would cause runtime failures. Enterprise-grade deployment orchestrators (e.g., Spinnaker, ArgoCD) handle this; the current model relies on human coordination.

3. **Single region**: The name `om-east-deploy` implies a West or other regional peer. Whether a corresponding `om-west-deploy` exists or is planned is not visible from this repo. Active-active multi-region deployment coordination would require a higher-level orchestration layer.

4. **Secret rotation**: Windows domain credentials (`QA_EAST_DEPLOY_PASSWORD`, `PROD_EAST_DEPLOY_PASSWORD`) stored as GitHub org secrets require manual rotation and do not integrate with enterprise secrets management platforms (e.g., HashiCorp Vault, Azure Key Vault). Phase 2 introduces Azure service principals, which can be managed via Azure AD and are more amenable to automated rotation.
