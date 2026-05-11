# echeck-claim-library_LIB — Enterprise Architect Report

## 1. Platform Generation

| Attribute | Value |
|-----------|-------|
| Platform generation | Gen-1 (original eCount/NorthLane platform) |
| Technology stack | Java 1.6, Spring 2.5.6, Log4j 1.x, jTDS JDBC, Apache DBCP |
| Architecture style | Spring XML-wired DAO library; no REST API; no Spring Boot |
| Packaging | Maven JAR library (`_LIB` suffix) |
| Group ID | `com.ecount.service` |
| Author attribution | OFSS (Oracle Financial Services Software — external development vendor) |

The `OFSS` author tag in multiple Java files (`@author OFSS`) indicates this library was built by Oracle Financial Services Software, a common vendor for banking/payments system development. This is characteristic of Gen-1 outsourced development with minimal internal ownership.

---

## 2. Business Domain

**Domain**: Payments — Electronic Check Claim Processing  
**Subdomain**: eCheck redemption flow (eCount legacy payment instrument)

This library implements the **eCheck payment claim flow** within the eCount prepaid platform. When a cardholder receives an eCheck (a legacy eCount payment instrument analogous to a digital check), they redeem it by providing a verification code. This library validates the certificate, runs velocity checks, and executes the money transfer from the claimable payment pool to the recipient's account.

The business processes this library supports:
1. Certificate/redemption code validation
2. Velocity and fraud rate-limiting
3. ECountCore money transfer (`eTransfer.begin` / `eTransfer.commit`)
4. User transaction history creation (regulatory audit trail)
5. Transaction device linking (card/DDA account assignment)

---

## 3. System Role in the Enterprise

| Role | Description |
|------|-------------|
| Claim processing library | Shared JAR consumed by web applications and services that handle eCheck claims |
| CDE component | Connects directly to `cbaseapp` — the core payments database; in PCI DSS CDE scope |
| Fraud control enforcement | Implements velocity check gate via `dbo.check_service_permissions` |
| Audit trail writer | Creates `user_transaction_history` records for Reg E compliance |
| Money transfer executor | Calls ECountCore eTransfer API for actual fund movement |

This library is **in the CDE (Cardholder Data Environment)** because it:
1. Connects to `cbaseapp` (core payments database with cardholder account data)
2. Processes payment redemption codes (`verificationCode`) — payment credentials
3. Executes fund transfers for amounts in the payment system

---

## 4. Dependencies

### Runtime dependencies (from POM)
| Dependency | Version | Role |
|-----------|---------|------|
| `com.ecount:xPlatform:2.5.45` | Internal | Core eCount platform library (account management, device types, eTransfer) |
| `org.springframework:spring:2.5.6` | EOL | IoC container, JDBC template |
| `com.ecount.daoutil:DAO-Util:1.0.1` | Internal | DAO utilities (Spring StoredProcedure wrappers) |
| `net.sourceforge.jtds:jtds:1.2.2` | EOL | SQL Server JDBC driver |
| `commons-dbcp:1.2.2` | Old | Connection pooling |
| `log4j:1.2.15` | EOL | Logging |
| `com.ecount.service.core.client:ecountCoreClient:1.0.5` | Internal | ECountCore service client (eTransfer) |
| `com.ecount.service.core.client:eventServiceClient:1.0.5` | Internal | Event service client |
| `com.ecount.service.core.client:profileClient:1.0.5` | Internal | Profile service client |
| `com.ecount.service.notification:notification-event-handler-client:0.0.1-SNAPSHOT` | Internal | Notification event handler client |

### External system dependencies
| System | Connection | Role |
|--------|-----------|------|
| `ppamwdcdifsql1:2232/cbaseapp` | jTDS JDBC, SQL Server | Core payments database — all claim transactions |
| ECountCore service | xPlatform `eTransfer` | Fund transfer execution |
| Director service | Internal XML-RPC | (Referenced in commented POM blocks) |

### Downstream consumers (who calls this library)
The library (`_LIB` suffix) is consumed by upstream services. Based on the `IECheckClaim` interface, likely consumers are:
- eCount cardholder web application (claim page)
- eCheck claim service/API (if one exists)
- Any batch process that handles eCheck redemption

---

## 5. Integration Patterns

| Pattern | Where Used | Assessment |
|---------|-----------|------------|
| Spring XML-wired DAO | `ECheckClaimDAO.xml` | Gen-1 pattern; no annotations, no Spring Boot auto-configuration |
| Spring StoredProcedure | All DAO beans via `DAO-Util` | All DB operations via stored procedures — no direct SQL |
| `ClassPathXmlApplicationContext` per request | `ECheckClaimImpl.claimECheck()` | **Anti-pattern** — creating a new Spring context on every request is an extreme performance issue |
| Synchronous money transfer | `UserTransaction.execute()` — begin/commit | Synchronous; no message queue; failure requires manual recovery |
| Plaintext connection credentials | `ECheckClaimDAO.xml` | Hardcoded credentials — PCI DSS violation |

---

## 6. Strategic Status

**Current status**: Active (inferred from CodeQL scan configuration and SNAPSHOT version).

**Assessment**: This library is a **Gen-1 technical debt item** with critical security and compliance deficiencies:

1. **Credentials in source** — `b2ctest/b2ctest` hardcoded; must be rotated and externalised immediately.
2. **EOL stack** — Java 1.6 (EOL 2013), Spring 2.5.6 (EOL 2013), Log4j 1.x (EOL 2015), jTDS (abandoned 2013). No security patches for 10+ years.
3. **Per-request Spring context** — the `ApplicationContext` creation in `ECheckClaimImpl` is a performance anti-pattern that would cause severe slowdowns under any meaningful load.

**Migration path**: The Gen-3 equivalent would be a Spring Boot 3.x service with:
- Spring Data JPA or Spring JDBC
- Azure Key Vault / AWS Secrets Manager for credentials
- Flyway/Liquibase for schema management
- Spring Security for auth
- Actuator for health/metrics

---

## 7. Migration Blockers

| Blocker | Detail |
|---------|--------|
| `xPlatform` dependency | Core eCount platform library; must be available or refactored for Gen-3 migration |
| `eTransfer` API (ECountCore) | Money transfer is delegated to ECountCore; Gen-3 must either port ECountCore or replace it |
| `cbaseapp` stored procedures | 8 stored procedures in `cbaseapp`; Gen-3 migration requires re-implementation |
| Consumer coupling | Library consumers must be identified and migrated simultaneously |
| Credentials exposure | `b2ctest/b2ctest` in git history — even after rotation, git history must be scrubbed or repository re-created |
| Java 1.6 source compatibility | Source code uses pre-generics `Map` and `Dictionary` (raw types); must be modernised |
