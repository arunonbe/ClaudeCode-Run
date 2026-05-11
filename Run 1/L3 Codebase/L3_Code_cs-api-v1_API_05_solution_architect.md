# Solution Architect View — cs-api-v1_API

## Architecture
Three-module Maven project. The web service logic lives in `card-management-ws`; two packaging modules provide legacy WAR and modern Spring Boot deployment options.

```
cs-api-v1_API/
├── card-management-ws/        (Core SOAP service — Spring + Axis)
│   ├── AccountManagement.java (interface: accountInquiry)
│   ├── AccountManagementImpl.java (business logic, ~420 lines)
│   ├── AccountManagementSoapBindingImpl/Stub/Skeleton (Axis-generated stubs)
│   ├── ApplicationContextProvider.java (static Spring context holder)
│   ├── RequestContextLookup.java (HashMap wrapper for config)
│   ├── ws/ (AccountManagement WS interface + service stubs)
│   ├── domain objects (AccountInquiry, Balance, CardDetail, etc.)
│   ├── helper/ProgramIdAwareGlobalRequestIDGenerator.java
│   └── resources/ (accountManagementContext.xml, i18n.properties)
│
├── card-management-war/       (Legacy WAR wrapper)
│   ├── HealthCheck.java
│   ├── context.xml (JNDI DataSource definitions)
│   ├── cardmanagementapi-servlet.xml (Spring MVC servlet config)
│   └── web.xml
│
└── card-management-boot/      (Spring Boot packaging)
    ├── CardManagementBootApplication.java (@SpringBootApplication)
    ├── config/
    │   ├── AccountManagementConfig.java (@Configuration — beans)
    │   ├── CardManagementWebConfig.java (servlet/MIME config)
    │   ├── ECountSystemConfiguration.java (conditional ecount init)
    │   ├── WebConfiguration.java
    │   └── properties/ECountConfigProperties.java (@ConfigurationProperties)
    ├── datasources/
    │   ├── cbase/config/CbaseAppDataSourceAutoConfiguration.java
    │   ├── ecount/config/ECountCoreDataSourceAutoConfiguration.java
    │   └── jobsvc/config/JobSvcDataSourceAutoConfiguration.java
    ├── health/HealthCheck.java
    └── resources/
        ├── application.yml
        ├── bootstrap.yaml (Azure App Config)
        └── config/ (applicationContext-V1.yml, director-client.yml, ecount-config.yml)
```

## API Surface
```
WSDL: /CardManagement/services/AccountManagement?wsdl
SOAP Endpoint: POST /CardManagement/services/AccountManagement

Operation: accountInquiry
Input:  application_id (String), card_number (String), puid (String),
        balance_detail (int), journal_detail (int), registration_detail (int),
        start_date (int YYYYMMDD), end_date (int YYYYMMDD), max_items (int)
Output: AccountInquiry { Balance, CardDetail, TransactionDetail[], Registration, Response }

Response codes:
  33030 — Application ID invalid
  33031 — Missing Account Identifier
  33032 — Invalid Partner User ID
  33033 — Invalid Card
  33034 — System Unavailable (catch-all exception)
  33035 — Not allowed to access this service
  0     — Success (completion_message = "OK")
```

## Security Architecture
| Control | Implementation | Status |
|---|---|---|
| Transport | HTTPS via server/APIM | Adequate |
| API Authentication | `application_id` → affiliate lookup via DB | Shared secret; no expiry mechanism |
| Authorisation | `cs_api_enabled` + `cs_api_v1` affiliate flags | Per-affiliate on/off toggle |
| Card masking | XXXXXXXX + last 8 in response | Weaker than V3; borderline PCI compliant |
| Log sanitisation | Card number logged as sanitised string (replaceAll `[^\\w]+`) | Good practice; present |
| MDC correlation | ProgramIdAwareGlobalRequestIDGenerator + Log4jMDCWriter | Good observability |
| Azure Auth | Managed Identity (non-local) / connection string (local) | Best practice |

## Technical Debt
1. **Instance-level fields in `AccountManagementImpl`**: `output`, `balance`, `card`, `journal`, `reg`, `response` are declared as instance fields then initialised in `initializeInputs()`. If the bean were ever singleton-scoped, this would be a critical thread-safety bug. The Spring Boot config must ensure prototype or request scope.
2. **`ApplicationContextProvider` static singleton**: `ApplicationContextProvider.getApplicationContext()` returns a statically held `ApplicationContext`. This pattern prevents proper unit testing and is incompatible with Spring Boot's `ApplicationContext` lifecycle management.
3. **Axis-generated stubs** (`AccountManagementSoapBindingStub`, `AccountManagementSoapBindingSkeleton`, `AccountManagementServiceLocator`): These are legacy Axis 1.x generated artefacts. They are included in the source tree and compiled, which means they must be maintained in sync with the WSDL manually.
4. **`jakarta.servlet.http.HttpUtils.java`**: A custom implementation of the deprecated `HttpUtils` class (removed from Jakarta EE) included in the source tree to maintain Axis 1.x compatibility. This is a sign of the deep technical debt in the Axis dependency.
5. **`ClassPathXmlApplicationContext` still referenced**: `accountManagementContext.xml` in `card-management-ws/src/main/resources` is an Axis/Spring-XML based context — this coexists with the Spring Boot `@Configuration` classes and could cause bean definition conflicts (mitigated by `allow-bean-definition-overriding: true`).
6. **Circular references**: `allow-circular-references: true` in application.yml — the circular dependency should be resolved rather than suppressed.

## Gen-3 Migration Path
1. **Replace SOAP with REST**: Expose `accountInquiry` as `GET /api/v1/account` with query parameters.
2. **Replace xPlatform with ecount-core-rest-api**: As done in cs-api-v3_API `SearchAccount.java` — `DeviceService.inquiryEcard()` replaces `EDevice.processInquiry()`.
3. **Remove static ApplicationContextProvider**: Use Spring Boot dependency injection throughout.
4. **Stateless bean design**: Refactor `AccountManagementImpl` to return values rather than accumulating state in instance fields.
5. **Remove Axis stubs and generated code**: Replace with JAX-WS or Spring-WS if SOAP must be maintained; otherwise remove entirely.
6. **Consolidate card masking**: Adopt V3 standard of first-4 + XXXXXXXX + last-4.

## Code-Level Risks
1. **`static ApplicationContext beanFactory`** in `AccountManagementImpl` — updated on each call via `getProperties()`. Not thread-safe under concurrent initialization.
2. **`programIdAwareGlobalRequestIDGenerator.clearGlobalRequestID()` in finally block** — correct pattern; prevents MDC leakage between requests.
3. **`Math.subtractExact(month, 1)`** in `add1DayToEndDate()` — will throw `ArithmeticException` on overflow (impossible for month values 1-12, but an unusual choice over the standard `month - 1`).
4. **No timeout on C-Base xPlatform calls** within the Java layer — relies entirely on `connectTimeout: 120000` / `readTimeout: 120000` configured in `ecount-config.yml`. If the config is not loaded, calls could block indefinitely.
