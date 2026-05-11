# Business Analyst Report — wirecard_sg-bank-agent_LIB

## Business Purpose

`wirecard_sg-bank-agent_LIB` is the Singapore bank agent service in the Wirecard/Northlane issuing platform (Gen-2). It acts as a bidirectional integration bridge between the Wirecard Central Card Platform (CCP) and CIMB Bank Singapore, facilitating wire transfer (outbound fund disbursements) from the Wirecard prepaid card platform to cardholders' CIMB bank accounts in Singapore.

The service handles:
- Receiving customer enrollment data from CCP and publishing to CIMB.
- Receiving wire transfer (GIRO/wire-out) requests from CCP and publishing them to CIMB via SFTP.
- Receiving status updates from CIMB (wire transfer confirmation/rejection files) and publishing them back to CCP.
- Wire transfer cancellation processing.
- Fraud alerting on large outbound wire transfers exceeding a configurable threshold.

## Capabilities

1. **Customer synchronization**: Import customers from CCP, export customer data to CIMB format.
2. **Wire transfer out**: Import new wire transfer requests from CCP, transform to CIMB-required XML format, PGP-encrypt and SFTP-upload to CIMB.
3. **Wire transfer status import**: Download CIMB status update files via SFTP, PGP-decrypt, parse, and publish status events back to CCP.
4. **Cancellation processing**: Import wire transfer cancellation requests from CCP and process them.
5. **Fraud monitoring**: Alert (via email) on wire transfer amounts exceeding the configured `fraud.wire-transfer-out-limit` ($50,000 by default).
6. **Batch job execution**: Spring Batch jobs for all above flows, with partitioned processing.
7. **Event-driven communication**: ActiveMQ-based event hub for asynchronous message exchange with CCP.
8. **Email notifications**: Production support alerts and fraud alerts via email templates.

## Client and Cardholder Impact

Direct cardholder impact. The Singapore bank agent processes cardholder fund disbursements to CIMB bank accounts. Failures or delays in the wire transfer processing directly prevent cardholders from accessing their funds. The fraud monitoring protects both cardholders and the platform from unauthorized large transfers.

## Business Rules in Code

- Wire transfer fraud threshold: `fraud.wire-transfer-out-limit: 50000.00` SGD (configurable).
- Settlement mode for CIMB: `B` (Batch).
- Debtor account: `1234567890` at `ANZBSGS0XXX` (ANZ Bank Singapore — suggesting the platform holds a settlement account at ANZ that funds CIMB transfers).
- SFTP polling rate: `500000000` (nanoseconds ≈ 500ms) for CIMB file pickup.
- Batch page size: 1 record per page for wire transfer jobs (extremely conservative — likely due to CIMB file format constraints or settlement risk management).

## Regulatory Obligations

- **MAS (Monetary Authority of Singapore)**: Wire transfer services in Singapore must comply with MAS Notice PSN02 on prevention of money laundering/terrorism financing. The `$50,000` fraud alert threshold is consistent with MAS wire transfer reporting thresholds.
- **GDPR / Singapore PDPA**: Customer data synchronized between CCP and CIMB constitutes cross-border personal data transfer. Both GDPR (for EU cardholders) and Singapore Personal Data Protection Act apply.
- **OFAC**: Wire transfers must be screened against OFAC sanctions lists before transmission to CIMB.
- **PCI DSS**: The service processes payment-related data (customer profiles, wire transfer amounts). The SFTP channel to CIMB is in scope for PCI DSS network security requirements.

## Key Business Risks

1. **SFTP private key committed to source code**: An RSA private key for the CIMB SFTP connection is embedded in `application.yml`. This is a critical security violation.
2. **Hardcoded credentials in `gradle.properties`**: Nexus deployment passwords and AWS access keys are hardcoded in the repository.
3. **All actuator endpoints exposed without authentication**.
4. **H2 console enabled in default profile**: The H2 web console is enabled, which in a production misconfiguration could allow direct database access.
