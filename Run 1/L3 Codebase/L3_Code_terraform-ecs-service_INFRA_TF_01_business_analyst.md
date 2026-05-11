# Business Analyst Report: terraform-ecs-service_INFRA_TF

## Business Purpose

terraform-ecs-service_INFRA_TF is a reusable Terraform module that provisions AWS Elastic Container Service (ECS) infrastructure for containerised services in the Onbe platform. It is a generic, parameterised infrastructure template — not tied to any specific business service — that ECS-hosted services use as a building block to define their task definitions, ECS services, networking, and CloudWatch log groups. This module represents the Gen-2 deployment infrastructure pattern for services running on AWS ECS (Fargate or EC2 launch types).

## Capabilities

The module provisions:
- **CloudWatch Log Group**: Named `/{workspace}/service/{service_name}` with 14-day log retention
- **ECS Task Definition**: Defines the container specification including image reference, CPU/memory allocation, port mappings, command, environment variables, secrets (via ECS secrets mechanism), and CloudWatch log configuration with multiline log pattern support
- **ECS Service**: Configures the service cluster membership, desired instance count, launch type (Fargate/EC2), network configuration (security groups, subnets), and optionally attaches to one or more load balancer target groups

## Client and Cardholder Impact

As infrastructure-as-code, this module does not directly interact with cardholder data. However, the infrastructure it provisions runs services that do. The security configuration of the ECS task (IAM role, security groups, subnets, secrets) directly determines the security posture of every service deployed through this module. A misconfigured module could expose services to the internet, grant overpermissive IAM rights, or fail to inject secrets correctly.

## Business Rules in Infrastructure Code

- `assign_public_ip = false`: Containers are placed on private subnets only — no direct internet exposure
- `desired_count` is lifecycle-ignored: ECS Auto Scaling manages the actual task count; Terraform won't reset counts set by the scaler
- Load balancer attachment is dynamic (`for_each = var.target_group_arn`): a service can attach to zero or more load balancers/target groups
- Deployment controller is standard ECS (not CodeDeploy rolling); this means deployments replace tasks directly
- Log retention: 14 days for CloudWatch logs; this is short for a payments company — PCI DSS Requirement 10.7 requires audit logs be retained for at least 12 months (3 months immediately available)

## Regulatory Obligations

- **PCI DSS Requirement 1 (Network)**: The module's security group and subnet variables (`service_security_groups`, `app_subnets`) determine network segmentation; correct values are essential for CDE network isolation
- **PCI DSS Requirement 2 (Secure config)**: The module's variable design means the ECS role ARN is caller-supplied; the IAM role's permissions are not controlled by this module — overpermissive roles can be passed in
- **PCI DSS Requirement 6 (Secure systems)**: The container image (`ecs_image_repo/app_image:service_version`) is caller-supplied; image provenance and vulnerability scanning are responsibilities of the calling module, not this one
- **PCI DSS Requirement 10 (Logging)**: 14-day CloudWatch log retention is insufficient for PCI DSS compliance; logs must be retained for 12 months

## Key Business Risks

1. **14-day log retention**: CloudWatch log groups created with `retention_in_days = 14` (`main.tf`, line 3) do not meet PCI DSS Requirement 10.7 (12-month minimum); any service using this module has non-compliant log retention
2. **No Terraform state configuration**: No `backend.tf` or `terraform.tf` is present in this module; state management is left entirely to the caller. If callers use local state, team collaboration and audit trail are broken; if remote state is used, the state files may contain sensitive values from `env_vars` and `env_secrets`
3. **`env_vars` and `env_secrets` as strings**: Both environment variables and secrets are passed as pre-formatted JSON strings (`"environment": ${var.env_vars}`, `"secrets": ${var.env_secrets}`); there is no type validation, schema enforcement, or access restriction on what values callers place in these variables. If secrets are passed as `env_vars` (plaintext) rather than `env_secrets` (ECS secrets from SSM/Secrets Manager), they will be visible in ECS task definition metadata
4. **Single IAM role for task and execution**: `task_role_arn` and `execution_role_arn` are both set to `var.ecs_role` — the same role is used for both the container's runtime permissions and the ECS service's permission to pull images and write logs. Best practice requires separate roles with least-privilege permissions for each purpose
