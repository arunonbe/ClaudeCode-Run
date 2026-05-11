# clientzone-help_SVC — Business Analyst View

## Business Purpose

`clientzone-help_SVC` is a standalone Java web application (WAR) that delivers contextual help content to users of the ClientZone portal — Onbe's (formerly ecount/Citi Prepaid) B2B client-facing administration interface. Its sole purpose is to serve structured help topics (video tutorials in SWF/MP4, PDF user guides, and HTML pages) to ClientZone operators and administrators who need guidance on prepaid card program management tasks.

The application was originally branded as **"Ecount ClientZone Help"** (display name in `web.xml`, line 7) and carries copyright to "Citibank, N.A." in `footer.jsp` (line 12), establishing its legacy origin from the Citi Prepaid era. The artifact ID is `ClientZoneHelp`, version `1.0.4-SNAPSHOT` (pom.xml, line 13).

## Business Capabilities

The application provides the following help capabilities, each mapped by region and locale:

| Capability | Content Folder | Regions |
|---|---|---|
| ClientZone Introduction / Dashboard Overview | `czintroduction`, `dashboard` | US (en_US), EMEA (en_IE) |
| QuickPay (rapid card-load disbursement) | `createquickpay` | US, EMEA |
| New Cardholder creation | `createnewcardholder` | US, EMEA |
| Instant Issue card issuance | `whatisinstantissue` | US, EMEA |
| Virtual Instant Issue (vCard) issuance | `whatisvinstantissue` | US, EMEA |
| Payment Reversal | `whatispaymentreversal` | US, EMEA |
| Precheck / Pre-authorisation assignment | `whatisprecheck` | US, EMEA |
| File Upload (bulk card/order loads) | `uploadafile` | US, EMEA |
| My Profile management | `myprofileoverview` | US, EMEA |
| Managing Users (administration) | `managingusers` | US, EMEA |
| Inventory Management | `managinginventory` | US, EMEA |
| Reports Overview | referenced in contentmapping but marked `<NOWEB>` — PDF/web not available | US only |
| Approving Orders | referenced but marked `<NOWEB>` | US, EMEA |

Content type flags in `contentmapping.properties`:
- `<NOWEB>` — web (SWF/video) version not available; PDF only, or not yet produced
- `<NOMEB>` / `<NOPDF>` — noted in comment headers as planned flags (not used in code as-of this snapshot)

Multi-locale support is delivered through three locale-specific `contentmapping.properties` files under `helpContent/region/`:
- `us/en_US/contentmapping.properties` — English (US)
- `us/es_ES/contentmapping.properties` — Spanish (US)
- `us/pt_BR/contentmapping.properties` — Portuguese Brazilian (US)
- `emea/en_IE/contentmapping.properties` — English (Ireland / EMEA)

Note: The Spanish (es_ES) and Portuguese (pt_BR) `contentmapping.properties` files mark all web content as `<NOWEB>`, meaning non-English US locale users receive PDF-only or no content.

## Business Entities

The application is primarily a content-delivery layer. Its logical entities are:

- **Help Topic**: a named subject area (e.g., `createquickpay`, `createnewcardholder`) with a heading key and one or more sub-topics. Defined in `contentmapping.properties` for each locale.
- **Help Content Item**: a set of media files per topic folder — `.mp4` video, `.swf` Flash player, `.pdf` user guide, `.html` landing page, `FirstFrame.png` thumbnail. Produced by Camtasia Studio 6 (evidenced by `ProductionInfo.xml` metadata).
- **Affiliate / Client**: represented in `affiliateContext.xml` as `affiliateId=100000`, `affiliateName=clientZone2`, with classification `cbaseapp_jdbc`. This is a hard-coded single-affiliate deployment.
- **Region**: US or EMEA, controlling which content set is presented to the user.
- **Locale**: language variant within a region (en_US, es_ES, pt_BR for US; en_IE for EMEA).
- **Help Links Navigation**: structured in `help_links.xml` (XML) and transformed for sidebar display via `help_links.xsl` (XSLT). Four top-level sections: Overview, QuickPay, New Cardholder, Precheck Assignment.

## Business Rules & Validations

1. **Content availability flag** (`<NOWEB>`): Any topic key suffixed `<NOWEB>` in `contentmapping.properties` must not be presented as a clickable web/video link. This rule governs which content types appear per locale.
2. **Content mapping key convention** (documented in each `contentmapping.properties`, lines 1-11):
   - `xxxx.heading` → main category link label
   - `xxxx.N.yyyy` → sub-link at position N, where `yyyy` = subfolder name on filesystem; the subfolder must exist for the link to function.
3. **Affiliate resolution**: `affiliateContext.xml` defines a `requestContextLookup` bean that resolves affiliate config (`config.clientZone`) from URL port (80 or 7001), context path (`${clientzone.context}`), or hard-coded affiliateId `100000`. Requests not matching a known affiliate will fail to resolve context.
4. **Session affiliate fallback**: `clientZone_header.jsp` (global_error.jsp, lines 6-18) applies a fallback affiliate name of `"fuse"` if the session attribute `affiliate.name` is unset.
5. **Error handling**: All unhandled exceptions are globally caught by `com.ecount.one.struts.exceptionHandler.GlobalExceptionHandler` and forwarded to `.error.systemFailure` tile (struts-config.xml, lines 24-28).
6. **File upload size**: Struts controller caps multipart uploads at 30 MB (`maxFileSize="30M"`, struts-config.xml line 62).
7. **i18n message lookup**: Region/locale UI labels use i18n key references (e.g., `userhelp.newui.help.link_overview`) resolved at runtime from the main ClientZone application's message bundles — not from this application's `ApplicationResources.properties`, which is a near-empty stub.

## Business Flows

**Normal help content retrieval flow:**
1. User navigates to ClientZone and clicks a help link.
2. Browser calls `/clientzone/login/help.do` with query params `?cType=swf&topic={topicKey}` or `?cType=pdf&topic={topicKey}` (visible in `help_links.xsl`, line 27 and 33).
3. The request is routed into this WAR (`/ClientZoneHelp` context, as set in `context.xml`, line 2).
4. The `index.jsp` welcome page (`index.jsp`, line 3) redirects to `getHelp.do`.
5. Struts action mapping for `getHelp.do` resolves to the help content tile.
6. `help_content.jsp` reads the `ClientZoneHelpConstants.RequestVariable.CONTENT_LOCATION` request attribute and renders an `<embed>` tag pointing to the resolved `.swf` or `.pdf` file path.
7. The sidebar is rendered via `help_links.jsp` which includes `menu.jsp`, and the navigation XML is transformed by `help_links.xsl` using XSLT to generate HTML `<dl>/<dt>/<dd>` link structures.

**CMS integration flow:**
- `cmsContext.xml` wires a `com.ecount.cms.CMSService` bean to a CMS backend (URL/context driven by `${cms.service.url}`, `${cms.service.context}`, `${cms.content.context}`, `${cms.name}` properties). The CMS service has a `maxHits=30` limit and a `defaultId="id"`. This provides an alternative or supplementary content source.

## Compliance & Regulatory Concerns

1. **Flash (SWF) content**: All help videos are delivered as Adobe Flash SWF files (`.swf` + `swfobject.js` in every topic folder). Adobe Flash was end-of-lifed in December 2020. This is a critical compliance gap — content cannot be served in any modern browser without a third-party Flash emulator, and Flash plugins are a known CVE attack surface.
2. **No access control on this WAR**: The `web.xml` defines no `<security-constraint>` or authentication mechanism. The application relies entirely on the parent ClientZone application's session context for authentication enforcement; it does not itself validate that a caller is authenticated. If deployed independently or the URL is guessable, unauthenticated access to help content is possible.
3. **Hardcoded credentials in settings.xml**: The Maven wrapper `settings.xml` contains plaintext passwords (`dwil15?`, `d3v0nly`, `acmng`) for Nexus and internal repository servers (lines 36-49). These are checked into source control.
4. **Cardholder data proximity**: Topics cover QuickPay (card loads), New Cardholder creation, Instant Issue, and Virtual Instant Issue — all PCI DSS in-scope operations. The help application itself does not process cardholder data, but its correct function supports operators performing CDE operations. Outdated or Flash-only help content increases training/operator error risk.
5. **GDPR/CCPA data minimisation**: The application does not appear to collect any personal data. However, `global_error.jsp` outputs server name, server port, remote host, stack traces, and affiliate context to the browser (lines 33-44) when an error occurs — this constitutes potential information leakage in production.
6. **Locale gaps**: Spanish and Portuguese BR locales have all web content disabled (`<NOWEB>`). This may create a disparate-access concern for non-English-speaking users of the ClientZone portal.

## Business Risks

1. **Dead content medium (Flash)**: The SWF/Flash delivery mechanism is obsolete. All video help content is effectively non-functional in production environments post-2020 without special browser plugins. End users receive no benefit from the web-video help path.
2. **Stale help content**: `ProductionInfo.xml` metadata for the `createnewcardholder` module records a production date of "24-Mar-10" (March 2010) — content is over 14 years old and likely does not reflect the current ClientZone UI.
3. **Single affiliate hardcoding**: `affiliateId=100000` is hardcoded in `affiliateContext.xml`. This means the help application is not multi-tenant; it cannot serve different content sets to different affiliate clients.
4. **No Java source code**: The `src/main/java/.ignore` file is the only file in the Java source tree. All application logic (e.g., `ClientZoneHelpConstants`, `EccmSimpleInitializer`, CMS service logic) lives in external dependencies (`eccm`, `xplatform`, `spring-dbctx-container`). This means the help application has no in-house Java business logic of its own — it is purely a configuration and static-content wrapper.
5. **Incomplete tiles definition**: `tiles-defs.xml` contains only an empty default tile definition (`<definition name="">`). All real tile definitions are expected from the parent `webapp-parent` POM at version 10.0.0, but those definitions are not visible in this repository.
