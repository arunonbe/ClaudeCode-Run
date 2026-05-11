# Business Analyst View — order_SVC

## Business Purpose

order_SVC is the core order management service in Onbe's Gen-1/Gen-2 prepaid platform (eCount/Citi lineage, `com.citi.prepaid.service.order`). It manages the full lifecycle of prepaid card orders — from creation through fulfillment, cancellation, stop-payment, and sweep — for enterprise B2C disbursement programs. It is a foundational platform component that sits between client load/request initiation and the card issuance/banking back-end.

## Capabilities Provided

- **Order creation and routing**: instantiates orders for plastic cards, virtual cards, instant-issue, and file-based batch orders
- **Instant issue processing**: real-time card issuance pathway (`InstantIssueProcessor`, `InstantIssueActivityHandler`)
- **File order management**: batch file-based order intake and posting (`FileOrderManager`, `PostFileOrderActivityHandler`, `PostCompletedFileOrderActivityHandler`)
- **Sweep management**: fund sweep orders to recover or redistribute balances (`CreateSweepOrdersActivityHandler`, `CloseSweepOrdersActivityHandler`, `FreeSweepOrderFundsActivityHandler`)
- **Stop payment**: order stop-payment integration (`OrderStopPaymentIntegrationTestCase`)
- **Order status management**: force-status, correction, close, and cancel operations
- **Invoice handling**: post-invoice order activity
- **Notification threshold checking**: monitors load thresholds for notification triggers
- **XML-RPC interface**: exposes order operations via XML-RPC for integration with legacy eCount core (`order-xmlrpc` module)
- **REST interface**: modern REST controller (`order-rest-controller` module) for integration with Gen-2/Gen-3 consumers
- **Job integration**: integrates with the job scheduler for batch order processing

## Client/Cardholder Impact

order_SVC is the transaction system of record for order state transitions. Failures here directly cause: delayed card issuance (client SLA impact), failure to sweep or cancel orders (financial exposure to Onbe), and stop-payment failures (regulatory/NACHA liability). The instant-issue pathway is latency-sensitive — slow or failed responses block real-time disbursement (healthcare, insurance claim payouts).

## Business Rules Found in Code

- Orders are routed by activity type and order type via configurable routing handlers (`OrderActivityTypeRoutingOrderActivityHandler`, `OrderTypeRoutingOrderActivityHandler`) — program-specific behavior is configurable without code changes
- Sweep orders have a two-phase lifecycle: create and close; free-funds is a separate step ensuring funds are released before close
- Instant issue has a status sub-step (`InstantIssueStatusActivityHandler`) separate from the issue action, indicating a polling or callback pattern for card network confirmation
- Secure profile memo is captured on certain order actions (`SecureProfileActionSecureMemo`) — this is a PCI-relevant field; memo content must not contain SAD
- File orders require both a "post" step and a "post completed" step — partial completion must not leave orders in an indeterminate state
- The enforcer plugin in `pom.xml` blocks SNAPSHOT dependencies in production builds (excepting same-groupId artifacts), enforcing release-only external dependencies

## Regulatory Obligations

- **NACHA**: File-based ACH orders must meet NACHA format, timing, and return-code handling requirements. Batch file order management in this service feeds ACH disbursement.
- **Reg E**: Stop-payment processing must be traceable and timely; stop-payment failures must be logged with sufficient audit trail.
- **PCI DSS**: The `SecureProfile` memo captured in order activity must not contain full PAN, CVV, or track data. Order records in the database must comply with PCI DSS storage requirements (Requirement 3).
- **OFAC**: Orders should integrate with OFAC screening before fund release; integration point is likely upstream (banker or request service) but order_SVC must propagate screening results.
- **GLBA**: Order records constitute financial records subject to GLBA safeguard requirements.

## Key Business Risks Found in Code

- **SNAPSHOT version in root POM**: `order` artifact is `4.1.13-SNAPSHOT` — this SNAPSHOT version should not be deployed to production environments. The enforcer rule blocks external SNAPSHOT dependencies but not the artifact itself.
- **IBM MQ dependency**: `com.ibm.mq.jakarta.client` 9.4.0.0 is included, indicating async messaging for order events. MQ connectivity failure would cause silent order loss if retry/dead-letter queue handling is not robust.
- **Dual interface exposure (XML-RPC + REST)**: The service exposes both a legacy XML-RPC surface and a REST surface. Maintaining both increases the attack surface and the risk of inconsistent behavior between interfaces.
- **Instant issue load test artifact**: `InstantIssueLoadTester` class exists in the service (visible in Javadoc), suggesting performance test tooling is co-located with production code — this should be excluded from production builds.
- **No GitLab CI observed**: The repo contains both `.gitlab-ci.yml` and GitHub Actions workflows, suggesting a CI migration is in progress. Duplicate CI pipelines can cause version drift if not synchronized.
