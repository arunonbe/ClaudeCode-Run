# DevOps and Operations Analysis — nlutil-aws_INFRA_TF

## Repository Structure

```
main.tf                    — AWS provider
variables.tf               — Input variables (region, VPC CIDR, ChaosSearch creds, etc.)
locals-env.tf              — Subnet CIDR calculations, instance sizes per workspace
locals-svc.tf              — ECS service definitions (image, CPU, memory, env vars, secrets)
network-vpc.tf             — VPC module (public/private subnets, NAT, VPN)
network-securitygroups.tf  — Security groups for ECS and ALB
network-external-alb.tf    — Application Load Balancer + HTTPS listener + target groups
network-external-nlb.tf    — Network Load Balancer for Logstash Beats
compute-ecs.tf             — ECS cluster, launch configuration, autoscaling group
identity-iam-ecs.tf        — IAM roles and policies for ECS tasks and instances
data-ecr.tf                — ECR repositories
data-sqs.tf                — SQS queues
chaossearch.tf             — ChaosSearch S3 bucket integration
data.tf                    — Data sources (ACM cert, SSM parameter)
outputs.tf                 — EIP outputs
util.tfvars                — Variable values (CONTAINS HARDCODED CREDENTIALS)
services/main.tf           — ECS task definition and service module
services/output.tf         — Module outputs
services/variables.tf      — Module input variables
README.md
```

## CI/CD Pipeline

No CI/CD pipeline is configured in this repository. Like `nlroot-aws_INFRA_TF`, all Terraform operations are manual. Given that this repository provisions compute (ECS), networking (VPC/ALB), and IAM roles, uncontrolled changes present significant operational and security risk.

## Workspace Strategy

`locals-env.tf` defines environment-specific values using Terraform workspace:
```hcl
local.count = { "default"=2 }
local.instances = { "default"="m5.2xlarge" }
local.public_subnets = { "default"=[...] }
```

Only a `"default"` workspace is defined, suggesting all environments share the same configuration. A proper multi-environment strategy would define `dev`, `staging`, and `prod` keys.

## ECS Operational Configuration

### Cluster Type
`variables.tf` line 43: `ecs_type = "FARGATE"` — Serverless compute, no EC2 instance management required. However, `compute-ecs.tf` still defines an `aws_launch_configuration` and `aws_autoscaling_group` with `count = upper(var.ecs_type) == "EC2" ? 1 : 0` — these are not created for Fargate but represent dead code that could confuse operators.

### Service Versions
`locals-svc.tf` lines 27, 61, 85, 107: All four services use `version = "latest"` for container image tags. Using `latest` is an anti-pattern for production deployments:
- Deployments are non-reproducible.
- A bad image push can immediately affect the running service on next restart.
- There is no audit trail of which image version is running.

**Recommendation:** Pin all ECS service image versions to immutable SHA digests or semantic version tags.

### Autoscaling
`compute-ecs.tf` lines 160–227: CloudWatch-triggered autoscaling is configured for `logstash-ship` based on SQS queue depth (`ApproximateNumberOfMessagesVisible`). Scale-up threshold: 50,000 messages. Scale-down when queue drains. Max capacity: 4 tasks.

However, `logstash-ship` has `ecs_count = "0"` — it is scaled to zero by default. The autoscaling policy will never trigger unless the desired count is manually set above 0 first.

## Load Balancer Configuration

### External ALB (`network-external-alb.tf`)
- Internet-facing ALB with HTTPS listener on port 443.
- TLS policy: `ELBSecurityPolicy-TLS-1-2-Ext-2018-06` — TLS 1.2 minimum. PCI DSS v4 requires TLS 1.2 minimum; TLS 1.3 is recommended. This policy is acceptable but not optimal.
- Default action returns HTTP 400 for unrecognised hosts — good security practice (rejects requests with no matching routing rule).
- Certificate sourced from `data.aws_acm_certificate.lb_cert` — ACM-managed certificate for `*.northlane.com`.

### External NLB (`network-external-nlb.tf`)
Network Load Balancer for Logstash Beats ingestion on port 5044 (TCP). NLBs pass source IPs to targets, enabling IP-based access control.

## Deployment Runbook (Inferred)

1. Set environment variables for AWS credentials (no hardcoded credentials in provider).
2. Create or update `util.tfvars` with environment-specific values (currently includes production credentials — see security findings).
3. `terraform init` — connects to remote state (not shown in this repo; implied sibling to `nlroot-aws_INFRA_TF`).
4. `terraform plan -var-file=util.tfvars` — review changes.
5. `terraform apply -var-file=util.tfvars` — apply.

**Critical gap:** `util.tfvars` is not in `.gitignore` and contains credentials. This file must not be committed to version control.

## Monitoring

`compute-ecs.tf` lines 211–227: CloudWatch alarm `{workspace}-ls-sqs-high` monitors SQS queue depth for autoscaling. No other CloudWatch alarms are defined for:
- ECS service health (task count below desired)
- ALB 5xx error rates
- ECR image scan findings
- SQS dead-letter queue depth

**Recommendation:** Add CloudWatch alarms for dead-letter queue depth (non-zero = processing failures), ECS service task failures, and ALB error rate.
