# Solution Architect View — j-integra-j2com_LIB

## Technical Architecture

**Stack**: Java 6 (compiler target), Spring 2.5.6, jintegra 2.12 (commercial Java-COM bridge), XML-RPC (ecount custom client), log4j 1.2.15, TIBCO JMS 5.0 (tibcrypt, tibjms), SLF4J 1.4.2, activation 1.0.2, JavaMail 1.4 (mail.jar), elf-1.4 (Citi ELF transaction logging).

**Architecture**:
- `JavaCOMConfiguration` static initialiser loads Spring context (`DirectorySettings.xml`) at class-load time, resolves Director client and DBCP DataSource factory.
- Each XML-RPC service has a dedicated client class extending `XMLRPCClient`.
- `XMLRPCServiceLocator` instances are created via `DirectorServiceLocator` — resolves service endpoints from the Director registry with 40-second cache.
- The jintegra bridge exposes these Java client objects as COM Automation servers to Windows scripts.
- The entire service is hosted as a Windows NT service (`jIntegraService.exe`).

**Key classes**:
| Class | Role |
|-------|------|
| `JavaCOMConfiguration` | Static factory for all XML-RPC client instances; Director + DBCP initialisation |
| `CryptoServiceXMLRPCClient` | PGP encrypt/decrypt proxy to StrongBox CryptoService |
| `StrongBoxXMLRPCClient` | StrongBox secure vault operations |
| `RepositoryServiceXMLRPCClient` | Repository file read/write |
| `ProfileServiceXMLRPCClient` | Cardholder profile management |
| `MemberXMLRPCClient` | Member account operations |
| `TransferXMLRPCClient` | Fund transfer |
| `WorkflowManagerXMLRPCClient` | Workflow engine |
| `XSecurityServiceXMLRPCClient` | Security hierarchy management |
| `OrderServiceXMLRPCClient` | Order processing |
| `EventServiceXMLRPCClient` / `EcountCoreEventServiceXMLRPCClient` | Event dispatch |

## API Surface
COM Automation server — no HTTP API. Exposed to Windows COM clients via jintegra.

**XML-RPC operations proxied** (per `ServiceConstants.java` — not read but inferred from client classes):
- CryptoService: `encryptPGP`, `decryptPGP`
- StrongBox: secure profile inquiry/update
- RepositoryService: read, write
- ProfileService: profile operations
- MemberService: member operations
- TransferService: transfer operations
- WorkflowManager/Agent: workflow operations
- JobFileManager / JobManager: job management
- XSecurity: hierarchy node management
- OrderService: order operations
- EventService / EcountCoreEventService: event dispatch

## Security Posture

### Authentication / Authorisation
- No HTTP-level authentication on the XML-RPC calls from J2COM to ecount services.
- COM access is controlled at the Windows OS level (COM registration security, DCOM permissions).
- No audit trail of which COM caller invoked which service method.
- The `agent` string is passed to all service calls — used for audit/logging in ecount services, but not authenticated.

### Cryptography
- **PGP operations** are proxied but not performed in this library — delegated to StrongBox CryptoService.
- ELF transport uses TLS/SSL (`sslEnabled: true`) with client certificate (`CitiPrepaid_159547.p12`).
- XML-RPC calls between J2COM service and ecount services: **no TLS enforcement visible** — traffic is over plain HTTP unless the network layer enforces it. Sensitive payloads (PGP plaintext, profile data) transit in cleartext.

### Secrets
- **ELF SSL private key**: `d:\c-base\config\elf-cert\CitiPrepaid_159547.p12` — at a fixed path on Windows server.
- **ELF password config**: `d:\c-base\config\elf-cert\pconfig.xml` — TIBCO JMS credentials, plaintext XML file.
- **`log4j.xml` email address**: `shomit.sahdev@citi.com` — Citi-era email, a data residue risk.
- No secrets from this library are committed to the repository source files (JAR files and config files are committed but not text-format credentials in Java source).

### CVEs / Dependency Risks
- **log4j 1.2.15**: CVE-2019-17571 (SocketServer RCE, CVSS 9.8). CVE-2022-23302 (JMSSink). CVE-2022-23305 (JDBCAppender SQL injection). The current log4j.xml uses `JMSQueueAppender` from a custom class; `JMSSink` from log4j core is not shown, but log4j 1.x must be replaced entirely.
- **Spring 2.5.6**: EOL 2013; multiple critical CVEs.
- **jintegra 2.12**: Commercial binary of unknown security maintenance status. Source not available; cannot assess for CVEs.
- **activation 1.0.2**: CVE-2018-8781 (DoS in certain scenarios). EOL.
- **elf-1.4**: Citi internal library; CVE status unknown.
- **SLF4J 1.4.2**: Very old; SLF4J 2.x is current.

## Technical Debt
1. Java 6 compiler target — severely EOL.
2. `JavaCOMConfiguration` uses a static initialiser for Spring context loading — any failure is non-recoverable without JVM restart.
3. `CryptoServiceXMLRPCClient.encryptPGP()` calls `Utility.reflectionToString(input)` at INFO level — the `EncryptPGPInput` object may contain the plaintext data to be encrypted; logging this violates data protection.
4. All XML-RPC client constructors take a `serviceFriendlyName` string; the superclass constructor call inverts `serviceFriendlyName` and `serviceName` arguments in some places (risk of misconfiguration).
5. jintegra binary (`jIntegraService.exe`) committed to source — binary provenance cannot be verified from source control.
6. `testJ2COM-Service.vbs` in `src/bin/` — test script committed to production source; content and any embedded test data should be audited and removed.
7. `src/conf/log4j.xml` references Citi-era email address and hostnames — broken post-acquisition operational configuration.
8. Jenkinsfile skips tests (`-Dmaven.test.skip=true`) — no automated test execution.

## Gen-3 Migration Requirements
This component should be retired rather than migrated. For any COM-script consumers that must continue:
1. Identify each VBScript/COM caller and their invoked service.
2. Replace COM calls with direct REST API calls to Gen-3 service endpoints.
3. For cryptographic operations: migrate to crypto-service_SVC REST API or equivalent.
4. For profile/member operations: migrate to profile_SVC or account-management-api REST API.
5. For workflow/job operations: migrate to jobservice_SVC or workflow-service REST API.
6. Decommission the Windows NT service once all COM callers are migrated.

If temporary continuation is required:
1. Upgrade log4j to Logback/SLF4J immediately (CVE-2022-23302 JMSSink is exploitable if JNDI is available).
2. Replace `Utility.reflectionToString(input)` calls in crypto client with masked/sanitised output.
3. Audit COM DCOM security settings to restrict which accounts can invoke the service.

## Code-Level Risks

| File | Line | Risk |
|------|------|------|
| `CryptoServiceXMLRPCClient.java` | 48 | `Utility.reflectionToString(input)` logged at INFO — may log PGP plaintext payload |
| `CryptoServiceXMLRPCClient.java` | 57 | Same issue for `decryptPGP` input |
| `JavaCOMConfiguration.java` | 54-61 | Static initialiser — Spring context failure causes `ExceptionInInitializerError`; no recovery |
| `src/conf/log4j.xml` | 23 | `shomit.sahdev@citi.com` — Citi-era email address; operational defect |
| `src/conf/log4j.xml` | 19 | `providerUrl: ssl://csdesbdev.nam.nsroot.net:7243` — Citi-era infrastructure hostname |
| `src/conf/timesync.properties` | 1-6 | ELF time server hostnames (`cccaelm10p.nam.nsroot.net` etc.) — Citi-era infra |
| `src/lib/jIntegraService.exe` | — | Binary committed to source; integrity unverifiable |
| `src/bin/testJ2COM-Service.vbs` | — | VBScript test file in source; audit for embedded test data |
