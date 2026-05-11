# Business Analyst Report — docker-logstash_INFRA_CONT

## Business Purpose
This repository defines a **containerised Logstash log aggregation and forwarding pipeline** for the Onbe platform. It acts as the central log ingestion and routing infrastructure, collecting structured logs from application services (via Beats agents) and forwarding them to a long-term storage and search backend (AWS S3 / ChaosSearch). The pipeline supports Onbe's security monitoring, operational observability, and compliance logging requirements.

## Capabilities
| Capability | Pipeline Config | Detail |
|---|---|---|
| Beats Log Ingestion | `ingest-beats.conf` | Receives logs from Filebeat/Metricbeat/etc. over mutual-TLS on port 5044 |
| SQS Message Bus | `ingest-beats.conf` (output) / `ship-chaos.conf` (input) | Decouples ingestion from delivery via AWS SQS queue |
| S3 Log Storage | `ship-chaos.conf` (output) | Ships logs to AWS S3 with KMS server-side encryption and private ACL |
| ChaosSearch Integration | `ship-chaos.conf` (commented out) | Amazon ES-compatible output to ChaosSearch was previously configured; replaced by S3 |
| PKI / Mutual TLS | `pki/` directory | CA cert + server cert/key for authenticating Beats agents |
| ECR Image Distribution | `.gitlab-ci.yml` | Built image pushed to AWS ECR on every commit |

## Key Entities
| Entity | Role |
|---|---|
| Logstash container | Central log processor and router |
| Beats agents | Log shippers running on application hosts (Filebeat, Metricbeat, Winlogbeat, etc.) |
| AWS SQS queue | Asynchronous message bus between ingest and delivery pipelines |
| AWS S3 bucket | Long-term log archive with KMS encryption |
| ChaosSearch (inactive) | Former search/analytics layer; S3 now feeds it directly or via another mechanism |
| AWS ECR | Container image registry for the Logstash Docker image |

## Business Rules
1. All Beats-to-Logstash connections must use mutual TLS (`ssl_verify_mode => "force_peer"` — `ingest-beats.conf:7`).
2. Logs stored in S3 must use server-side encryption with KMS (`server_side_encryption_algorithm => "aws:kms"` — `ship-chaos.conf:20`).
3. S3 bucket ACL must be `private` (`canned_acl => "private"` — `ship-chaos.conf:26`).
4. All configuration values (queue names, regions, bucket names, credentials) are injected via environment variables — no hardcoded values in pipeline configs.
5. The Docker image tag is generated from the Git commit date + short SHA to ensure traceability.

## Business Flows
```
Application Hosts
  Beats agents (Filebeat/Metricbeat)
    │  mTLS :5044
    ▼
[ingest-beats.conf — Logstash]
  Input:  Beats (mTLS port 5044)
  Output: AWS SQS (${OUTPUT_SQS_QUEUE})
    │
    ▼
[AWS SQS Queue]
    │
    ▼
[ship-chaos.conf — Logstash]
  Input:  AWS SQS (${INPUT_SQS_QUEUE})
  Output: AWS S3 (KMS encrypted, private ACL)
    │
    ▼
[AWS S3 Bucket] → ChaosSearch / analytics consumers
```

## Compliance Relevance
- **PCI DSS Req 10**: Log collection, retention, and monitoring — this pipeline is a key Req 10 control for centralised audit logging.
- **SOC 2 CC7**: Monitoring of system operations — log aggregation underpins anomaly detection.
- **NIST CSF DE.CM**: Continuous monitoring — Logstash is the collection layer.
- **GLBA**: Log retention for financial services operations data.
- **GDPR / CCPA**: Logs may contain PII (IP addresses, user identifiers) — retention policy and access controls on the S3 bucket are critical.

## Risks
| Risk | Severity | Notes |
|---|---|---|
| PKI private key committed to Git | Critical | `pki/server.key` is in the repository and baked into the Docker image. If the image or repo is accessed by an unauthorised party, the private key is exposed. |
| Single pipeline — no redundancy visible | Medium | Single Logstash container; no HA or failover configuration in the repo |
| ChaosSearch output commented out | Low | Transition artefact — confirm ChaosSearch is fully decommissioned or re-wired directly from S3 |
| SQS queue names/regions externally configured | Low | Correct environment variable injection is critical at runtime; missing vars would silently drop logs |
