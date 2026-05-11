# DevOps and Operations Analysis — nlroot-aws_INFRA_TF

## Repository Structure and Operational Model

The repository follows a flat, single-workspace Terraform layout with no modules or environment separation beyond Terraform workspaces (implied by other repos). Files:

```
backend.tf            — S3/DynamoDB remote state configuration
main.tf               — AWS provider (region only)
r53-zones.tf          — 29 Route 53 hosted zones
r53-records.tf        — DNS records for northlane.com
variables.tf          — Single variable: region (default us-east-1)
backend/main.tf       — Bootstrap: creates S3 bucket + DynamoDB table
README.md             — (present)
.gitignore            — (present)
```

## CI/CD Pipeline

**No CI/CD pipeline is configured in this repository.** There are no `.github/workflows/`, `.gitlab-ci.yml`, or `Jenkinsfile` files. All Terraform operations are manual, executed by engineers with appropriate IAM permissions.

**Risk:** Manual Terraform applies with no automated plan review, no policy-as-code gates (e.g., OPA, Checkov, tfsec), and no audit trail beyond AWS CloudTrail and the commit history. For a PCI DSS Level 1 environment, all changes to production infrastructure should be executed through a controlled pipeline with documented approval workflows.

## State Management

- **Remote state backend**: S3 bucket `wc-root-state`, key `root/terraform.tfstate`, region `us-east-1` (`backend.tf` lines 4–9).
- **State locking**: DynamoDB table `terraform-root-locking` provides optimistic locking.
- **Encryption**: KMS key `alias/wc-root-state-encryption-key` encrypts state at rest.

**Bootstrap procedure (`backend/main.tf`):**
The `backend/main.tf` uses a public GitHub module `git::https://github.com/bincyber/terraform-aws-remote-state` to create the S3 bucket and DynamoDB table. This introduces a third-party dependency on an external public module with a `backend "local" {}` — meaning the bootstrapper's own state lives on disk. This should be treated as a one-time operation and the local state file archived securely.

**Operational gap:** The `backend/main.tf` comment `# Replace this with your bucket name!` (echoed in `backend.tf` line 3) suggests this may be templated infrastructure that was partially customised. The actual bucket name `wc-root-state` retains the legacy `wc-` (Wirecard) prefix, suggesting it was created during the Wirecard NA era and not renamed post-acquisition.

## Deployment Runbook (Inferred)

1. Authenticate to AWS via IAM role with appropriate Route 53 and S3 permissions.
2. `terraform init` — downloads the AWS provider, connects to remote state.
3. `terraform workspace select <env>` — though no workspace logic is used in this repo's resources, the convention exists in sibling repos.
4. `terraform plan` — review changes to zones and records.
5. `terraform apply` — applies DNS changes.

**DNS propagation:** Route 53 changes propagate globally within ~60 seconds for most record types; TTL values in `r53-records.tf` range from 300 seconds (QA records) to 3600 seconds (production apex and MX), so downstream caches may retain old values for up to an hour after a Terraform apply.

## Operational Risk Register

| Risk | Severity | Notes |
|---|---|---|
| No CI/CD pipeline — manual applies only | High | No automated validation, no approval gate |
| Bootstrap state stored locally | Medium | Loss of local state orphans S3+DynamoDB from TF management |
| Only `northlane.com` records are Terraform-managed | Medium | 28 other zones may have manually managed records creating drift |
| Single-region state bucket (no cross-region replication) | Medium | Region outage prevents Terraform operations |
| Hardcoded QA IP addresses in production DNS file | Low | IP changes require code changes |
| No Terraform version pinning in `backend.tf` | Low | Provider version drift risk |
| No `required_providers` block with version constraints | Low | `main.tf` has only `provider "aws"` with no version constraint |

## Monitoring and Alerting

No CloudWatch alarms, Route 53 health checks, or alerting configurations are present in this repository. For business-critical DNS records (`northlane.com` apex), Route 53 health checks should be defined to alert on endpoint availability.

## Provider Version Management

`main.tf` defines only:
```hcl
provider "aws" {
  region = var.region
}
```

There is no `required_providers` block with version constraints. This means `terraform init` will pull the latest AWS provider version, which could introduce breaking changes. Best practice for production infrastructure is to pin providers:

```hcl
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}
```

## Access Control for Operations

Access to apply this repository's infrastructure requires:
- Route 53 full access (`route53:*`) for hosted zone and record management.
- S3 read/write to `wc-root-state` bucket.
- DynamoDB read/write to `terraform-root-locking` table.
- KMS decrypt/generate for `alias/wc-root-state-encryption-key`.

The bootstrap module creates two IAM groups (`terraform_root_rw_access`, `terraform_root_ro_access`) for role-based state access, but no enforcement of least-privilege within the repo itself is visible.
