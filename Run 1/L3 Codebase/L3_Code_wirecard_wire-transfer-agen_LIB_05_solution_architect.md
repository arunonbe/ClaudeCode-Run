# Solution Architect — wirecard_wire-transfer-agen_LIB

## Technical Architecture
- **Framework**: Spring Boot 1.5.13.RELEASE, Java 8, Gradle 4.8
- **Batch**: Spring Batch (chunk-oriented, file-partitioned)
- **Persistence**: JPA/Hibernate + Liquibase (db module); HikariCP
- **Messaging**: Wirecard EventHub client (ActiveMQ transport)
- **Serialisation**: Jackson (JSON) for batch files; JAXB (`javax.xml.bind`) for EventHub events
- **REST API**: Spring MVC (`spring-boot-starter-web`); Thymeleaf for templates; Swagger (`issuing-boot-actuator-utils`)
- **XJC**: JAXB code generation for XML-bound event objects (`xjcGenerate`)
- **Email**: Spring Mail via `EmailService`
- **Modules**: batch, config, data, service; jenkins-plugins (CI sub-module)

## API Surface
### REST Endpoints (wire-transfer-agent REST controller)
| Endpoint | Method | Description |
|---|---|---|
| `/wire-transfer-agent/v1/wire-transfer-out/send-money` (S2S) | POST | Initiate outbound wire transfer (system-to-system) |
| `/wire-transfer-agent/v1/wire-transfer-out/send-money` (S2C) | POST | Initiate outbound wire transfer (system-to-customer) |
| `/wire-transfer-agent/v1/wire-transfer-out/{id}/cancel` | POST | Cancel outbound wire transfer |
| `/wire-transfer-agent/monitoring/*` | GET | Spring Boot Actuator |

### Batch Jobs
See `BatchJob` enum: 5 named batch jobs (see Business Analyst doc)

### EventHub Events (published)
- `NEW_WIRE_TRANSFER_OUT_EVENT` (XML/JAXB)
- `CANCEL_WIRE_TRANSFER_OUT_EVENT` (XML/JAXB)
- `INCOMING_WIRE_TRANSFER_STATUS_UPDATED_EVENT` (XML/JAXB)

### EventHub Events (consumed)
- `IncomingWireTransferEvent`
- `WireTransferOutStatusUpdatedEvent`
- `WireTransferOutCancellationStatusEvent`
- `WireTransferOutNotificationOfChangeEvent`

## Security Posture

### Authentication / Authorisation
- REST endpoints likely protected by OAuth2/JWT (consistent with FTC sibling and `iss-resource-server` pattern)
- Spring Security configuration not fully visible in available batch module source; service module not fully cloned
- Internal service — network segmentation assumed

### Sensitive Data in Events
`NewWireTransferOutEvent` (JAXB XML, published to EventHub):
- `payeesBankAccountNumber` — bank account number (DDA)
- `payeesBankRoutingNumber` — ABA routing number
- `payeesFirstName` / `payeesLastName` — PII
- Transmitted over ActiveMQ without observed payload-level encryption
- Persisted in EventHub EVENT_HUB_EVENT.EVENT (blob) without observed encryption

### Known CVEs (library-level risk)
| Library | Version | Risk |
|---|---|---|
| Spring Boot | 1.5.13.RELEASE | EOL; Tomcat embed CVEs; Spring Framework CVEs (CVE-2022-22965 Spring4Shell affects Spring Boot) |
| Spring Security OAuth2 | (from BOM) | Same as FTC |
| JAXB (`javax.xml.bind`) | Java 8 bundled | Deprecated from Java 9+; removed in Java 11 |
| Spring Batch | (from 1.5 BOM) | EOL |
| commons-collections | 3.2.2 | Historical RCE; safe if no untrusted deserialisation |
| Hibernate | (from 1.5 BOM) | Old version |

## Technical Debt
1. Spring Boot 1.5.13 — EOL Aug 2019
2. `javax.xml.bind` (JAXB) — removed in Java 11+; migration to Java 17/21 requires Jakarta XML Bind
3. `bootRepackage` Gradle task — Spring Boot 1.x; removed in Spring Boot 2.x
4. Deprecated Gradle `compile` scope
5. `suppressions.xml` suppresses Checkstyle rules — extent of suppressed violations unknown
6. Jenkins sub-module in repo — CI/CD coupled to application lifecycle
7. `WireTransferOutPendingRequest` — "pending" state management in REST API suggests complex stateful flows
8. XJC code generation with `extraArgs = ['-Xannotate']` — generates JAXB annotated POJOs; tight coupling to schema
9. `ipAddress` field in `S2SSendMoneyBankAccountRequest` — IP address captured in wire transfer request; privacy/CCPA implications

## Gen-3 Migration Requirements
1. Spring Boot 1.5.13 → 3.x (two-major-version jump; extensive refactoring required)
2. Replace `javax.xml.bind` (JAXB) with Jakarta XML Bind or switch to JSON for EventHub payloads
3. Replace EventHub/ActiveMQ with cloud-native messaging; re-model XML events as JSON
4. Implement field-level encryption or tokenisation for `payeesBankAccountNumber` and `payeesBankRoutingNumber` in event payloads and database
5. Replace shared filesystem file exchange with NAM-bank-agent → use cloud object storage (S3/Azure Blob) or direct messaging
6. Containerise; remove RPM/Ansible
7. Extract Jenkins sub-module
8. Replace Oracle with cloud-managed DB
9. Add event idempotency keys to prevent duplicate wire transfer processing
10. Remove `ipAddress` from wire transfer request or obtain explicit privacy consent framework

## Code-Level Risks
| File | Line | Risk |
|---|---|---|
| `NewWireTransferOutEvent.java` | Lines 77-89 | Bank account number and routing number fields required in XML event — unencrypted financial data in EventHub |
| `S2SSendMoneyBankAccountRequest.java` | Line 26 | `bankAccountIdentifier` field — financial reference in API request; no observed masking in logs |
| `ImportIncomingWireTransfersReader.java` | Line 23 | `FlatFileItemReader` on JSON files — no checksum/integrity verification of input files |
| `build.gradle` (root) | Line 18-20 | HTTP Nexus URL — no TLS for artifact download |
| `wire-transfer-agent-batch/build.gradle` | Line 141 | `curl -k -u "${username}:${password}"` in `uploadRpmToAWS` — `-k` disables TLS verification; password in command line (visible in process list) |
