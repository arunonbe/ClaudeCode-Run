# Business Analyst Analysis — nlroot-aws_INFRA_TF

## Repository Overview

`nlroot-aws_INFRA_TF` is the root-level AWS infrastructure Terraform repository for the Northlane platform (a Onbe/Wirecard NA prepaid-card and payments brand). It manages the foundational AWS account-level resources that all other Northlane services depend on: public DNS zones, Terraform remote-state bootstrapping, and Route 53 DNS records for customer-facing and internal subdomains.

## Business Purpose and Context

Northlane is Onbe's prepaid card and B2C disbursements platform, previously operating under the Wirecard NA brand (evidenced by the `wirecardna.com` zone and S3 bucket name `wc-root-state`). The repo's business responsibility is to ensure that:

1. **Brand continuity and domain portfolio management** — All public-facing Northlane domain variants are registered and DNS-authoritative within AWS Route 53. The 29 hosted zones managed in `r53-zones.tf` cover `.com`, `.net`, `.org`, `.co`, `.biz`, `.me`, and `.info` TLDs for five brand families: `northlane`, `northlanepayments`, `northlanepaymenttechnologies`, `northlanetech`, `northlanetechnologies`, `paynorthlane`, `prepaid-program`, and the legacy `wirecardna.com`.

2. **Cardholder and client portal DNS** — Records in `r53-records.tf` resolve environments for cardholder-facing portals (`northlane.com` root A record) and internal tooling subdomains (`clientzone-qa`, `csa-qa`, `login-qa`). These are direct business-critical DNS entries: if misconfigured, cardholders cannot access their accounts and clients cannot reach the Customer Service Application.

3. **Platform-wide Terraform state management** — The `backend/main.tf` bootstraps the S3 bucket (`wc-root-state`) and DynamoDB table (`terraform-root-locking`) used for locking state across all other Northlane Terraform workspaces. This is purely an infrastructure governance concern with direct business continuity implications.

## Stakeholder Impact

| Stakeholder | Dependency |
|---|---|
| Cardholders | DNS A records for `northlane.com` direct portal access |
| Client Operations | `clientzone-qa.northlane.com`, `csa-qa.northlane.com` subdomains |
| Engineering / DevOps | Remote state infrastructure (S3 + DynamoDB) |
| Legal / Brand | Domain portfolio coverage across 29 hosted zones |
| Compliance | DNS proof-of-ownership records (TXT: MS=, SPF, Atlassian domain verification) |

## Business Processes Supported

- **Domain portfolio protection**: The breadth of TLD coverage (`.biz`, `.me`, `.co`, `.info`) represents a deliberate brand-squatting defence strategy typical for regulated fintechs.
- **Email deliverability governance**: MX records pointing to `northlane-com.mail.protection.outlook.com` (Office 365) and SPF record `v=spf1 include:spf.protection.outlook.com -all` indicate all business email flows through Microsoft 365.
- **Certificate management**: ACM CNAME validation records (`_32fc18551234e105c48a357fabb53c4d.northlane.com`) enable automated TLS certificate issuance — required for PCI DSS Requirement 4 (encrypted transmission).
- **Microsoft 365 integration**: `autodiscover`, `enterpriseenrollment`, and `enterpriseregistration` CNAMEs support Microsoft Intune device management and Exchange autodiscovery for Northlane staff.
- **Website infrastructure**: `www.northlane.com` CNAME to `ext-cust.squarespace.com` shows the public marketing site is hosted on Squarespace, while backend systems remain on AWS.

## Key Business Risks

1. **Legacy brand exposure**: The `wirecardna.com` zone (`r53-zones.tf` line 113) represents the Wirecard NA legacy. If this domain is not actively renewed and monitored, it could be claimed by third parties, creating brand confusion and potential fraud risk for cardholders redirected to a look-alike domain.

2. **QA subdomain records in production DNS**: Records for `clientzone-qa`, `csa-qa`, and `login-qa` point to non-AWS IP addresses (`204.141.49.x`), suggesting legacy data-centre infrastructure. If these IPs are decommissioned without DNS cleanup, broken DNS can affect QA testing pipelines.

3. **Hardcoded production IP addresses**: `r53-records.tf` lines 7, 15–16 contain hardcoded public IP addresses. Any infrastructure IP change requires a Terraform code change and deploy, increasing lead time for incident recovery.

4. **Single-region deployment**: All infrastructure is locked to `us-east-1` (Virginia). For a PCI DSS Level 1 provider, a regional AWS outage would affect all DNS resolution and Terraform state operations simultaneously.

## Regulatory Relevance (PCI DSS / GLBA)

DNS integrity is foundational to PCI DSS Requirement 4 (protect cardholder data in transit). If DNS is hijacked or misconfigured:
- Cardholders could be directed to fraudulent sites (phishing risk).
- TLS certificates based on DNS-01 challenges could be compromised.
- MX manipulation could intercept transactional email notifications containing partial card data.

The SPF record (`-all` hardfail) is a positive security signal indicating strict email origin enforcement.
