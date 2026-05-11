# Enterprise Architect Analysis — nlutil-aws_INFRA_TF

## Position in the Northlane Platform Architecture

`nlutil-aws_INFRA_TF` is infrastructure Layer 1 — the utility platform layer. It depends on the root layer (`nlroot-aws_INFRA_TF`) for the DNS zone and the ACM certificate, and provides the runtime infrastructure that all application services (Layer 2) deploy into.

```
Layer 0: nlroot-aws_INFRA_TF     (DNS, state infrastructure)
Layer 1: nlutil-aws_INFRA_TF     (VPC, ECS cluster, ALB, ECR, IAM, logging pipeline)
Layer 2: Application services    (notification, account management, etc.)
```

## Architectural Patterns

### Logging Architecture Pattern: Logstash → SQS → ChaosSearch

This is a **log broker pattern** with buffering:
```
Beats Agents → NLB:5044 → Logstash-Ingest → SQS Queue → Logstash-Ship → S3 → ChaosSearch
```

The SQS queue acts as a durable buffer, decoupling ingestion speed from shipping speed. This is architecturally sound for high-volume log ingestion. However, the shipping service being scaled to zero (`ecs_count = "0"`) renders the entire pipeline non-functional in its current state.

### Service Discovery Pattern

Services use internal ALB routing via hostname-based rules (`config-server.northlane.com` → spring-config). This means service-to-service communication for config retrieval traverses the ALB, adding latency and cost compared to AWS Cloud Map or direct ECS service DNS resolution.

### Single-Workspace Architecture

The Terraform code only defines a `"default"` workspace in `locals-env.tf`. This suggests either:
1. All environments share the same AWS account and workspace, or
2. The repo is intended to be forked/branched per environment.

For a PCI DSS Level 1 provider, environment separation is required. Running QA and production workloads in the same AWS account and VPC increases blast radius from security incidents.

## Cross-Service Integration Points

| Integration | Method | Direction | Notes |
|---|---|---|---|
| Application services → Config Server | HTTPS via ALB | Inbound | `config-server.northlane.com` |
| Application services → Logstash | TCP/Beats via NLB | Inbound | Port 5044 |
| Logstash-Ship → ChaosSearch S3 | S3 PutObject | Outbound | IAM policy scoped to `nl-chaossearch-ingest-us-east-1/*` |
| ChaosSearch → S3 | AssumeRole (cross-account) | Inbound to S3 | External ID: `c27d9cc2-0f00-4569-b653-22be9f7684ca` |
| ECS tasks → ECR | Docker pull | Outbound (HTTPS) | Via NAT Gateway |
| ECS tasks → Secrets Manager | HTTPS | Outbound | For secret retrieval |
| ECS tasks → SSM | HTTPS | Outbound | GitLab SSH key for spring-config |

## IAM Architecture Assessment

### ECS Task Role (`identity-iam-ecs.tf` lines 43–66)

```json
{
  "Action": ["ecr:*", "ssm:GetParameters", "secretsmanager:GetSecretValue",
             "kms:Decrypt", "logs:CreateLogStream", "logs:PutLogEvents"],
  "Resource": "*",
  "Effect": "Allow"
}
```

**Finding: `ecr:*` with Resource `*` is overly permissive.** This grants all ECR actions (including `ecr:DeleteRepository`, `ecr:BatchDeleteImage`, `ecr:PutLifecyclePolicy`) on all ECR repositories in the account. A compromised ECS task could delete container image repositories, disabling all deployments. The policy should be scoped to specific repository ARNs and only the required ECR actions (`ecr:GetAuthorizationToken`, `ecr:BatchCheckLayerAvailability`, `ecr:GetDownloadUrlForLayer`, `ecr:BatchGetImage`).

### ECS SSM Policy (`identity-iam-ecs.tf` lines 122–137)

```json
{
  "Action": ["ec2:describeInstances", "ec2messages:*", "iam:PassRole",
             "iam:ListRoles", "ssm:*", "ssmmessages:*"],
  "Resource": "*"
}
```

**Finding: `ssm:*` and `ec2messages:*` with Resource `*` are overly permissive.** `ssm:*` includes `ssm:PutParameter`, `ssm:DeleteParameter`, and `ssm:DescribeParameters` — granting ECS instances the ability to read, write, and delete all SSM parameters in the account. `iam:PassRole` with `Resource: *` is particularly dangerous, as it allows passing any IAM role to any service.

## Networking Architecture

### VPC Design (`network-vpc.tf`)

CIDR: `10.10.0.0/16` with three subnet tiers across three AZs:
- Public: `10.10.10.0/24`, `10.10.11.0/24`, `10.10.12.0/24`
- Application (private): `10.10.20.0/24`, `10.10.21.0/24`, `10.10.22.0/24`
- Data (private): `10.10.30.0/24`, `10.10.31.0/24`, `10.10.32.0/24`

The three-tier subnet model is architecturally correct for PCI DSS (network segmentation between presentation, application, and data tiers).

**Gap:** No VPC Flow Logs are configured. PCI DSS Requirement 10.2 requires logging all network access. VPC Flow Logs should be enabled for the entire VPC and stored in the centralised log bucket.

### Security Group Architecture

- `external_alb_sg`: ALB security group restricts inbound HTTPS to `var.nl_whitelist` (3 CIDR ranges: `204.141.49.0/24`, `204.141.48.1/32`, `4.35.222.186/32`). Egress is `0.0.0.0/0` (all outbound). This means the ALB is NOT public — it only accepts connections from whitelisted IPs. This is appropriate for internal tooling but restricts cardholder-facing services (if any are behind this ALB).
- `ecs_sg`: ECS cluster security group only allows inbound on ports 5044 (Logstash) and 9990 (spring-config) from the whitelist and public subnets. Egress is `0.0.0.0/0`.

**Finding:** Egress `0.0.0.0/0` on all security groups is a broad allowance. For CDE systems, egress should be restricted to known destinations (ECR endpoints, Secrets Manager, SQS). However, for utility/logging infrastructure this is a lower-risk pattern.
