# Business Analyst — infrastructure

## Overview

The `infrastructure` repository is Onbe's **web server infrastructure configuration management** repository. It does not contain Terraform, Bicep, or ARM templates. Instead it is a configuration-as-code repository storing IIS/Tomcat reverse-proxy configurations and cryptographic key material that was historically deployed to production and non-production Azure Windows virtual machines.

## What Azure Resources Are Defined

No Azure resource templates (Terraform, Bicep, ARM) are present in this repository. The repository contains two distinct areas:

### 1. `platform-certificates-keys/` — SFTP/SSH Key Material

This folder stores private keys and passphrases for SFTP integrations with two external systems:

| System | Environments | Key files |
|--------|-------------|-----------|
| **Harland** (card manufacturer) | QA | `qa-public`, `qa_open-ssh-private.ppk`, `qa_private.ppk`, `key.txt` |
| **Titan** (likely card personalization bureau) | PROD, QA | `sftp.northlane.com_Private`, `sftp.northlane.com_Private.ppk`, `sftp-qa.northlane.com_openssh_Private`, corresponding public keys, `key.txt` |

The `key.txt` files in all three environments contain the passphrase `n0ty0u` (platform-certificates-keys/harland/QA/key.txt, platform-certificates-keys/titan/PROD/key.txt, platform-certificates-keys/titan/QA/key.txt).

> **CRITICAL FINDING**: Private SSH/SFTP key files and their passphrases are committed to source control. This exposes the cryptographic material to anyone with repository read access. Private keys for production SFTP connections to Harland and Titan are present in plaintext. This is a PCI DSS Requirement 3.5.1 and Requirement 8 violation.

### 2. `webserver-iis-workers/` — IIS/Tomcat AJP Proxy Configurations

This folder stores **IIS ISAPI Redirector** configuration files for the Onbe web tier deployed across multiple Azure Windows Server VMs. The structure mirrors the actual file system paths on the servers (e.g., `PROD\p-az-web02\D\c-base\opt\iis-proxy\`).

**Server inventory identified:**

| Environment | Servers |
|-------------|---------|
| PROD | p-az-web02, p-az-web08, p-az-web09, p-az-web10, p-az-web11, p-az-web13, p-az-web14 |
| QA | q-az-web01, q-az-web02 (inferred) |
| UAT | u-az-web01, u-az-web02 |

**Web application domains configured (PROD):**

| Domain | Purpose |
|--------|---------|
| `clientzone.mypaymentadmin.com` | Client zone portal — mypaymentadmin.com brand |
| `clientzone.northlane.com` | Client zone portal — northlane.com brand (Onbe predecessor) |
| `clientzone.wirecard.com` | Client zone portal — wirecard.com brand (legacy) |
| `csa.northlane.com` | Customer service application |
| `csa.wirecard.com` | Customer service application (legacy brand) |
| `enroll.wirecard.com` | Enrollment portal |
| `login.northlane.com` | Authentication portal |
| `login.wirecard.com` | Authentication portal (legacy brand) |
| `na.citiprepaid` | CitiPrepaid North America |
| `na.clientzone` | North America client zone |
| `na.enroll.com` | North America enrollment |
| `oneplatform_isapi`, `ophub_isapi`, `czhub_isapi` | One Platform hub, CZ Hub |

### Load Balancer / Cluster Configuration

Each `workers.properties` file (`clientzone.mypaymentadmin.com/conf/workers.properties` lines 1–72) defines a **Tomcat AJP load balancer cluster** with:
- Type: `lb` (software load balancer within IIS ISAPI Redirector)
- Balance workers: `clientzone1`, `clientzone2`, `clientzone3`
- Backend hosts: `p-az-app01.nam.wirecard.sys`, `p-az-app02.nam.wirecard.sys`, `p-az-app03.nam.wirecard.sys`
- Protocol: AJP/1.3 on port 9127
- Sticky sessions: `True`

## Business Significance

This repository serves as the **source of truth for web tier topology** for the Onbe payment platform. It enables:
- Reproducible deployment of IIS reverse-proxy configurations.
- Audit of which domains and applications are served by which servers.
- Documentation of SFTP trust relationships with card manufacturing and personalization partners.

The presence of legacy `wirecard.com` domains confirms this infrastructure predates Onbe's acquisition of the Wirecard North America prepaid business. These legacy configurations may represent both active traffic and defunct endpoints requiring decommission review.
