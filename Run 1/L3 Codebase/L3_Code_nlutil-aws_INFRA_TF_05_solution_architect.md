# Solution Architect Analysis — nlutil-aws_INFRA_TF

## Security Findings — PCI DSS Critical Review

### Finding 1: HARDCODED AWS CREDENTIALS IN TFVARS FILE (CRITICAL — PCI DSS Req 8.6.2)

**File:** `util.tfvars`, lines 10–11

```
cs_access_key    = "ICEADM1DMPMILGF8LDTR"
cs_secret_key    = "N5tV8/AAxyk7+tkjr6d+BviDmu9eno2C/4yUyCvJ"
```

These are AWS IAM access key credentials committed in plaintext to the repository. They are passed directly as environment variables to the `logstash-ship` ECS task definition (`locals-svc.tf` lines 49–50):

```hcl
{"name": "CHAOSSEARCH_ACCESS_KEY_ID", "value": var.cs_access_key },
{"name": "CHAOSSEARCH_SECRET_ACCESS_KEY", "value": var.cs_secret_key },
```

**Impact:** Any person with repository access can obtain these credentials. ECS task definitions with embedded credentials are visible in the AWS console without additional authentication. Credentials stored in ECS environment variables appear in CloudTrail logs when task definitions are described.

**Required remediation:**
1. Immediately rotate these credentials.
2. Store them in AWS Secrets Manager.
3. Reference via `secrets` block in the ECS task definition (not `environment`):
   ```hcl
   secrets = [
     {"name": "CHAOSSEARCH_ACCESS_KEY_ID", "valueFrom": "arn:aws:secretsmanager:..."}
   ]
   ```
4. Remove `util.tfvars` from version history using `git filter-branch` or BFG Repo Cleaner.
5. Add `*.tfvars` to `.gitignore`.

### Finding 2: IAM Policy with `ecr:*` and `Resource: *` (HIGH — PCI DSS Req 7)

**File:** `identity-iam-ecs.tf`, lines 53–65

The `ecs_task_policy` grants `ecr:*` on `Resource: "*"`, giving all ECS tasks full ECR administrative access including destructive operations (`ecr:DeleteRepository`, `ecr:BatchDeleteImage`). A compromised task could delete all container images.

**Recommendation:** Replace `ecr:*` with minimum necessary ECR actions and scope to specific repository ARNs:
```json
{
  "Action": ["ecr:GetAuthorizationToken", "ecr:BatchCheckLayerAvailability",
             "ecr:GetDownloadUrlForLayer", "ecr:BatchGetImage"],
  "Resource": ["arn:aws:ecr:us-east-1:<account_id>:repository/wc-logstash",
               "arn:aws:ecr:us-east-1:<account_id>:repository/wc-spring-config"]
}
```

### Finding 3: IAM Policy with `ssm:*` and `Resource: *` (HIGH — PCI DSS Req 7)

**File:** `identity-iam-ecs.tf`, lines 122–137

`ssm:*` on `Resource: "*"` grants ECS instances the ability to read and write all SSM parameters in the account, including secrets stored by other services. This violates least-privilege.

**Recommendation:** Restrict to `ssm:GetParameter`, `ssm:GetParameters`, `ssm:DescribeParameters` and scope to specific parameter ARN prefixes (e.g., `arn:aws:ssm:us-east-1:<account>:parameter/northlane/*`).

### Finding 4: `iam:PassRole` with `Resource: *` (HIGH — PCI DSS Req 7)

**File:** `identity-iam-ecs.tf`, line 129

`iam:PassRole` on `Resource: "*"` allows the ECS instance role to pass any IAM role to any AWS service. An attacker who compromises an ECS instance could escalate privileges by passing a highly permissive role.

**Recommendation:** Restrict to specific role ARNs needed for SSM operations:
```json
{
  "Action": "iam:PassRole",
  "Resource": "arn:aws:iam::<account>:role/*-ecs-tasks-role",
  "Condition": {"StringEquals": {"iam:PassedToService": "ssm.amazonaws.com"}}
}
```

### Finding 5: S3 Bucket for ChaosSearch Without Explicit Encryption Configuration (MEDIUM)

**File:** `chaossearch.tf` — delegates bucket creation to external module `git::https://github.com/ChaosSearch/terraform-modules.git//encrypted-s3-bucket-live-indexing`

No commit hash is pinned. The module name suggests encryption is configured, but this cannot be verified without auditing the external module. Log data written to this bucket may contain PII.

**Recommendation:** Fork the external module into an Onbe-controlled repository, verify its encryption configuration explicitly sets a CMK, and pin to a specific commit.

### Finding 6: SQS Queues Without Explicit Encryption (MEDIUM)

**File:** `data-sqs.tf`

Neither `aws_sqs_queue` resource specifies `kms_master_key_id` or `sqs_managed_sse_enabled`. Log messages in transit through SQS may not be encrypted at rest.

**Recommendation:** Add to both SQS queues:
```hcl
kms_master_key_id = "alias/northlane-sqs-key"
```

### Finding 7: ECR Image Tag Mutability Set to MUTABLE (MEDIUM)

**File:** `data-ecr.tf`

Both ECR repositories set `image_tag_mutability = "MUTABLE"`. This allows existing image tags to be overwritten silently, breaking deployment reproducibility and audit integrity.

**Recommendation:** Change to `image_tag_mutability = "IMMUTABLE"` for production repositories.

### Finding 8: Container Image Version `latest` (MEDIUM)

**File:** `locals-svc.tf` lines 27, 61, 85, 107

All services use `version = "latest"`. In production environments, `latest` should never be used.

### Finding 9: No VPC Flow Logs (MEDIUM — PCI DSS Req 10)

No `aws_flow_log` resource is defined. VPC Flow Logs are required for PCI DSS network traffic monitoring.

### Finding 10: No Public Access Block on ChaosSearch S3 Bucket (UNVERIFIED)

The S3 bucket created by the external ChaosSearch module does not have a verified public access block configuration within this repository.

## Security Risk Summary

| Finding | Severity | PCI DSS Requirement |
|---|---|---|
| Hardcoded credentials in `util.tfvars` | CRITICAL | 8.6.2 |
| `ecr:*` Resource `*` in ECS task policy | HIGH | 7.2.1 |
| `ssm:*` Resource `*` in SSM policy | HIGH | 7.2.1 |
| `iam:PassRole` Resource `*` | HIGH | 7.2.1 |
| External module not pinned (ChaosSearch) | MEDIUM | 6.3.3 |
| SQS queues not explicitly encrypted | MEDIUM | 3.5 |
| ECR MUTABLE image tags | MEDIUM | 6.2 |
| `latest` container image tag | MEDIUM | 6.2 |
| No VPC Flow Logs | MEDIUM | 10.2 |
