# branded-currency_LIB — Enterprise Architect View

## Platform Generation (Gen-1/Gen-2/Gen-3)

**Classification: Gen-1 / Legacy**

Evidence:
- Depends on `com.ecount:xplatform:6.1.9` and `com.ecount:xplatformlibrary:4.0.1` — the legacy ECountCore money transfer platform.
- Depends on `com.cbase.*` classes: `MemberManagerImpl`, `TransferManagerImpl`, `MoneyTransferHelper`, `RequestContext`, `ECoreMember`, `ECoreTransfer` — the CBase proprietary backend.
- Uses Spring XML bean wiring (`brandedCurrencyContext.xml`) rather than Spring Boot auto-configuration.
- Uses `net.sourceforge.jtds.jdbc.Driver` (unmaintained jTDS SQL Server driver).
- Pervasive use of raw types (`Map`, `Dictionary`, `Hashtable`) without generics.
- Deprecated Java date API (`Date.getDate()`, `Date.getMonth()`, `Date.getYear()`) in `PaymentVO`.
- Author comments reference `IntelliJ IDEA` (dated to `Mar 4, 2008` in `EmailScheduleImpl`) indicating this codebase originates circa 2008.
- The library's version history and parent POM (`prepaid-parent:6.0.12`) are consistent with Onbe's Gen-1 prepaid stack.
- Wirecard (`cbtsclient:2.1.4`) dependency — further evidence of Gen-1 heritage.

The library has received targeted enhancement (Virtual Card enhancement in `ClaimTransactionImpl` with comment markers, `apiFlag` field for API-sourced transactions) but the core architecture is unchanged from its original design.

---

## Business Domain

**Domain: Branded Currency / Digital Gift Certificate Issuance & Redemption**

Sub-domains covered:
- **Certificate Lifecycle**: Issuance (purchase), lookup, redemption (claim), cancellation, reissuance.
- **Payment Lifecycle**: Payment creation, history, constraints, reissuance tracking.
- **Transaction Execution**: Multi-device money transfer orchestration (ecard, echeck, DDA, IEFT, credit card).
- **Velocity / Risk Controls**: Service permission checks and spend velocity constraints per user.
- **Notification Scheduling**: Email schedule retrieval, template management, stop-notification on claim.
- **User Management**: User-device binding, user group assignment, unclaimed/claimed payment retrieval.

Bounded context boundary: This library sits entirely within the **Branded Currency** bounded context. It has hard dependencies on:
- **CBase / ECountCore** context (money movement, member identity).
- **Notification** context (`StopNotificationService`).

---

## Role in Platform

This library is a **shared domain library** — it encodes the domain model and DAO layer for the Branded Currency product and is consumed by one or more upstream web application or service modules (not visible in this repository but expected to be the actual user-facing or API-facing services).

Position in the layered stack:
```
[Consumer: Web App / API Service]  ← not in this repo
         |
         v
[branded-currency_LIB]             ← this library
         |
         v
[ECountCore / xplatform]           ← Gen-1 money movement engine
[CBase MemberManager]              ← Gen-1 member identity
         |
         v
[cbaseapp SQL Server]              ← Gen-1 RDBMS
```

The library acts as an **anti-corruption layer** that encapsulates all stored procedure calls and ECountCore API interactions behind Java interfaces (`CertificateDAO`, `PaymentDAO`, `TransactionDAO`, `UserDAO`, `IEmailSchedule`).

---

## Dependencies

### Upstream (consumers of this library)
- Unknown from this repository alone. Expected to be Onbe web applications or REST API services for the Branded Currency product.

### Downstream (dependencies this library calls)

| Dependency | Type | Coupling |
|---|---|---|
| `com.ecount:xplatform:6.1.9` | Internal platform (Gen-1) | **Tight** — `MoneyTransferHelper`, `RequestContext`, `Account`, `ExtendedAddenda` used directly in `UserTransactionImpl` |
| `com.ecount:xplatformlibrary:4.0.1` | Internal library | **Medium** — additional utilities |
| `com.wirecard.crossbordertransferservice:cbtsclient:2.1.4` | Legacy cross-border client | **Unknown** — declared but no direct code reference found in this library's sources (may be used by xplatform transitively) |
| `com.cbase.business.core.*` | CBase platform (Gen-1) | **Tight** — `IMemberManager`, `MemberManagerImpl`, `TransferManagerImpl`, `ECoreTransfer`, `ECoreMember` |
| `com.cbase.services.notification.StopNotificationService` | CBase notification platform | **Tight** — direct instantiation in `StopNotificationClaimedCodeImpl` |
| `com.cbase.ecount.helpers.MoneyTransferHelper` | ECountCore helper | **Tight** — all transaction flows |
| `org.springframework:spring-context` | Spring Framework | **Medium** — XML context, `StoredProcedure`, `JdbcTemplate` |
| SQL Server (`cbaseapp`) via jTDS | RDBMS | **Tight** — all business data persisted here |
| `com.parents:prepaid-parent:6.0.12` | Internal parent POM | Build-time dependency management |

---

## Integration Patterns

1. **Data Access Object (DAO) Pattern**: All database access is encapsulated behind `CertificateDAO`, `PaymentDAO`, `TransactionDAO`, `UserDAO`, `IEmailSchedule` interfaces, with Spring implementations (`SpringCertificateDAO`, `SpringPaymentDAO`, etc.).

2. **Abstract Factory Pattern**: `BrandedCurrencyDAOFactory` (singleton) provides the concrete DAO implementations. The `BrandedCurrencyDAO` interface aggregates all DAOs.

3. **Template Method Pattern**: `UserTransactionImpl` defines the transaction execution skeleton (`preProcess` → `checkVelocity` → `begin` → `commit` → `createTransactionDevices` → `postProcess`). Subclasses (`ClaimTransactionImpl`, `CertificatePurchaseTransactionImpl`, `AddFundsTransactionImpl`) override specific phases.

4. **Value Object Pattern**: `PaymentVO`, `CertificateVO`, `BasketCertificateVO`, `UserTransactionVO`, `ClaimTransactionVO`, `ConstraintVO`, `VelocityVO` are plain Java objects with no behavior beyond getters/setters (mostly).

5. **Spring XML Dependency Injection**: Business objects are wired via `brandedCurrencyContext.xml` using constructor injection with the `CbaseappDataSource` bean provided by the consumer.

6. **Stored Procedure Integration**: All database interactions are exclusively via stored procedures (no ORM, no raw SQL in the business layer). Spring's `StoredProcedure` base class and `JdbcTemplate` with `PreparedStatementCreator` are used.

7. **Facade Integration with ECountCore**: `MoneyTransferHelper.addECardDevice()`, `.addECheckDevice()`, `.addCreditCardDevice()`, `.addDDADevice()`, `.addIEFTDevice()`, `.transferBegin()`, `.transferCommit()` form a facade over the underlying ECountCore transfer engine.

8. **Service Adapter Pattern**: `StopNotificationClaimedCodeImpl` uses `ServiceAdapter` wrapping `StopNotificationService` with a dictionary-based inputs/outputs contract — a legacy service bus pattern.

---

## Strategic Status

**Status: Active but Stale / Maintenance Mode**

Assessment:
- The library is actively maintained in GitHub with CI/CD (CodeQL scanning, Dependabot, automated publish workflow).
- It targets Java 21 (up-to-date runtime) but the internal architecture is deeply rooted in Gen-1 patterns from ~2008.
- No REST or messaging API surface; no Spring Boot; no cloud-native patterns.
- The addition of Virtual Card enhancement (circa post-2015 based on feature context) and `apiFlag` field for API-sourced transactions indicates the library continues to evolve to support new product features.
- The Wirecard CBTS dependency represents a strategic risk given Wirecard's 2020 insolvency — this artifact must be internally owned.
- There is no indication of a Gen-2 or Gen-3 replacement in progress for the Branded Currency domain within this repository.

---

## Migration Blockers

The following items must be resolved before this library can be migrated to a Gen-2 or Gen-3 architecture:

1. **Hard dependency on CBase/ECountCore platform**: All money movement goes through `MoneyTransferHelper` and `RequestContext` from the CBase stack. These classes are not available in a modern Spring Boot or cloud-native environment without re-platforming the money movement engine first.

2. **SQL Server stored procedure coupling**: 25+ stored procedures in `cbaseapp.dbo.*` schema implement all business logic. These must be reverse-engineered, documented, and migrated (or exposed as internal APIs) before the Java layer can be re-written.

3. **No REST or messaging API**: The library's public surface is Java method calls only. Exposing Branded Currency capabilities as REST services requires designing an API contract first.

4. **Static singleton DAO factory**: `BrandedCurrencyDAOFactory.getInstance()` uses a JVM-static singleton, incompatible with dependency injection frameworks that expect prototype or request-scoped beans. Must be refactored to Spring `@Component` / `@Bean`.

5. **Plaintext credentials in test context**: `brandedCurrencyTestContext.xml` hardcodes SQL Server credentials. Tests cannot be run safely in shared CI without rotating these credentials and externalizing them.

6. **Raw type usage**: `Map`, `Dictionary`, `Hashtable` (non-generic) are used in all DAO interfaces and return types. A Gen-3 service would require typed DTOs with proper validation.

7. **Deprecated Java API**: `Date.getDate()`, `Date.getMonth()`, `Date.getYear()` must be replaced with `java.time` (LocalDate/ZonedDateTime) before the library can be considered production-quality on modern Java.

8. **No unit test coverage for live code**: All integration tests require a live SQL Server + CBase installation. No mockable test surface exists because DAOs are instantiated directly with `new` inside implementation classes, making unit testing without infrastructure impossible.

9. **Wirecard CBTS client provenance**: The `cbtsclient:2.1.4` artifact from `com.wirecard.crossbordertransferservice` must be verified as an internally maintained artifact and its license/ownership confirmed.

10. **`BrandedCurrencyDAO` as aggregate**: The aggregate DAO factory pattern creates a new `SpringCertificateDAO`, `SpringPaymentDAO`, etc. on every call. In a high-throughput service, this adds object allocation overhead. Gen-3 should inject scoped beans.
