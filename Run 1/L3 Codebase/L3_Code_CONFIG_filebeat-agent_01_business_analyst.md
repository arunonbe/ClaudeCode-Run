# Business Analyst View — CONFIG_filebeat-agent

## Business Purpose
This repository distributes and maintains the Elastic Filebeat 7.9.2 log-shipping agent that is installed on every application and batch server across all Onbe environments (DEV, QA, UAT, PROD). Its purpose is to collect application log files from Windows servers and ship them to the central observability platform (Logstash → Kibana / ChaosSearch).

## Business Capabilities
- Centralised distribution of a versioned, pre-configured Filebeat binary for Windows
- Log shipping from all application and batch servers to the observability pipeline
- mTLS-secured transport of log data to Logstash (certificate-based client authentication)
- Event buffering (in-memory queue) to handle Logstash intermittency
- Filtering of JSON parse errors to reduce noise

## Business Entities
- **Server** — any application or batch Windows server running the Filebeat service
- **Log stream** — an individual application's log file(s), described by per-app YAML input files (stored in environment-specific CONFIG repos)
- **Logstash** — the central log aggregation endpoint
- **Kibana / ChaosSearch** — the log visualisation and search layer

## Business Rules
- Each application/job must have its own `{APPLICATION_NAME}.yml` input file in the `inputs.d` folder on the server
- Per-application input files are managed in environment-specific repos (CONFIG_dev, CONFIG_qa, CONFIG_uat, CONFIG_prod) under `{SERVER_NAME}/filebeat_application.yml/` subdirectories
- The Filebeat binary and base configuration are shared across all environments from this repo
- JSON parse error events are dropped to reduce noise
- Log files are retained locally for 10 rotations

## Business Flows
1. New application deployed to a server
2. Engineer creates `{APPLICATION_NAME}.yml` in the appropriate environment CONFIG repo under the server's `filebeat_application.yml/` folder
3. Filebeat base installation is deployed to `D:\filebeat\filebeat-7.9.2\` on the server
4. Filebeat service is restarted via Windows Services
5. Application logs flow: Server log file → Filebeat → Logstash (`logstash.util.northlane.com:5044`) → Kibana/ChaosSearch

## Compliance Concerns
- Log shipping enables audit trail availability — relevant to PCI DSS Requirement 10 (log monitoring and retention)
- mTLS between Filebeat and Logstash supports PCI DSS encrypted transmission requirements
- **`ssl.verification_mode: none`** disables certificate chain verification — this is a compliance gap for PCI DSS and SOC 2 (encrypted transport without server certificate validation is vulnerable to MITM)
- Log content may include cardholder data, PII, or other sensitive data depending on application logging practices — the Filebeat config itself does not redact or filter PII

## Business Risks
- Version 7.9.2 is significantly outdated (released 2020); Elastic has released many security and bug fixes since then
- All environments share the same Filebeat binary and base config — a vulnerability in Filebeat 7.9.2 affects all environments simultaneously
- `ssl.verification_mode: none` means a compromised network path could intercept log data in transit
- If per-app input YAML files are not created when a new service is deployed, that service's logs will not be shipped — potential audit/compliance gap
