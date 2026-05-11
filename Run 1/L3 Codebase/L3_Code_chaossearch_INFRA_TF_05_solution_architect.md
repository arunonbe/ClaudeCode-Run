# chaossearch_INFRA_TF — Solution Architect View

## Technical Architecture

This repository is a minimal Terraform root module that delegates all resource creation to a single external module. The architecture has three layers:

**Layer 1 — Terraform Root Module (this repo)**
- `backend.tf`: Configures remote S3 + DynamoDB state backend with KMS encryption.
- `variables.tf`: Declares four input variables (`region`, `cs_external_id`, `cs_data_bucket`, `sqs_queue`).
- `main.tf`: Declares the AWS provider (aliased `us-east-1`) and invokes the `chaossearch-prereq` module, passing all four variables.
- `poc.tfvars`: Supplies concrete values for the POC environment.

**Layer 2 — External Terraform Module**
- Source: `git@gitlab.com:northlane/infrastructure/terraform/modules.git//chaossearch-prereq`
- This module is not in-repo; its exact implementation is not visible from this repository.
- Based on the README description and module inputs, it creates: S3 data bucket, SQS queue, S3-to-SQS bucket notification, IAM role/policy for ChaosSearch cross-account access.

**Layer 3 — Pre-existing Infrastructure**
- S3 state bucket (`wc-poc-state`), DynamoDB locking table (`terraform-poc-locking`), and KMS key (`alias/wc-poc-state-encryption-key`) must exist before this module can be initialised.

**Component Diagram (logical)**
```
[Terraform Operator]
        |
        | terraform apply -var-file=poc.tfvars
        v
[Root Module: chaossearch_INFRA_TF]
        |
        | module call
        v
[chaossearch-prereq module @ GitLab:northlane]
        |
        |-- aws_s3_bucket: wc-chaossearch-poc
        |-- aws_sqs_queue: (name in module)
        |-- aws_s3_bucket_notification: S3 -> SQS
        |-- aws_iam_role / aws_iam_policy: ChaosSearch cross-account
        |-- aws_s3_bucket_policy: grants ChaosSearch read access
        |
        v
[ChaosSearch SaaS] <-- assumes IAM role using cs_external_id UUID
        |
        v
[Indexes log data from wc-chaossearch-poc]
```

## API Surface

This repository does not expose any application API. The integration points are:

| Interface | Type | Direction | Notes |
|---|---|---|---|
| AWS S3 (data bucket) | AWS API | Inbound (log producers write) / Outbound (ChaosSearch reads) | Mediated by IAM bucket policy |
| AWS SQS | AWS API | Outbound (ChaosSearch polls/receives) | S3 event notifications trigger messages |
| AWS IAM AssumeRole | AWS STS API | Cross-account (ChaosSearch -> Onbe AWS account) | External ID `cs_external_id` is the trust condition |
| AWS S3 (state bucket) | AWS API | Terraform internal | State read/write on `terraform apply` |
| AWS DynamoDB | AWS API | Terraform internal | State lock acquire/release |
| GitLab SSH | Git over SSH | Build-time module fetch | `git@gitlab.com:northlane/infrastructure/terraform/modules.git` |

## Security Posture (any hardcoded credentials — note existence only, not values)

| Finding | Severity | File | Line | Description |
|---|---|---|---|---|
| External ID value committed to source control | Medium | `poc.tfvars` | 2 | The `cs_external_id` UUID is committed in plaintext. The `.gitignore` file's own comment block states `.tfvars` files "are likely to contain sensitive data" and should not be in version control — the exclusion rule is commented out, so the file was intentionally committed. This value is used in the IAM trust policy and acts as a shared secret between Onbe and ChaosSearch. |
| No hardcoded AWS credentials found | N/A | All files | — | No AWS access keys, secret keys, or tokens were found in any file. |
| No hardcoded passwords or tokens found | N/A | All files | — | No application passwords or API tokens were found. |
| KMS key alias referenced but not managed here | Low | `backend.tf` | 8 | The KMS key alias `alias/wc-poc-state-encryption-key` is referenced by alias name. If the underlying key is deleted or the alias is changed, Terraform will fail to read/write state silently. |
| Terraform provider has no version constraint | Low | `main.tf` | 1–4 | Without a `required_providers` block with version constraints, the AWS provider version is indeterminate. A future incompatible provider version could break the apply. |
| Module source has no ref/tag pin | Medium | `main.tf` | 7 | The module is fetched from the default branch HEAD. A malicious or accidental upstream change to the module could alter what resources are created in Onbe's AWS account. |

**IAM Trust Pattern**: The cross-account assume-role pattern using `cs_external_id` is the correct and recommended approach for granting third-party SaaS platforms access to S3. Provided the external ID is treated as confidential, this is a sound pattern.

## Technical Debt

| Item | Impact | Effort to Fix |
|---|---|---|
| No Terraform `required_version` constraint | Reproducibility risk; different operators may use different versions | Low — add one block to `backend.tf` or a new `versions.tf` |
| No AWS provider version pinning (`required_providers`) | Provider API drift risk | Low — add `required_providers` block |
| Module source has no `ref`/`tag` | Infrastructure drift risk on next `terraform get` | Low — append `?ref=<tag>` to the source URL |
| No `terraform.lock.hcl` | Provider version not reproducible across machines | Low — run `terraform providers lock` and commit the output |
| Only POC environment exists | Cannot promote to production without new `.tfvars` and state config | Medium — needs environment separation strategy |
| No CI/CD pipeline | Manual apply; no audit trail, no plan review gate | High — requires pipeline work |
| `poc.tfvars` committed to git | Sensitive config in version control | Low-Medium — remove from git, add to secrets manager or CI/CD vars |
| No observability/alerting | Operational issues with SQS or S3 access go undetected | Medium — requires CloudWatch alarm definitions |
| No README deployment instructions | Operational risk; only a one-line description | Low — documentation gap |
| Module source is in external GitLab org (`northlane`) | If access is lost, all Terraform operations break | Medium — consider mirroring or importing the module |

## Gen-3 Migration Requirements

To bring this repository to a Gen-3 standard (production-grade, fully automated, compliance-ready), the following changes are required:

1. **Terraform version and provider pinning**: Add `terraform { required_version = "~> 1.x" }` and `required_providers { aws = { source = "hashicorp/aws", version = "~> 5.x" } }`.
2. **Module version pinning**: Add a `ref` to the GitLab module source URL, or bring the module in-repo / to a versioned registry.
3. **Multi-environment structure**: Create `environments/dev/`, `environments/staging/`, `environments/prod/` with separate state backends and variable files, or adopt Terraform workspaces.
4. **CI/CD pipeline**: Implement `terraform fmt`, `terraform validate`, `tfsec` / `checkov` security scanning, `terraform plan` with plan output archival, and `terraform apply` behind a manual approval gate.
5. **Secrets management**: Remove `poc.tfvars` from git history (via `git filter-branch` or BFG), store `cs_external_id` in AWS Secrets Manager or CI/CD environment secrets.
6. **Tagging strategy**: Apply Onbe-standard resource tags (`Environment`, `CostCenter`, `DataClassification`, `Owner`, `PCI-Scope`) to all provisioned resources.
7. **S3 bucket hardening**: Confirm (via module review) that the data bucket has: server-side encryption, public access block, versioning enabled, access logging to a separate audit bucket, and an explicit deny-all-non-TLS bucket policy.
8. **Observability**: Add CloudWatch alarms for SQS queue depth, approximate age of oldest message, and S3 access errors.
9. **Data classification tagging**: Tag the S3 bucket with data classification (e.g., `DataClassification=Internal` or `DataClassification=Restricted` if PCI-scoped).
10. **Vendor compliance documentation**: Obtain and attach ChaosSearch's PCI DSS Attestation of Compliance (AoC) or equivalent SOC 2 report as part of the vendor risk package before production use.

## Code-Level Risks

| Risk | File | Severity | Detail |
|---|---|---|---|
| Unpinned module ref | `main.tf` line 8 | High | Any change pushed to the `chaossearch-prereq` module's default branch takes effect on next `terraform init -upgrade` or fresh clone |
| `poc.tfvars` in source control | `poc.tfvars` | Medium | Contains `cs_external_id` UUID; see Security Posture section |
| No `required_version` or `required_providers` | `main.tf`, `backend.tf` | Medium | Terraform and AWS provider versions are fully indeterminate |
| Backend bucket/table names are POC-specific | `backend.tf` | Low | Copying this config for production without updating backend block would write production state into the POC state bucket |
| AWS provider alias (`us-east-1`) hardcoded | `main.tf` line 2–4 | Low | Region is declared in both the provider alias and the `var.region` variable. If `var.region` is changed, the provider alias label is misleading (though AWS uses the `region` attribute, not the alias label, for actual routing) |
