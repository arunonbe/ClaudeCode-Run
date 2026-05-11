# Business Analyst View — xplatform_LIB

## Business Purpose
xPlatform (artifact: `xplatform`) is the core business logic library for the eCount prepaid card platform. It provides the shared domain model, data access layer, affiliate/program management, member lifecycle management, and cross-cutting services consumed by virtually every downstream service and application in the eCount ecosystem. It is the authoritative Gen-1 platform core for Onbe's prepaid card operations.

## Capabilities
- **Affiliate and program management:** Load, cache, and retrieve affiliate (client/partner) configuration objects including metadata and data values (`AffiliateFactory`, `Affiliate`, `AffiliateMetaDataFactory`)
- **Member / cardholder lifecycle:** Member inquiry, registration, device history, EMember/ECard management (`IMemberManager`, `MemberManagerImpl`, `EMemberInquiry`)
- **Account management:** Account summary, fee sources, account history view, device manager
- **Job / payment processing:** Ticket management, job account mapping, pre-check definitions
- **Notification:** Email notification services
- **Login / session support:** `LoginManager` integration test present
- **Cross-border transfer integration:** Dependency on `cbtsclient` (Wirecard/CBTS client library)
- **XML serialisation / deserialisation:** XStream integration for object-to-XML mapping
- **Hibernate ORM:** Hibernate Core used for relational data access
- **Azure AD integration:** `msal4j` dependency present — Microsoft MSAL for identity/token acquisition
- **Config file support:** Relies on `xplatformlibrary` for `ConfigurationFile`/`ConfigDB` infrastructure

## Key Entities
| Entity | Package | Description |
|---|---|---|
| Affiliate | `com.cbase.business.affiliate` | Client/partner configuration and metadata |
| Member | `com.cbase.business.core` | Cardholder account record |
| ECard / Device | `com.cbase.business.ecount.device` | Physical or virtual prepaid card |
| AccountSummary | `com.cbase.business.accountsummary` | Aggregated account balance and fee data |
| Ticket | `com.cbase.business.ticket` | CSA/support ticket entity |
| Notification | `com.cbase.business.notification` | Email notification value objects |
| EManageManager | `com.cbase.business.core.impl` | Orchestration manager for member/account operations |
| JobAccountMap | `com.cbase.business.core.value` | Maps job records to account identifiers |

## Business Rules
- Affiliate objects are cached via `CacheableObjectFactoryImpl` — live affiliate config is not re-fetched on every request
- Agent context (`agent` string) is propagated throughout all business operations to distinguish client environments
- Cross-border transfer operations depend on the CBTS client (`cbtsclient 2.1.5`) — a Wirecard-heritage dependency
- Member searches support wildcard (`%`) queries with role-based restrictions enforced at the service layer
- Program ID encodes affiliate ID in positions 4–7 (8-character string) — used for affiliate resolution in SSO and search

## Process Flows
1. Downstream service (e.g., xsso_SVC, xsearch) obtains an `Affiliate` via `AffiliateFactory.getAffiliate(affiliateId, context)`
2. Business operations (member search, account inquiry) are executed through manager classes (`MemberManagerImpl`, `EManageManagerImpl`)
3. Data access is via Hibernate ORM or Spring JDBC depending on the entity type
4. Results are serialised/deserialised using XStream for inter-service communication

## Compliance Relevance
- Contains cardholder data access patterns — in scope for PCI DSS cardholder data environment (CDE)
- `secureprofileaddenda` fields (SSN, DOB, DL) flow through this layer for member profile operations
- CBTS cross-border transfer integration is subject to OFAC/sanctions screening requirements
- Azure AD (`msal4j`) integration may relate to operator authentication — relevant to access control requirements under PCI DSS Req 8

## Risks
- Load-bearing library: a breaking change here propagates to all downstream consumers
- CBTS client (`cbtsclient`) retains Wirecard branding — vendor relationship and support status unclear post-acquisition
- `msal4j` Azure AD dependency in a Gen-1 library creates a hybrid architecture concern
- No evidence of field-level encryption for sensitive data within this library
