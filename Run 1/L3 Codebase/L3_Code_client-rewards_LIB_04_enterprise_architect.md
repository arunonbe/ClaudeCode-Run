# client-rewards_LIB — Enterprise Architect View

## Platform Generation (Gen-1/Gen-2/Gen-3)

**Generation: Gen-1**

Evidence:
- Spring Framework 2.0.8 (released 2008) — the oldest supported Spring release at the time of original development.
- JAXB 2.0EA3 (early-access pre-release, non-standard `com.sun.xml` groupId).
- Java source/target `1.5` (Java 5 — released 2004).
- SCM originally on SVN (`ecsvn.office.ecount.com`) — migrated to Git but retaining all SVN history artefacts (`vssver2.scc` files indicate even earlier Visual SourceSafe lineage before SVN).
- No REST or SOAP API surface — purely file-based batch integration.
- No containerisation, no cloud-native patterns, no 12-factor compliance.
- Proprietary internal platform (`xPlatform`, `director-client`, `xSecurity-impl`, `ecount-system`) — all Gen-1 internal infrastructure.
- Spring XML-bean wiring without annotations — pre-Spring 2.5 annotation style.
- JAXB classes were generated on 2008-08-18 and 2008-12-15 and have not been regenerated since.

---

## Business Domain

**Domain: Client Incentive Disbursements / Rewards Fulfilment**

This library implements the **client-facing reward loading pipeline** within Onbe's prepaid card / incentive disbursement platform. Specifically, it handles:

- Onboarding reward recipient data from client-supplied XML files into the Onbe platform database.
- Translating staged reward records into payment request files for downstream card issuance or funds loading.
- Expiring unclaimed / aged reward records per programme rules.

It sits at the intersection of the **B2B client integration** domain (receiving client batch files) and the **B2C disbursement** domain (issuing prepaid card funds to end recipients). The known client at time of development was Sprint (programme ID `3801`), but the `program_id` / `partner_id` lookup architecture is designed for multi-client use.

---

## Role in Platform

```
[Client (e.g., Sprint)] ──(XML input file)──> [client-inputfile]
                                                      |
                                              SQL Server: cbaseapp
                                                      |
                                          [client-requestfile] ──(XML request file)──> [requestfile-impl / payment rail]
                                                      |
                                          [client-expire-records] ──(SP call)──> expire aged records
```

This library is a **library/batch module** positioned between:
- **Upstream**: External client file drops (FTP or filesystem delivery).
- **Downstream**: `requestfile-impl` (internal payment request builder that drives card issuance or ACH).
- **Platform services consumed**: Director (DB config discovery), JobSvc/ProfileManager (partner ID resolution), `xPlatform` (utilities).

It does **not** expose any API (no REST, no SOAP, no JMS) — it is purely a scheduled batch consumer and producer.

---

## Dependencies

### Inbound (consumes)
| Component | Type | Version | Status |
|---|---|---|---|
| `com.ecount.service:service-parent` | Maven parent POM | 3 | Internal; required for build |
| `com.ecount:xPlatform` | Internal utility lib | 1.0.14 / 1.0.12-SNAPSHOT (inconsistent) | Internal; Gen-1 |
| `com.ecount.service.Core2:ecount-system` | Internal platform core | 1.0.7 | Internal; Gen-1 |
| `com.ecount.service.Core2.director:director-client` | Service discovery | 1.0.9 | Internal; Gen-1 |
| `com.ecount.service.xmlrpc:xmlrpc` | XML-RPC comm | 1.0.6 | Internal; Gen-1 |
| `com.ecount.service.xSecurity:xSecurity-impl` | Security utilities | 1.0.5 | Internal; Gen-1 |
| `com.ecount.spring-dbctx:spring-dbctx-container` | Spring DB context | 1.0.2 | Internal |
| Director HTTP service | Runtime service | `http://ECIFLEXAPPDEV/...` | Dev address only |
| JobSvc / ProfileManager | Runtime service | `com.cbase.business.profile.*` | Resolves partner_id |
| SQL Server (`cbaseapp`) | Database | Unknown | Via Director DBCP |

### Outbound (produces for)
| Component | Type | Notes |
|---|---|---|
| `requestfile-impl` (`com.ecount.service:requestfile-impl:1.0.1-SNAPSHOT`) | Internal payment builder | Receives `RequestFileVO`/`BatchVO`/`RequestVO` objects |
| `com.ecount.payment.common.*` | Payment commons | `AccountCreationVO`, `FundsAdditionVO`, `PaymentRequestFile`, `ReqFileNameGenerator` |
| XML request files on filesystem | File output | Consumed by downstream payment processing |
| Reply XML files on filesystem | File output | Consumed by the client |

### Sibling module dependency
`client-requestfile` declares `client-inputfile` as a Maven dependency (`com.ecount.service.rewards.client:client-inputfile:1.0-SNAPSHOT`) — it reuses `IClientRewardsConstants` and DTO classes from the input module.

---

## Integration Patterns

| Pattern | Used | Detail |
|---|---|---|
| **File-based batch integration** | Yes | Client drops XML file; library processes it; produces reply XML and payment request XML |
| **Stored procedure as service** | Yes | All DB interactions are via named stored procedures (`dbo.*`); no direct SQL |
| **Spring dependency injection** | Yes | Spring 2.0.8 XML beans; setter injection throughout |
| **Spring programmatic transaction management** | Yes | `PlatformTransactionManager` in `InputDAO`; `DataSourceTransactionManager` in `ClientRewardsRequestFileDAO` |
| **JAXB XML binding** | Yes | Input and reply files marshalled/unmarshalled via JAXB 2.0EA3 with XSD validation |
| **Director service discovery** | Yes | DataSource obtained from internal Director HTTP service rather than static JDBC URL |
| **JobSvc profile lookup** | Yes | `ProfileManager.getProfileDriver()` used to resolve `partner_id` from `program_id` |
| **JMS / messaging** | No | ActiveMQ dependency present in root POM but only in test scope; not used at runtime |
| **REST / SOAP API** | No | None |
| **Event-driven** | No | Purely polling/batch |

---

## Strategic Status

**Status: Legacy / Sunset Candidate**

- Codebase dates from 2008 with no evidence of significant refactoring since original development.
- All frameworks (Spring 2.0.8, Log4j 1.2.13, JAXB 2.0EA3, Java 1.5 target) are end-of-life.
- The only active CI automation is a weekly CodeQL scan — no build/test/deploy pipeline.
- Depends on internal Gen-1 infrastructure (`Director`, `xPlatform`, `ecount-system`) which would need to be replaced in any Gen-3 migration.
- `vssver2.scc` files indicate this code traces its lineage to Visual SourceSafe — it predates even the SVN migration.
- No unit tests with meaningful assertions (`AppTest.java` in all three modules contains only Maven archetype placeholder stubs with `assertTrue(true)`).
- The library is architecturally straightforward (3 batch jobs, 6 stored procedure wrappers, 1 Spring context per module) and could be rewritten from scratch in a Gen-3 environment more efficiently than migrated.

---

## Migration Blockers

| Blocker | Severity | Detail |
|---|---|---|
| `director-client` dependency | High | DataSource obtained via internal Director HTTP service; must be replaced with modern connection pooling (HikariCP) and secrets manager (Vault, AWS Secrets Manager) |
| `xPlatform` dependency | High | Internal utility library with no Maven Central equivalent; requires reverse-engineering or replacement |
| `ecount-system` / `Core2` dependency | High | Internal Gen-1 platform core; `com.cbase.*` classes (`Member`, `ProfileManager`, `RequestContext`) deeply wired |
| `requestfile-impl` / `com.ecount.payment.common.*` dependency | High | Payment request file building depends on internal Gen-1 payment commons; must be rearchitected to Gen-3 payment rail API |
| JAXB 2.0EA3 with `com.sun.xml` groupId | Medium | Non-standard early-access artefact; standard Jakarta XML Binding should replace, with XSD regeneration |
| Java 1.5 source/target | Medium | Requires recompilation and code modernisation (generics with type erasure suppressions, `@SuppressWarnings("unchecked")` throughout) |
| Spring 2.0.8 XML bean wiring | Medium | Must migrate to Spring Boot or equivalent; all bean definitions need rewriting |
| Hardcoded filesystem paths (`D:\c-base\`) | Medium | No environment abstraction; requires externalised config (Spring Boot application.properties, Kubernetes ConfigMaps) |
| Stored procedures as sole DB interface | Medium | Stored procedure names and schemas are unknown without DB access; all business logic in SP bodies is invisible in this codebase |
| No test coverage | Medium | Zero meaningful tests; migration validation requires test suite to be written from scratch |
| File-based integration pattern | Low | Can be replaced with event-driven (Kafka, SQS) or API-based integration with clients |
