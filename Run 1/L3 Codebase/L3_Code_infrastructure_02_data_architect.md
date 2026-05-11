# Data Architect — infrastructure

## Data Stored in This Repository

This repository does not provision databases or storage accounts. However, it directly stores **cryptographic secret material** and **network topology data** that is architecturally significant from a data governance perspective.

## Cryptographic Key Material Inventory

### SFTP Private Keys

| File Path | System | Env | Type | Risk Level |
|-----------|--------|-----|------|-----------|
| `platform-certificates-keys/harland/QA/qa_open-ssh-private.ppk` | Harland (card manufacturer) | QA | OpenSSH private key (PuTTY format) | HIGH |
| `platform-certificates-keys/harland/QA/qa_private.ppk` | Harland | QA | PuTTY private key | HIGH |
| `platform-certificates-keys/titan/PROD/sftp.northlane.com_Private` | Titan (personalization bureau) | **PROD** | OpenSSH private key | **CRITICAL** |
| `platform-certificates-keys/titan/PROD/sftp.northlane.com_Private.ppk` | Titan | **PROD** | PuTTY private key | **CRITICAL** |
| `platform-certificates-keys/titan/QA/sftp-qa.northlane.com_openssh_Private` | Titan | QA | OpenSSH private key | HIGH |

### Passphrases in Plaintext

All three `key.txt` files (`harland/QA/key.txt`, `titan/PROD/key.txt`, `titan/QA/key.txt`) contain the identical passphrase string `n0ty0u`. This passphrase protects the private keys above.

**Assessment**: Committing private keys and their passphrases to a source code repository, even a private one, is a fundamental secrets management failure. Under PCI DSS v4.0.1:
- **Requirement 3.5.1**: Cryptographic keys must be protected against disclosure and misuse. Storage in git history is permanent disclosure.
- **Requirement 12.3.3**: Cryptographic keys must be documented and key custodians identified. Version control is not a key management system.
- If these keys provide access to systems that receive card data (e.g., personalized card files from Titan), then the exposure of these keys represents a **potential unauthorized access path to the CDE**.

## Network Topology Data

### Application Server Internal Hostnames

The `workers.properties` files expose internal production infrastructure hostnames:
- `p-az-app01.nam.wirecard.sys`
- `p-az-app02.nam.wirecard.sys`
- `p-az-app03.nam.wirecard.sys`

The `.wirecard.sys` domain suffix is an internal Active Directory domain, indicating these servers are joined to a domain previously managed under the Wirecard North America infrastructure, now operated by Onbe. This information assists attackers in lateral movement if the repository is compromised.

### IIS ISAPI Redirector Configuration Data Model

Each IIS proxy configuration triplet defines:

```
isapi_redirect.properties
  ├── extension_uri           (DLL path for ISAPI)
  ├── log_file               (log rotation path, 20 MB rotate)
  ├── log_level              (info in PROD)
  ├── worker_file            (→ workers.properties)
  └── worker_mount_file      (→ uriworkermap.properties)

workers.properties
  ├── worker.list            (cluster name, status)
  ├── clientzone-cluster.*   (lb type, balance_workers, sticky_session)
  └── clientzoneN.*          (host, type=ajp13, port, connection_pool_size=200)

uriworkermap.properties
  └── URL path → worker mapping rules
      (includes exclusions for /HealthChk, /admin, /balancer, /manager, /probe)
```

### Sensitive Configuration Observations

1. **AJP Protocol on Port 9127**: The AJP/1.3 (Apache JServ Protocol) connection between IIS and Tomcat is not encrypted in transit. AJP runs over plain TCP. If the server-to-server network path is not protected by network segmentation (VLAN isolation), AJP traffic including HTTP request headers, session cookies, and POST bodies would be visible to an attacker with access to that network segment. This is relevant to PCI DSS Requirement 4.2.1.

2. **Connection Pool Size 200 per node**: `workers.properties` configures `connection_pool_size=200` across three nodes (600 concurrent AJP connections per web server). This is a topology data point relevant to capacity planning and DoS surface analysis.

3. **Admin endpoints in URL map exclusions**: `uriworkermap.properties` explicitly excludes `/admin`, `/manager`, `/host-manager`, `/balancer`, `/probe`, `/jsp-examples`, `/servlets-examples`, `/webdav`, `/tomcat-docs` from AJP routing. This prevents these Tomcat manager interfaces from being exposed via the IIS proxy, which is a correct security control. However, it also implies these manager endpoints exist on the Tomcat backends — if the Tomcat backends are reachable directly (bypassing IIS), these endpoints may be accessible.

## Security Configuration Review

| Finding | Severity | Requirement |
|---------|----------|-------------|
| Production SFTP private key committed to git | Critical | PCI DSS Req 3.5.1 |
| Key passphrase `n0ty0u` committed to git | Critical | PCI DSS Req 3.5.1 |
| Identical passphrase across PROD and QA keys | High | PCI DSS Req 12.3.3 (key management) |
| Internal production hostnames in repo | Medium | Defense in depth |
| AJP/1.3 unencrypted server-to-server | Medium | PCI DSS Req 4.2.1 |
| Legacy wirecard.com domains may serve live traffic | Medium | Attack surface |
