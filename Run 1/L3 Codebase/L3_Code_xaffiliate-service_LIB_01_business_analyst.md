# Business Analyst View — xaffiliate-service_LIB

## Business Purpose

xaffiliate-service_LIB (`com.ecount.one.service.affiliate:xaffiliate-service:4.0.1`, Java 21) is the Gen-1/Gen-2 affiliate management service library for the OnePlatform web application. An "affiliate" in the eCount/OnePlatform context is a program configuration unit — essentially a client program (e.g., a specific prepaid card program for a brand like T-Mobile, Sprint, or an insurance company) along with its associated branding (skins), supported languages/locales, content copy (text strings, error messages), display settings, and partner contact details.

This library is the authoritative data source for how each client program's portal (OnePlatform cardholder web) looks and behaves — it governs branding, localization, and CSA screen configuration per affiliate/program.

## Capabilities Provided

- **Affiliate lookup**: retrieve affiliate by virtual directory name, program ID, or field value; lookup by affiliate ID
- **Affiliate creation/configuration**: create new affiliates and configure them with program IDs, domain, presentation, start/end dates
- **Locale/language management**: assign supported languages (locales) to affiliates; set default locale; retrieve all locales configured for an affiliate
- **Skin/theme management**: retrieve available display skins (visual themes); assign default and override skins to affiliates per locale; add new skins
- **Locale copy management**: CRUD operations on locale-specific content copy (UI text strings, error messages, messages) organized by skin and copy type (copy, errors, messages); supports multi-level copy inheritance (affiliate → default → root)
- **Access level configuration**: retrieve program-level feature flags controlling which features are accessible at each user access level (via `cbaseapp` database integration)
- **B2C CSA detail screen**: manage CSA (Customer Service Agent) detail screen configuration for B2C programs
- **Partner detail management**: store and retrieve partner business details and contact information for each program
- **Cardholder zone (CZ) screen driver flags**: via `B2cCsaDetailscreen` operations — configures which fields are shown on the CZ screens for CSA agents

## Client/Cardholder Impact

This library directly determines what cardholders see when they log into the OnePlatform cardholder portal:
- Wrong or missing locale copy means cardholder-facing error messages, labels, and instructions may display incorrectly
- Wrong skin assignment changes the visual branding the cardholder sees
- Incorrect CSA screen configuration affects what customer service agents see when managing cardholder accounts
- Incorrect access level configuration could expose features to users who should not have access (security/compliance concern)

## Business Rules Found in Code

- Copy inheritance is multi-level: affiliate copy → affiliate default skin copy → root/default copy; lower levels override higher levels (`mergeCopyLists()` in `AffiliateServiceImpl`)
- A locale must be assigned to an affiliate before locale-specific copy can be added
- The default locale is flagged with `isLocaleDefault='1'`; exactly one locale per affiliate should be the default
- The `ROOT_SKIN_ID` (value not shown but referenced) acts as the ultimate fallback; affiliates with only root skin inherit all copy from the root skin
- Skin inheritance supports two levels: affiliate skin → affiliate's default skin → root skin (three-tier hierarchy)
- `lookupAffiliate()` applies a heuristic when multiple affiliates share a virtual directory name: prefers affiliates with an ID longer than 4 characters (OnePlatform-style affiliate IDs) — this is a fragile business rule encoded as magic number comparison (`strAffiliateId.length() > 4`)
- Copy key uniqueness is enforced by the combination of `(copyTag, copyType, skinId, localeId)` — the four-dimensional namespace for all locale copy

## Regulatory Obligations

- **GLBA/CCPA/GDPR**: Locale copy strings may include privacy disclosures, cardholder rights notices, and data collection statements that must be program-specific and legally accurate. Incorrect copy management could result in cardholders receiving incorrect privacy disclosures.
- **PCI DSS**: Access level configuration (`findAccessLevelFeatureMap()`) controls which CSA agent functions are accessible. Misconfiguration could violate PCI DSS Requirement 7 (least-privilege access) by granting agents access to cardholder data or functions beyond their role.
- **UDAAP**: Incorrect or missing locale copy (e.g., fee disclosures, terms and conditions) could constitute a deceptive practice.

## Key Business Risks Found in Code

- **Magic number in affiliate lookup** (`AffiliateServiceImpl.java:1238`): `if (strAffiliateId.length() > 4)` — this heuristic assumes OnePlatform affiliate IDs are always longer than 4 characters. If a valid OP affiliate ID is 4 characters or shorter, this rule silently returns 0 (no affiliate found), breaking all portal functionality for that program.
- **Exception swallowing with `printStackTrace()`**: Multiple methods catch `Exception`, call `e.printStackTrace()`, then throw a `RuntimeException`. Stack traces to System.err are not captured by the logging framework; errors would be missed in production log monitoring.
- **Transactional annotation on service class**: `@Transactional("affiliateTransactionManager")` on the entire class means all methods share the same transaction manager; any database error in one method could roll back unrelated operations.
- **`AffiliateServiceImplOld.java`**: An old implementation file is still present in the repository. Dead code representing a previous design increases maintenance confusion and code analysis surface.
- **No input validation on `languageCountryCode`**: While `getContext()` validates the 5-character format, `getLocaleId()` and other internal callers do not consistently validate — a malformed locale code could produce incorrect SQL results.
