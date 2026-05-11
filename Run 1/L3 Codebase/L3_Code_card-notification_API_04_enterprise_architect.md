# card-notification_API — Enterprise Architect View

## Platform Generation (Gen-1/Gen-2/Gen-3)

**Classification: Gen-1**

Evidence:
- Spring Framework 2.5.4 (released 2008) — the earliest Spring release to support annotation-based AOP
- Apache Axis 1.4 (built Apr 22, 2006) — pre-JAX-WS, pre-CXF SOAP stack
- JUnit 3.8.1 test framework (circa 2002–2004)
- `AbstractDependencyInjectionSpringContextTests` base class (deprecated since Spring 3.0, removed in Spring 4.0)
- Servlet API 2.4 (2003-era)
- EHCache 1.3.0 (circa 2007)
- WAR packaging with XML-heavy Spring configuration (no annotations on business beans, no Spring Boot)
- `web.xml` DTD references `web-app_2_3.dtd` (Servlet 2.3, year 2001)
- SCM history references `wirecard-cloud.com` (pre-Northlane, pre-Onbe era)
- Artifact parent group `com.ecount` using the "ecount" brand name — the original platform identity before Northlane/Onbe rebranding

This service was built against the original eCount platform (pre-Wirecard acquisition) and has not been modernized since initial development. The package namespace `com.ecount.services.cardnotification` and all platform library imports (`com.cbase.*`, `com.ecount.*`) are Gen-1 platform identifiers.

## Business Domain

**Domain**: Prepaid Card — Cardholder Self-Service / SMS Channel

This service belongs to the cardholder-facing notification and self-service domain. It is the back-end inquiry engine for the SMS Pull channel, one of multiple cardholder communication channels (alongside web portal, IVR, mobile app). It is scoped exclusively to the **pull inquiry** pattern — cardholders initiate requests; there is no outbound push notification capability in this service.

**Client segment**: Prepaid card programs with SMS Pull enabled (`SMSPULLENABLEDPROGRAMS = Y`). Historical evidence from `messages.properties` and test code suggests original deployment was for Citi Prepaid programs.

## Role in Platform

`card-notification_API` is a **thin inquiry aggregator** sitting at the intersection of three platform subsystems:

```
SMS Gateway (SAP or carrier aggregator)
        |
        | SOAP/HTTP
        v
[card-notification_API]  <-- this service
   |           |
   |           v
   |    xSearch-xmlrpc     (member lookup by mobile number)
   |
   v
eCount Core (EDevice, EMember)  (account balance, journal, definition)
   |
   v
SQL Server CbaseApp DB          (affiliate config, SMS message templates, audit log)
```

It does not own any business data — it is a **read-through service** (with one write: the audit log insert). All authoritative data resides upstream in eCount core and the CbaseApp database.

## Dependencies

### Upstream (this service depends on)
| System | Interface | Purpose |
|---|---|---|
| eCount Core / cbase | Java library (`com.cbase.*`, `xPlatform:3.0.4`) | Account balance, journal, definition inquiry via EDevice |
| xSearch-xmlrpc | XML-RPC over HTTP (via `xSearch-client:2013.2.1-SNAPSHOT`) | Member lookup by mobile phone number |
| Director Service | HTTP (internal service registry) | Datasource resolution and xSearch endpoint routing |
| xAffiliateService (`1.0.9`) | Java library + SQL stored procs | Program configuration (SMS enabled flag, affiliate metadata) |
| SQL Server CbaseApp | JDBC via Director-provisioned DBCP | app_sms_msg_profile, affiliate tables, log insert |
| AppSmsMsgProfileClass | Part of xPlatform / cbase | SMS message template retrieval |

### Downstream (depends on this service)
| System | Notes |
|---|---|
| SMS Gateway (SAP or carrier aggregator) | Primary caller; sends cardholder text messages and receives formatted SMS responses |
| Any SOAP client | The WSDL (`CardNotificationService.wsdl`) is publicly discoverable on the deployed endpoint |

### Internal Platform Libraries (no public Maven repository)
- `com.ecount:xPlatform:3.0.4`
- `com.ecount.one.service.affiliate:xAffiliateService:1.0.9`
- `com.ecount.service.xSearch-New:xSearch-client:2013.2.1-SNAPSHOT`

All three must resolve from the internal Nexus at `d-na-stk01.nam.wirecard.sys:8080`.

## Integration Patterns

| Pattern | Implementation | Notes |
|---|---|---|
| Synchronous SOAP/RPC | Apache Axis 1.4, JAX-RPC binding style | Request-response; SMS gateway must wait for response |
| In-process caching | EHCache 1.3.0 with disk overflow | Cache-aside pattern for member data (7-day idle TTL) and message profiles (14-day live TTL) |
| AOP audit logging | Spring AOP `@AfterReturning` via AspectJ annotations | Decoupled audit trail; fires after response is assembled |
| Service Locator (anti-pattern) | `CardNotificationUtils.getSpringContext().getBean("affiliateContextService")` | Hard-coded bean lookup in `CardNotificationServiceImpl.java` line 270 and `CardNotificationMessageHelp.java` line 32 — bypasses DI |
| Factory Method | `CardNotificationMessageFactory` | Static `ConcurrentHashMap` factory for message processor selection by action type |
| Strategy Pattern | `CardNotificationMessage` interface with four implementations (Balance, Payment, Transaction, Help) | Clean extensibility for new action types |
| Template Method | `AbstractCardNotificationMessage` → `CardNotificationMessagePayment`, `CardNotificationMessageTransaction` | Shared journal sort/filter logic |
| Stored Procedure DAO | `CardNotificationLogInsertDAO extends StoredProcedure` | Spring JDBC `StoredProcedure` pattern for `dbo.sms_cardnotification_log_insert` |

## Strategic Status

**Status: Legacy / Sunset Candidate**

Indicators:
- No active development evidence — version is `2.0.0-SNAPSHOT` with no recent commits visible
- All CI test phases skip tests — suggests the test suite may no longer pass
- Depends on a SNAPSHOT library (`xSearch-client:2013.2.1-SNAPSHOT`) dated 2013
- Technology stack (Axis 1.4, Spring 2.5, log4j 1.x, Servlet 2.3) is 15–20 years behind current standards
- Original brand references (`ecount.com`, `wirecard-cloud.com`, `Citi Prepaid`) indicate the service predates the Northlane/Onbe rebranding and has not been updated to reflect the current business identity
- Hard-coded TODO comments (e.g., affiliate app ID = 6 in `CardNotificationMessageHelp.java` line 34) indicate deferred work that was never completed
- No Dockerfile, no Kubernetes manifests, no cloud deployment configuration — entirely on-premises Windows Tomcat

## Migration Blockers

The following items must be addressed before migrating to a Gen-3 platform:

1. **Apache Axis 1.4 / SOAP RPC-encoded style**: The WSDL uses `use="encoded"` (deprecated in WS-I Basic Profile). Gen-3 would use REST/JSON or document-literal SOAP. The SMS gateway caller must be updated to change the protocol contract.

2. **Spring 2.5.4**: Over 15 years of Spring evolution must be absorbed. The XML-only Spring configuration, `AbstractDependencyInjectionSpringContextTests`, and `spring-mock:2.0.4` are all removed in modern Spring. Full configuration rewrite required.

3. **xPlatform / cbase library coupling**: All business logic is tightly coupled to `com.cbase.*` and `com.ecount.*` platform objects (`EDevice`, `EMember`, `AccountJournal`, `MemberInquiryValue`, `AppSmsMsgProfile`). A Gen-3 migration requires either porting or wrapping these libraries, or replacing them with Gen-3 domain services.

4. **xSearch-client SNAPSHOT dependency**: The `xSearch-client:2013.2.1-SNAPSHOT` must be stabilized, replaced, or the member lookup must be re-implemented against a current member search service.

5. **Director-based datasource provisioning**: `DirectorConfiguredDBCPdatasourceCreator` is a proprietary Gen-1 service discovery mechanism. Gen-3 would use Kubernetes secrets, Vault, or cloud-native connection management.

6. **EHCache 1.x disk cache with PAN data**: The caching strategy must be redesigned. Storing `MemberInquiryValue` objects (containing PANs) in a disk cache is a PCI DSS blocker. Gen-3 must use a token or masked reference in the cache key and value.

7. **Log4j 1.x / EOL logging**: Must be migrated to SLF4J + Logback or log4j2 before production hardening.

8. **Hard-coded Citi Prepaid branding in error messages**: Error message templates must be program-configurable before the service can be used for non-Citi programs in a multi-tenant Gen-3 deployment.

9. **No authentication on SOAP endpoint**: A Gen-3 migration must introduce API authentication (mutual TLS, OAuth2, or API key) at the gateway layer.

10. **Windows-specific deployment artifacts**: The log4j config path `d:/c-base/...` and Windows service name `CardNotificationSMSPull` must be replaced with environment-agnostic configuration management.
