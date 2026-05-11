# chaossearch_INFRA_TF — Data Architect View

## Data Stores

| Store | Type | Name / Identifier | Purpose |
|---|---|---|---|
| ChaosSearch Data Bucket | AWS S3 | `wc-chaossearch-poc` | Holds raw log/event data to be indexed by ChaosSearch |
| Terraform State Bucket | AWS S3 | `wc-poc-state` | Stores Terraform state file (`chaossearch/terraform.tfstate`) |
| DynamoDB Locking Table | AWS DynamoDB | `terraform-poc-locking` | Prevents concurrent Terraform state writes |
| SQS Queue | AWS SQS | Name not specified in this repo (delegated to module) | Delivers S3 object-created notifications to ChaosSearch |

## Schema & Tables

This repository provisions infrastructure storage, not application-level schemas. The ChaosSearch data bucket is schema-free at the S3 level; ChaosSearch applies its own indexing schema upon ingestion. No database schemas, table definitions, or data models are defined in this codebase.

The DynamoDB locking table is a standard Terraform state-lock table and stores only lock metadata (lock ID, timestamp, who holds the lock).

## Sensitive Data Handling

- The data bucket (`wc-chaossearch-poc`) is intended to hold log data. The nature of that log data (whether it contains PII, PAN, or other regulated data) is not defined in this repository. This is a critical gap.
- The `cs_external_id` value — a UUID identifying Onbe's ChaosSearch customer account — is stored in plaintext in `poc.tfvars` and committed to git. This value is used in the IAM assume-role trust policy. Its sensitivity level should be confirmed with the ChaosSearch vendor. Location: `poc.tfvars`, line 2.
- No explicit data classification tags are applied to the S3 bucket resources within this repository's direct Terraform code (tags are delegated to the external module).

## Encryption & Protection

- **Terraform state encryption**: The S3 backend for Terraform state has `encrypt = true` and uses a named KMS key alias (`alias/wc-poc-state-encryption-key`). This means Terraform state at rest is encrypted with a customer-managed KMS key.
- **Data bucket encryption**: Encryption configuration for the ChaosSearch data bucket (`wc-chaossearch-poc`) is not defined in `main.tf` directly — it is delegated entirely to the external Terraform module (`chaossearch-prereq`) sourced from GitLab. The actual encryption posture of the data bucket cannot be confirmed from this repository alone.
- **SQS encryption**: Similarly delegated to the module. Cannot confirm whether SQS messages are encrypted at rest or in transit from this repository.
- **KMS key management**: The KMS key alias `alias/wc-poc-state-encryption-key` must exist in the `us-east-1` account before Terraform can initialise. There is no definition or management of this key in this repository.

## Data Flow

```
Log/Event Sources
      |
      v
AWS S3 Bucket: wc-chaossearch-poc  (Onbe-owned, us-east-1)
      |
      | S3 Event Notification (ObjectCreated)
      v
AWS SQS Queue  (Onbe-owned, us-east-1)
      |
      | SQS Poll / Push (cross-account, via IAM assume-role using cs_external_id)
      v
ChaosSearch Platform  (third-party SaaS)
      |
      v
ChaosSearch Index / Search UI
```

The Terraform state data flow is separate:
```
terraform apply
      |
      v
S3 Bucket: wc-poc-state  (key: chaossearch/terraform.tfstate)
      |  encrypted with KMS alias/wc-poc-state-encryption-key
      |
      v
DynamoDB: terraform-poc-locking  (state lock)
```

## Data Quality & Retention

- No data retention policies, S3 lifecycle rules, or bucket expiry configurations are defined in this repository. These are either absent or delegated to the external module.
- No data quality checks, schema validation, or data contracts are in scope for this infrastructure repository.
- There is no versioning configuration for the S3 data bucket visible in this repository.

## Compliance Gaps

1. **Data classification not defined**: The type of data stored in `wc-chaossearch-poc` is unspecified. Without classification, PCI DSS scoping, GDPR/CCPA applicability, and GLBA applicability cannot be determined.
2. **No visible bucket policy restricting access**: The data bucket's access policy is in the external module and cannot be reviewed from this repository.
3. **No S3 access logging for data bucket**: No access logging configuration is visible. This would be required for PCI DSS Requirement 10 (audit logging) if the bucket is in scope.
4. **No lifecycle/retention policy**: GLBA, GDPR, and PCI DSS all have data retention and disposal requirements. No lifecycle rules are confirmed.
5. **SQS message retention**: SQS default message retention is 4 days. If log events queue up without being consumed, data may be silently dropped. No dead-letter queue (DLQ) configuration is visible.
6. **tfvars in source control**: Sensitive configuration values including the external ID are committed to git, violating data governance best practices noted in the `.gitignore` file's own comments.
