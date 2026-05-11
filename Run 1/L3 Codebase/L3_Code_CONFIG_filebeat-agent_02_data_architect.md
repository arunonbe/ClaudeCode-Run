# Data Architect View — CONFIG_filebeat-agent

## Data Stores
- **Application log files on disk** — source data; read by Filebeat from paths defined in per-app input YAMLs (stored in CONFIG_dev/qa/uat/prod repos)
- **Filebeat in-memory queue** — transient buffer; `events: 4096`, flushed at `512` events or `5s` timeout
- **Logstash** (`logstash.util.northlane.com:5044`) — downstream log aggregation; data forwarded via Beats protocol over TLS
- **Filebeat local log files** (`d:\filebeat\logs\`) — agent's own operational logs; retained 10 rotations
- **Kibana / ChaosSearch** — final persistence and search layer (not configured in this repo)

## Schema
- **`filebeat.yml`** — base agent configuration: output destination (Logstash), TLS cert paths, queue settings, input discovery path, log settings, event processor rules
- **Per-app input YAMLs** (not in this repo) — define `paths:` for log file globs, `fields:` for metadata, and `multiline:` patterns per application; stored in environment CONFIG repos
- **`fields.yml`** — Elastic schema descriptor for all supported Filebeat module fields (1,400+ lines); not customised — stock Filebeat 7.9.2 file
- **`filebeat.reference.yml`** — full annotated reference config; not the active config — documentation only

## Sensitive Data Handling
- **TLS private key path**: `d:/filebeat/pki/filebeat.northlane.com.key` — the private key file path is committed in `filebeat.yml`. The private key file itself is not in the repo, but its location on disk is exposed.
- **TLS certificate path**: `d:/filebeat/pki/filebeat.northlane.com.crt` — similarly exposed in config.
- **CA certificate path**: `d:/filebeat/pki/ca.crt` — CA cert path committed.
- Log data in transit may contain application-layer sensitive data (transaction identifiers, error messages with partial PII); Filebeat performs no PII scrubbing.

## Encryption
- **In transit**: TLS to Logstash using mutual TLS (client cert + key); **however, `ssl.verification_mode: none` disables server certificate validation** — this is a significant gap. The connection is encrypted but the server is not authenticated, making it vulnerable to MITM attacks.
- **At rest**: No encryption of Filebeat's own log files or registry (cursor position tracking) is configured.

## Data Flow
```
Application log files (D:\c-base\logs\...)
  → Filebeat inputs.d/*.yml (per-app input configs from CONFIG_dev/qa/uat/prod)
  → Filebeat in-memory queue (4096 events, 512 min flush, 5s timeout)
  → JSON parse error events dropped
  → Logstash logstash.util.northlane.com:5044 (TLS/mTLS, no server cert verify)
  → Kibana / ChaosSearch
```

## Quality
- `keepfiles: 10` — Filebeat operational logs retained for 10 rotations; no size or age limits specified
- `queue.mem.flush.timeout: 5s` — maximum 5-second data latency under low-volume conditions
- No deduplication or enrichment configured in Filebeat itself

## Compliance Gaps
- `ssl.verification_mode: none` — violates PCI DSS Requirement 4.2 (strong cryptography) in spirit; encrypted channel but unverified endpoint
- Filebeat 7.9.2 (released 2020) — known CVEs exist in this version; should be upgraded to current 8.x
- No log retention policy enforced at the Filebeat level — retention is handled downstream (Logstash/Elasticsearch/ChaosSearch)
- Application logs may contain sensitive data; no field-level redaction is configured
