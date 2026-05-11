# DevOps & Operations Report: terraform-ecs-service_INFRA_TF

## IaC Patterns

This is a pure Terraform module repository — three files, no application code:

- **`main.tf`**: Resource definitions (CloudWatch log group, ECS task definition, ECS service)
- **`variables.tf`**: Input variable declarations
- **`output.tf`**: Output value declarations

The module follows standard Terraform module conventions: it is designed to be referenced by other Terraform root configurations using a `module` block with the repository as a source. There are no `provider` or `backend` blocks — these are the responsibility of the calling root module.

**Workspace usage**: The module uses `terraform.workspace` for log group naming (`/${terraform.workspace}/service/${var.service_name}`), indicating the module supports Terraform workspace-based environment separation (e.g., `dev`, `qa`, `staging`, `prod` workspaces).

## State Management

No backend configuration is present in this module. State management risks:

- The module produces Terraform state that includes the full `container_definitions` JSON (which may contain plaintext `env_vars`)
- If root modules using this module store state locally, the state file is unencrypted and not team-sharable
- If remote state is used (S3 with DynamoDB locking — the AWS standard pattern), the state bucket's encryption and access control settings determine the security of any sensitive values captured in state
- The `definitions` output (`output.tf`, line 6) exposes the full container definition JSON; root module state will contain this value

**Recommendation**: The module should declare the `definitions` output as `sensitive = true` to suppress it from Terraform plan output and mark it as sensitive in state handling.

## Secrets in Terraform Files

No hardcoded credentials or secrets are present in any `.tf` file — this is correct. The module correctly separates:
- Plaintext environment variables: passed via `var.env_vars` (JSON string)
- Secrets: passed via `var.env_secrets` (JSON string referencing SSM/Secrets Manager ARNs)

The actual secret values never appear in the Terraform files themselves. However, if callers (root modules) hardcode values into `env_vars` that should be secrets, those values would appear in the caller's Terraform configuration — a problem in the caller, not in this module.

## CI/CD Pipeline

No CI/CD configuration files are present in this repository (no GitHub Actions workflows, no `Jenkinsfile`, no `.gitlab-ci.yml`). This is consistent with a reusable Terraform module that is called by other root configurations rather than deployed independently. However, the absence of CI means:
- No automated `terraform validate` or `terraform fmt` checks
- No static analysis (`tflint`, `tfsec`, `checkov`) to catch misconfigurations before they are merged
- No automated documentation generation (e.g., `terraform-docs`)

## Runtime and Version Management

No `required_providers` or `required_terraform` version constraints are declared in any file. This means:
- The module can be used with any Terraform version, including older versions with different behaviour
- The `aws` provider version is unconstrained; a major provider version upgrade could introduce breaking changes
- Dependabot or similar cannot automatically propose provider version updates
- `hashicorp/aws` provider version pinning is a best practice that is absent here

The absence of version constraints is particularly risky for a shared infrastructure module; if one team uses it with Terraform 0.13 and another with Terraform 1.5, they may see different behaviour from the same module code.

## Observability

The module creates a CloudWatch log group and configures the container to use the `awslogs` log driver. The multiline pattern (`multiline_pattern` variable with a timestamp-based default regex) handles multi-line log messages correctly for structured logging.

Log group retention is hardcoded at 14 days (`main.tf`, line 3) — insufficient for PCI DSS compliance (12 months required). This should be a variable with a default of 365 days, with the option for calling modules to specify shorter retention for non-PCI workloads.

## Deployment Controller and Rollback

`deployment_controller { type = "ECS" }` (standard ECS rolling deployment). This means:
- During deployment, ECS replaces old tasks with new ones
- No blue/green deployment support (would require CodeDeploy deployment controller)
- Rollback requires re-applying Terraform with the previous image version
- The `lifecycle { ignore_changes = [desired_count] }` block prevents Terraform from overriding ECS Auto Scaling's desired count, which is correct but means Terraform cannot be used to scale services manually

## Operational Gaps

1. No version constraints on Terraform or AWS provider — non-deterministic behaviour across teams
2. No automated validation in CI — module changes are not tested before use
3. 14-day log retention hardcoded — non-compliant for PCI DSS workloads
4. No `sensitive = true` on `definitions` output — plaintext env vars visible in plan output
5. Same IAM role for task and execution — violates least-privilege separation
6. No documentation via `terraform-docs` or equivalent
