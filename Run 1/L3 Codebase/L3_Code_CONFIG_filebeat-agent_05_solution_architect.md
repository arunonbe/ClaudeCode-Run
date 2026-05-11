# Solution Architect View — CONFIG_filebeat-agent

## Technical Architecture
- **Agent**: Elastic Filebeat 7.9.2, Windows x64 binary (`filebeat.exe`)
- **Installation**: Windows service, registered via `install-service-filebeat.ps1` PowerShell script
- **Base path**: `D:\filebeat\filebeat-7.9.2\` on all target servers
- **Input discovery**: Dynamic glob `${path.config}/inputs.d/*.yml` — each application gets its own input YAML file
- **Output**: Logstash using the Beats protocol over TLS on port 5044
- **Queue**: In-memory (`queue.mem`); not disk-persistent — events lost if Filebeat crashes before flush

## API Surface
No API exposed. Filebeat is a data shipper only; it exposes no HTTP/REST endpoints in this configuration (monitoring API not enabled).

## Security Posture

### TLS Configuration (filebeat.yml)
- Client certificate authentication is configured (mTLS): cert and key paths referenced in `filebeat.yml`
- **`ssl.verification_mode: none`** — server certificate is NOT validated. This means:
  - The TLS handshake encrypts traffic but does not verify the Logstash server identity
  - A MITM attacker with network access could intercept log data
  - This is a hardcoded security weakness in the committed config file
- Cert file paths committed in `filebeat.yml`: `d:/filebeat/pki/ca.crt`, `d:/filebeat/pki/filebeat.northlane.com.crt`, `d:/filebeat/pki/filebeat.northlane.com.key`

### Other Security
- No credentials are hardcoded in `filebeat.yml`
- Filebeat 7.9.2 may contain known CVEs — upgrade assessment required
- `install-service-filebeat.ps1` installs the service under the default system context — Windows service account permissions not defined in this repo

## Technical Debt
- **Version 7.9.2** — released September 2020, approximately 4+ years behind current Elastic 8.x release
- **`ssl.verification_mode: none`** — should be `full` or `strict`
- **No disk-persistent queue** — in-memory queue means log events are lost if Filebeat process is killed before flushing
- **Manual deployment** — no automation; binary is stored in Git (a large binary in version control)
- **No monitoring endpoint** — Filebeat HTTP monitoring API not enabled; service health not observable from outside
- **Kibana dashboards** are stock unmodified Elastic 7.9 assets — not tailored to Onbe's log structure
- **GitHub Actions CodeQL** is present but analysis of a binary-only repo has limited value

## Gen-3 Migration Requirements
1. Upgrade to Filebeat 8.x or replace with OpenTelemetry Collector / Fluent Bit
2. Set `ssl.verification_mode: full` and ensure valid server certificates on Logstash
3. Remove binary from Git — use package manager or artifact registry for distribution
4. Automate deployment via Ansible/DSC/infrastructure pipeline
5. Enable disk-persistent queue for durability
6. Enable Filebeat monitoring API and add health alerting
7. Centralise per-app input configs (or generate dynamically) rather than distributing across 4 environment CONFIG repos
8. Evaluate migration from on-prem Logstash to cloud-native log forwarding (e.g., Azure Monitor Agent, AWS CloudWatch Agent)

## Code-Level Risks
- Binary (`filebeat.exe`) stored in Git repository — inflates repo size and complicates patch management
- `install-service-filebeat.ps1` runs without privilege elevation validation — may fail silently on servers with restrictive UAC policies
- Input reload not explicitly enabled in `filebeat.yml` — adding new `inputs.d/*.yml` files requires manual service restart
