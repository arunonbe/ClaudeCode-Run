# Enterprise Architect View — xaffiliate-service_LIB

## Platform Generation Classification

**Generation**: Gen-1 / Gen-1.5 hybrid — upgraded runtime, retained architecture

xaffiliate-service_LIB occupies an unusual position in the platform portfolio: the artifact version (`4.0.1`), parent POM (`prepaid-parent:6.0.12`), and Java 21 compiler target indicate active modernization investment, yet the architectural patterns (Hibernate ORM with `SessionFactory.getCurrentSession()`, stored procedure data access via `Proc*` wrappers, SQL Server, no Spring Boot) are firmly Gen-1 eCount/Citi heritage. The library bridges Gen-1 and Gen-2 consumers: OnePlatform web (`oneplatform_WAPP`), CSA application (`csa_WAPP`), and `bmcwizard_WAPP` all depend on it. It is not a Gen-3 component and has no Azure or cloud-native characteristics.

## Strategic Role in the Enterprise

This library is **tier-1 configuration infrastructure** for the OnePlatform cardholder web portal. Every cardholder-facing portal rendering request traverses this library to resolve affiliate branding, locale, skin, and content copy. The access level feature flag map (`findAccessLevelFeatureMap()`) makes this library a de facto access control enforcement point for CSA agents — a compliance-critical function intersecting PCI DSS Requirement 7.

Because the library is shared by all Gen-1/Gen-2 consumer applications through Maven dependency, any defect — including the `length() > 4` affiliate lookup heuristic or the `e.printStackTrace()` exception swallowing — propagates silently to all consumers simultaneously. There is no runtime isolation boundary. This concentration of configuration authority without an audit trail is an enterprise risk.

## Integration Patterns

**Inbound coupling (consumers)**:
- Consumed as a compiled JAR dependency by OnePlatform, CSA, and BMC Wizard applications
- Spring application context injection: consumers must provide a configured `affiliateSessionFactory` (Hibernate) and `affiliateTransactionManager` (Spring `PlatformTransactionManager`), as well as a `cbaseapp` datasource for the access level queries
- No runtime service contract (no REST, no messaging, no gRPC): coupling is compile-time binary

**Outbound integration**:
- SQL Server (`ecountcore` database) via Hibernate ORM — HQL queries for reads, stored procedure wrappers (`Proc*` classes) for writes
- `cbaseapp` database via `IAccessLevelConfigDAO` — separate datasource, separate connection pool

**Integration risks**:
- Compile-time binary coupling means any API-incompatible change to this library requires coordinated releases of all consumer applications — a significant change management burden
- The dual-database pattern (ecountcore + cbaseapp) means the library participates in two different transaction scopes; the `@Transactional("affiliateTransactionManager")` class-level annotation covers only the ecountcore operations; cbaseapp access is outside the managed transaction boundary, creating potential partial-failure scenarios

## Architecture Debt Assessment

| Concern | Severity | Detail |
|---|---|---|
| Binary coupling, no service boundary | High | All consumers share the same JAR; a defect affects all simultaneously; no independent deployability |
| Magic number business rule (`length() > 4`) | High | Silent failure for valid short affiliate IDs; no unit test coverage visible for this path |
| No audit trail on access level changes | High | PCI DSS Req 10.2.5: changes to CSA feature flags must be logged; current design has no audit record |
| `e.printStackTrace()` exception handling | Medium | In containerized deployments, System.err is not captured by log aggregators; errors are silently lost |
| `AffiliateServiceImplOld.java` dead code | Medium | Increases CodeQL scan surface; maintenance confusion risk |
| Hibernate `SessionFactory.getCurrentSession()` | Medium | Requires careful Spring transaction integration; Hibernate 6.x context management differences from 5.x must be validated |
| No input validation on locale code | Medium | `getLocaleId()` and internal callers do not consistently validate 5-character format |
| No service API contract (IDL/OpenAPI) | Low | No formal contract exists; consumers rely on Java binary interface directly |

## Migration and Modernization Posture

**Current trajectory**: The library is being maintained and modernized in-place (Java 21, stable release versioning, GitHub Actions CI). This is the correct approach for a library with many active consumers, but it does not address the fundamental architectural debt of binary coupling.

**Recommended modernization path**:
1. **Near-term (within 6 months)**: Fix `e.printStackTrace()` calls, remove `AffiliateServiceImplOld.java`, add audit logging for access level configuration changes to satisfy PCI DSS Req 10.2.5
2. **Medium-term (6–18 months)**: Wrap this library behind a standalone REST microservice (affiliate-config-service) to decouple consumers from compile-time binary coupling; publish an OpenAPI contract; enable independent deployability
3. **Long-term (Gen-3 migration)**: Replace the Gen-1 stored procedure data layer with JPA/Spring Data repositories backed by Azure SQL; migrate cardholder portal to retrieve affiliate configuration from the affiliate-config-service via API Gateway, enabling blue-green and canary deployment strategies

**Retirement recommendation**: Do not retire; the library is active and load-bearing. Invest in wrapping it behind a service boundary to enable safe evolution. The access level feature flag mechanism in particular must eventually migrate to a dedicated, audited authorization service (potentially integrating with Azure Active Directory B2C or a purpose-built entitlements service).

## Cross-Cutting Concerns

- **PCI DSS Requirement 6.3.3** (all software components protected from known vulnerabilities): Dependencies (Hibernate, Spring) are managed by `prepaid-parent`; version control and vulnerability scanning depends on parent POM update cadence
- **PCI DSS Requirement 7** (restrict access): The `findAccessLevelFeatureMap()` method is a PCI-relevant access control mechanism; changes must be subject to formal change management
- **UDAAP**: Locale copy content (fee disclosures, terms) served by this library is directly tied to regulatory disclosure accuracy; incorrect content constitutes a potential deceptive practice under UDAAP
- **Observability gap**: Library produces SLF4J log output routed through the consuming application; no standalone health or metrics endpoint; monitoring coverage is entirely dependent on consuming application's instrumentation — acceptable for a library but creates blind spots if consumers have different logging configurations
