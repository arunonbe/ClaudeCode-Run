# Enterprise Architect Analysis — nlroot-aws_INFRA_TF

## Role in the Northlane Platform Architecture

`nlroot-aws_INFRA_TF` sits at the apex of the Northlane infrastructure hierarchy. It is the **account-level root** Terraform workspace — meaning it manages resources that are shared across all environments (dev, QA, staging, production) and cannot be scoped to a single workload:

- **Route 53 hosted zones** are account-global resources; one zone serves all environments via subdomains.
- **Terraform remote state infrastructure** (S3 bucket + DynamoDB table) is the foundation that all other Terraform workspaces depend on.

This positions the repo as infrastructure Layer 0 in the Northlane platform stack, below `nlutil-aws_INFRA_TF` (Layer 1 — utility networking and compute) and all application-tier Terraform repos.

## Architecture Patterns

### Domain Portfolio Architecture

The 29 Route 53 hosted zones represent a deliberate defensive domain registration strategy:

```
northlane.{biz, com, info, me, net, org}          — Primary brand
northlanepayments.{co, com, net, org}              — Payments sub-brand
northlanepaymenttechnologies.{co, com, net, org}   — Full legal name variants
northlanetech.{com, net, org}                      — Short tech brand
northlanetechnologies.{co, com, net, org}          — Long tech brand
paynorthlane.{com, net, org}                       — Action verb domain
prepaid-program.{co, com, net, org}                — Product category
wirecardna.com                                     — Legacy brand (Wirecard NA)
```

This pattern is consistent with fintech brand protection requirements. However, only `northlane.com` has Terraform-managed DNS records, meaning 28 zones have no records or have records managed outside IaC — an architectural inconsistency.

### Terraform State Hierarchy

The architecture uses a two-tier state model:
1. **Bootstrap state** (`backend/main.tf`): Local state, creates the S3 bucket and DynamoDB table. One-time operation.
2. **Root state** (`backend.tf`): Remote state in `wc-root-state/root/terraform.tfstate`. All ongoing DNS and zone management.

This hierarchy implies that sibling repos (`nlutil-aws_INFRA_TF` and others) use separate state keys within the same or different S3 buckets, enabling state isolation while sharing the same AWS account.

## Integration Architecture

### Upstream Dependencies
- **AWS Route 53** (global): Zone management and record resolution.
- **AWS S3** (`wc-root-state`): State file storage.
- **AWS DynamoDB** (`terraform-root-locking`): State locking.
- **AWS KMS** (`alias/wc-root-state-encryption-key`): State encryption.

### Downstream Consumers
- **`nlutil-aws_INFRA_TF`**: References `northlane.com` ACM certificate (wildcard `*.northlane.com` per `util.tfvars`), which depends on the hosted zone existing here.
- **All application services** (indirectly): All services reachable via `*.northlane.com` subdomains depend on this repo's zone delegation being correct.
- **Email delivery**: MX record for `northlane.com` pointing to Office 365 means all transactional notification emails (sent by the notification framework services) depend on this record being accurate.

## Architectural Gaps and Recommendations

### 1. Missing Records for 28 Zones
**Gap:** Only `northlane.com` has Terraform-managed records. The remaining 28 zones appear to be registration-only (no records), meaning they serve purely as domain squatting protection and are not actively used.
**Recommendation:** Add `lifecycle { prevent_destroy = true }` to all zones to prevent accidental deletion. Document explicitly which zones are active vs. protective-only.

### 2. No Cross-Account or Multi-Account Architecture
The state bucket name `wc-root-state` and the provider having no `assume_role` configuration suggest all resources are in a single AWS account. Enterprise best practice for regulated fintechs is to use AWS Organizations with separate accounts per environment (dev, staging, prod), with root-level DNS in a dedicated DNS account.

### 3. No DNSSEC Configuration
Route 53 supports DNSSEC signing for hosted zones. None of the 29 zones have DNSSEC enabled. For a payments brand, DNSSEC prevents DNS spoofing attacks that could redirect cardholders to fraudulent sites. This is an architectural gap from a PCI DSS Requirement 4 perspective.

### 4. Legacy Brand Dependency
The S3 bucket name `wc-root-state` (Wirecard) creates a naming inconsistency in the architecture. Renaming an S3 bucket requires creating a new bucket and migrating state — a non-trivial operation. This represents technical debt from the Wirecard NA to Northlane/Onbe brand transition.

## Compliance Architecture Assessment

| Control | Status | Evidence |
|---|---|---|
| Terraform state encrypted at rest | Compliant | `encrypt = true`, KMS CMK configured |
| State locking prevents concurrent modification | Compliant | DynamoDB table configured |
| Changes tracked in version control | Compliant | Git repository |
| Infrastructure changes require code review | Gap | No CI/CD pipeline enforces PR review before apply |
| DNSSEC on cardholder-facing domains | Gap | No `aws_route53_key_signing_key` or `aws_route53_hosted_zone_dnssec` resources |
| Separation of environments via separate AWS accounts | Gap/Unknown | Single account pattern observed |
