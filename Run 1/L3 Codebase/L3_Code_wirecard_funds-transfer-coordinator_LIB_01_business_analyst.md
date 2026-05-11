# Business Analyst — wirecard_funds-transfer-coordinator_LIB

## Business Purpose
The Funds Transfer Coordinator (FTC) is a Spring Boot microservice that orchestrates the disbursement of funds from corporate prepaid/virtual accounts to recipients via multiple payment rails. It acts as the business-rule engine sitting between event producers (CCP, card-authorisation, overdraft, client-file) and downstream payment-execution agents (check-agent, NAM-bank-agent, wire-transfer-agent).

## Capabilities
- Configures rule-based transfer triggers per account (event-driven or time-driven)
- Evaluates business logic (balance thresholds, percentage-of-balance, fixed amounts) before initiating transfers
- Initiates outbound transfers via ACH, wire, A2A, check, and money-remittance channels
- Tracks every transfer attempt in an audit log (TRANSFER_REQUEST_LOG)
- Sends past-due invoice email notifications on a schedule
- Exposes a REST API (Swagger-documented) for trigger configuration management
- Schedules recurring transfer jobs via Quartz (clustered, JDBC-backed)
- Publishes downstream events (NewDrawdownEvent, SalesOrderUpdateEvent) to EventHub/ActiveMQ

## Key Entities
| Entity | Purpose |
|---|---|
| Account | Prepaid/VCA account tracked by loading number |
| FTC_TRIGGER | Named rule linking an account to transfer logic |
| TRANSFER | Defines rail (ACH/wire/check/A2A) and amount logic for a trigger |
| LOGIC | Business-rule: source (balance/transaction), calculation type, threshold, percentage |
| EVENT_TRIGGER | Fired on incoming CCP/card/wire/overdraft events |
| TIME_TRIGGER | Fired on a recurring schedule (day/month/cron) |
| SALES_ORDER | Records corporate money-remittance order attempts |
| TRANSACTION | Event-sourced ledger of balance-changing transactions |
| CARD_AUTHORIZATION | Card auth events evaluated for sweep logic |
| OVERDRAFT | Overdraft update events for trigger evaluation |
| TRANSFER_REQUEST_LOG | Full audit trail of every outbound transfer attempt |
| CLIENT_EMAIL | Email addresses for invoice notifications per trigger |
| TARGET_ACCOUNT | Destination accounts for A2A transfers |
| CHECK_TRANSFER | Check-specific fields (express shipping, secondary payee, fee waiver) |

## Business Rules
1. A trigger fires when its associated event type/source is received or its time schedule fires
2. Logic evaluation: BALANCE, TRANSACTION_AMOUNT, or OVERDRAFT source; calculation: ALL, PERCENTAGE, AMOUNT_ABOVE_THRESHOLD
3. Transfer method: ACH, WIRE, CHECK, A2A, MONEY_REMITTANCE; type: CREDIT, DEBIT
4. 90-day code-coverage minimum enforced at build time
5. Incoming wire transfer events (FAILED status) cancel pending drawdown triggers
6. Sales orders require invoice when INVOICE_ENABLED is set on the trigger; past-due emails sent at configured cron
7. Circuit-breaker (Resilience4j) wraps check-agent calls: 40% failure threshold, 60 s open-state wait

## Business Flows
1. **Event-triggered transfer**: CCP/EventHub event received → EventConsumer → TriggerService evaluates logic → calls CCP reserve-money → calls check-agent or wire-transfer API → records TRANSFER_REQUEST_LOG
2. **Time-triggered transfer**: Quartz fires scheduled job → same service path as above
3. **Client-file ingestion**: ClientFileReceivedEvent → SalesOrderService creates SALES_ORDER with face-value discount ranges
4. **Past-due notification**: Scheduled task scans SALES_ORDER.INVOICE_DUE_DATE → sends email via SMTP → marks PAST_DUE_EMAIL_SENT

## Compliance Relevance
- Stores monetary amounts (number(19,5) precision); currency-aware
- Hibernate Envers audit tables for ACCOUNT, FTC_TRIGGER, TRANSFER — supports immutable audit trail (PCI DSS 10.x, SOC 2 CC7)
- TLS to Oracle database (javax.net.ssl.trustStore, JKS truststore loaded from Base64 config)
- OAuth2/JWT resource-server authentication (iss-resource-server) for REST endpoints
- SecurityAutoConfiguration explicitly excluded; custom OAuth2 resource server applied instead
- Sensitive fields: CLIENT_EMAIL, VIRTUAL_CLIENT_KEY, CUSTOMER_ID stored in Oracle; no PAN/SAD fields observed

## Risks
- Hardcoded QA credentials in application.yml (`password: [REDACTED — rotate immediately]`, `callcenter_QA`) — must not reach production config
- CCP client URL contains hostname (`q-horust-app02.wirecard.sys`) in source — environment-specific overrides required
- `h2-console` enabled in base application.yml — if promoted to production without environment profile override, exposes in-memory DB
- EventHub ActiveMQ password `local` / `local` in base YAML — test-only placeholder
- Spring Boot 2.0.7 / Gradle Docker image `gradle:4.8-jdk8` — end-of-life versions with known CVEs
- Check-agent URL config has a TODO comment and placeholder credentials
