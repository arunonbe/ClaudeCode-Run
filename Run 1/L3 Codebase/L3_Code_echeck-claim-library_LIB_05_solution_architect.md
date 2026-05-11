# echeck-claim-library_LIB — Solution Architect Report

## 1. Technical Architecture

| Attribute | Value |
|-----------|-------|
| Language | Java 1.6 (compiler source/target `1.6`) |
| Framework | Spring Framework 2.5.6 (EOL 2013) |
| Architecture | Two-module Maven library (common + svc) |
| IoC | Spring XML-wired beans (`ClassPathXmlApplicationContext`) |
| DB driver | jTDS 1.2.2 (`net.sourceforge.jtds.jdbc.Driver`) — legacy, EOL |
| Connection pool | Apache Commons DBCP 1.2.2 — no pool size limits configured |
| Logging | Apache Commons Logging → Log4j 1.2.15 (EOL 2015) |
| DB access pattern | Spring `StoredProcedure` wrappers (from `DAO-Util`) — all operations via stored procedures |
| Build | Maven 2.0.2 compiler plugin, Maven Source Plugin 2.0.3 |
| Tests | JUnit 4.7 (test scope only; no test sources visible) |
| Code analysis | CodeQL via GitHub Actions (weekly) |
| Version | `1.0.0-SNAPSHOT` (unstable; never released to stable) |

---

## 2. API Surface

This is a library, not a service. The public API is defined by the `IECheckClaim` interface:

```java
// com.ecount.eCheckClaim.service.IECheckClaim
TransactionStatusVO claimECheck(ECheckClaimInput input) throws ServiceException;
```

### Input: `ECheckClaimInput`
| Field | Type | Notes |
|-------|------|-------|
| `redemptionCode` | String | Certificate verification code (payment credential) |
| `userId` | int | User (recipient) ID |
| `memberId` | String | Account member ID |
| `redeemingUserName` | String | Username claiming the eCheck |
| `ipAddress` | String | Client IP address (PII) |
| `ecardId` | String | Target eCard device ID |
| `requestContext` | Object | ECountCore request context |
| `velocityCheckNeeded` | boolean | Whether to enforce velocity/fraud check |
| `memo` | String | Optional memo |
| `ecountActivityCode` | String | ACH activity code |
| `isDDAOnly` | boolean | DDA (bank account) redemption flag |
| `addenda` | Dictionary | PPD/xPPD addenda data |

### Output: `TransactionStatusVO`
Returns the final transaction status including:
- Processing phase (INIT → PRE_PROCESS → VELOCITY_CHECK → EE_BEGIN → EE_COMMIT → CREATE_TX_DEVICES → POST_PROCESS)
- `transactionId` and `confirmationCode`
- Success/failure indicators

### Secondary interfaces (DAO layer via `IECheckClaimDAO`)
All DAO methods are backed by SQL Server stored procedures in `cbaseapp`:

| Method | Stored Procedure | Data |
|--------|----------------|------|
| `getCertificateDetail(verificationCode)` | `dbo.get_op_certificate_detail` | Certificate with recipient PII |
| `getTemplateDetail(templateId)` | `dbo.get_certificate_template_detail` | HTML template |
| `createUserTransactionHistoryItem(...)` | `dbo.create_user_transaction_history_item` | Audit record with IP, amount |
| `createTransactionDevice(...)` | `dbo.create_user_transaction_device` | Device linkage |
| `checkServicePermission(...)` | `dbo.check_service_permissions` | Velocity/fraud check |
| `updateTransactionStatus2(...)` | `dbo.update_transaction_status2` | Status + confirmation code |
| `claimPayment(...)` | `dbo.claim_payment` | Core fund transfer trigger |
| `UpdateUserEcountId(...)` | `dbo.update_user_ecount_id` | User-account linkage |

---

## 3. Security Posture

### 3.1 Authentication

No authentication layer is present in this library — it is called by a consuming service that handles authentication. The library itself authenticates to SQL Server using the hardcoded `b2ctest` SQL Server account.

### 3.2 Secrets / Credentials — CRITICAL

**File: `eCheckClaim-svc/src/main/resources/ECheckClaimDAO.xml` (lines 73–78)**

```xml
<bean id="CbaseappDataSource" class="org.apache.commons.dbcp.BasicDataSource">
    <property name="driverClassName" value="net.sourceforge.jtds.jdbc.Driver" />
    <property name="url" value="jdbc:jtds:sqlserver://ppamwdcdifsql1:2232/cbaseapp" />
    <property name="username" value="b2ctest" />
    <property name="password" value="b2ctest" />
</bean>
```

| Finding | Severity | Regulation |
|---------|---------|-----------|
| SQL Server credentials in `src/main/resources` — packaged into JAR | CRITICAL | PCI DSS Req 8.3.1 |
| Same string as username and password (`b2ctest`) — trivially guessable if it is a real credential | CRITICAL | PCI DSS Req 8.3.6 (min password length/complexity) |
| Server `ppamwdcdifsql1:2232` hardcoded | HIGH | PCI DSS Req 2.2.1 (system configuration security) |
| Credential committed to git history — cannot be fully remediated without history scrub | CRITICAL | PCI DSS Req 8.3.1 |

**Required actions:**
1. Immediately rotate `b2ctest` credentials on `ppamwdcdifsql1:2232/cbaseapp`.
2. Determine whether `ppamwdcdifsql1` is production, staging, or test — treat as production until confirmed otherwise.
3. Replace with externalised configuration (Spring `PropertySource` + secrets vault).
4. Scrub git history using `git filter-repo` or re-initialise repository.
5. Alert PCI DSS QSA of the finding for assessment documentation.

### 3.3 Encryption

- No transport encryption explicitly configured for the jTDS JDBC connection. jTDS 1.2.2 supports SSL for SQL Server connections but it is not enabled by default — `ssl=off` is the jTDS default. SQL Server TLS enforcement may already reject this connection if the server is patched.
- No data-at-rest encryption in the library layer (handled at DB level).

### 3.4 Dependency Vulnerabilities

| Dependency | Known Vulnerabilities |
|-----------|----------------------|
| `log4j:1.2.15` | CVE-2019-17571 (JMSAppender deserialization RCE — CVSS 9.8), CVE-2020-9488 (SMTP appender MITM), multiple other CVEs |
| `org.springframework:spring:2.5.6` | Multiple CVEs across Spring 2.5 including XSS, open redirect, SpEL injection in later patched versions |
| `net.sourceforge.jtds:jtds:1.2.2` | Abandoned; no CVE tracking; no TLS 1.2/1.3 support |
| `commons-dbcp:1.2.2` | Multiple minor CVEs; superseded by DBCP2 |
| `xerces:1.2.3` | Ancient; multiple XML parsing CVEs |
| `xstream:1.2.1` | Multiple deserialization CVEs (XStream has extensive CVE history; 1.2.1 is extremely old) |

**CodeQL** weekly scans will surface many of these.

---

## 4. Technical Debt

| Issue | Severity | Detail |
|-------|---------|--------|
| Hardcoded credentials in source | CRITICAL | `b2ctest/b2ctest` in `ECheckClaimDAO.xml` |
| Log4j 1.x (CVE-2019-17571 etc.) | CRITICAL | EOL; multiple RCE-severity CVEs |
| Spring 2.5.6 EOL | CRITICAL | 12+ years out of support |
| jTDS 1.2.2 EOL | CRITICAL | No TLS 1.2+ support |
| `ApplicationContext` per request | HIGH | `new ClassPathXmlApplicationContext(CONTEXTS)` in `ECheckClaimImpl.claimECheck()` — creates and destroys a Spring container on every claim call. This is an extreme performance anti-pattern |
| No connection pool limits | HIGH | `BasicDataSource` with no `maxActive` — unlimited connections possible; can exhaust DB |
| Raw `Map` and `Dictionary` types | MEDIUM | Java 1.6 raw types; no generics; unsafe unchecked casts |
| SNAPSHOT version | MEDIUM | Library never promoted to stable release; `1.0.0-SNAPSHOT` in all POM files |
| No unit tests | HIGH | No test source directories visible; CodeQL is only automated check |
| Wirecard Nexus dependency | HIGH | `d-na-stk01.nam.wirecard.sys:8080/nexus` — build dependency on Wirecard infrastructure |
| `xstream:1.2.1` | HIGH | XStream 1.x has extensive deserialization CVE history; 1.2.1 is from ~2007 |

---

## 5. Gen-3 Migration Assessment

**Migration complexity**: HIGH (due to xPlatform and ECountCore coupling)

### Replacement design

```
Current (Gen-1):
ECheckClaimImpl (Spring 2.5)
    → ClassPathXmlApplicationContext (per request — anti-pattern)
    → ECheckClaimDAOImpl (Spring StoredProcedure)
    → jTDS → SQL Server cbaseapp
    → xPlatform eTransfer → ECountCore

Gen-3 target:
ECheckClaimService (Spring Boot 3.x @Service)
    → Spring-managed singleton bean (ApplicationContext lifecycle correct)
    → ECheckClaimRepository (Spring Data JPA / Spring JDBC)
    → mssql-jdbc 12.x → SQL Server cbaseapp (or Gen-3 DB)
    → ECountCore REST API client (Feign / WebClient)
```

### Migration steps
1. **Rotate `b2ctest` credentials immediately** — prerequisite to any migration.
2. **Upgrade to Spring Boot 3.x** — replaces Spring 2.5.6, Log4j 1.x, DBCP with HikariCP, all in one step.
3. **Replace jTDS with mssql-jdbc** — enables TLS 1.2+, modern SQL Server features.
4. **Externalise configuration** — Spring Cloud Config + Azure Key Vault for credentials.
5. **Fix ApplicationContext anti-pattern** — inject `ECheckClaimDAO` as a Spring-managed singleton; remove `ClassPathXmlApplicationContext` from `claimECheck()`.
6. **Add unit tests** — mock `IECheckClaimDAO` to test business logic; target >80% coverage.
7. **Replace raw types** — parameterise all `Map`, `Dictionary` usages.
8. **Replace xPlatform eTransfer** — identify Gen-3 equivalent (likely `payment-service_SVC` or equivalent microservice).

---

## 6. Code-Level Risks

| Risk | File | Detail |
|------|------|--------|
| Credentials in source | `ECheckClaimDAO.xml:76-77` | `b2ctest/b2ctest` — CRITICAL |
| Per-request Spring context | `ECheckClaimImpl.java:34-36` | `new ClassPathXmlApplicationContext(CONTEXTS)` — performance anti-pattern; creates ~100ms overhead per claim |
| No connection pool limits | `ECheckClaimDAO.xml:72-78` | No `maxActive`, `maxWait`, or `validationQuery` on `BasicDataSource` |
| Log4j 1.x CVE-2019-17571 | `pom.xml:log4j` dependency | RCE via JMSAppender; CVSS 9.8 |
| XStream deserialization | `pom.xml:xstream:1.2.1` | Multiple deserialization CVEs across XStream history |
| Raw Map unchecked cast | `ECheckClaimDAOImpl.java:32` | `return getTemplateDetail.execute(templateId)` returns raw `Map` — unchecked; NPE/ClassCast risk |
| No null check on `claimECheck` input | `ECheckClaimImpl.java:29` | Input `ECheckClaimInput input` not null-checked before accessing `input.getRedemptionCode()` |
| Velocity check bypass | `ECheckClaimInput.isVelocityCheckNeeded()` | Caller can set `velocityCheckNeeded=false` to bypass fraud velocity check — must be restricted to authorised callers only |
