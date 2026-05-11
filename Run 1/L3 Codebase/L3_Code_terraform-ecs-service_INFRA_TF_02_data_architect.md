# Data Architect Report: terraform-ecs-service_INFRA_TF

## Data Models

This is an infrastructure-as-code repository; it has no application data models or database schemas. The "data" it handles is:
- Input variables (defined in `variables.tf`) that parameterise the infrastructure
- Output values (defined in `output.tf`) that expose provisioned resource attributes
- Terraform state (managed externally) that tracks the actual infrastructure vs. desired configuration

**Input variables** (from `variables.tf`):

| Variable | Type | Sensitivity |
|---|---|---|
| `region` | string | Low |
| `service_name` | string | Low |
| `service_version` | string | Low |
| `app_cpu` | string | Low |
| `app_memory` | string | Low |
| `app_count` | string | Low |
| `app_port` | string | Low |
| `app_image` | string | Low |
| `ecs_cluster_id` | string | Low |
| `ecs_image_repo` | string | Low |
| `ecs_role` | string | Medium (IAM ARN) |
| `env_vars` | string | **High if misused** |
| `env_secrets` | string | **High** |
| `run_cmd` | string | Medium |
| `service_security_groups` | list | Medium |
| `app_subnets` | list | Medium |
| `target_group_arn` | list(object) | Low |
| `launch_type` | string | Low |
| `multiline_pattern` | string | Low |

## Sensitive Data Concerns

**`env_vars` and `env_secrets`**: Both are typed as `string` in `variables.tf`, accepting pre-serialised JSON. The distinction between the two is critical for security:

- `env_vars` (line 46): passed into the container definition as plaintext environment variables: `"environment": ${var.env_vars}`. If a caller puts a database password or API key into `env_vars` instead of `env_secrets`, it is stored in plaintext in:
  - The ECS task definition (visible in AWS Console, CLI, CloudTrail)
  - The Terraform state file (potentially plaintext if using local or unencrypted remote state)
  - The CloudWatch log stream on startup if the service logs its environment

- `env_secrets` (line 51): passed as `"secrets": ${var.env_secrets}` in the ECS container definition. The ECS secrets mechanism references values in AWS Secrets Manager or SSM Parameter Store by ARN/name; the actual secret values are injected into the container at runtime by ECS and are not stored in the task definition or Terraform state. This is the correct pattern for credentials

**Risk**: The module design accepts both patterns but does not enforce that sensitive values use `env_secrets`; the distinction relies entirely on caller discipline.

## Terraform State Concerns

The module has no `backend` configuration. When called as a module, state is managed by the root module (caller). Terraform state contains:

- The full `container_definitions` JSON blob (which includes all `env_vars` in plaintext)
- All input variable values
- All output values

If the `env_vars` variable contains any sensitive value (a misconfiguration), that value is stored in Terraform state in plaintext. Terraform state files must be:
- Stored in an encrypted S3 bucket (with `server_side_encryption_configuration`)
- Access-controlled via S3 bucket policy and IAM
- State-locked via DynamoDB to prevent concurrent applies
- Never committed to version control

None of these requirements are enforced or documented by this module.

## CloudWatch Log Data

The module creates a CloudWatch log group at `/{workspace}/service/{service_name}` with 14-day retention. Logs from containerised services may contain:
- Application log messages with partial data references
- SQL query logs if debug logging is enabled
- Stack traces that reveal internal architecture
- Potentially sensitive data if services do not implement log masking (a common gap in Gen-1/Gen-2 services)

14-day retention (`main.tf`, line 3) is insufficient for PCI DSS Requirement 10.7 (12-month minimum retention with 3 months immediately accessible).

## Output Values

Outputs (`output.tf`) expose:
- `app_port`: the container port
- `definitions`: the full container definitions JSON (contains all env_vars and secrets ARNs)
- `revision`: the ECS task definition revision number
- `service_name`: the ECS service name

The `definitions` output exposes the complete container definition, including any plaintext environment variables — callers should treat this output as sensitive.

## PCI DSS Compliance Assessment

- **Req 3**: If any `env_vars` values contain credentials or sensitive data, they are stored in plaintext in Terraform state and ECS task definitions — a direct Req 3 violation
- **Req 10.7**: 14-day log retention violates the 12-month PCI DSS minimum
- **Req 7**: The IAM role ARN is caller-supplied; the module cannot enforce least-privilege — this must be governed at the calling module level
- **Req 1**: Security group and subnet configuration is caller-supplied; CDE isolation is not enforced by the module
