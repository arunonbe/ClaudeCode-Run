# chaossearch_INFRA_TF — Business Analyst View

## Business Purpose

This repository provisions the AWS infrastructure prerequisites required to integrate Onbe's environment with ChaosSearch, a cloud-native log analytics and observability platform. ChaosSearch indexes data directly from customer-owned S3 buckets, so the primary business purpose is to create and configure the S3 storage and notification resources that ChaosSearch needs to consume log data in real time. The POC (proof-of-concept) naming convention in the variable values (`wc-chaossearch-poc`, `wc-poc-state`) confirms this is currently at the proof-of-concept stage and has not been promoted to production.

## Business Capabilities

- Enables log data ingestion from Onbe-owned S3 buckets into ChaosSearch for search, analysis, and observability.
- Supports near-real-time log indexing via an SQS queue that notifies ChaosSearch when new objects land in the S3 bucket.
- Delegates controlled read access to the ChaosSearch service's AWS IAM role via an external ID mechanism (cross-account assume-role pattern), limiting what ChaosSearch can access to only the designated bucket.
- Provides a repeatable, version-controlled infrastructure deployment via Terraform, allowing the POC to be torn down or reproduced consistently.

## Business Entities

| Entity | Description |
|---|---|
| S3 Data Bucket | AWS S3 bucket (`wc-chaossearch-poc`) that holds the log/event data to be indexed by ChaosSearch |
| SQS Queue | AWS SQS queue that delivers S3 event notifications to ChaosSearch for live/streaming updates |
| ChaosSearch External ID | A UUID (`cs_external_id`) that identifies Onbe as the ChaosSearch customer and authorises the assume-role trust relationship |
| Terraform State Bucket | S3 bucket (`wc-poc-state`) that stores Terraform state, separate from the data bucket |
| DynamoDB Locking Table | `terraform-poc-locking` table that prevents concurrent Terraform state modifications |

## Business Rules & Validations

- The `cs_external_id` value is a customer-specific UUID assigned by ChaosSearch. It must be kept consistent; changing it would break the cross-account trust relationship and prevent ChaosSearch from accessing the data bucket.
- The `sqs_queue` flag is boolean; when `true` (as in the POC), SQS notifications are enabled for live indexing. When `false`, only batch/scheduled indexing is available.
- The AWS region is fixed at `us-east-1`. All resources (data bucket, SQS, state bucket) must reside in the same region as declared.
- The `.gitignore` comment block notes that `.tfvars` files should ordinarily be excluded from version control because they may contain sensitive values. The `poc.tfvars` file is intentionally committed here (the exclusion rule is commented out), which is a deviation from that stated policy.

## Business Flows

1. Terraform applies this configuration, creating the S3 data bucket and SQS queue in Onbe's AWS account.
2. The module also creates an IAM role or bucket policy that permits ChaosSearch's AWS account to assume a role identified by `cs_external_id`.
3. When log/event data is written to the S3 bucket, S3 emits a notification to the SQS queue.
4. ChaosSearch polls or receives from the SQS queue, identifies the new object, and indexes it into the ChaosSearch platform.
5. Onbe operators query log data via the ChaosSearch UI or API without needing to manage a separate log storage tier.

## Compliance & Regulatory Concerns

- **PCI DSS**: If the S3 bucket receives logs containing cardholder data (PANs, CVVs, or other SAD), that bucket becomes part of the Cardholder Data Environment (CDE). ChaosSearch's cross-account access would then require PCI DSS scoping review and vendor assessment as a third-party service provider.
- **Data Residency**: All resources are in `us-east-1`. For GDPR/PIPEDA/Quebec Law 25 compliance, confirmation is needed that no EU or Canadian resident PII flows through this bucket.
- **External ID in tfvars**: The `cs_external_id` UUID is committed to git in `poc.tfvars`. If this value is treated as a secret by ChaosSearch, it should not be in source control. Recommend review with Security and the ChaosSearch vendor.
- **Vendor Access**: ChaosSearch is a third-party SaaS vendor with IAM-level read access to Onbe's S3 bucket. This requires a vendor risk assessment, BAA (if health data is present), and DPA (if EU/CA PII is present) per Onbe's third-party management obligations.
- **SOC 2**: Vendor access and logging configuration should be inventoried in Onbe's SOC 2 control environment.

## Business Risks

- **POC-to-Production promotion without security review**: The POC naming suggests this has not gone through formal production change management. Promoting without review creates compliance risk.
- **Sensitive log data ingested by third party**: If logs contain PII or payment card data, ChaosSearch's access could expand the data-sharing perimeter without appropriate controls.
- **No environment separation**: There is only one `.tfvars` file for the POC environment. There is no `dev`, `staging`, or `prod` vars file, suggesting no multi-environment governance is in place.
- **External ID committed to source control**: See Compliance section above.
- **Proof-of-concept state**: The infrastructure is not demonstrably production-hardened. Business continuity and SLA obligations are undefined.
