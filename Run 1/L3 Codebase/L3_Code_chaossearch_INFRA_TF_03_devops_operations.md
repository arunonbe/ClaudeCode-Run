# chaossearch_INFRA_TF — DevOps & Operations View

## Build & Packaging

- **Language/Toolchain**: HashiCorp Terraform (version not pinned — no `required_version` constraint in `terraform {}` block or `versions.tf` file).
- **Provider**: AWS provider (no explicit version pinning in this repository; version constraints are not declared).
- **Module Source**: External Terraform module sourced from GitLab over SSH:
  `git@gitlab.com:northlane/infrastructure/terraform/modules.git//chaossearch-prereq`
  No `ref`, `tag`, or `sha` is specified in the module source URL, meaning Terraform always pulls the HEAD/default branch of that module repository. This is a mutable reference and introduces unpredictable behaviour on re-apply.
- **No build pipeline files**: There are no CI/CD pipeline definitions (no `.gitlab-ci.yml`, no `Jenkinsfile`, no GitHub Actions workflows, no `Makefile`) in this repository.
- **No `terraform.lock.hcl`**: There is no dependency lock file, meaning provider versions are not pinned and may drift between runs.

## Deployment (Terraform Resources Provisioned)

Resources are provisioned via the `chaossearch-prereq` module. Based on the module inputs and README description, the following resources are created:

| Resource Type | Logical Name / Description | Details from this repo |
|---|---|---|
| `aws_s3_bucket` | ChaosSearch data bucket | Name: `wc-chaossearch-poc` (from `cs_data_bucket` var) |
| `aws_sqs_queue` | S3 event notification queue | Enabled (`sqs_queue = true`); name delegated to module |
| `aws_s3_bucket_notification` | S3-to-SQS event notification | Triggered on ObjectCreated; wires data bucket to SQS queue |
| `aws_iam_role` or `aws_iam_policy` | ChaosSearch cross-account access | Uses `cs_external_id` as the external ID in the assume-role trust policy |
| `aws_s3_bucket_policy` | Bucket access policy | Grants ChaosSearch IAM principal read access to data bucket |

The following resources are referenced as pre-existing (managed externally, not created by this repo):

| Resource Type | Name | Notes |
|---|---|---|
| `aws_s3_bucket` (backend) | `wc-poc-state` | Must exist before `terraform init` |
| `aws_dynamodb_table` (backend) | `terraform-poc-locking` | Must exist before `terraform init` |
| `aws_kms_key` (backend) | `alias/wc-poc-state-encryption-key` | Must exist in `us-east-1` |

**AWS Region**: All resources deploy to `us-east-1`.

## Configuration Management

- **Variables**: Four input variables defined in `variables.tf`: `region`, `cs_external_id`, `cs_data_bucket`, `sqs_queue`.
- **Variable values**: Supplied via `poc.tfvars`. There is only one environment's worth of variable values. No `dev.tfvars`, `staging.tfvars`, or `prod.tfvars` files exist.
- **Secrets management**: No secrets manager (AWS Secrets Manager, HashiCorp Vault) integration is present. The `cs_external_id` is supplied as a plain-text Terraform variable in `poc.tfvars`.
- **State management**: Remote state stored in S3 (`wc-poc-state`) with DynamoDB locking and KMS encryption. This is a correct pattern for team-based Terraform usage.
- **Module versioning**: The GitLab module source has no pinned ref. Any change to the upstream `chaossearch-prereq` module could silently alter infrastructure on the next `terraform apply`.

## Observability

- No observability tooling is configured in this repository (no CloudWatch alarms, no SNS alerts, no dashboards, no log group definitions).
- The SQS queue itself provides some operational observability via CloudWatch metrics (queue depth, message age), but those are not configured here.
- The ChaosSearch platform is the consumer of the log data; observability of the log data itself is the platform's responsibility.
- There is no alerting on S3 bucket access failures, SQS consumer lag, or IAM assume-role failures.

## Infrastructure Dependencies

| Dependency | Type | Required Before | Notes |
|---|---|---|---|
| `wc-poc-state` S3 bucket | Pre-existing AWS resource | `terraform init` | Must be manually created |
| `terraform-poc-locking` DynamoDB table | Pre-existing AWS resource | `terraform init` | Must be manually created |
| `alias/wc-poc-state-encryption-key` KMS key | Pre-existing AWS resource | `terraform init` | Must be manually created |
| GitLab SSH access to `northlane/infrastructure/terraform/modules.git` | Network/auth dependency | `terraform init` / `terraform get` | SSH key with GitLab access required on the runner |
| AWS credentials with sufficient IAM permissions | Runtime dependency | `terraform plan` / `terraform apply` | Scope of permissions not documented |

## Operational Risks

1. **No Terraform version pinning**: Infrastructure behaviour may differ between Terraform versions. No `required_version` constraint exists.
2. **No provider version pinning**: AWS provider may be upgraded automatically on next `terraform init`, potentially introducing breaking changes.
3. **Unpinned module reference**: The `chaossearch-prereq` module is pulled from HEAD of the GitLab repository with no `ref`. Any upstream change is picked up immediately on `terraform get`.
4. **Single environment only**: No multi-environment (dev/staging/prod) structure exists. Disaster recovery via a separate environment is not possible with the current structure.
5. **No runbook or operational documentation**: The README is a single line description with no deployment instructions, pre-requisites, or teardown steps.
6. **GitLab module dependency**: Loss of access to the GitLab module repository (`northlane/infrastructure`) would break all Terraform operations.
7. **POC state bucket naming**: The bucket `wc-poc-state` and table `terraform-poc-locking` use POC-specific names, suggesting they may not be subject to production-grade lifecycle management.
8. **No drift detection**: No scheduled `terraform plan` or drift detection pipeline is configured.

## CI/CD

No CI/CD pipeline is defined in this repository. There are no pipeline files of any kind. Terraform operations are presumed to be run manually from a developer workstation with:
- Appropriate AWS credentials configured.
- SSH access to the GitLab module repository.
- The prerequisite S3 bucket, DynamoDB table, and KMS key already existing.

This is a significant operational gap for any production or compliance-sensitive workload.
