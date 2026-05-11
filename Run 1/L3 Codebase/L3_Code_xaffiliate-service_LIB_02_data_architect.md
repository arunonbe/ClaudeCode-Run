# Data Architect View — xaffiliate-service_LIB

## Data Models

xaffiliate-service_LIB has a rich Hibernate ORM domain model:

**Core affiliate entities**:
- `Affiliate` — root entity: `affiliateId` (Integer, PK), `affiliateVirtualDirectory` (String), `ecountProgramId` (String), description, `presentationId`, `applicationId`, `domain`, start/end dates
- `AffiliateDetail` — extended affiliate details
- `AffiliateProperty` — assembled property set for a specific affiliate + locale combination (view model)

**Locale/language entities**:
- `AffiliateLocale` — locale definitions: `localeId` (Integer, PK), `languageCode` (2-char), `countryCode` (2-char), `displayName`
- `AffiliateLocaleAffiliate` — join table mapping affiliates to locales with skins: `affiliateId`, `localeId`, `skinId`, `defaultSkinId`, `isLocaleDefault`; composite PK via `AffiliateLocaleAffiliateId`
- `AffiliateLanguage` — lightweight language descriptor (code, displayName, isDefault)

**Skin/theme entities**:
- `AffiliateLocaleSkin` — skin (visual theme) definitions: `skinId` (Integer, PK), `skinName`, `description`

**Locale copy entities** (i18n content):
- `AffiliateLocaleCopy` — individual content key-value: `copyValue`, linked to `AffiliateLocaleCopyTag`, `AffiliateLocale`, `AffiliateLocaleSkin`; composite PK via `AffiliateLocaleCopyId`
- `AffiliateLocaleCopyTag` — copy key definition: `copyTagId` (Integer, PK), `name` (the key), linked to `AffiliateLocaleCopyType`
- `AffiliateLocaleCopyType` — type categories: `id` (Integer, PK), `name` (e.g., "copy", "errors", "messages")

**Partner detail entities**:
- Partner detail and contact tables (via `ProcPartnerDetailAffiliate`, `ProcPartnerContactDetailsAffiliate` stored procedure wrappers)

**DAO/stored procedure wrappers** (numerous `Proc*` classes): All data mutations go through stored procedure wrappers (`ProcSetAffiliate`, `ProcSetAffiliateLocale`, `ProcAffiliateLocaleCopySave`, etc.); reads use a mix of Hibernate HQL queries and stored procedures.

## Sensitive Data Handled

| Data Category | Presence | Risk |
|---|---|---|
| PAN / CVV | None | Affiliate configuration data has no card data |
| Partner contact details | Present (via ProcPartnerContactDetails*) | Business PII (partner names, phone numbers, emails) |
| Program/affiliate IDs | Primary keys | Business identifiers; not sensitive |
| Domain names | In `Affiliate.domain` | Infrastructure data |
| Copy content (privacy notices) | In AffiliateLocaleCopy | May include legal text; must be program-accurate |
| Access level feature flags | Via `cbaseapp` integration | Controls which features CSA agents can access |

No cardholder PAN, CVV, or financial transaction data is stored in this library's domain. This is configuration/governance data.

## Encryption and Protection Status

- No application-level field encryption observed
- Hibernate session factory manages SQL Server connections; TLS on the database connection depends on the connection pool configuration in the consuming application
- The `cbaseapp` database access (via `IAccessLevelConfigDAO`) uses the consuming application's DataSource; credentials are not managed by this library

## Database Schemas

**Primary database**: SQL Server (`ecountcore` or `cbaseapp` — specific database determined by the consuming application's datasource configuration)

Key tables (inferred from Hibernate entity names and stored procedure names):

| Table | Key Columns | Description |
|---|---|---|
| `affiliate` | `affiliateId`, `affiliateVirtualDirectory`, `ecountProgramId` | Affiliate/program master |
| `affiliate_locale` | `localeId`, `languageCode`, `countryCode` | Supported locales |
| `affiliate_locale_affiliate` | `affiliateId`, `localeId`, `skinId`, `defaultSkinId` | Affiliate-locale-skin mapping |
| `affiliate_locale_skin` | `skinId`, `skinName` | Visual theme definitions |
| `affiliate_locale_copy` | `skinId`, `localeId`, `copyTagId`, `copyValue` | Localized content strings |
| `affiliate_locale_copy_tag` | `copyTagId`, `name`, `copyTypeId` | Content key definitions |
| `affiliate_locale_copy_type` | `id`, `name` | Content category (copy/errors/messages) |
| Partner detail/contact tables | Program-specific partner info | Via stored procedures |

**Schema migration**: `init.sql` in repository root and `docker-compose.yml` suggest a Docker-based local development environment with schema initialization.

## Data Flows

```
OnePlatform Web / CSA Application
  → xaffiliate-service_LIB (AffiliateServiceImpl)
    → Hibernate SessionFactory (SQL Server)
      → HQL queries (reads)
      → Proc* stored procedure wrappers (writes)
    → IAccessLevelConfigDAO (cbaseapp DataSource)
      → cbaseapp stored procedures
```

Content resolution for a cardholder portal request:
```
Request (affiliateVirtualDirectory) → lookupAffiliate()
  → getContext(affiliateId, locale) → AffiliateProperty (skin + locale config)
  → getAffiliateCopy(affiliateId, locale, copyType) → AffiliateLocaleCopy list
    → mergeCopyLists(rootCopy, defaultCopy, affiliateCopy) → merged content map
      → cardholder portal rendering
```

## Retention Concerns

- Affiliate configuration is operational configuration; no defined retention period for regulatory purposes
- However, historical affiliate configurations may be relevant for dispute resolution if a cardholder claims they were shown incorrect terms or fees — change history is not audited in the current design
- `docker-compose.yml` and `init.sql` for local dev should use synthetic data only; if they contain real affiliate IDs or program names, they must be replaced with synthetic examples

## PCI DSS Data Storage Compliance

- No PAN/SAD stored — not a CDE component
- **PCI DSS Requirement 7** compliance: The `findAccessLevelFeatureMap()` method controls CSA agent feature access — this is an access control mechanism. Changes to access level configuration must be subject to change management and must enforce least privilege.
- **PCI DSS Requirement 10.2.5**: Changes to the access level configuration (which features CSA agents can access) should be logged; the current design has no audit trail for these changes.
- **Hibernate and SQL injection**: All reads use parameterized HQL (`setParameter()`); no string concatenation into queries observed — injection risk is low for the HQL queries. Stored procedure calls also use parameterized input. Good posture.
