# card-enrollment-maricopa_LIB — Enterprise Architect View

## Platform Generation (Gen-1/Gen-2/Gen-3)

**Generation: Gen-1**

Evidence:
- Spring Framework 2.5.4 (`pom.xml` line 28) — released 2008; this is the original Spring XML-configuration era.
- Spring context loaded via `ClassPathXmlApplicationContext` and DTD-based `spring-beans.dtd` XML (`appContext.xml` line 2) — a hallmark of Gen-1 Spring applications, predating annotations and JavaConfig.
- Dependency on `com.ecount:xPlatform:2.5.45` and `com.ecount.service.Core2` — these are the eCount (Wirecard/Citi-era) Core2 libraries, which represent the original Gen-1 platform core.
- `com.citi.process` package namespace — explicitly references the Citi-era ownership of the platform before the Wirecard/eCount rebrand.
- Configuration loaded from hardcoded Windows `D:\c-base\...` paths — the `c-base` directory structure is characteristic of the original eCount/Citi on-premises Windows server deployment model.
- `coreDeviceManager` bean class `com.cbase.business.core.impl.DeviceManagerImpl` — the `cbase` library is part of the original Gen-1 eCount Core.
- Artifact version `1.0` with no SNAPSHOT — suggests a frozen, unmaintained artifact.
- No REST, no messaging, no cloud-native patterns whatsoever.

## Business Domain

**Prepaid Card Lifecycle — Physical Card Issuance**

Specifically: **Client Program Enrollment Operations** for the **Maricopa** program. This covers the downstream fulfillment step of associating a physical plastic card with a pre-existing DDA (Demand Deposit Account) enrollment record. It sits at the intersection of:
- Card account management (eCount Core device/account model)
- Physical card fulfillment (plastic embossing and delivery)
- Client-specific program operations (Maricopa is a named client/affiliate)

## Role in Platform

This library functions as a **client-specific batch enrollment utility** — a thin operational script layered on top of the Gen-1 eCount Core platform. Its role in the broader platform:

- **Consumes**: eCount Core database (via `Get_MaricopaDDA_With_No_Card` stored procedure), Director service (for DataSource provisioning), eCount Core Java API (`IDeviceManager`/`DeviceManagerImpl`/xPlatform).
- **Produces**: Plastic card issuance events within eCount Core.
- **Does not expose**: No API, no service endpoint, no message queue. It is purely a consumer/executor.
- **Client-program scoped**: Logic is entirely Maricopa-specific (hardcoded procedure name, zero fee, no configurability). It is not a general enrollment framework.
- **Operational context**: Likely run on demand or on a schedule by an operations team when a backlog of unissued Maricopa DDA cards exists — for example, following a new cardholder onboarding wave.

## Dependencies

### Upstream (what this library depends on)

| Dependency | Type | Version | Status |
|---|---|---|---|
| `com.parents:service-parent` POM | Maven parent | 9.0.0 | Internal; resolved from GitHub Packages / Nexus |
| `org.springframework:spring` | Framework | 2.5.4 | End-of-life (2008) |
| `org.springframework:spring-jdbc` | Framework | 1.2.6 | End-of-life (ca. 2006) |
| `com.ecount:xPlatform` | Internal platform | 2.5.45 | Gen-1 eCount Core platform library |
| `com.ecount.service.Core2.director:director-client` | Internal service client | 1.0.11 | Gen-1 Director connectivity |
| `com.ecount.service.Core2:ecount-system` | Internal platform | 1.0.10 | Gen-1 eCount system library |
| `com.cbase.business.core.IDeviceManager` | Internal API | (from xPlatform/cbase) | Physical card issuance API |
| Director Service (runtime) | Internal service | — | Provides JDBC DataSource; must be running |
| eCount Core Database (runtime) | RDBMS | — | Contains Maricopa account data |
| Stored proc `Get_MaricopaDDA_With_No_Card` | Database object | — | Must exist in eCount Core DB schema |

### Downstream (what depends on this library)

No code in this repository indicates any downstream consumer. This is a standalone executable JAR; no other library imports it.

## Integration Patterns

| Pattern | Used | Evidence |
|---|---|---|
| **Stored Procedure call** | Yes | `GetCardIdsList extends StoredProcedure` — Spring JDBC `StoredProcedure` abstraction |
| **Spring XML Dependency Injection** | Yes | `appContext.xml` — all beans wired via XML, loaded via `ClassPathXmlApplicationContext` |
| **PropertyPlaceholderConfigurer** | Yes | `appContext.xml` lines 4–13 — externalizes DB and director config |
| **Factory Bean (DataSource creation)** | Yes | `directorDataSourcesFactory` bean with `factory-method="getNewDatasource"` |
| **DAO Pattern** | Yes | `IAccountIdDAO` / `AccountIdDAOImpl` — interface-based data access |
| **REST / HTTP** | No | — |
| **Messaging (JMS/Kafka/MQ)** | No | — |
| **Event-Driven** | No | — |
| **Microservice** | No | — |
| **Scheduler (built-in)** | No | External triggering only |

The integration model is entirely **synchronous, in-process, JDBC-based** — classic Gen-1 enterprise Java.

## Strategic Status

**Status: Legacy / Decommission Candidate**

Rationale:
1. **Frozen at Gen-1**: No evidence of any updates toward Gen-2 or Gen-3 patterns. The `com.citi.process` package namespace indicates this predates even the Wirecard era of the platform.
2. **Client-specific hardcoding**: The Maricopa-specific stored procedure name and zero-fee hardcoding make this non-reusable without source modification.
3. **Critically outdated dependencies**: Spring 2.5.4 (2008), Spring-JDBC 1.2.6 (ca. 2006), JUnit 3.8.1 (2002). No upgrade path without a full rewrite.
4. **No tests**: Zero test coverage prevents safe modification or regression testing.
5. **Wirecard-era infrastructure references**: The Nexus URL (`d-na-stk01.nam.wirecard.sys`) ties this to pre-acquisition infrastructure.
6. **`_LIB` suffix in repo name**: Suggests this is treated as a shared/reference library rather than an active service, but it is not structured or published as one.
7. **Incomplete implementation**: The `issuePlastic` method contains commented-out pseudo-code and a `//TBD` marker (`EnrollmentHelper.java` lines 55–71), indicating the implementation was never fully finished or reviewed.

If the Maricopa client program is still active, this functionality should be evaluated for migration into a Gen-3 event-driven enrollment pipeline. If the program is inactive, this library should be archived.

## Migration Blockers

| Blocker | Severity | Detail |
|---|---|---|
| `com.cbase` and `com.ecount` Gen-1 API dependency | High | `IDeviceManager`, `DeviceManagerImpl`, `Account`, `Funds`, `AccountDefinitionECard` (imported but unused) are all Gen-1 eCount Core classes. No Gen-3 equivalents mapped. |
| Stored procedure `Get_MaricopaDDA_With_No_Card` | High | Business logic is embedded in the DB procedure. Migration requires porting this logic to a Gen-3 query/service layer with equivalent filtering. |
| Hardcoded Windows filesystem paths | High | `D:\c-base\...` paths prevent containerization or cloud deployment without a config refactor. |
| Spring XML DTD-based context | Medium | Must be replaced with Spring Boot / annotation-based config or a cloud-native framework. |
| No test coverage | Medium | Any rewrite has no regression baseline. |
| Legacy Wirecard Nexus as active Maven mirror | Medium | `settings.xml` active profile resolves from `d-na-stk01.nam.wirecard.sys` — if this Nexus is gone, the current build is already broken. |
| Plaintext credentials in `settings.xml` | Medium | Must be rotated and moved to a secrets manager (e.g., HashiCorp Vault, GitHub Actions secrets) before any CI/CD pipeline can be established. |
| `DEFAULT_RETRY_COUNT` never implemented | Low | Retry behavior was planned but not built — any Gen-3 equivalent must implement proper resilience patterns from scratch. |
