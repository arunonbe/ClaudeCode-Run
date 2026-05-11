# Enterprise Architect View — CONFIG_qa

## Platform Generation
**Generation 2 (Gen-2)** — Same legacy Windows/Tomcat stack as DEV and PROD. QA mirrors production infrastructure at reduced scale, except for a larger fleet than DEV (12 app servers). The QA environment is the final verification gate before UAT and PROD deployments.

## Business Domain Coverage
Full platform coverage — identical to PROD in capability set. QA configures all services needed for full regression testing: card management, cardholder portals, payments, batch, and notification services.

## Role in Platform
QA is the **pre-production integration testing environment**. It serves:
- Functional regression testing of new releases
- Integration testing with external systems (Cambridge FX beta, KYC QA, BioCatch test, IBM MQ UAT)
- Performance testing at production-representative fleet scale
- Final sign-off environment before UAT promotion

QA is the only environment with an automated GitLab CI pipeline for config deployment (via `.gitlab-ci.yml`), making it slightly more mature than DEV from a DevOps perspective.

## Dependencies
| Dependency | Notes |
|------------|-------|
| `q-db01.nam.wirecard.sys:2431` | QA SQL Server — different port from DEV (2432 vs 2232) |
| `ppnaut.nam.wirecard.sys:8080` | QA Director dispatch server |
| `dflnxswmqu.nam.wirecard.sys:1414` | QA IBM MQ (different from DEV's MQ server) |
| `login-qa.northlane.com` | QA-branded CMS URL (HTTPS, unlike DEV's HTTP) |
| BioCatch (`api-osiristest.us.v2.customers.biocatch.com`) | QA fraud scoring — not in DEV |
| KYC Portal (Azure QA) | Shared with DEV — same endpoint |
| Cambridge FX beta | Shared with DEV — same endpoint |
| SAP Mobile Services (SMS, UAT endpoint) | Same endpoint as UAT |
| ci-templates (SQ-4057 branch) | GitLab CI — config deployment automation |

## Integration Patterns
- Same as DEV: externalized properties, JDBC, IBM MQ JMS, XML-RPC, REST/HTTP
- Additionally: BioCatch fraud API integration active in QA
- GitLab CI automated config deployment (unique to QA among the lower environments)

## Strategic Status
**Active QA environment.** QA is the most mature non-production environment from a DevOps perspective due to the automated config deployment pipeline. However, it still uses the same Gen-2 legacy patterns as DEV.

The presence of BioCatch fraud scoring in QA (but not DEV) suggests QA is used for fraud feature testing as well as functional testing.

## Migration Blockers
Same as DEV plus:
- BioCatch integration — requires cloud-native equivalent configuration when migrating
- Larger server fleet (12 servers) — migration effort proportionally greater
- Config deployment pipeline references a feature branch of ci-templates — production-readiness of this automation needs validation before Gen-3 migration
- Multiple datasources absent from DEV (greatplains, webcertomaha) suggest QA-specific external dependencies that need migration planning
