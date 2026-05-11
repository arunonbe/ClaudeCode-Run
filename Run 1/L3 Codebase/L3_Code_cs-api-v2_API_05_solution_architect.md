# Solution Architect View — cs-api-v2_API

## Architecture
Single-module Maven project producing a WAR artifact. All code is in `src/main/java` with no modular separation between the web service layer and business logic.

```
cs-api-v2_API/
├── src/main/java/com/ecount/one/cs/
│   ├── AccountManagement.java         (SOAP interface — accountInquiry + updateAccountProfile)
│   ├── AccountManagementImpl.java     (860-line monolith — ALL business logic)
│   ├── AccountInquiry.java            (response aggregate)
│   ├── Balance.java
│   ├── CardDetail.java
│   ├── Registration.java
│   ├── RequestContextLookup.java
│   ├── Response.java
│   ├── TransactionDetail.java
│   ├── ZipValidation.java             (postal code validation patterns)
│   └── ws/                            (Axis-generated stubs)
│       ├── AccountManagement.java
│       ├── AccountManagementService.java
│       ├── AccountManagementServiceLocator.java
│       ├── AccountManagementSoapBindingImpl.java
│       ├── AccountManagementSoapBindingStub.java
│       ├── AccountProfile.java        (V2 addition — update request type)
│       ├── Balance.java
│       ├── CardDetail.java
│       ├── Registration.java
│       ├── Response.java
│       ├── ResultCode.java
│       └── TransactionDetail.java
├── src/main/java/com/ecount/one/       (Context listener, WSContext value object)
├── src/main/resources/
│   ├── accountManagementContext.xml   (Spring beans + static configMap)
│   ├── applicationContext-xCSAPI.properties (external, not committed)
│   ├── i18n.properties, i18n_ja.properties
│   └── jetty-env.xml
└── src/main/webapp/
    ├── WEB-INF/web.xml
    ├── WEB-INF/jboss-web.xml
    ├── META-INF/context.xml
    └── SOAPMonitorApplet.java         (Embedded Axis monitoring applet source)
```

## API Surface
```
WSDL: /CardManagementV2/services/AccountManagement?wsdl
Endpoint: POST /CardManagementV2/services/AccountManagement

Operations:
1. accountInquiry
   Input:  application_id, card_number, puid, balance_detail, journal_detail,
           registration_detail, start_date, end_date, max_items
   Output: AccountInquiry (same structure as V1)
   Errors: 34001 (invalid app_id), 34002 (missing identifier), 34003+ (various)

2. updateAccountProfile
   Input:  AccountProfile (puid, program_id, address, name, phones, email)
   Output: ResultCode (code String, description String)
   Error codes: "1" through "7" — string-typed, not integer
```

## Security Architecture
| Control | Implementation | Assessment |
|---|---|---|
| Application authentication | Static configMap lookup in XML | Critical weakness — no expiry, no revocation without redeploy |
| Authorisation | None beyond configMap presence | No affiliate flags, no per-operation control |
| Transport | HTTPS (server-level assumed) | Adequate if TLS 1.2+ |
| Card masking | XXXXXXXX + last 8 | Borderline PCI compliant |
| Input validation | `prepareInputData` + `validateRequest` | Present but incomplete — state validation is 2-alpha only |
| SQL injection | No explicit scrubber in V2 — application IDs resolved via configMap; EMember/EDevice calls use platform library | Partial — depends on platform library |
| No rate limiting | None | Enumeration risk |
| `SOAPMonitorApplet.java` | Axis monitoring applet present in webapp | Remove — exposes monitoring endpoint risk |

## Critical Code Defects

### NPE Bug in `generateErrorCode`
```java
public static ResultCode generateErrorCode(ReturnStatus result) {
    log.info("Generating Error Code...");
    ResultCode rc = null;   // rc is null!
    rc.setCode("7");        // NullPointerException — GUARANTEED
    ...
}
```
This method will always throw a `NullPointerException` when called. It is invoked when `updateRegistrationInfo` returns a non-zero error code. This means any profile update that fails at the C-Base registration layer will return an unhandled exception to the SOAP caller rather than a proper error response.

### Per-Request Spring Context Creation
```java
public static RequestContextLookup getProperties() {
    ClassPathXmlApplicationContext appContext = new ClassPathXmlApplicationContext(
        new String[] { "accountManagementContext.xml" });
    BeanFactory beanFactory = (BeanFactory) appContext;
    return (RequestContextLookup) beanFactory.getBean("requestContextLookup");
}
```
A new Spring `ApplicationContext` is created on every call to `getProperties()`. This is called multiple times per request (in `accountInquiry`, in `updateAccountProfile`, in `translateProgramId`, in `performUpdate`). The cost is:
- Full XML parsing and bean instantiation on every call
- JNDI lookup on every call
- No context caching or sharing
This is a severe architectural defect, not just inefficiency.

## Technical Debt Inventory
1. **860-line monolith**: `AccountManagementImpl` contains SOAP handler, input validation, business logic, platform integration, output assembly, and utility methods in one class
2. **Duplicate domain classes**: `com.ecount.one.cs` and `com.ecount.one.cs.ws` packages contain near-identical `Balance`, `CardDetail`, `Registration`, `Response`, `TransactionDetail` classes
3. **Axis-generated stubs in source**: `AccountManagementSoapBindingStub.java` — auto-generated; must be regenerated if WSDL changes
4. **Java 1.5 syntax**: Uses `new Integer(...)` (deprecated), no generics in several collections, no type-safe iteration
5. **Static method proliferation**: 15+ static utility methods on the main implementation class — untestable without refactoring
6. **Developer SQL credentials in XML comments**: Must be removed
7. **`SOAPMonitorApplet.java`**: An Axis monitoring applet sitting in the webapp directory — this exposes a monitoring interface; should be removed from production

## Gen-3 Migration Path
V2 has no equivalent Spring Boot module. The migration path is:
1. Identify any clients still calling the V2 endpoints (`/CardManagementV2`)
2. Map their `application_id` values to `cs_api_v3_app_id` entries in the CbaseApp AffiliateService
3. Migrate clients to V3 endpoints which provide a superset of V2 capabilities
4. Verify `updateAccountProfile` → V3 `updateAccount` parity (note: V3 uses int error codes vs. V2 string codes)
5. Decommission the V2 WAR
6. Archive this repository as read-only

Priority: High — Java 5, Spring 2.5, Axis 1.4 all have multiple CVEs and no vendor support.
