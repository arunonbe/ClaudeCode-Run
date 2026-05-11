# Solution Architect Report — docker-logstash_INFRA_CONT

## Architecture Overview
```
┌─────────────────────────────────────────────────────────────┐
│  Application Hosts (VMs / Containers)                       │
│  Beats agents (Filebeat, Metricbeat, Winlogbeat, etc.)      │
└──────────────────────┬──────────────────────────────────────┘
                       │ mTLS :${INPUT_BEATS_PORT:5044}
                       │ Client cert verified via pki/ca.crt
┌──────────────────────▼──────────────────────────────────────┐
│  Logstash Container (logstash:7.9.3)                        │
│  Pipeline: ingest-beats.conf                                │
│  Input:  beats (ssl=true, force_peer mTLS)                  │
│  Output: sqs → ${OUTPUT_SQS_QUEUE} (${OUTPUT_SQS_REGION})  │
└──────────────────────┬──────────────────────────────────────┘
                       │ AWS SDK (env-var credentials)
┌──────────────────────▼──────────────────────────────────────┐
│  AWS SQS Queue                                              │
│  ${OUTPUT_SQS_QUEUE} / ${INPUT_SQS_QUEUE}                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│  Logstash Container (same image)                            │
│  Pipeline: ship-chaos.conf                                  │
│  Input:  sqs ← ${INPUT_SQS_QUEUE}                          │
│  Output: s3 → ${CHAOSSEARCH_S3_BUCKET} (KMS, private ACL)  │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│  AWS S3 Bucket (${CHAOSSEARCH_S3_BUCKET})                   │
│  SSE: aws:kms | ACL: private | Codec: json_lines            │
│  Rotation: size=${CHAOSSEARCH_S3_SIZE} / time=${...S3_TIME} │
└─────────────────────────────────────────────────────────────┘

[ChaosSearch Amazon ES output — COMMENTED OUT in ship-chaos.conf:10–17]
```

## Pipeline Configurations

### `ingest-beats.conf`
| Section | Key Setting | Value |
|---|---|---|
| Input type | `beats` | Port `${INPUT_BEATS_PORT:5044}` |
| SSL | `ssl => true` | Enabled |
| CA cert | `ssl_certificate_authorities` | `["${HOME}/pki/ca.crt"]` |
| Server cert | `ssl_certificate` | `"${HOME}/pki/server.crt"` |
| Server key | `ssl_key` | `"${HOME}/pki/server.key"` |
| Client auth | `ssl_verify_mode` | `"force_peer"` — mutual TLS enforced |
| Output type | `sqs` | Queue: `${OUTPUT_SQS_QUEUE}` |
| Filter stage | None | No parsing or transformation |

### `ship-chaos.conf`
| Section | Key Setting | Value |
|---|---|---|
| Input type | `sqs` | Queue: `${INPUT_SQS_QUEUE}` |
| Output type | `s3` | Bucket: `${CHAOSSEARCH_S3_BUCKET}` |
| Encryption | `server_side_encryption => true` | Algorithm: `aws:kms` |
| ACL | `canned_acl => "private"` | Private access only |
| Codec | `json_lines` | One JSON document per line |
| Alt output | `amazon_es` | **Commented out** (lines 11–17) |

## Security Architecture
| Control | Status | File:Line | Notes |
|---|---|---|---|
| Mutual TLS (Beats) | Implemented | ingest-beats.conf:3–8 | Both client and server cert required |
| Private key in repo | Critical gap | pki/server.key | Should never be in version control |
| S3 KMS encryption | Implemented | ship-chaos.conf:19–20 | Data at rest encrypted |
| S3 private ACL | Implemented | ship-chaos.conf:26 | No public access |
| Non-root container user | Implemented | Dockerfile:15–16 | Runs as `logstash` user |
| AWS credentials (ECR) | GitLab CI vars | .gitlab-ci.yml:19–20 | Not in code; injected at CI time |
| AWS credentials (SQS/S3) | Runtime env vars | ship-chaos.conf / ingest-beats.conf | Not in code; must be injected at container start |
| Docker daemon TLS | Disabled | .gitlab-ci.yml:17 (commented `DOCKER_TLS_CERTDIR`) | Unencrypted Docker API in CI |
| CI runner image trust | Unverified | .gitlab-ci.yml:1 | `wcareplogle/cloud-deploy:latest` from Docker Hub |

## Technical Debt
| Item | Severity | File:Line |
|---|---|---|
| `logstash:7.9.3` base image — EOL (Elastic 7.x support ended Feb 2025) | High | Dockerfile:1 |
| `pki/server.key` private key committed to repository | Critical | pki/server.key |
| `wcareplogle/cloud-deploy:latest` unverified CI runner image | High | .gitlab-ci.yml:1 |
| Docker daemon unencrypted in CI (`tcp://docker:2375`) | High | .gitlab-ci.yml:21 |
| `docker:19.03.12-dind` — old Docker version in CI | Medium | .gitlab-ci.yml:23 |
| No filter/parse stage — logs stored without structured parsing | Medium | ingest-beats.conf, ship-chaos.conf |
| ChaosSearch ES output commented out — dead code with AWS key references in comments | Medium | ship-chaos.conf:10–17 |
| No dead letter queue for failed events | Medium | Both .conf files |
| No health check in Dockerfile | Medium | Dockerfile |
| No restart policy defined | Low | Dockerfile (would be in compose/ECS task) |
| `logstash-output-amazon_es` plugin installed but output is inactive | Low | Dockerfile:11 |

## Gen-3 Migration Recommendations
| Dimension | Current | Recommended |
|---|---|---|
| Logstash version | 7.9.3 (EOL) | 8.x LTS (note: requires config migration; security on by default) |
| PKI management | Certs baked in Docker image | AWS Certificate Manager or Vault PKI; inject at runtime via secrets mount |
| Private key storage | Git / Docker layer | AWS Secrets Manager; never in version control |
| CI runner | `wcareplogle/cloud-deploy:latest` | Onbe-managed CI image in ECR |
| Docker daemon security | Unencrypted TCP | Enable `DOCKER_TLS_CERTDIR` in GitLab CI |
| Log parsing | None (pass-through) | Add Logstash filter pipeline with grok/json/mutate for structured log schema |
| PII masking | None | Add `mutate` / `fingerprint` filter to mask PII before S3 storage |
| Dead letter queue | None | Add `dead_letter_queue` plugin + SQS DLQ |
| Search layer | ChaosSearch (inactive) | Re-evaluate: OpenSearch Serverless, Elastic Cloud, or re-enable ChaosSearch via S3 |
| IaC | None in repo | Add Terraform/CDK for ECS task definition, SQS queues, S3 bucket, KMS key, IAM roles |
| Log integrity | None | Enable S3 Object Lock (WORM) for PCI DSS Req 10.3.3 tamper-evidence |
| HA / scaling | Not defined | Define ECS service with auto-scaling; or consider Amazon Data Firehose as managed alternative |
