# Business Analyst View — qa-test-automation

## Business Purpose

`qa-test-automation` is an internal QA framework that provides integration test coverage for the Gen-1 eCount/Citi platform's XML-RPC service layer. It tests the backend microservices that power Onbe's prepaid card programs: cryptography, order management, repository, strong box (secrets), directory (routing), notification, and user management services. The business goal is to provide automated regression confidence when changes are made to eCount platform services, reducing the risk of broken service contracts reaching production cardholders.

## Capabilities

The framework is built on Spock (Groovy) with Spring integration, executing against live QA environment services via XML-RPC. Test specifications cover:

- **CryptoSvcSpec**: PGP public key lifecycle management — list, add, and remove cryptographic keys used to encrypt sensitive cardholder data files.
- **DirectorSvcSpec**: Routing/dispatch service connectivity and invocation.
- **ECountCoreSvcSpec**: Core eCount account management operations.
- **FileOrderManagerSvcSpec**: File-based order submission and tracking.
- **NotificationSvcSpec**: Notification event dispatch (email/SMS triggers for cardholders).
- **RepositorySvcSpec**: Shared repository service reads and writes (program/member data).
- **StrongBoxSvcSpec**: Secrets/key vault service — retrieval and management of platform encryption keys.
- **UserManagementSvcSpec**: Platform user account operations.
- **OrderManagerSvcSpec, OrderServiceSpec, OrderSynchronizerSvcSpec**: Full prepaid card order lifecycle — sweep orders, instant-issue requests, fund reservation, and synchronization.

## Client and Cardholder Impact

Failures in the tested services directly impact client programs and cardholders. For example:
- Failure in `OrderService.processInstantIssue` prevents instant-issue card transactions.
- Failure in `CryptoService` breaks PGP file encryption used to protect cardholder data in batch disbursements.
- Failure in `NotificationService` prevents cardholder SMS/email notifications (Reg E disclosure obligations).
- Failure in `RepositoryService` can corrupt program or member state.

## Business Rules in Code

Business rules are tested but not defined here. The test specifications assert connectivity and correctness of service contracts. Key rules exercised:
- Sweep order lifecycle requires a `programId`, `promotionId`, and `memberId` — all must be valid UUIDs/identifiers for operations to succeed.
- Instant issue requests require explicit fund actions (e.g., `AddFundsAction` with a USD amount and a claimable flag).
- Notification threshold checking requires both a program identifier and a secondary program identifier.
- Cryptographic key operations require a valid `programId` and a reachable PGP key path (UNC path: `\\q-na-app05\pgpkeys\...`).

## Regulatory Obligations

- **PCI DSS**: The StrongBox service being tested manages platform encryption keys. Test coverage of key retrieval and management is a control-effectiveness validation supporting PCI DSS Req 3.5 (protect cryptographic keys).
- **NACHA / Reg E**: Order processing and notification services support ACH-adjacent workflows and consumer notification requirements. Test coverage ensures these channels remain functional.
- **GLBA**: The RepositoryService tests cover access to program and member data stores — ensuring availability and correctness of data handling supporting GLBA data integrity obligations.

## Key Business Risks

1. **Tests point to live QA environment**: The `Environments.groovy` file contains hardcoded QA URLs (`http://ppnaut.nam.wirecard.sys:8080`) and actual programIds, memberIds, and ecountIds. These are real test system identifiers. If these values are stale (e.g., QA accounts deactivated), tests will silently fail without indicating a code defect.
2. **SNAPSHOT dependency instability**: The pom.xml uses `-SNAPSHOT` versions for all eCount platform dependencies (`repository-common:3.0.0-SNAPSHOT`, `strong-box-common:4.0.0-SNAPSHOT`, etc.), meaning the compiled test artifact is non-deterministic.
3. **No negative-path coverage**: All Spock specifications test the positive path (service responds successfully) with minimal error-scenario coverage, which may miss regression in error-handling code paths.
4. **Single QA environment**: Tests are hardcoded to the `qa` environment label; there is no multi-environment configuration for stage or production smoke tests.
