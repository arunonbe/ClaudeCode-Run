# Enterprise Architect Report: terraform-ecs-service_INFRA_TF

## Platform Generation

**Gen-2 (Wirecard/Northlane) AWS infrastructure pattern**. This Terraform module reflects the Gen-2 adoption of Infrastructure-as-Code using Terraform on AWS ECS. The Gen-2 platform moved services from traditional VM-based deployments to Docker containers on ECS (using Fargate or EC2 launch type), and this module is the shared IaC component that standardises that deployment pattern. The `master` branch name (vs. `main`) and the absence of GitHub Actions workflows are also consistent with a Gen-2-era repository.

The module predates the Gen-3 Azure migration — Gen-3 services use Azure Kubernetes Service (AKS) and Azure Terraform modules, not AWS ECS. This module is therefore relevant only to the Gen-2 AWS-hosted services, which are coexisting with Gen-3 Azure-hosted services during the migration period.

## Integration Patterns

- **Terraform module**: Consumed by calling root Terraform configurations via a `source` reference to this repository; no API, no HTTP endpoint
- **ECS integration**: Provisions `aws_ecs_task_definition` and `aws_ecs_service` resources; integrates with the caller-provided ECS cluster, IAM role, VPC networking, and load balancer target groups
- **CloudWatch Logs**: Log driver configured via `awslogs`; logs flow to CloudWatch under a workspace-namespaced log group
- **Secrets management**: The `env_secrets` variable references AWS Secrets Manager or SSM Parameter Store secrets by ARN; ECS retrieves these values at task startup

## External Dependencies

- AWS ECS cluster (caller-provided via `ecs_cluster_id`)
- AWS IAM role (caller-provided via `ecs_role`; used for both task runtime and execution permissions)
- AWS VPC resources: subnets (`app_subnets`) and security groups (`service_security_groups`) — caller-provided
- AWS Application Load Balancer target groups (caller-provided via `target_group_arn`)
- AWS CloudWatch Logs (created by module)
- Container registry (caller-provided `ecs_image_repo`; could be ECR, Docker Hub, or GitHub Container Registry)
- AWS Secrets Manager / SSM Parameter Store (for secrets referenced in `env_secrets`)

## Position in the Broader Platform

This module is the **Gen-2 AWS ECS deployment standard**. It represents the standardisation layer between service teams (who build Docker images) and the AWS infrastructure (ECS, CloudWatch, VPC). Without it, each Gen-2 service team would write their own ECS Terraform code, creating inconsistency in log retention, networking, security group configuration, and IAM role attachment.

The module's existence is architecturally valuable — it enforces consistency. However, because all security-relevant decisions (IAM role, security groups, subnets, secrets vs. env_vars) are delegated to callers, its security value depends entirely on how callers use it.

Within the three-generation context:
- **Gen-1 services**: Deployed on VMs or via Tomcat/JBoss on-premises; do not use this module
- **Gen-2 services**: Use this module for ECS deployment on AWS; this is the active use case
- **Gen-3 services**: Use Azure AKS; use Azure Terraform modules; do not use this module

The platform therefore runs on two clouds simultaneously (AWS for Gen-2, Azure for Gen-3) during the migration period. This creates dual cloud management complexity and dual cloud cost.

## Migration Blockers for Gen-3

1. **AWS-Azure incompatibility**: Gen-2 services using ECS on AWS cannot be simply migrated to AKS on Azure; the entire infrastructure model changes (ECS tasks → Kubernetes pods, IAM roles → Managed Identities, Secrets Manager → Key Vault, CloudWatch → Azure Monitor)
2. **ECS service coupling**: Services that expose ports to other ECS services via security groups and VPC peering have internal dependencies that must be migrated simultaneously or via a bridge period with cross-cloud connectivity
3. **Log retention gap**: Services currently running with 14-day CloudWatch log retention would need their log retention policy extended or a log forwarding solution to Azure Log Analytics as part of migration

## Strategic Status

**Retain for Gen-2 lifespan; do not extend to new services**. This module should:
- Be fixed for its compliance gaps (log retention, IAM role separation, output sensitivity) for the duration of Gen-2
- Not be used for any new services; all new services must target Gen-3 (Azure/AKS) deployment patterns
- Be deprecated and archived when the last Gen-2 ECS service is migrated to Gen-3

Immediate improvements required:
1. Set log retention to 365 days (configurable with compliant default)
2. Split `ecs_role` into separate `task_role_arn` and `execution_role_arn` variables
3. Add Terraform version and provider version constraints
4. Add `sensitive = true` to the `definitions` output
5. Add a CI pipeline with `terraform validate`, `tfsec`, and `terraform-docs`
