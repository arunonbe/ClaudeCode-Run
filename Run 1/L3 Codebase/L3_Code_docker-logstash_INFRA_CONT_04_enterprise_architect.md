# Enterprise Architect Report — docker-logstash_INFRA_CONT

## Platform Generation
**Generation 2 (Containerised Infrastructure)** — Dockerised Logstash with GitLab CI for image build and ECR for distribution. The architecture uses AWS-native services (SQS, S3, KMS) as the integration bus and storage layer. It does not yet leverage Gen-3 patterns such as managed streaming (Kinesis, MSK), serverless log processing (Lambda), or infrastructure-as-code for the runtime environment.

## Domain
**Infrastructure / Observability** — This is a platform-level infrastructure component, not a business application. It sits in the cross-cutting **observability and logging** domain, serving all Onbe application teams. Classified as `_INFRA_CONT` (Infrastructure Container) in the Onbe naming convention.

## Role in Enterprise Architecture
| Role | Detail |
|---|---|
| Log collection gateway | Receives Beats log streams from all application hosts with mTLS authentication |
| Log routing bus | Routes via AWS SQS to decouple producers from consumers |
| Log archive | Writes to S3 with KMS encryption for long-term retention and compliance |
| Observability backbone | Underpins PCI DSS Req 10, SOC 2 CC7, and NIST CSF monitoring requirements |
| Potential feed for SIEM | S3/ChaosSearch can feed a SIEM (Splunk, Elastic SIEM, etc.) — not configured in repo |

## Dependencies
| Dependency | Type | Criticality | Notes |
|---|---|---|---|
| AWS SQS | Runtime message bus | Critical | Both pipelines; queue names injected at runtime |
| AWS S3 | Runtime storage | Critical | Log archive destination |
| AWS KMS | Runtime encryption | Critical | SSE for S3 |
| AWS ECR | Build artefact store | High | Container image registry |
| Beats agents (Filebeat, etc.) | Runtime clients | Critical | Log sources; authenticate via mTLS |
| GitLab CI | Build pipeline | High | `.gitlab-ci.yml`; uses `Onbe/` GitLab organisation |
| `wcareplogle/cloud-deploy` | Build dependency | High | Docker Hub image used as CI runner — supply chain risk |
| ChaosSearch | Former consumer | Inactive | Output commented out; S3 is current terminal store |
| Logstash 7.9.3 | Runtime engine | Critical | EOL — must upgrade |
| logstash-output-amazon_es | Plugin | Medium | Installed but output inactive; retain for re-enablement |

## Architectural Patterns
| Pattern | Detail |
|---|---|
| Event streaming / log pipeline | Beats → Logstash → SQS → Logstash → S3 (two-stage fan-out via SQS) |
| Immutable container image | PKI certs baked in (though private key inclusion is a security antipattern) |
| Environment variable injection | All runtime config via env vars — 12-factor app compliant for config |
| Mutual TLS | Beats client certificate verification (`ssl_verify_mode => "force_peer"`) |
| Date + SHA image tagging | Traceability: `{YYYYMMDD}-{SHORT_SHA}` tag pattern |
| Dual pipeline | Two separate `.conf` files for ingest and ship — clear separation of concerns |

## Status
**Active production infrastructure** — This is not a prototype. It is the live logging pipeline for the Onbe platform, based on the presence of AWS ECR integration, PKI material, and production SQS/S3 environment variable references.

## Enterprise Blockers / Gaps
1. **Logstash 7.9.3 EOL**: Core platform component is on an unsupported version. Upgrade to 8.x required — note that 8.x has breaking changes (Java 11 required, security enabled by default).
2. **PKI Lifecycle Management**: Certificates and key are static in Git/image. No automated rotation, no expiry monitoring. If certs expire, all Beats log collection stops.
3. **No IaC for Runtime**: The Logstash container's deployment environment (ECS task, Kubernetes deployment, VM) is not defined in this repository. The build pipeline produces an image but there is no deployment definition.
4. **Single Log Destination**: ChaosSearch (search layer) is disabled. S3 stores logs but there is no searchable interface configured — potential gap for incident response and compliance queries.
5. **No Centralized Log Schema**: No Logstash filter/parse stage means logs arrive in heterogeneous formats. This complicates SIEM correlation and compliance reporting.
6. **Supply Chain Risk**: CI runner image from unverified Docker Hub account must be replaced with an Onbe-managed or verified image.
