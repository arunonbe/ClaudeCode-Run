# Enterprise Architect — oneplatform_WAPP

## Platform Generation
**Gen-1** — This is the clearest Gen-1 application in the Onbe portfolio. Evidence:
- Struts 1.3.10 MVC framework (first released 2000, EOL 2013).
- Spring 2.0.3 (2007 era).
- Log4j 1.2.17 (EOL 2015).
- Java 8 target.
- WAR deployment to on-premises Windows Tomcat.
- xDoclet 1.x code generation (pre-annotation era).
- jTDS 1.2 JDBC driver (replaced by Microsoft JDBC Driver decades ago).
- `com.citi.prepaid` group IDs indicating pre-Onbe Citi Prepaid lineage.
- Version `2.1.58-SNAPSHOT` indicating long-running active development on legacy stack.
- SCM URL points to `gitlab.com/northlane/...` (prior brand).

## Business Domain
**Cardholder Self-Service Portal** — Core CDE application serving prepaid card holders across multiple affiliate/program configurations.

## Role in the Platform
Central cardholder touchpoint. The `display_recipient_web = Y` feature flag in the codebase indicates the active migration path: programs being migrated to Gen-3 are redirected away from this application to the new Recipient Web (Gen-3). OnePlatform will eventually be retired as programs migrate.

## Dependencies

### Upstream Libraries (compiled in)
- `xPlatform:3.0.29` — core platform library (data access, session management).
- `xAffiliateService:2016.1.1` — affiliate configuration service.
- `xSecurity:2016.1.1` — security framework.
- `webapp-common:1.0.1` — shared web utilities.
- `rsa-mfa-impl:2019.4.1` — RSA multi-factor authentication.
- `symbol-svc:1.0.0` — symbol / token service.
- `eccm:1.0.1` — tag library.
- `dfapiclient:2018.1.0` — Data Foundation API client.
- `subaru-rewards-impl:1.0.8` — loyalty rewards.
- `brandedCurrency:2016.1.1` — branded currency.
- `inventory-mgmt:2016.1.1` — card inventory management.
- `security-audit-common:2020.2.1` — audit event infrastructure.
- `spring-dbctx-container:1.0.4` — multi-database context switching.

### External Services
- SQL Server databases (multiple instances).
- RSA Authentication Server (MFA).
- Biocatch (behavioral analytics).
- Cambridge FX (international transfers).
- KYC portal (identity verification).
- Message Center (notifications).

## Integration Patterns
- Synchronous HTTP (browser/mobile → Struts actions).
- Synchronous JDBC (Spring data access → SQL Server).
- Synchronous RPC to backend services via Spring beans (xPlatform, xSecurity, etc.).
- Asynchronous audit events via Message Center.

## Strategic Status
**Sunset / Active Migration** — OnePlatform is being retired as cardholders are migrated to the Gen-3 Recipient Web. The `display_recipient_web` flag is the operational migration switch. New feature development should not occur on this application; only compliance patching and migration enablement.

## Migration Blockers
1. **Program migration completeness**: each affiliate/program must be individually assessed and migrated to Gen-3; until all programs are migrated, OnePlatform must remain operational.
2. **KYC integration**: if Gen-3 does not yet support all KYC flows, programs requiring KYC cannot be migrated.
3. **Cambridge IEFT integration**: global deposit/FX transfer feature must be replicated in Gen-3 before those programs can migrate.
4. **Spin/game experience**: claimable payment game flow must be available in Gen-3.
5. **Biocatch integration**: behavioral analytics must be re-integrated in Gen-3 stack.
6. **SSO / Express Login**: external SSO partners must be re-configured against Gen-3 endpoints.
7. **Tech debt volume**: ~58 SNAPSHOT versions indicates active maintenance load; migration team must absorb ongoing fixes.
