# chaossearch_INFRA_TF — Enterprise Architect View

## Platform Generation (Gen-1/Gen-2/Gen-3)

**Assessment: Gen-1 / Early Gen-2 (POC-stage)**

Indicators supporting this classification:
- Resource naming uses `poc` suffixes (`wc-poc-state`, `wc-chaossearch-poc`, `terraform-poc-locking`), explicitly marking this as a proof-of-concept, not a production deployment.
- No CI/CD automation, no multi-environment structure, no provider/module version pinning — all hallmarks of early-stage or exploratory infrastructure.
- The Terraform module is sourced from an external GitLab namespace (`northlane/infrastructure`) without a pinned version, suggesting early-stage practices rather than mature platform engineering.
- No tagging strategy, no cost allocation tags, no security baseline controls visible in the root module.

## Business Domain

**Domain**: Observability / Log Analytics Infrastructure

This repository sits within the platform engineering and observability domain. It does not directly implement a business capability (payments, disbursements, cardholder management) but enables operational visibility into those systems by routing log data to a third-party analytics platform (ChaosSearch).

Within Onbe's architecture, this falls under the **Security & Compliance Operations** and **Platform Engineering** domains, supporting:
- Security event monitoring and SIEM-adjacent log analysis.
- Operational troubleshooting and audit trail maintenance.
- Potentially: PCI DSS Requirement 10 log aggregation (if ChaosSearch is used for compliance log review).

## Role in Platform

This repository provisions the AWS-side prerequisites for ChaosSearch connectivity. Its role in the broader platform is:

- **Enabler**: It does not produce a direct business outcome but enables ChaosSearch to ingest Onbe's log data.
- **Data egress boundary**: The S3 bucket and IAM trust relationship define the boundary at which Onbe's internal log data exits to a third-party platform.
- **Downstream dependency**: Any team or workflow relying on ChaosSearch for log search, alerting, or compliance reporting depends on the infrastructure in this repository being correctly deployed and maintained.

## Dependencies

| Dependency | Direction | Type | Notes |
|---|---|---|---|
| ChaosSearch SaaS platform | Outbound (data flows to ChaosSearch) | Third-party vendor | Cross-account IAM trust; vendor must maintain their AWS account and IAM role |
| GitLab (`northlane/infrastructure/terraform/modules.git`) | Build-time | Internal infrastructure module | Module must be accessible at apply time; no version pin |
| AWS account (`us-east-1`) | Hosting | Cloud provider | All resources in single region |
| Pre-existing KMS key (`alias/wc-poc-state-encryption-key`) | Bootstrap | AWS managed key | Must be provisioned separately |
| Pre-existing S3 state bucket (`wc-poc-state`) | Bootstrap | AWS S3 | Must be provisioned separately |
| Pre-existing DynamoDB locking table (`terraform-poc-locking`) | Bootstrap | AWS DynamoDB | Must be provisioned separately |
| Log-producing systems | Upstream | Applications / services | Must write to the designated S3 bucket for ChaosSearch to index anything |

## Integration Patterns

- **Cross-account IAM assume-role with external ID**: ChaosSearch accesses Onbe's S3 bucket by assuming an IAM role in Onbe's AWS account. The external ID (`cs_external_id`) acts as a second factor to prevent confused deputy attacks. This is the standard AWS pattern for third-party SaaS S3 integrations.
- **Event-driven notification (S3 to SQS)**: S3 ObjectCreated events are published to an SQS queue. ChaosSearch reads from this queue to detect new objects without polling the bucket directly. This is a pull-based, near-real-time integration pattern.
- **Infrastructure as Code via Terraform modules**: The integration configuration is encapsulated in a reusable Terraform module (`chaossearch-prereq`), supporting repeatability across environments (though only one environment is currently configured).
- **Remote Terraform state**: State is centralised in S3 with DynamoDB locking, enabling collaborative infrastructure management.

## Strategic Status

| Dimension | Assessment |
|---|---|
| Deployment maturity | POC — not production-promoted |
| Operational maturity | Low — no CI/CD, no monitoring, no runbooks |
| Vendor relationship | ChaosSearch is a third-party SaaS; vendor assessment status unknown |
| Strategic fit | Observability is a strategic need; whether ChaosSearch is the selected long-term platform is unclear given the POC designation |
| Duplication risk | If Onbe uses other log aggregation tools (e.g., Splunk, Datadog, Elastic), this may be an overlapping or replacement capability |

## Migration Blockers

If this POC is to be promoted to production or migrated to a Gen-3 platform pattern, the following blockers must be resolved:

1. **No production environment configuration**: Only `poc.tfvars` exists. Production variable files, state buckets, and KMS keys do not exist in this repository.
2. **Unpinned Terraform module**: The `chaossearch-prereq` module has no version pin. A production deployment requires a stable, versioned reference.
3. **No Terraform or provider version constraints**: Must be added to ensure reproducible deployments.
4. **No CI/CD pipeline**: A production deployment pipeline with plan/apply approvals, drift detection, and audit logging is required.
5. **Vendor risk assessment gap**: ChaosSearch's access to Onbe log data requires formal vendor assessment, contractual data processing agreements, and confirmation of their own PCI DSS / SOC 2 compliance posture.
6. **Data classification of log content**: The type of data flowing into the bucket must be classified before production promotion. If PCI-in-scope, the bucket must be treated as CDE.
7. **tfvars committed to git**: The `poc.tfvars` file containing the external ID is committed to source control. For production, secrets must be managed via a vault or CI/CD environment variables, not committed files.
8. **Single-region architecture**: `us-east-1` only. No DR/failover region is configured for the log ingestion path.
