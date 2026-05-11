# Solution Architect — infrastructure

## Technical Debt Register

### Critical Severity

| ID | Location | Issue | Regulatory Impact |
|----|----------|-------|-------------------|
| TD-001 | `platform-certificates-keys/titan/PROD/sftp.northlane.com_Private` | Production SFTP private key committed to source control | PCI DSS Req 3.5.1 — key disclosure |
| TD-002 | `platform-certificates-keys/titan/PROD/sftp.northlane.com_Private.ppk` | Production SFTP private key (PuTTY format) committed to source control | PCI DSS Req 3.5.1 |
| TD-003 | `platform-certificates-keys/titan/PROD/key.txt` | Passphrase `n0ty0u` committed to source control | PCI DSS Req 3.5.1 |
| TD-004 | `platform-certificates-keys/harland/QA/key.txt`, `titan/QA/key.txt`, `titan/PROD/key.txt` | Identical passphrase across all three environments; single passphrase compromise unlocks all keys | PCI DSS Req 12.3.3 |

### High Severity

| ID | Location | Issue | Impact |
|----|----------|-------|--------|
| TD-005 | `webserver-iis-workers/PROD/*/workers.properties` | AJP/1.3 on TCP 9127 — unencrypted server-to-server protocol; session cookies and POST bodies visible on the LAN segment | PCI DSS Req 4.2.1 |
| TD-006 | All `workers.properties` files | Internal production hostnames `p-az-app01/02/03.nam.wirecard.sys` committed to source control | Defense in depth; reconnaissance risk |
| TD-007 | Repository root | No `.gitignore` preventing future key or credential commits | Secrets management hygiene |
| TD-008 | Repository | No CI/CD pipeline; no secret scanning; no deployment automation | Operational risk; no compliance gate |

### Medium Severity

| ID | Location | Issue | Impact |
|----|----------|-------|--------|
| TD-009 | `webserver-iis-workers/PROD/*/uriworkermap.properties` | Tomcat manager endpoints (`/admin`, `/manager`, `/host-manager`) excluded from AJP routing but implied to exist on app backends — direct backend access would expose them | Attack surface |
| TD-010 | `webserver-iis-workers/PROD/*/isapi_redirect.properties` | `log_level=info` in PROD — IIS ISAPI Redirector logs may contain URL parameters; log access controls not visible from config alone | PCI DSS Req 10.3 |
| TD-011 | `webserver-iis-workers/PROD/*/workers.properties` | `connection_pool_size=200` per node (600 total) — large pool; no idle timeout or connection drain configured | DoS surface; resource exhaustion |
| TD-012 | All environments | No documented key rotation schedule; passphrase appears unchanged since initial deployment | PCI DSS Req 3.7.1 |

## Security Vulnerabilities

### Finding 1 — Production SFTP Private Key in Source Control (TD-001, TD-002, TD-003)

**Files**: `platform-certificates-keys/titan/PROD/sftp.northlane.com_Private`, `sftp.northlane.com_Private.ppk`, `key.txt`

**Description**: The OpenSSH and PuTTY-format private keys for the Titan (Northlane card personalization bureau) SFTP server are committed directly to the repository. The passphrase protecting these keys (`n0ty0u`) is stored in `key.txt` in the same directory. Any person with repository read access — past or present — possesses complete credentials to authenticate to the Titan SFTP server as the Onbe service account.

**PCI DSS Impact**: Titan is a card personalization bureau that receives card embossing data files. Access to the Titan SFTP server likely provides access to files containing cardholder names, card numbers (PANs), expiry dates, and service codes — all Sensitive Authentication Data (SAD) or PAN data in transit. This represents a potential **unauthorized access path into the CDE** via third-party partner systems.

**Remediation**:
1. Treat the exposed keys as compromised. Coordinate with Titan/Northlane to revoke the current public key registration and generate a new key pair.
2. Remove all key files and `key.txt` from the repository and purge from git history using `git filter-repo` or BFG Repo Cleaner.
3. Store the new private key in Azure Key Vault; deploy to SFTP client via Managed Identity retrieval at runtime.
4. Add `.gitignore` entries for `*.ppk`, `*_Private`, `*_private`, `key.txt`.
5. Enable GitHub Advanced Security secret scanning with push protection to block future commits.

### Finding 2 — Identical Passphrase Across PROD and QA (TD-004)

**Files**: `harland/QA/key.txt`, `titan/PROD/key.txt`, `titan/QA/key.txt`

**Description**: All three `key.txt` files contain the same string `n0ty0u`. This passphrase simultaneously unlocks the Harland QA key, the Titan PROD key, and the Titan QA key. A QA-environment exposure (which is typically lower-security) therefore directly compromises production key material.

**PCI DSS Impact**: PCI DSS Requirement 12.3.3 requires that cryptographic keys have identified custodians and documented management procedures. Requirement 3.7.4 recommends key changes when there is any indication of possible compromise. The use of a single passphrase across environments is inconsistent with a documented key management program.

**Remediation**: Generate distinct, high-entropy passphrases (minimum 16 characters, mixed character classes) for each key pair and store them in Azure Key Vault. Do not store passphrases in source control under any circumstances.

### Finding 3 — AJP/1.3 Unencrypted Internal Protocol (TD-005)

**Files**: All `workers.properties` files, e.g., `PROD/p-az-web02/.../clientzone.mypaymentadmin.com/conf/workers.properties`

**Description**: The IIS ISAPI Redirector communicates with Tomcat backend servers using AJP/1.3 on TCP port 9127. AJP/1.3 is a binary protocol with no transport encryption. HTTP headers (including session cookies and authorization headers), POST body data (including form field values), and URL parameters are transmitted in plaintext between the IIS server and the Tomcat application server.

If any of the following can reach the IIS-to-Tomcat network segment, they can passively capture session data: any VM on the same Azure VNet subnet, any compromised process on the web or app servers, a misconfigured NSG rule.

**PCI DSS Impact**: Requirement 4.2.1 requires strong cryptography for transmission of cardholder data. If session data or form submissions on ClientZone, CSA, or Login portals contain PAN data or authentication credentials, AJP transmission violates this requirement.

**Remediation**: Replace AJP/1.3 with HTTPS reverse proxy using IIS ARR (Application Request Routing) or Azure Application Gateway. Alternatively, configure AJP with a required secret and network-layer encryption (IPsec or Azure VNet encryption) on the server-to-server segment. Evaluate whether migration to Azure App Service or AKS makes this configuration obsolete.

### Finding 4 — No Secret Scanning in Repository (TD-007, TD-008)

**Description**: The repository has no GitHub Actions workflow, no branch protection rules, and no secret scanning configuration. The private key exposure described in TD-001 through TD-004 would have been prevented by GitHub Advanced Security secret scanning with push protection enabled, which recognizes OpenSSH private key headers (`-----BEGIN OPENSSH PRIVATE KEY-----`) and PuTTY `.ppk` files.

**Remediation**: Enable GitHub Advanced Security. Configure secret scanning with push protection. Add a `.gitignore` that blocks key files. Add a branch protection rule requiring CI workflow checks to pass before merge.

## Remediation Priority Matrix

| Priority | Item | Estimated Effort |
|----------|------|-----------------|
| 1 — Immediate | Rotate Titan PROD SFTP key pair; revoke exposed key at partner | 1–2 days (partner coordination) |
| 2 — Immediate | Remove all key files and passphrases from repo; purge git history | 1 day |
| 3 — Immediate | Enable GitHub secret scanning with push protection | 0.5 day |
| 4 — Sprint 1 | Migrate SFTP key storage to Azure Key Vault | 2–3 days |
| 5 — Sprint 1 | Add distinct passphrases per environment/key pair | 0.5 day |
| 6 — Sprint 1 | Implement deployment pipeline for IIS configs (GitHub Actions + Ansible) | 3–5 days |
| 7 — Sprint 2 | Replace AJP/1.3 with HTTPS reverse proxy (IIS ARR or App Gateway) | 3–5 days |
| 8 — Sprint 2 | Implement NSG rules isolating web-to-app server segment if AJP retained | 1–2 days |
| 9 — Quarter 2 | Assess and schedule decommission of `wirecard.com` domain configurations | 2 days (assessment) |
| 10 — Quarter 2 | Evaluate migration of web tier from IIS-on-VM to Azure App Gateway + App Service | 10–20 days |

## Positive Observations

- The URL exclusion map in `uriworkermap.properties` correctly prevents Tomcat manager endpoints (`/admin`, `/manager`, `/jsp-examples`) from being exposed via the IIS reverse proxy. This is a correct defensive configuration that prevents external access to Tomcat management interfaces.
- Environment separation (PROD/UAT/QA) is maintained in the folder structure, making it straightforward to identify which configuration applies to which tier.
- The presence of both OpenSSH and PuTTY (.ppk) format keys for each integration indicates consideration for multiple deployment tools — though the key management approach is fundamentally flawed.
- Sticky session configuration (`sticky_session=True` in `workers.properties`) is appropriate for stateful session management in the legacy web application tier, preventing session affinity breaks during load-balanced requests.
- PROD `isapi_redirect.properties` sets `log_level=info` rather than `debug`, which reduces (but does not eliminate) the volume of sensitive data captured in web server logs.
