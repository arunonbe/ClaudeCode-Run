# Data Architect Analysis — nlroot-aws_INFRA_TF

## Data Assets Managed

This repository does not manage application data stores directly. Its data architecture concerns are limited to:

1. **Terraform state data** — The S3 bucket `wc-root-state` (defined in `backend.tf` line 4 and bootstrapped in `backend/main.tf` line 12) stores the Terraform state file at key `root/terraform.tfstate`. This file is the authoritative record of all AWS resources managed by this repo.

2. **DNS zone data** — Route 53 hosted zone records defined in `r53-zones.tf` and `r53-records.tf` are authoritative DNS data: A records, MX records, CNAME records, TXT records, NS records, and SOA records.

3. **IAM group data** — The bootstrap module (`backend/main.tf` lines 7–8) creates two IAM groups (`terraform_root_rw_access`, `terraform_root_ro_access`) that control who can read or write root Terraform state.

## Terraform State Architecture

### State Storage Configuration (`backend.tf`)

```hcl
backend "s3" {
  bucket         = "wc-root-state"
  key            = "root/terraform.tfstate"
  region         = "us-east-1"
  dynamodb_table = "terraform-root-locking"
  encrypt        = true
  kms_key_id     = "alias/wc-root-state-encryption-key"
}
```

**Positive findings:**
- `encrypt = true` — State file is encrypted at rest using SSE-KMS.
- `kms_key_id = "alias/wc-root-state-encryption-key"` — Uses a customer-managed KMS key alias, not the default AWS-managed key. This means Onbe controls key rotation and access policies.
- `dynamodb_table = "terraform-root-locking"` — State locking is implemented, preventing concurrent Terraform apply operations from corrupting state.

**Data integrity concern:**
The bootstrap backend (`backend/main.tf` line 16–18) uses `backend "local" {}`, meaning the Terraform state for the state-bootstrap itself is stored locally on the engineer's workstation. If this local state is lost, the S3 bucket and DynamoDB table may become orphaned from Terraform management. This is a common but accepted bootstrap pattern; however, there is no documented procedure for recovering this local state.

## DNS Data Model

### Hosted Zone Inventory (`r53-zones.tf`)

29 hosted zones are managed, covering 8 brand families across 7 TLDs. The data model is purely declarative — each `aws_route53_zone` resource produces:
- A hosted zone ID (AWS-assigned)
- Four nameserver (NS) records delegated to AWS Route 53 name servers

### Record Data (`r53-records.tf`)

The file manages records for `northlane.com` only. Other zones have no records defined in this repository, suggesting their records may be managed outside Terraform (in the domain registrar or manually) — a data consistency risk.

**Record types observed:**

| Type | Count | Purpose |
|---|---|---|
| A | 4 | Portal IPs, QA environment IPs |
| MX | 1 | Email routing to Office 365 |
| NS | 1 | Nameserver delegation |
| SOA | 1 | Zone authority |
| TXT | 1 | SPF, domain verification tokens |
| CNAME | 6 | ACM cert validation, O365 autodiscover, Squarespace, Intune |

**Data sensitivity in DNS records:**
- `r53-records.tf` line 66: Atlassian domain verification token in TXT record — not sensitive but publicly visible.
- `r53-records.tf` line 69: SPF record — operational security signal, not sensitive.
- `r53-records.tf` line 76: ACM validation CNAME — contains an ACM challenge token, exposes that Onbe uses ACM for TLS on this domain.

## Data Lineage and Drift Risk

**DNS drift concern:** Only `northlane.com` records are managed by Terraform. The other 28 zones have no Terraform-managed records. Any records added manually in the AWS console for those zones create configuration drift that is invisible to Terraform state and could be inadvertently deleted if `terraform destroy` is run.

**Recommended data governance improvement:** Add `terraform import` blocks or data sources for all manually managed records in non-`northlane.com` zones, or add explicit documentation of which zones are intentionally record-free.

## Data Encryption Assessment

| Asset | Encryption at Rest | Encryption in Transit |
|---|---|---|
| Terraform state (S3) | Yes — KMS `alias/wc-root-state-encryption-key` | Yes — S3 HTTPS endpoint |
| DynamoDB lock table | AWS default (SSE with AWS-managed key) | Yes — HTTPS |
| Route 53 zone data | AWS-managed (not configurable by customer) | Yes |

**Gap:** The DynamoDB lock table does not specify a customer-managed KMS key in the bootstrap configuration. For PCI DSS compliance it is preferable to use a CMK for all data stores, even operational ones.

## Data Residency

All assets are in `us-east-1` (N. Virginia). Route 53 is a global service but zone data is managed from us-east-1. No cross-region replication is configured for the state bucket — a single-region failure would make the state file unavailable until the region recovers.
