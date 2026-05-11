# Solution Architect View — xsearch_LIB

## Technical Architecture
- **Language:** Java 21 (compiler target); Commons Logging for log framework
- **Build:** Maven; parent `prepaid-parent:6.0.12`; artifact `xsearch:2.0.1` JAR
- **Architecture style:** DAO library — Spring JDBC, stored procedures, no HTTP surface
- **Package structure:**
  - `com.ecount.data.member.*` — member inquiry DAOs and value objects
  - `com.ecount.data.device.*` — device/card inquiry DAOs and value objects
  - `com.ecount.data.job.*` — job action inquiry DAOs
  - `com.ecount.data.member.csa.comment.*` — CSA comment DAOs
  - `com.ecount.one.service.emember.*` — EMember service facade, `MaskCCHelper`
  - `com.ecount.one.service.search.*` — search orchestration (`SearchServiceImpl`)
  - `com.ecount.one.value.*` — context and constants
- **Spring wiring:** `search.xml` defines all beans

## API Surface
The library's public API is consumed through Spring dependency injection:
- `SearchService.search(SearchMessage)` — main search entry point
- `SearchService.searchDevice(DeviceSearchCriteria)` — device search
- `SearchService.searchMember(AddendaSearchCriteria)` — addenda-based member search
- `EMember.find(agent, lastname, firstname, cardNumber, ...)` — low-level member finder
- `MaskCCHelper.maskThisCC(String)` — PAN masking
- `MaskCCHelper.maskThisSSN(String)` — SSN masking
- `MaskCCHelper.maskAchAccountNumber(String)` — ACH account masking
- `DeviceInquiry.searchByPUD(DeviceSearchCriteria)` — device by PUD
- `MemberByAddendaInquiry.searchByAddenda(AddendaSearchCriteria)` — addenda search

## Security Posture

### Authentication
- None — this is a library; caller is responsible for authentication

### Data Masking — Critical Non-Compliance Finding
`MaskCCHelper.maskThisCC()` masks the middle 8 digits of a card number:
```
numCharsNotMasked = 8
startMasking = (length - 8) / 2   // for 16-digit: (16-8)/2 = 4
endMasking   = length - startMasking // = 12
```
Result: first 4 and last 4 digits are unmasked; 8 middle digits are masked with `X`.

**This is non-compliant with PCI DSS Req 3.3.1** which permits at most the first 6 (BIN) and last 4 digits to be displayed. The current masking exposes position 1–4 and 13–16 rather than 1–6 and 13–16. While 4 digits may be acceptable in some interpretations, the inconsistency with the standard BIN display convention (first 6) should be assessed by the QSA.

### SSN in Application Flow
- `nss` (SSN) is accepted as a String parameter in `SearchServiceImpl.searchWithEcard()` and passed to the EMember finder
- All debug log calls that would have logged `nss` are commented out — positive action, but the comments remain, indicating prior risk
- SSN is not masked within this library; masking is provided only for card numbers and ACH account numbers

### Wildcard SQL Injection Mitigation
Single quotes in search terms are escaped (`'` → `''`) before being passed to Spring JDBC:
```java
txtFirstS = txtFirstS.replaceAll("'", "''");
```
This is a secondary defence; Spring JDBC's `JdbcTemplate` with parameterised queries (`?` placeholders) is the primary SQL injection protection. The manual escaping is redundant if proper parameterisation is used but is not harmful.

### CVE Exposure
- **XStream** — version controlled by parent POM; historically high-CVE (deserialization, XXE); version must be confirmed
- **spring-context** — version controlled by parent POM; must be confirmed as a supported version

## Technical Debt
| Item | Severity | Detail |
|---|---|---|
| PAN masking non-compliant | High | `MaskCCHelper.maskThisCC()` — exposes first 4 + last 4 instead of first 6 + last 4 |
| SSN as plain String parameter | High | `nss` parameter in `searchWithEcard()` — SSN in stack traces, possible log leakage |
| Hardcoded BIN values | Medium | `galileoAccountCheck = "514977"`, `privateLabelNumber_1 = "44815619"`, `privateLabelNumber_2 = "448184"` in `MaskCCHelper.java` |
| Debug logging commented out | Medium | 30+ commented-out debug log lines in `SearchServiceImpl` — observability debt |
| Manager singleton pattern | Medium | `DeviceManager.getInstance()`, `MemberManager.getInstance()` — static singletons, not Spring-managed; difficult to test |
| No search audit log | High | No record of who searched for what data |
| Four database connections | Medium | Operational complexity; each needs separate failover and credential management |
| `Hashtable` usage | Low | `new Hashtable()` passed to `BasicMemberSearch` — pre-generics, untyped |

## Gen-3 Migration Requirements
1. Fix `MaskCCHelper.maskThisCC()` to comply with PCI DSS — expose first 6 (BIN) and last 4 only
2. Implement search audit logging (who, what criteria, timestamp, result count)
3. Externalise BIN/prefix constants from `MaskCCHelper` to a configurable data store
4. Convert all searches to explicitly use parameterised queries (verify no string concatenation into SQL)
5. Replace manager singleton pattern with Spring-managed singletons
6. Consolidate four-database access into a unified data layer with a clear CDE boundary

## Code-Level Risks
| Risk | File:Line | Detail |
|---|---|---|
| PAN masking non-PCI-compliant | `MaskCCHelper.java:26-47` | `numCharsNotMasked = 8`; exposes 8 unmasked digits instead of 10 (BIN 6 + last 4) |
| Hardcoded Galileo BIN | `MaskCCHelper.java:72` | `galileoAccountCheck = "514977"` |
| Hardcoded private label BINs | `MaskCCHelper.java:100-101` | `privateLabelNumber_1 = "44815619"`, `privateLabelNumber_2 = "448184"` |
| SSN as plain method parameter | `SearchServiceImpl.java:380` | `nss = txtFirstS` — SSN not protected in JVM stack |
| Manual SQL quote escaping | `SearchServiceImpl.java:144,289` | Redundant escaping alongside parameterised queries; creates false sense of security |
| Card number prefix wildcard | `SearchServiceImpl.java:689` | `cardNumber = "%" + cardNumber` for 10-digit inputs — wildcard injected into query parameter |
