# Data Architect Analysis — nlutil-aws_INFRA_TF

## Data Stores and Flows

### 1. SQS Queues (`data-sqs.tf`)

Two SQS queues are defined:
- `{workspace}-logstash` (main ingest queue): 14-day retention (`1209600` seconds), 256 KB max message size. Dead-letter queue configured with `maxReceiveCount = 4`.
- `{workspace}-lsdeadletter-queue`: Same retention and size. Holds messages that failed processing 4 times.

**Data content:** SQS messages contain structured log events from Northlane application services. These log events may include request metadata, transaction IDs, user identifiers, and potentially PII if application logging is not sanitised before ingestion.

**PCI DSS concern:** SQS queues are **not encrypted with a customer-managed KMS key**. The `aws_sqs_queue` resources in `data-sqs.tf` do not specify `kms_master_key_id`. AWS SQS encrypts at rest using SSE-SQS (AWS-managed key) only when explicitly configured with `sqs_managed_sse_enabled = true` (Terraform AWS provider v4+) or via KMS. The absence of explicit encryption configuration means messages may be stored unencrypted at rest, or using only the default AWS-managed key depending on the account default configuration.

**Recommendation:** Add `kms_master_key_id` to both SQS queues to enforce CMK-based encryption, consistent with the approach used for Terraform state.

### 2. S3 Log Data Bucket (via ChaosSearch module, `chaossearch.tf`)

The `module "s3_customer_buckets"` creates an S3 bucket named `wc-chaossearch-poc` via the external ChaosSearch Terraform module. The module name `encrypted-s3-bucket-live-indexing` suggests the bucket is created with encryption, but the encryption configuration depends entirely on the external module implementation.

**Data flow:** Application logs → Logstash (ECS) → SQS → Logstash-Ship (ECS) → S3 (`nl-chaossearch-ingest-us-east-1`) → ChaosSearch API indexing.

**Data residency:** Log data ultimately stored in `nl-chaossearch-ingest-us-east-1` S3 bucket remains in Onbe's AWS account (us-east-1). ChaosSearch performs read-only indexing via an assumed IAM role.

### 3. ECR Container Image Repositories (`data-ecr.tf`)

Two ECR repositories are defined:
- `wc-logstash` — Logstash container images.
- `wc-spring-config` — Spring Config Server container images.

Both have `image_scanning_configuration { scan_on_push = true }` — a positive security control. However, both have `image_tag_mutability = "MUTABLE"`, meaning image tags can be overwritten. For production deployments, `IMMUTABLE` tags are recommended to ensure reproducible deployments.

### 4. CloudWatch Log Groups (`services/main.tf`)

The ECS service module creates CloudWatch log groups at path `/{workspace}/service/{service_name}` with `retention_in_days = 14`. Log data for all ECS containers flows to CloudWatch.

**PCI DSS Requirement 10:** 14-day CloudWatch retention satisfies the immediate availability requirement but PCI DSS requires 12 months of audit log retention with 3 months immediately accessible. Logs should be archived to S3 with longer retention.

## Data Flow Architecture

```
Application Services
       ↓ (Beats/TCP port 5044)
Logstash-Ingest ECS Service
       ↓ (SQS message)
{workspace}-logstash SQS Queue
       ↓ (poll)
Logstash-Ship ECS Service
       ↓ (S3 PutObject)
S3: nl-chaossearch-ingest-us-east-1
       ↓ (AssumeRole cross-account)
ChaosSearch SaaS Indexing
       ↓
northlane.chaossearch.io (query endpoint)
```

## Sensitive Data Assessment

### Variables File (`util.tfvars`) — CRITICAL FINDING

The `util.tfvars` file contains **hardcoded AWS access credentials**:

```
cs_access_key    = "ICEADM1DMPMILGF8LDTR"
cs_secret_key    = "N5tV8/AAxyk7+tkjr6d+BviDmu9eno2C/4yUyCvJ"
```

These appear to be ChaosSearch API user credentials (AWS IAM access keys for the ChaosSearch integration). These are committed in plaintext to the repository.

**Severity:** CRITICAL — PCI DSS Requirement 8.6.2 prohibits hardcoded credentials. These credentials grant S3 and SQS access as defined by the associated IAM policy. If the repository is accessible to any party beyond the minimum required, these credentials should be considered compromised. They should be immediately rotated and moved to AWS Secrets Manager or Parameter Store.

These credentials are also passed directly as environment variables to the `logstash-ship` ECS task (`locals-svc.tf` lines 49–50), meaning they are visible in ECS task definitions via the AWS Console/API without encryption.

## Data Encryption Summary

| Asset | Encryption at Rest | KMS CMK | Status |
|---|---|---|---|
| SQS `logstash` queue | Not explicitly configured | No | RISK |
| SQS dead-letter queue | Not explicitly configured | No | RISK |
| ECR `wc-logstash` | Yes (AWS default for ECR) | No | Acceptable |
| ECR `wc-spring-config` | Yes (AWS default for ECR) | No | Acceptable |
| CloudWatch log groups | Yes (AWS default) | No | Acceptable |
| ChaosSearch S3 bucket | Depends on external module | Unknown | Unverified |
