# Enterprise Architect View — CONFIG_filebeat-agent

## Platform Generation
**Generation 2 (Gen-2)** — Windows-based log shipping for the legacy Tomcat application platform. Filebeat 7.x on Windows is the Gen-2 observability agent pattern. A Gen-3 migration would move to structured logging with a container-native log collection approach (Fluent Bit, OpenTelemetry Collector, or cloud-native log forwarding).

## Business Domain
**Platform Operations / Observability** — cross-cutting concern supporting all business domains. Log availability underpins PCI DSS Requirement 10 (audit log monitoring), incident response, and operational alerting.

## Role in Platform
The observability agent layer — the mechanism by which all application log data reaches the central SIEM/observability platform (Kibana/ChaosSearch). Without Filebeat running correctly on each server, application logs are invisible to operations, security, and support teams.

## Dependencies
| Dependency | Type | Notes |
|------------|------|-------|
| Logstash (`logstash.util.northlane.com`) | Downstream sink | Must be reachable from all app servers |
| PKI CA / cert infrastructure | Security | Client certs at `d:/filebeat/pki/` on each server |
| Windows Service Manager | Runtime | Filebeat runs as a Windows service |
| CONFIG_dev/qa/uat/prod repos | Configuration | Per-app input YAMLs are stored there |
| Kibana / ChaosSearch | Visualisation | Downstream from Logstash |

## Integration Patterns
- **Pull-based log tailing**: Filebeat tails log files on local filesystem, no push from applications required
- **Per-application input files**: Loose coupling — adding a new service only requires adding one YAML file to `inputs.d`
- **mTLS to Logstash**: Authenticated and encrypted transport channel (with cert verification disabled — see risks)
- **Dynamic input discovery**: `inputs.d/*.yml` glob pattern allows hot-addition of new input files without Filebeat restart (if reload is enabled — not explicitly configured in `filebeat.yml`)

## Strategic Status
**Active but aging.** Filebeat 7.9.2 on Windows is the current production log shipping mechanism. This is a Gen-2 pattern tightly coupled to Windows Tomcat infrastructure. Migration to Gen-3 would require replacing this with a cloud-native log collection approach.

ChaosSearch is referenced in the README as an alternative to Kibana, suggesting cloud-native observability migration may already be underway.

## Migration Blockers
- Filebeat Windows binary deployment is manual — no automation (Ansible, DSC, or similar)
- Per-app input YAML files distributed across multiple CONFIG repos — migration requires coordinating changes across 4 environment repos
- Logstash endpoint (`logstash.util.northlane.com`) — internal DNS; must migrate to cloud-native equivalent
- All PKI certs stored at hardcoded Windows paths — migration requires certificate lifecycle automation
- Kibana dashboards bundled in repo are stock Elastic 7.9 dashboards — not customised, but re-importing to Kibana 8.x requires dashboard migration
