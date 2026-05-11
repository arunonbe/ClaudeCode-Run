# Solution Architect View — subaru-rewards_WAPP

## Technical Architecture
Multi-module Maven project. Active modules:
- `subaru-rewards-common`: Domain model POJOs (Sale, SalesPerson, Dealer, PayCycle, RewardJournal, etc.).
- `subaru-rewards-impl`: Business logic (state machine, DAOs, caching, request file builder).

Inactive (commented out of build):
- `subaru-rewards-service`: Service layer (unknown state).
- `subaru-rewards-web`: Web UI (WAR; unknown state).
- `subaru-rewards-requestfile`: JAXB-generated XML payment request types.

Core pattern: **State Machine** (`StateMachine` + 20+ `AbstractRewardRequestState` subclasses) driven by `SubaruRewardsImpl`. Each state reads/writes `RewardRequest` and chains to the next state.

## API Surface
No HTTP/REST/RPC API surface. This is a batch application invoked via:
- `SubaruRewardsImpl.run(Date)` — main entry point.
- `SubaruRewardsAdminImpl` — admin queries (regional, dealer, salesperson data) consumed by the (inactive) web module.
- `SubaruRewardsClient` — thin wrapper for external invocation.

## Security Posture

### Authentication and Authorization
- No authentication mechanism observed in the active codebase.
- Admin queries (`SubaruRewardsAdminImpl`) have no role-based access control — access is governed at the web layer (which is inactive/excluded from build).
- `testLogin` property (`${test.login}`) wired into production bean `subaruRewards` — if set to a non-empty value, it overrides the real sales person ID lookup in `getRewards()`.

### Cryptography
None. No encryption at rest or in transit for application data.

### Secrets Management
- DataSource credentials expected in externally injected `applicationContext-subaru-datasource.xml` — not present in this repo (good practice).
- `test.login` must not be set in production Spring context.

### Known CVE / Vulnerable Dependencies
| Library | CVE Exposure | Severity |
|---------|-------------|---------|
| Spring 2.0.2 | EOL; numerous Spring Security and core CVEs over 15+ years | Critical |
| Log4j 1.x | CVE-2019-17571 (SocketServer deserialization RCE), CVE-2022-23302/23303/23305 (JMSSink, JMSAppender) | High |
| Spring Modules (cache) | Unmaintained; no CVE tracking | High |
| EHCache 1.x | EOL; check for specific version in parent POM | Medium |
| `wagon-webdav:1.0-beta-2` (build extension) | Ancient Maven Wagon extension; potential supply chain risk | Medium |

## Technical Debt
| Item | Location | Severity |
|------|----------|----------|
| Spring 2.0.2 (`<spring-version>2.0.2</spring-version>`) | `pom.xml:38` | Critical |
| Spring XML DTD config (pre-namespace schema config) | `applicationContext-subaru-rewards-impl.xml:3` | High |
| `e.printStackTrace()` in multiple state classes | Various state files | Medium |
| `beginTran()` / `commit()` are empty methods — no actual transaction management | `SubaruRewardsImpl.java:350-356` | High |
| `testLogin` wired into production Spring bean | `applicationContext-subaru-rewards-impl.xml:118` | High |
| `todo.txt` in `subaru-rewards-impl/` | `todo.txt` | Medium |
| `scratch.sql` in SQL directory | `src/main/sql/scratch.sql` | Medium |
| Log4j 1.x in test resources | `subaru-rewards-common/src/test/resources/log4j.properties` | High |
| Three modules commented out of parent POM | `pom.xml:31-34` | Medium |
| SCM points to SVN (stale metadata) | `pom.xml:17-25` | Low |
| `CustomerName` (`cust_name`) stored unencrypted in sales table | `cbaseapp.rewards_subaru_sales.sql:25` | High |
| `ppid` (payment profile ID) stored as plaintext VARCHAR(50) | `cbaseapp.rewards_subaru_reward.sql:15` | High |

## Code-Level Risks
| Risk | Location | Description |
|------|----------|-------------|
| Empty transaction demarcation | `SubaruRewardsImpl.java:350-356` | `beginTran()` and `commit()` are no-ops. If the state machine throws mid-processing, partial reward records may be committed without rollback. |
| Infinite loop guard by TrxNo comparison only | `SubaruRewardsImpl.java:242-244` | The loop guard compares `sale.getTrxNo().equals(trxNo)` — only catches repeated single-record loops, not more complex cycle scenarios. |
| `throw new RuntimeException(e)` in state machine | `SubaruRewardsImpl.java:328` | Any exception in any state causes unchecked exception propagation; no compensation logic. |
| Inline SQL in Spring XML with no parameterisation audit | `applicationContext-subaru-rewards-impl.xml` throughout | All SQL uses `?` placeholders via JdbcTemplate — correct for parameterised queries — but the volume and complexity makes auditing difficult. |
| `FileWriter` not properly closed on exception path | `SubaruRequestBuilder.java:73-79` | `fw.close()` in `finally` block may itself throw and suppress the original exception; `fw` could be null if `new FileWriter(...)` throws. |
| Payment request XML written to filesystem without integrity check | `SubaruRequestBuilder.java:47-58` | No hash/signature on generated XML file; file could be tampered before payment platform picks it up. |

## Gen-3 Migration Requirements
1. Upgrade to Spring Boot 3.x; replace Spring XML with `@Configuration` classes.
2. Replace Log4j 1.x with Logback or Log4j 2.x.
3. Replace Spring Modules cache with Spring Cache abstraction + Caffeine or EHCache 3.x.
4. Implement proper transaction management (Spring `@Transactional` or JTA).
5. Replace VBScript scheduler with Spring Batch or a container-native CronJob.
6. Encrypt PII (`cust_name`, salesperson name/email) and `ppid` at rest — integrate with StrongBox or a modern KMS.
7. Sign or encrypt XML payment request files before filesystem handoff.
8. Add comprehensive automated tests (unit + integration) before any refactoring.
9. Remove or gate `testLogin` behind a feature flag / Spring profile.
10. Audit and document inactive modules — retain useful code, delete dead code.
