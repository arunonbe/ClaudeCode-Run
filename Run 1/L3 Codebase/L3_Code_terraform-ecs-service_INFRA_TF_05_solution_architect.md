# Solution Architect Report: terraform-ecs-service_INFRA_TF

## API Surface

This Terraform module has no HTTP API surface. Its interface is:

**Inputs** (`variables.tf`): 19 variables parameterising the ECS task definition and service

**Outputs** (`output.tf`): 4 outputs exposing provisioned resource attributes

**Resources provisioned** (`main.tf`):
- `aws_cloudwatch_log_group.service_loggroup`
- `aws_ecs_task_definition.service_task_definition`
- `aws_ecs_service.service`

## Security Posture

**Medium risk as a module; downstream risk is high depending on caller configuration.**

The module itself contains no hardcoded credentials, no access keys, and no static secrets — this is correct. Its security posture is largely determined by how callers instantiate it.

**Inherent security weaknesses in the module design:**

1. **Same IAM role for execution and task**: `task_role_arn` and `execution_role_arn` are both set to `var.ecs_role` (line 12–13 in `main.tf`). The execution role (used by ECS to pull images and write logs) should have minimal permissions (`ecr:GetAuthorizationToken`, `logs:CreateLogStream`, `logs:PutLogEvents`). The task role (used by the container at runtime) has the permissions needed for the application. Merging them means the container's runtime role also has the permissions to pull its own image and write logs — typically over-permissive for the runtime role

2. **`env_vars` accepts arbitrary JSON string**: The `"environment"` field in the container definition is set directly from `var.env_vars`; there is no schema validation, no type checking, and no warning if a caller places a secret value as a plaintext environment variable. ECS task definitions are visible in the AWS Console and CloudTrail — plaintext secrets in `environment` are fully visible to anyone with ECS DescribeTaskDefinition permissions

3. **`env_secrets` accepts arbitrary JSON string**: Similarly unvalidated. The correct format is `[{"name": "VAR_NAME", "valueFrom": "arn:aws:secretsmanager:..."}]`; if a caller provides malformed JSON, the task definition will be invalid and the service will fail to deploy

4. **Log retention hardcoded at 14 days**: Non-compliant for PCI DSS; creates risk of log loss before required retention period

## Critical Findings

1. **CloudWatch log retention: 14 days** (`main.tf`, line 3):
   ```hcl
   retention_in_days = 14
   ```
   - PCI DSS Requirement 10.7 requires 12 months (365 days) minimum log retention with 3 months (90 days) immediately accessible
   - Every ECS service deployed through this module has non-compliant log retention
   - Severity: **HIGH** — affects every service using this module

2. **Same IAM role for task and execution** (`main.tf`, lines 12–13):
   ```hcl
   task_role_arn       = var.ecs_role
   execution_role_arn  = var.ecs_role
   ```
   - Violates least-privilege principle (PCI DSS Req 7); the container runtime inherits image-pull permissions and log-write permissions
   - Any service using an overpermissive `ecs_role` (e.g., broad S3 or RDS access) also grants those permissions to the ECS execution mechanism
   - Severity: **MEDIUM** — scope depends on how callers configure the role

3. **`definitions` output not marked sensitive** (`output.tf`, lines 5–7):
   ```hcl
   output "definitions" {
       value = aws_ecs_task_definition.service_task_definition.container_definitions
   }
   ```
   - If `env_vars` contains any sensitive value, `definitions` exposes it in `terraform plan` output, CI logs, and remote state without the protection of `sensitive = true`
   - Severity: **MEDIUM** — depends on caller usage of `env_vars`

4. **No Terraform or provider version constraints**:
   - No `required_version` or `required_providers` block in any file
   - Module behaviour may differ between Terraform 0.13 and 1.x; `for_each = var.target_group_arn` on a `dynamic` block may behave differently across versions
   - Severity: **LOW** for security, **HIGH** for operational reliability

5. **Multiline log pattern default matches timestamp format** (`variables.tf`, lines 54–56):
   - Default pattern `^\\[[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2},[0-9]{3}\\]` is specific to a particular log format; services with different log formats must override this variable or multi-line log events will be split incorrectly, breaking log parsing and security event detection

## Technical Debt

- **No input validation**: Terraform `validation` blocks (available since Terraform 0.13) could validate that `env_secrets` is valid JSON and that `env_vars` does not contain obviously sensitive keys (e.g., `PASSWORD`, `SECRET`, `KEY`). None are present
- **No module versioning**: The module has no `CHANGELOG` and no Git tag-based versioning; callers that reference the module by branch name (`?ref=master`) will pick up breaking changes silently
- **No `terraform-docs` generation**: Documentation for variables and outputs must be maintained manually; the README exists but contains no module usage example
- **`run_cmd` is a string variable**: The command is passed as a JSON string (`${var.run_cmd}` in the container definition); if a caller injects a malicious or incorrectly formatted command, the ECS task will fail to start with an obscure error
- **`desired_count` lifecycle ignore**: While correct for allowing ECS auto scaling, this means Terraform cannot be used to scale down a runaway service — an operator must manually adjust the ECS service desired count; there is no Terraform-managed scaling policy in this module
