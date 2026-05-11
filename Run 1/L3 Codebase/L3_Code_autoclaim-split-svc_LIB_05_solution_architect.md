# autoclaim-split-svc_LIB — Solution Architect View

## Technical Architecture

The library is a **two-module Maven multi-project** structured as a contract/implementation split:

```
autoclaimsplit-common (contract JAR)
  com.citi.prepaid.core.autoclaim
    ├── domain/
    │   ├── Allotment.java          — Output: list of device allocations + metadata
    │   ├── AllotmentVO.java        — Internal computation state per device
    │   ├── AutoclaimSplitConstants.java  — Error codes + constant strings
    │   ├── DeviceTypes.java        — Enum-style constants: eCard, eCheck, DDA, ACH, Plastic, CreditCard, Operator, IEFT
    │   ├── DeviceVO.java           — Output device: id, type, amount, priority, beneficiary, country, currency, fee
    │   ├── PaymentVO.java          — Input: memberId, echeckId, programId
    │   └── ProgramAutoClaimProfile.java  — Program-level autoclaim configuration
    ├── exception/
    │   └── AutoclaimException.java — Checked exception with errorCode + errorMesg
    └── service/
        └── AutoclaimSplit.java     — Single-method public interface: performSplit(PaymentVO)

autoclaimsplit-svc (implementation JAR)
  com.citi.prepaid.core.autoclaim
    ├── dao/
    │   ├── PaymentDao.java         — Interface: getPaymentDetail(memberId, echeckId, programId)
    │   ├── PaymentDaoImpl.java     — Spring StoredProcedure implementation; inner class PaymentQuerySP
    │   └── PaymentDTO.java         — DB row mapping: amount, echeck_id, action_code, verification_code
    ├── helper/
    │   ├── IAllotmentConfigLoader.java   — Stubbed interface (method commented out)
    │   ├── AllotmentConfigLoaderImpl.java — Stubbed implementation (body fully commented out)
    │   └── UserAllotmentAllocation.java  — Core allocation engine: execute(), allocateFundsToDevice(), helpers
    └── service/
        └── AutoclaimSplitImpl.java — Orchestration: validate → DB query → load IEFT config → allocate → return
```

**Runtime wiring:** Spring 2.5.6, XML context (`appCtx-AutoclaimSplit.xml`). All beans wired by property injection (no annotations). The library registers five Spring beans: `paymentDao`, `autoclaimSplit`, `ieftConfigurationLoader`, `userAllotmentAllocation`, `contextHolder`.

## API Surface

This is an embedded library; there are no HTTP/REST/gRPC endpoints.

### Public Contract (autoclaimsplit-common)

```java
// Entry point
public interface AutoclaimSplit {
    Allotment performSplit(PaymentVO paymentVO) throws AutoclaimException;
}

// Input
public class PaymentVO {
    String memberId;   // UUID string
    String echeckId;   // UUID string
    String programId;  // Program code string
}

// Output
public class Allotment {
    List<DeviceVO> devices;
    String claimCode;        // verification_code from DB
    String eCheckId;
    String programId;
    String memberId;
    double eCheckAmt;        // NOTE: double — financial precision risk
}

public class DeviceVO {
    String deviceId;
    long deviceAmt;          // Amount in minor currency units (cents)
    String deviceType;       // See DeviceTypes constants
    int priority;
    String beneficiaryName;
    String country;
    String currency;
    double fee;              // NOTE: double — financial precision risk
}

// Exception
public class AutoclaimException extends Exception {
    int errorCode;    // See AutoclaimSplitConstants (4000-4012)
    String errorMesg;
}
```

### Error Codes

| Code | Constant | Meaning |
|---|---|---|
| 4000 | GENERAL_EXCEPTION | Uncategorised Throwable caught |
| 4001 | INVALID_PAYMENT | Null/missing PaymentVO input fields |
| 4002 | INVALID_PROGRAM_PROFILE | Program autoclaim feature not found |
| 4003 | INVALID_PROFILE | ProfileException from eCount Core |
| 4004 | INVALID_FEE_PROFILE | (Reserved; unused — fee retrieval commented out) |
| 4005 | NO_DEFAULT_DEVICE | No default DDA configured for member |
| 4010 | INVALID_ECHECK | Invalid eCheck |
| 4011 | ECHECK_CLAIMED | eCheck already claimed |
| 4012 | ECHECK_NOTFOUND | eCheck record not found |

## Security Posture

### Critical Issues

1. **Plaintext credentials committed to source** (`.mvn/wrapper/settings.xml`):
   - `nexus-qa` server: `deployment` / `dwil15?`
   - `ecount.release` server: `deployment` / `d3v0nly`
   - `ecount.snapshot` server: `deployment` / `d3v0nly`
   - `wirecard-mavenproxy-repository`: `acmng` / `acmng`
   - These must be considered compromised. Rotate all passwords and remove the file from git history.

2. **Real-looking production UUIDs in test source** (`TestAutoclaimSplitImpl.java`):
   - `MEMBERID = "0E3C9230-0705-461D-B0EF-A3BD54CD7ACA"` — commented-out alternatives include multiple other UUID sets (lines 35-54).
   - `ECHECKID = "DF69FAD5-3240-4574-AF20-BEBE58EE8E8B"`, `PROGRAMID = "04011145"`.
   - If these are real cardholder/payment identifiers from a production or staging environment, their presence in source code violates PCI DSS Requirement 3.2 and GLBA data handling obligations.

### High Issues

3. **PII and financial data in log output without masking** — `memberId`, `echeckId`, device IDs, and monetary amounts are written to Log4j at INFO/DEBUG level. In a production environment with log aggregation (Splunk, ELK, etc.), this creates an uncontrolled secondary store of financial data.

4. **Log4j 1.2.15** — CVE-2019-17571 (remote code execution via SocketServer), plus numerous other known CVEs. This dependency should be replaced with SLF4J + Logback or Log4j 2.x.

5. **Spring 2.5.6** — No security patches since ~2010. Spring Security, CSRF protection, and all modern framework hardening are unavailable.

6. **Java 1.6 target** — Cannot negotiate TLS 1.2 or 1.3 by default. PCI DSS v4.0 Requirement 4.2.1 mandates TLS 1.2 minimum for all data in transit.

7. **jTDS 1.2.2** — Abandoned JDBC driver; no TLS support for SQL Server 2016+.

### Medium Issues

8. **No input sanitisation on DB parameters** — `PaymentDaoImpl` passes `memberId`, `echeckId`, and `programId` as `Types.VARCHAR` bind parameters via Spring's `StoredProcedure`, which prevents SQL injection. However, there is no length or format validation on these inputs before they reach the DAO.

9. **`StaticRequestContextHolder` singleton pattern** — Relies on a static/ThreadLocal request context. In a multi-threaded application server, incorrect context binding/unbinding could leak agent or request IDs across threads.

10. **No `@SuppressWarnings` scope control** — `@SuppressWarnings("unchecked")` at method level in `PaymentDaoImpl.getPaymentDetail()` suppresses warnings across the entire method including the raw-type `Map` handling.

## Technical Debt

| Item | Location | Severity | Description |
|---|---|---|---|
| `AllotmentConfigLoaderImpl` fully commented out | `AllotmentConfigLoaderImpl.java` | Critical | Entire implementation is dead code. Program profile loading via Profile Service is non-functional. |
| `IAllotmentConfigLoader` interface method commented out | `IAllotmentConfigLoader.java` | Critical | Interface has no operational contract. |
| Fee retrieval commented out | `AutoclaimSplitImpl.java` lines 95-110 | High | `allotmentFee` is always 0. IEFT device fee deduction logic exists but is never triggered with a real fee value. |
| `getDeviceIDByMemberID` returns null | `UserAllotmentAllocation.java` lines 318-330 | High | Body entirely commented out; returns null always. Callers in `getDefaultDeviceForMember` would produce a `DeviceVO` with null `deviceId`. |
| `getDefaultDDAForMember(String memberId)` returns null | `UserAllotmentAllocation.java` lines 240-253 | High | `AccountDefinitionDDA` lookup commented out; always returns null. |
| `double` for monetary amounts | `Allotment.java` line 13; `DeviceVO.java` line 16 | High | `eCheckAmt` and `fee` are `double`; all other amount fields correctly use `long`. Inconsistency risks rounding errors. |
| `DeviceVO` constructor is `void` | `DeviceVO.java` line 18 | Medium | `public void DeviceVO(...)` is a method, not a constructor; Java will compile it but it is never called as a constructor. Unreachable initialisation code. |
| Raw `Map` type in `PaymentDao` | `PaymentDao.java` line 8 | Medium | `Map getPaymentDetail(...)` returns raw `Map`; no generic typing. Callers cast blindly. |
| `@SuppressWarnings("unchecked")` | `PaymentDaoImpl.java` line 36 | Medium | Hides type safety issues in SP result handling. |
| Test constants contain environment-specific UUIDs | `TestAutoclaimSplitImpl.java` lines 48-57 | High | Hardcoded UUIDs appear to be real data; no synthetic test data used. |
| Both test classes have assertions commented out | `AllotmentConfigLoaderImplTest.java`, `TestAutoclaimSplitImpl.java` | High | Zero test coverage enforced. |
| `AutoclaimSplitImpl` logger bound to wrong class | `AutoclaimSplitImpl.java` line 38 | Low | `LogFactory.getLog(PaymentDaoImpl.class)` — logger incorrectly names `PaymentDaoImpl` instead of `AutoclaimSplitImpl`. |
| Duplicate default-device fallback paths | `UserAllotmentAllocation.java` lines 83-92 | Low | `if(fixedAmt)` and `else` branches are identical — both assign `eCheckAmt - allotedAmt` to `defaultDevice`. Dead conditional. |
| Spring DTD reference uses HTTP | `appCtx-AutoclaimSplit.xml` line 2 | Low | `http://www.springframework.org/dtd/spring-beans.dtd` — insecure HTTP DTD fetch at startup. |

## Gen-3 Migration Requirements

To migrate this capability to a Gen-3 (cloud-native, Spring Boot, containerised) architecture:

1. **Replace Spring 2.5 XML context with Spring Boot 3.x**
   - Convert `appCtx-AutoclaimSplit.xml` to `@Configuration` / `@Bean` classes.
   - Replace `PropertyPlaceholderConfigurer` with `application.yml` + environment variable injection.

2. **Replace Java 1.6 target with Java 17 or 21**
   - Update `maven-compiler-plugin` source/target.
   - Address: `java.util.Date` → `java.time.*`; raw types → generics; `@SuppressWarnings` removals.

3. **Replace jTDS with Microsoft JDBC Driver 12.x**
   - `com.microsoft.sqlserver:mssql-jdbc:12.x` with SSL/TLS enforced in connection string.

4. **Replace Commons DBCP 1.x with HikariCP**
   - Remove Director dependency; configure HikariCP via Spring Boot DataSource auto-configuration.

5. **Replace Log4j 1.x with SLF4J + Logback**
   - Add PII masking/redaction for `memberId`, `echeckId`, device IDs in log output.
   - Structured JSON logging for log aggregation compatibility.

6. **Implement fee retrieval**
   - Uncomment and rewrite `FeeStructureProfileClass` integration, replacing with Gen-3 fee service API call.

7. **Implement program profile loading**
   - Rewrite `AllotmentConfigLoaderImpl` against Gen-3 profile service REST/gRPC API.

8. **Fix monetary precision**
   - Change `Allotment.eCheckAmt` and `DeviceVO.fee` from `double` to `long` (minor units) or `java.math.BigDecimal`.

9. **Replace eCount Core SPI**
   - `IEFTConfigurationLoader`, `DeviceManagerImpl`, `MemberManagerImpl`, `ECoreDevice`, `ECoreMember` — all must be replaced with calls to Gen-3 platform APIs.

10. **Secret management**
    - Remove `.mvn/wrapper/settings.xml` from the repository; rotate all embedded passwords.
    - Use GitHub/GitLab CI secret injection for Maven credentials.

11. **Restore test coverage**
    - Implement unit tests with mocked dependencies for all allocation logic paths.
    - Replace hardcoded UUIDs with synthetic test data.

## Code-Level Risks

| Risk | Location | Impact |
|---|---|---|
| NullPointerException on null `PaymentDTO.amount` | `UserAllotmentAllocation.java:35` | Runtime crash if SP returns null amount; `Integer` unboxed to `long` |
| NullPointerException on null device ID | `UserAllotmentAllocation.addDeviceToAllotments():283` | `allotmentDevice.getDeviceId().equals(...)` — NPE if `deviceId` is null |
| ClassCastException on SP result | `AutoclaimSplitImpl.java:69` | `(List<PaymentDTO>) output.get("rs")` — unchecked cast; type mismatch if SP returns unexpected structure |
| Integer overflow in amount arithmetic | `UserAllotmentAllocation.allocateFundsToDevice():143` | `Math.round((percentAmt * 0.01) * echeckAmt)` — floating-point multiplication of `long` values; precision loss for large amounts |
| Silent allotmentFee=0 | `AutoclaimSplitImpl.java:56` | Fee always 0 passed to allocation; IEFT fee deduction path effectively dead |
| Exception message string concatenation NPE | `AutoclaimSplitImpl.java:61` | `"..." + paymentVO==null?"":"..."` — Java operator precedence means the ternary evaluates `("..." + paymentVO)==null` which is always false; the null guard is logically broken |
| Infinite loop risk if `allotedAmt` never increments | `UserAllotmentAllocation.execute():49-79` | If all devices are invalid and `defaultDevice` has zero amount, loop completes but result list may be empty — not an infinite loop but silent zero-allocation |
| Credentials in git history | `.mvn/wrapper/settings.xml` | Passwords remain accessible in git log even after file deletion unless history is rewritten |
