# Solution Architect View — cs-api-singlewar_API

## Architecture
Multi-module Maven project producing a single WAR. Two modules:

```
cs-api-singlewar_API/
├── csapi-impl/              (Business logic — domain objects, service interfaces, implementations)
│   ├── domain/             (AccountInquiryInput/Output, Balance, CardDetail, Registration, etc.)
│   ├── service/            (AccountInquiryService, UpdateAccountService, ReissueCardService, HandleEscalationService)
│   ├── service/helper/     (RequestContextLookup, ResponseCode, SQLInjectionScrubber)
│   ├── service/validation/ (ActionValidator)
│   └── type/               (ExceptionTypes, RequestStatusType, RequestType)
│
└── csapi-ws/               (SOAP web service layer — Apache Axis + Spring)
    ├── action/             (BaseAction, SearchAccount + V3 variants)
    ├── action/helper/v3/   (SQLInjectionScrubber — duplicated!)
    ├── action/v3/          (HandleEscalation, ReissueCard, SearchAccount, UpdateAccount)
    ├── action/validation/  (ActionValidator — duplicated!)
    ├── ws/                 (AccountManagement interface, AccountManagementImpl)
    ├── ws/v3/              (AccountManagement V3 interface, AccountManagementJaxRPC)
    └── resources/          (accountManagementContext.xml, log4j.properties, i18n*.properties)
```

**Notable duplication**: `SQLInjectionScrubber` and `ActionValidator` exist in both `csapi-impl` and `csapi-ws/action/helper/v3/` — a technical debt item creating maintenance risk.

## API Surface
### V1 Endpoint
```
POST /CardManagement/services/AccountManagement
SOAP Operation: accountInquiry
Parameters: application_id, card_number, puid, balance_detail, journal_detail,
            registration_detail, start_date, end_date, max_items
Returns: AccountInquiry (balance, card, journal[], registration, response)
```

### V3 Endpoints
```
POST /CardManagementV3/services/AccountManagement
SOAP Operations:
  - accountInquiry (V3) — adds ppd, mobile_phone; returns comments[], payment_details[]
  - updateAccountProfile — AccountProfile input → response code
  - reissueCard — application_id, puid, block_code → response
  - handleEscalation — application_id, escalation data → response
```

## Security Architecture
| Control | Implementation | Assessment |
|---|---|---|
| Application authentication | `application_id` in SOAP body mapped to affiliate via configMap | Weak — shared secret, no expiry, stored in XML |
| Transport encryption | HTTPS (server-level) | Adequate if TLS 1.2+ enforced |
| Input sanitisation | SQLInjectionScrubber (quote escaping + wildcard stripping) | Present but incomplete — no XSS protection |
| Card number masking | First 8 chars masked as XXXXXXXX + last 8 digits | Weaker than PCI DSS first-6/last-4 standard |
| Access control | Affiliate metadata flags (cs_api_enabled, cs_api_v1/v3) | Per-affiliate toggle, no RBAC |
| Audit logging | INFO log with duration | Minimal — no structured security audit log |
| No rate limiting | None visible | Risk of enumeration/brute force |
| Admin Servlet | Commented out in web.xml | Good — exposure of Axis admin console would be critical |

## Technical Debt
1. **Apache Axis 1.4 + Spring 2.0.8**: The entire SOAP stack is EOL. Multiple CVEs exist. No viable upgrade path within the existing architecture — requires full stack replacement.
2. **Duplicate classes**: `SQLInjectionScrubber` and `ActionValidator` exist in both modules. Any change to the scrubbing logic must be applied in two places.
3. **Static affiliate-to-program-id map in XML**: The configMap in `accountManagementContext.xml` contains 50+ hard-coded application_id → program_id mappings. Adding a new affiliate requires a code change + deployment.
4. **`ClassPathXmlApplicationContext` per-request in V2-style**: While the singlewar version uses Spring properly via `getApplicationContext()`, the V2 pattern (`new ClassPathXmlApplicationContext(...)` on every request) persists in the V2 standalone repo and represents a severe performance issue.
5. **No unit tests**: The `csapi-ws` module has no test source directory. `csapi-impl` has no visible test classes. Zero test coverage.
6. **i18n properties files**: `i18n.properties` and `i18n_ja.properties` present — Japanese locale support was at some point required; unclear if still active.
7. **JNDI DataSource lookup**: Hard coupling to JNDI means the service cannot be tested outside a full application server without mocking JNDI.

## Gen-3 Migration Path
This repository's code has already been largely superseded:
- V1 logic → `cs-api-v1_API` (Spring Boot 3.x, Java 21, Azure App Config)
- V3 logic → `cs-api-v3_API` (Spring Boot 3.x, Java 21, REST client, Azure App Config)
- Payout → `csapiws-payout_API` and `cs-api-v3_API` payout modules

Migration steps for any remaining clients on the singlewar WAR:
1. Identify clients still calling the `/CardManagement/` (V1) or `/CardManagementV3/` (V3) context paths on this WAR
2. Redirect them to the Spring Boot equivalents
3. Decommission this WAR once zero active traffic confirmed
4. Remove from deployment pipeline

## Code-Level Risks
1. **`System.setProperty("ecount.configfile", configFile)`** in `AccountManagementImpl.initRequestContext()` — setting a JVM-global system property from a per-request method is thread-unsafe. Under concurrent requests, one thread can overwrite the config file path seen by another.
2. **`singleton="false"` for action beans**: Correct use of prototype scope for stateful action objects, but the parent class `AccountManagementImpl.beanFactory` is declared `static` — a shared static reference updated on first call per JVM instance. This is a concurrency risk if the Spring context is reloaded.
3. **`ecard.getCreditCard().getLastEmbossDate()` without null check** in V1-style code paths could throw NPE if the date is not set.
4. **No timeout on C-Base RPC calls**: If the ecount xPlatform is slow or unavailable, requests will block indefinitely until the Tomcat thread pool is exhausted.
