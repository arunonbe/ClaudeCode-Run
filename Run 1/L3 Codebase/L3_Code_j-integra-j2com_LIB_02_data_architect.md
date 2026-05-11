# Data Architect View — j-integra-j2com_LIB

## Data Stores
This library does not own or directly manage any data store. It is a client-side proxy library. Data stores are owned by the target ecount services.

| Accessed Via | Type | Notes |
|-------------|------|-------|
| RepositoryService (XML-RPC) | File/document repository | Read and write operations via RepositoryServiceXMLRPCClient |
| StrongBox (XML-RPC) | Secure credential vault | InquirySecureProfile, UpdateSecureProfile |
| CryptoService (XML-RPC) | Cryptographic service | PGP encrypt/decrypt |
| ecount platform databases | SQL Server (indirect) | Accessed via XML-RPC calls to Java services, not directly |
| Director registry | Service registry | Endpoint resolution and caching |
| ELF / TIBCO JMS | Logging infrastructure | Transaction log forwarding |

## Schema / Tables
No schema is owned by this library. Data structures are defined as Java DTOs:

| DTO Class | Purpose |
|-----------|---------|
| EncryptPGPInput / Output | PGP key name, plaintext/ciphertext payload |
| DecryptPGPInput / Output | PGP key name, ciphertext/plaintext payload |
| InquirySecureProfileInput / Output | Profile ID, secure data fields |
| UpdateSecureProfileInput / Output | Profile update fields |
| RepositoryServiceRead / Output | File path / content |
| RepositoryServiceWrite / Output | File path / content |
| EventDispatchInput / Output | Event type, payload |
| TriggerServiceInput / Output | Trigger type, parameters |
| RuleCreateInput / Output | Rule definition |
| SimpleFeeInquiryInput / Output | Fee inquiry parameters |
| XSecuritySetHierarchyNodesInput / Output | Security hierarchy configuration |

## Sensitive Data Classification
| Data | Classification | Risk |
|------|---------------|------|
| PGP plaintext/ciphertext | Potentially Cardholder Data or credentials | Handled by CryptoService; callers could pass PANs |
| Secure profile data | Potentially PII / cardholder data | InquirySecureProfile / UpdateSecureProfile |
| Repository file content | Variable — could contain cardholder data | RepositoryService read/write |
| TIBCO JMS credentials | Infrastructure credentials | pconfig.xml file |
| ELF SSL private key | PKI material | CitiPrepaid_159547.p12 |

## Encryption
- PGP encryption/decryption is delegated to the StrongBox CryptoService via XML-RPC — this is the intended cryptographic protection mechanism.
- ELF JMS transport uses SSL (`sslEnabled: true`) to `csdesbdev.nam.nsroot.net:7243`.
- XML-RPC calls are over plain HTTP (not HTTPS) unless the Director-resolved endpoint includes TLS — no TLS enforcement is visible in the XMLRPCClient base class reference.
- SSL certificates: identity file `CitiPrepaid_159547.p12`, trusted root `entrust_root_dev.cert.pem`, stored at `d:\c-base\config\elf-cert\`.

## Data Flow
1. COM script calls jintegra stub → Java XMLRPCClient receives call.
2. XMLRPCClient serialises input DTO to XML-RPC request.
3. Request sent over HTTP to Director-resolved service endpoint.
4. Response deserialised to output DTO.
5. Output returned to COM caller via jintegra bridge.
6. Transaction log events sent asynchronously to TIBCO JMS queue (ELF).

## Data Quality / Retention
- No data validation in the DTO/client layer — inputs are passed as-is to the XML-RPC service.
- ELF logging buffers up to 2500 log messages in the async appender before flushing.
- Transaction log records are forwarded to Citi ELF infrastructure (hostnames: `cccaelm10p.nam.nsroot.net` etc.) for compliance logging.

## Compliance Gaps
1. XML-RPC calls are over HTTP (not enforced HTTPS) — data including potentially sensitive payloads transits in cleartext on the network unless network-layer controls exist.
2. PGP plaintext passed as a string parameter through the XML-RPC call — the cleartext is on the wire between J2COM service and the target Java service.
3. ELF logging configuration references a Citi email address (`shomit.sahdev@citi.com`) — operational continuity and notification routing are broken post-acquisition.
4. SSL certificates at hardcoded filesystem paths (`d:\c-base\config\elf-cert\`) require manual lifecycle management; expiry would break ELF logging silently (fallback to file appender).
5. No masking of secure profile or PGP payload data before logging via log4j reflection utility (`Utility.reflectionToString`).
