# Business Analyst Analysis — nlutil-aws_INFRA_TF

## Repository Overview

`nlutil-aws_INFRA_TF` is the utility-layer AWS infrastructure Terraform repository for the Northlane platform. Where `nlroot-aws_INFRA_TF` manages account-level resources (DNS, state), this repo manages the core runtime AWS infrastructure: VPC networking, ECS compute clusters, ECR container registries, Application/Network Load Balancers, SQS queues, IAM roles, and a ChaosSearch log analytics integration.

## Business Purpose

This repository provisions the cloud infrastructure that directly hosts Northlane's containerised services. Key business capabilities it enables:

### 1. Log Analytics Pipeline (ChaosSearch)
The primary workload in this repo is a **Logstash-based log ingestion and shipping pipeline** that feeds into ChaosSearch (a cloud-native Elasticsearch alternative). Two ECS services are managed:
- `logstash-ingest`: Receives log events from application services via Beats protocol on port 5044, writes them to an SQS queue.
- `logstash-ship`: Reads from SQS, batches logs, and ships them to ChaosSearch's S3-based index (`nl-chaossearch-ingest-us-east-1`) and Elasticsearch API at `northlane.chaossearch.io`.

**Business value:** Centralised log aggregation enables operations teams to monitor platform health, investigate cardholder disputes, perform incident root-cause analysis, and support PCI DSS audit log requirements.

### 2. Spring Config Server
The `spring-config` ECS service hosts a Spring Cloud Config Server on port 9990. This provides centralised configuration management for all Northlane microservices, allowing configuration changes without container redeployment.

**Business value:** Centralised config reduces deployment risk and enables operational configuration changes (e.g., feature flags, connection strings) without code releases.

### 3. Estimation Application
The `estimation-app` ECS service (Node.js, port 3000, accessible at `estimate.util.northlane.com`) appears to be a project estimation or work-sizing tool for internal engineering use.

### 4. Networking
The VPC (`10.10.0.0/16`) provides network isolation for all Northlane services. Public and private subnets across 3 availability zones support high-availability deployments. A NAT Gateway and VPN Gateway are provisioned for outbound-only internet access from private subnets and VPN connectivity.

## Business Stakeholders

| Stakeholder | Dependency |
|---|---|
| Security/Compliance | Log pipeline for audit trails (PCI DSS Req 10) |
| Engineering | Spring Config Server for service configuration |
| Operations/SRE | ChaosSearch dashboards for monitoring |
| Engineering Managers | Estimation app |
| All application services | VPC networking, ECR, ECS cluster |

## ChaosSearch Business Context

ChaosSearch is a third-party SaaS log analytics platform. The integration stores log data in an Onbe-owned S3 bucket (`nl-chaossearch-ingest-us-east-1`), which ChaosSearch then indexes from. This is a key architectural decision: **log data stays in Onbe's AWS account** (S3 bucket) rather than being sent to a ChaosSearch-managed data store. ChaosSearch accesses the data via an IAM assume-role with the external ID `c27d9cc2-0f00-4569-b653-22be9f7684ca`.

**PCI DSS relevance:** Log data may contain cardholder data if application logging is not properly sanitised. The fact that logs flow through SQS → Logstash → S3 → ChaosSearch means multiple services handle potentially sensitive log entries.

## Business Risks

1. **ChaosSearch PoC context**: The `util.tfvars` file shows `project = "chaossearch-poc"`, indicating this infrastructure may have originated as a proof-of-concept that became production. PoC infrastructure often lacks the hardening, documentation, and change management processes required for production systems handling cardholder data.

2. **Single NAT Gateway**: `network-vpc.tf` line 12 shows `single_nat_gateway = true`. All private-subnet internet traffic flows through one NAT Gateway. A NAT Gateway failure would disrupt all outbound connectivity for containerised services.

3. **Logstash service count set to 0**: `locals-svc.tf` line 39 shows `ecs_count = { "default"="0" }` for `logstash-ship`. This means the log shipping service is scaled to zero, implying logs are being ingested (via `logstash-ingest`) but not shipped to ChaosSearch unless manually scaled. This could mean the ChaosSearch integration is inactive.
