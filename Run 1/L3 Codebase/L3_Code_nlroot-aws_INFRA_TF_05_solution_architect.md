# Solution Architect Analysis — nlroot-aws_INFRA_TF

## Security Findings — PCI DSS Critical Review

### Finding 1: No S3 Public Access Block on State Bucket (CRITICAL)

The `backend.tf` references the S3 bucket `wc-root-state` but does not define an `aws_s3_bucket_public_access_block` resource. The bootstrap `backend/main.tf` uses the external module `git::https://github.com/bincyber/terraform-aws-remote-state` to create the bucket. Whether that module applies a public access block depends on the external module's implementation — which is not pinned to a commit hash, making it non-deterministic over time.

**PCI DSS impact:** PCI DSS v4.0.1 Requirement 1.3.2 requires that all network access to system components in the CDE is restricted. If the state bucket is publicly accessible, Terraform state files (which may reference resource ARNs, environment names, VPC CIDRs, subnet IDs, and potentially sensitive variable values) could be exfiltrated.

**Recommendation:** Add an explicit `aws_s3_bucket_public_access_block` resource in `backend/main.tf` or verify the external module applies it. Do not rely on the module's current behavior.

### Finding 2: External Module Without Version Pinning (HIGH)

`backend/main.tf` line 6:
```hcl
source = "git::https://github.com/bincyber/terraform-modules.git//encrypted-s3-bucket-live-indexing"
```
(Also referenced in `nlutil-aws_INFRA_TF/chaossearch.tf` — see that repo's analysis.)

For `backend/main.tf` specifically:
```hcl
source = "git::https://github.com/bincyber/terraform-aws-remote-state"
```
No Git ref (tag or commit hash) is specified. A supply chain compromise of this public GitHub repository could inject malicious Terraform code into Onbe's infrastructure bootstrap.

**Recommendation:** Pin the module to a specific commit hash:
```hcl
source = "git::https://github.com/bincyber/terraform-aws-remote-state?ref=<commit-sha>"
```

### Finding 3: No IAM Wildcard Policies in This Repo (PASS)

The root repo (`main.tf`, `r53-zones.tf`, `r53-records.tf`) does not define any IAM policies. The bootstrap module creates IAM groups but their policies are defined within the external module. No wildcard IAM policies were found directly in this repository's code.

### Finding 4: No Security Groups in This Repo (PASS)

No `aws_security_group` or module security group resources are present. This is expected for a DNS/state-management repo.

### Finding 5: No Hardcoded AWS Credentials (PASS)

`variables.tf` contains only a `region` variable. No `aws_access_key_id` or `aws_secret_access_key` variables are present. The provider uses implicit credential resolution (IAM role or environment variables).

### Finding 6: QA Environment Data in Production Infrastructure Repo (MEDIUM)

`r53-records.tf` lines 11–23 define A records for `clientzone-qa`, `csa-qa`, and `login-qa` subdomains pointing to IPs in the `204.141.49.0/24` range. These appear to be on-premises or legacy data centre IPs, not AWS resources. Including non-production DNS records in the same Terraform workspace as production infrastructure creates a change coupling risk — a misconfiguration applied while updating QA records could affect production.

**Recommendation:** Separate QA DNS records into a dedicated workspace or file, and apply change controls that distinguish production from non-production DNS changes.

### Finding 7: Hardcoded IP Addresses in DNS Records (LOW)

`r53-records.tf` lines 7, 15, 16, 18, 21, 23, 28, 31, 34 contain hardcoded IP addresses:
- `198.185.159.144`, `198.185.159.145`, `198.49.23.144`, `198.49.23.145` (Squarespace IPs for apex)
- `204.141.49.71`, `204.141.49.74`, `204.141.49.77` (QA environment IPs)

Squarespace IPs may change without notice; hardcoded values will cause DNS resolution failures. These should be sourced from a variable or data source where possible, or documented with a clear ownership and update procedure.

### Finding 8: Bootstrap Module Uses `backend "local"` (MEDIUM)

`backend/main.tf` line 16:
```hcl
terraform {
  backend "local" {
}
```
The state for the bootstrapper is stored locally. No remote backup of this state exists in the repository. If the engineering workstation is lost, the S3 bucket and DynamoDB table become "untracked" by Terraform.

**Recommendation:** After bootstrap, migrate the local state to a separate protected S3 location, or document a recovery procedure.

## Architecture Recommendations Summary

| Priority | Recommendation |
|---|---|
| P1 | Verify/enforce S3 public access block on `wc-root-state` bucket |
| P1 | Implement CI/CD pipeline with Terraform plan review and Checkov/tfsec scanning |
| P1 | Enable DNSSEC on `northlane.com` and `northlanepayments.com` |
| P2 | Pin external Terraform module to a specific commit hash |
| P2 | Separate QA DNS records from production DNS records |
| P2 | Add Route 53 health checks for cardholder-facing A records |
| P3 | Add `required_providers` block with version constraints to `main.tf` |
| P3 | Rename state bucket to remove legacy `wc-` prefix (migration required) |
| P3 | Add `lifecycle { prevent_destroy = true }` to all 29 hosted zones |
| P3 | Store bootstrap state remotely after initial execution |
