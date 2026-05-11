# Data Architect Report — docker-logstash_INFRA_CONT

## Data Stores
| Store | Type | Config Reference | Purpose |
|---|---|---|---|
| AWS SQS Queue | Message queue | `${OUTPUT_SQS_QUEUE}` / `${INPUT_SQS_QUEUE}` — ingest-beats.conf:14, ship-chaos.conf:4 | Decouple ingest from delivery; buffer during S3 write spikes |
| AWS S3 Bucket | Object store | `${CHAOSSEARCH_S3_BUCKET}` — ship-chaos.conf:22 | Long-term log archive (encrypted) |
| ChaosSearch (Amazon ES) | Search / analytics | `${CHAOSSEARCH_ES_HOST}` — ship-chaos.conf (commented out lines 11–17) | Formerly the search layer; currently disabled |
| PKI store (container-local) | File system | `pki/` directory → `${HOME}/pki/` in container | mTLS certificates for Beats authentication |

## Schema / Data Structures
Logstash processes raw log events as JSON documents. No schema is defined within this repository — schema is determined by the Beats agents and application log formats. The S3 output codec is `json_lines` (`ship-chaos.conf:25`), meaning each log line is a complete JSON document.

**SQS output codec**: `${OUTPUT_SQS_CODEC}` — configurable at runtime; value unknown from repo.

## Sensitive Data Assessment
| File | Sensitivity | Detail |
|---|---|---|
| `pki/server.key` | Critical | Private key for the Logstash server TLS certificate — committed to repository and baked into container image. Existence noted; key material redacted here. |
| `pki/ca.crt` | Medium | Certificate Authority public certificate — less sensitive but should be managed in a secrets store |
| `pki/server.crt` | Medium | Server public certificate — baked into image |
| Log content (runtime) | Variable | Application logs may contain PII (IP addresses, user IDs, email addresses), financial data, or operational data. Log content is not visible in repo but must be assessed for PCI DSS and GDPR scoping. |

**Note on PKI**: The `pki/server.key` file present in this repository represents a key management risk. Any log data protected by mTLS using this key could be retrospectively decrypted if the key is compromised. The key should be rotated immediately and removed from version control. Replace with runtime injection via AWS Secrets Manager or Vault.

## Encryption
| Layer | Status | Detail |
|---|---|---|
| Beats → Logstash transport | Implemented | Mutual TLS; `ssl => true`, `ssl_verify_mode => "force_peer"` — ingest-beats.conf:3–8 |
| SQS messages | AWS-managed | SQS server-side encryption; not explicitly configured in Logstash output but AWS default applies |
| S3 storage | Implemented | `server_side_encryption => true`, `server_side_encryption_algorithm => "aws:kms"` — ship-chaos.conf:19–20 |
| S3 access | Implemented | `canned_acl => "private"` — ship-chaos.conf:26 |
| AWS API authentication | Runtime env vars | `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` injected via GitLab CI variables into build; runtime injection needed for container |

## Data Flow
```
[Beats Agents]
  mTLS :5044 with pki/ca.crt, pki/server.crt, pki/server.key
    ▼
[Logstash — ingest-beats.conf]
  Codec: ${OUTPUT_SQS_CODEC}
    ▼
[AWS SQS: ${OUTPUT_SQS_QUEUE} / ${INPUT_SQS_QUEUE}]
    ▼
[Logstash — ship-chaos.conf]
  Codec: json_lines
    ▼
[AWS S3: ${CHAOSSEARCH_S3_BUCKET}]
  KMS encrypted, private ACL
  size_file: ${CHAOSSEARCH_S3_SIZE}
  time_file: ${CHAOSSEARCH_S3_TIME}
    ▼
[ChaosSearch / Analytics] (reads from S3 directly)
```

## Data Quality
- No filtering, parsing, or transformation rules are defined in either pipeline config.
- The `ingest-beats.conf` passes events directly from Beats input to SQS output without any mutation/filter stage.
- The `ship-chaos.conf` passes events from SQS to S3 without transformation.
- **No grok parsing, no field enrichment, no dead letter queue (DLQ), no error handling pipelines.**

## Compliance Gaps
| Gap | Standard | Recommendation |
|---|---|---|
| Private key in Git / Docker image | PCI DSS Req 3.5, SOC 2 CC6 | Rotate key immediately; inject at runtime via Secrets Manager; add `pki/` to `.gitignore` |
| Log retention policy not defined in repo | PCI DSS Req 10.7, GLBA | Define S3 lifecycle policy (min 12 months online per PCI DSS); document in IaC |
| PII in logs not addressed | GDPR Art. 5, CCPA | Implement log masking/filtering in Logstash pipeline for PII fields before S3 storage |
| No DLQ for failed events | SOC 2 CC7 | Add SQS DLQ and Logstash dead_letter_queue plugin to capture and alert on dropped events |
| ChaosSearch credentials in commented code | PCI DSS Req 3 | Remove commented-out credentials block from ship-chaos.conf:11–17 (AWS key/secret references) |
| No log integrity mechanism | PCI DSS Req 10.3 | Consider S3 Object Lock (WORM) for tamper-evidence |
