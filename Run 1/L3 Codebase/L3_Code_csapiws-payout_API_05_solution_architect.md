# Solution Architect View — csapiws-payout_API

## Architecture
Single-module Maven WAR project. All business logic is split across action classes that are Spring-managed beans (prototype scope). The SOAP layer uses Apache Axis 1.4 with a JAX-RPC handler (`AccountManagementJaxRPC`). The Spring context is loaded from multiple XML files at servlet startup. Most operations declared in the original interface are commented out (JIRA 476), leaving only `payoutAccountInquiry` active.

```
csapiws-payout_API/
├── src/main/java/com/ecount/one/cs/
│   ├── AccountManagement.java             (SOAP interface — payoutAccountInquiry only; others commented out)
│   ├── AccountManagementJaxRPC.java       (Axis JAX-RPC handler; delegates to Spring beans)
│   ├── PayoutAccountInquiry.java          (response: extends AccountInquiry + PayoutApp + PayoutAppRegistration)
│   ├── PayoutApp.java                     (payout portal content metadata: URLs, ATM type, CS phone)
│   ├── PayoutAppRegistration.java         (cardholder registration as seen by payout portal)
│   ├── UpdateRegistrationDetails.java     (update registration input including ddaNumber)
│   ├── AccountInquiry.java, Balance.java, CardDetail.java, ...  (shared CS API value types)
│   ├── action/
│   │   ├── PayoutSearchAccount.java       (payout inquiry action — xPlatform RPC path)
│   │   ├── UpdateRegistrationAction.java  (registration update with US/CA/MX validation + audit)
│   │   ├── BaseAction.java                (request context init, request ID tracking)
│   │   ├── SearchAccount.java             (commented out per JIRA 476 — wired but not exposed)
│   │   ├── UpdateAccount.java             (commented out per JIRA 476)
│   │   ├── ReissueCard.java               (commented out per JIRA 476)
│   │   ├── HandleEscalation.java          (commented out per JIRA 476)
│   │   ├── dao/CoreDeviceDDAInquiry.java  (SQL DAO for DDA device lookup on EcountCoreDataSource)
│   │   ├── helper/SQLInjectionScrubber.java
│   │   ├── validation/ActionValidator.java
│   │   └── content/
│   │       ├── ContentManagementServiceClient.java  (CMS HTTP client for payout app URLs)
│   │       ├── ContentHelper.java
│   │       ├── ContentURLBuilder.java
│   │       └── DocumentParser.java
│   └── exception/CSAPIException.java
├── src/main/resources/
│   └── accountManagementContext.xml       (Spring beans; external properties from filesystem)
└── src/main/webapp/WEB-INF/
    └── web.xml                            (Axis servlet; 5 Spring context XML files loaded)
```

## API Surface
```
Context path: /CardManagementPayoutV3
WSDL: /CardManagementPayoutV3/services/AccountManagement?wsdl
Endpoint: POST /CardManagementPayoutV3/services/AccountManagement

Active Operations:
1. payoutAccountInquiry
   Input:  application_id, card_number, puid, ppd, mobilePhone, ddaNumber,
           balance_detail, journal_detail, registration_detail,
           start_date, end_date, max_items
   Output: PayoutAccountInquiry (AccountInquiry + PayoutApp + PayoutAppRegistration)
   Errors: 34001 (invalid payout app_id), similar error code range to V3

Commented-Out (JIRA 476 — code present, not exposed):
- accountInquiry
- updateAccountProfile
- reissueCard
```

Note: `updateRegistrationAction` is wired as a Spring bean and the class is present but is not in the `AccountManagement` interface. It may be invoked via an alternate path or was prepared for interface reactivation.

## Security Architecture
| Control | Implementation | Assessment |
|---|---|---|
| Application authentication | AffiliateService lookup (`cs_api_payout_app_id`) | Dynamic — revocable without redeploy |
| Authorisation | No `cs_api_enabled` / `cs_api_payout` flag check in PayoutSearchAccount | Weaker than V3 — only attribute presence checked |
| Transport | HTTPS at server/load balancer level | Adequate if TLS 1.2+ at reverse proxy |
| Card masking | Applied in PayoutSearchAccount | Consistent with V3 inquiry masking |
| DDA numbers | Passed in plaintext SOAP — no JWE | Gap vs. V3 payout sub-service which uses JWE encryption |
| SQL injection | SQLInjectionScrubber for search inputs | Present |
| Input validation | ActionValidator (length, format, charset) | Present |
| Audit trail | UpdateRegistrationAction writes comment (csUserId = "cs-api-Payout") | Present for registration updates |
| Rate limiting | None | Enumeration risk |
| Admin/Monitor servlets | Commented out in web.xml | AdminServlet and SOAPMonitorService properly disabled |

## Critical Findings

### DDA Numbers Transmitted Without Encryption
`payoutAccountInquiry` accepts a `ddaNumber` parameter. In this standalone service, DDA numbers are passed as plaintext strings through the SOAP request with no JWE or other message-level encryption. The V3 payout sub-service (`cs-api-v3_API/csapi-v3-payout-ws`) encrypts DDA numbers using JWE. Any clients that need to migrate from this service to V3 must add JWE encryption for DDA parameters.

### No `cs_api_enabled` Flag Check
`PayoutSearchAccount.execute()` calls `affiliateContextService.getAffiliateForValue("cs_api_payout_app_id", ...)` and returns error 34001 if no mapping is found. It does not then check a `cs_api_payout_enabled` or `cs_api_enabled` flag. Access control is binary — either the `cs_api_payout_app_id` mapping exists or it does not. There is no per-operation or per-affiliate feature flag to disable specific capabilities.

### JIRA 476 Commented Code
Four complete operation classes (SearchAccount, UpdateAccount, ReissueCard, HandleEscalation) are present in source and registered as bean definitions in comments in `accountManagementContext.xml`. If anyone uncomments either the interface methods or the XML beans (independently of each other), partially tested code paths could be re-exposed. The commented code should be either formally deleted or the operations should be formally reactivated with updated tests.

### Prototype Scope on Action Beans
All action beans use `scope="prototype"`. While this prevents the instance-field thread safety issue seen in V1 (`AccountManagementImpl`), it means a new bean graph (including all injected dependencies) is created on every request. Under load, this creates excessive object creation pressure. The correct pattern for stateless action classes is singleton scope with method-local state only.

## Technical Debt Inventory
1. **Spring 2.5.4 + Axis 1.4 + Java 8**: All EOL. Multiple CVEs across all three.
2. **xAffiliateService 1.0.8**: Three major versions behind the V3 equivalent (4.0.1). Internal API changes between versions may present compatibility issues during migration.
3. **comment 1.0.3**: Two major versions behind V3 (3.0.1). Comment schema or API differences may exist.
4. **jTDS 1.2**: Old SQL Server JDBC driver — TLS 1.2 database connection encryption at risk.
5. **SNAPSHOT version in CI**: `2.0.2-SNAPSHOT` — production deployments should use release versions.
6. **Prototype scope for stateless beans**: All action beans declared prototype — unnecessary GC pressure.
7. **Hardcoded displayMerchantName list**: 8 program IDs directly in XML; should be in external configuration or managed via affiliate flag.
8. **Dead commented code**: 4 operation classes present but commented — creates confusion about active scope.
9. **Wirecard Nexus server in distributionManagement**: `d-na-stk01.nam.wirecard.sys` — inaccessible from current infrastructure.
10. **Log4j path disclosure**: `log4j.configLocation` exposes `D:/C-Base/config/CSWS/log4j-Payout.xml` internal path.
11. **No test execution in CI**: All Maven phases have `maven.test.skip=true`.

## Modernisation Assessment
This service should be superseded by the V3 payout sub-service embedded in `cs-api-v3_API`. The primary migration blockers are:
1. DDA encryption: clients must add JWE support
2. Mexico address validation: V3 updateAccount does not have MXStatesSet; must be added before migration
3. `cs_api_payout_app_id` attribute continuity in AffiliateService
4. Comment service API compatibility between version 1.0.3 and 3.0.1

Priority: Medium-High — Java 8/Spring 2.5.x/Axis 1.4 have multiple CVEs; Windows Tomcat deployment is not cloud-native; no container build; no test coverage in CI.
