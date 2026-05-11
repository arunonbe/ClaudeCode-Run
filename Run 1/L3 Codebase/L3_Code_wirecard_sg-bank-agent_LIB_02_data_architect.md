# Data Architect Report — wirecard_sg-bank-agent_LIB

## Data Models

The service uses a multi-module Spring Batch / Spring Data JPA architecture with Oracle as the production database and H2 for testing. Key domain entities:

- **Customer**: Cardholder identity record synchronized between CCP and CIMB. Contains name, address, identification details.
- **Wire Transfer Out Transaction**: Outbound payment instruction including amount, debtor account, creditor account details, beneficiary name, transfer reference.
- **Wire Transfer Out Status**: Status update received from CIMB (ACCEPTED, REJECTED, PENDING, COMPLETED) linked to a transaction.
- **Batch job metadata**: Spring Batch `JobInstance`, `JobExecution`, `StepExecution` tables (managed by Liquibase, stored in H2 in the `sg-bank-agent-db-app` module or Oracle in production).

Database scripts managed by Liquibase (`db.changelog-master.xml`). Production database: Oracle (`ojdbc6:11.2.0.2.0`).

## Sensitive Data Identified

| Data Type | Location | Handling |
|-----------|----------|---------- |
| Cardholder name / identity | Customer domain objects, CIMB file output | Transmitted to CIMB bank via SFTP |
| Wire transfer amounts | `WireTransferOutTransaction` entity | Financial PII; fraud threshold applied |
| Creditor bank account details (CIMB account number) | Wire transfer instruction | Financial data |
| Debtor account number | `application.yml:22` (`debtor-account-number: 1234567890`) | Hardcoded settlement account |
| CIMB SFTP RSA private key | `application.yml:34–61` | **CRITICAL — embedded in source code** |
| PGP private key passphrase | `application.yml:154` (`pgp.cimb.passphrase: wirecard`) | **CRITICAL — hardcoded in source** |
| PGP private key file | `sg-bank-agent-config/src/main/resources/sgba-pgp/0xCE5B683F-sec.asc` | Private key committed to repo |
| Nexus passwords | `gradle.properties:10,14,21,25` | Hardcoded plaintext |
| AWS credentials | `gradle.properties:31–32` | AWS access key and secret key hardcoded |

## Encryption Status

- **SFTP transport**: RSA key-based SFTP to CIMB — encrypted transport. However, the private key is committed to source code.
- **PGP file encryption**: Files sent to CIMB are PGP-encrypted with the CIMB public key. Files received from CIMB are PGP-decrypted with the Wirecard private key (`0xCE5B683F-sec.asc` committed to source).
- **Database**: H2 in-memory for test/dev; Oracle for production. No column-level encryption configured.
- **Event hub**: ActiveMQ transport — encryption depends on ActiveMQ TLS configuration.

## Data Flows

1. **Inbound customer sync**: CCP (ActiveMQ) → event consumer → `ImportCustomersWriter` → Oracle DB.
2. **Outbound customer publish**: Oracle DB → `PublishCustomersReader` → CCP (ActiveMQ event).
3. **Inbound wire transfer**: CCP (ActiveMQ) → `ImportNewWireTransferOutTransactionsWriter` → Oracle DB.
4. **Outbound wire transfer file**: Oracle DB → `PublishWireTransferOutTransactionProcessor` → XSLT transform → PGP encrypt → SFTP upload → CIMB.
5. **Inbound CIMB status file**: CIMB SFTP → download → PGP decrypt → `ImportWireTransferOutStatusFileReader` → Oracle DB → CCP (ActiveMQ event).
6. **Fraud alert**: `WireTransferOutFraudValidator` → email alert if amount > $50,000.

## Retention Concerns

- Wire transfer records are subject to BSA/AML 5-year retention requirements.
- Customer PII is subject to Singapore PDPA (data minimization, retention limits).
- PGP-encrypted SFTP files archived in `/tmp/sg-bank-agent/` paths — no retention policy is configured in the application.

## PCI DSS Compliance

- **CRITICAL: RSA private key in source code** (`application.yml:34–61`) — violates PCI DSS Req. 3.5 (protect cryptographic keys) and Req. 2.2 (system configuration security).
- **CRITICAL: PGP private key file committed to repository** (`0xCE5B683F-sec.asc`) — violates PCI DSS Req. 3.5.
- **HIGH: AWS access key and secret in `gradle.properties`** (`[REDACTED — rotate immediately]`) — exposed credential material.
- **HIGH: Nexus passwords in `gradle.properties`** — exposed credential material.
- **MEDIUM: H2 console enabled** (`spring.h2.console.enabled: true`) in the shared application.yml — if production uses this configuration, it exposes a direct SQL interface to the database.
