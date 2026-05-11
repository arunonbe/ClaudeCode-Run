# Enterprise Architect View — csapiws-payout_API

## Platform Generation
**Gen-1.5** — WAR-only deployment, no Spring Boot, no cloud integration. Java 8 (above V2's Java 5 but below V3's Java 21). Spring 2.5.4, Apache Axis 1.4. Deploys to Windows Tomcat via GitLab CI. Uses newer internal library versions than V2 (xPlatform 2019.1.1 vs. 2.4.5) but is architecturally aligned with Gen-1 patterns. The jsonevent-layout dependency and GitLab CI pipeline represent partial modernisation relative to V2.

## Domain
- **Domain**: Customer Service — Cardholder Payout Portal Account Inquiry and Registration Update
- **Bounded context**: CS API Payout V3 — payout-specific read/write access for portal clients
- **Business capability**: First dedicated payout portal service; adds DDA inquiry, CMS content delivery, Mexico address support

## Role in Ecosystem
```
Payout Portal Clients (Web / Mobile)
        │  SOAP (HTTPS)
        ▼
Apache Axis (/CardManagementPayoutV3/services/AccountManagement)
        │
        ├── AffiliateService (xAffiliateService 1.0.8)
        │     └── CbaseappDataSource (SQL Server / Hibernate)
        │           cs_api_payout_app_id → affiliate (access gate)
        │
        ├── EMember / EDevice → C-Base xPlatform (2019.1.1 RPC)
        │     member inquiry, card device inquiry, registration update
        │
        ├── GetPuid (JobSvcDataSource) — PUID resolution
        │
        ├── CoreDeviceDDAInquiry (EcountCoreDataSource) — DDA device lookup
        │
        ├── ICommentService (comment 1.0.3)
        │     └── CbaseappDataSource — audit comments, comment history
        │
        └── ContentManagementServiceClient
              └── CMS HTTP (northlane.com) — payout app URLs
```

## Relationship to cs-api-v3_API
`csapiws-payout_API` contains a superset of the payout operations that are also present in `cs-api-v3_API/csapi-v3-payout-ws`. The key differences:

| Aspect | csapiws-payout_API (standalone) | cs-api-v3_API/payout sub-service |
|---|---|---|
| Java version | 1.8 | 21 |
| Spring version | 2.5.4 | Spring Boot 3.5.7 |
| Deployment | Windows Tomcat (GitLab CI) | Docker (GitHub Actions) |
| xPlatform | 2019.1.1 (direct RPC) | 6.5.8 (via ecount-core-rest-api) |
| DDA encryption | None (plaintext) | JWE (jwe.secretKey) |
| Config management | Filesystem properties | Azure App Config + Key Vault |
| CI/CD | GitLab CI (northlane group) | GitHub Actions (OnbeEast) |
| Mexico support | Yes (MXStatesSet) | No (US/CA only) |
| xAffiliateService version | 1.0.8 | 4.0.1 |
| Comment service version | 1.0.3 | 3.0.1 |

The two implementations share the same payout operations in concept but diverge significantly in infrastructure. This creates a dual-maintenance burden and version drift risk.

## Version Evolution Context

### Where This Service Fits
```
cs-api-v1_API  (1.x: read-only inquiry, V1)
cs-api-v2_API  (2.x: + updateAccountProfile, V2)
cs-api-v3_API  (3.x: full CS API, V3, current platform)
      │
      └── csapi-v3-payout-war  (V3 payout, embedded in V3, Spring Boot)
csapiws-payout_API  (standalone payout WAR, pre-dates V3 consolidation, legacy)
```

`csapiws-payout_API` is the origin artifact for the payout service. When the V3 Spring Boot consolidation happened, the payout sub-service was incorporated into `cs-api-v3_API`, but this standalone repository continued to exist and be deployed separately (or as a backup). The JIRA 476 changes that commented out most operations suggest active operational management of this service as recently as the JIRA was filed.

## Dependencies
| Dependency | Version | Notes |
|---|---|---|
| Spring | 2.5.4 | EOL — same as V2 |
| Apache Axis | 1.4 | EOL — same as V2 |
| xPlatform | 2019.1.1 | Internal; calendar-versioned |
| xPlatformLibrary | 2014.3.1 | Internal; calendar-versioned — oldest library version in any payout service |
| xAffiliateService | 1.0.8 | Internal — three major versions behind V3 (4.0.1) |
| comment | 1.0.3 | Internal — two major versions behind V3 (3.0.1) |
| jTDS | 1.2 | EOL SQL Server driver |
| Log4j | 1.2.17 | EOL |
| jsonevent-layout | 1.7 | JSON log formatting — indicates structured logging pipeline |

## Patterns
- **Prototype-scoped Spring beans**: `payoutSearchAccount`, `contentHelper`, `coreDeviceManager`, `coreSpiDevice`, `PuidLookup` — all `scope="prototype"` in XML. This avoids the singleton mutation race condition present in V1's instance-level fields but creates per-request instantiation overhead.
- **Service Locator (Axis pattern)**: `AccountManagementJaxRPC` does `getBean("payoutSearchAccount")` per request.
- **JIRA-commented operations**: Operations are commented out in both the interface and XML context rather than removed — code archaeology is required to understand the full intended scope.
- **Static state set beans**: US/CA/MX state sets defined as Spring HashSet beans in XML (57 values each).

## Status
**Legacy / Partially Active**
- Active CI/CD pipeline (GitLab) targeting Windows Tomcat — this is likely deployed
- JIRA 476 changes suggest recent active management
- Only `payoutAccountInquiry` is exposed via the SOAP interface
- Java 8, Spring 2.5.4, Axis 1.4 — all EOL
- Duplicate of functionality in cs-api-v3_API payout sub-service
- No Spring Boot module; not containerised

## Migration Path to V3 Payout
1. Confirm all active clients consuming `/CardManagementPayoutV3/services/AccountManagement`
2. Map their `application_id` values — these use `cs_api_payout_app_id` attribute type (different from `cs_api_v3_app_id`)
3. Confirm V3 payout sub-service has `cs_api_payout_app_id` attribute type registered in AffiliateService
4. Evaluate DDA encryption gap: V3 uses JWE for DDA numbers; clients sending plaintext DDA to this service may need protocol update
5. Confirm Mexico address support if any clients use MX addresses (not present in V3 updateAccount)
6. Reactivate commented operations in V3 payout sub-service if needed (reissueCard, updateAccountProfile)
7. Decommission this WAR and archive the repository as read-only
