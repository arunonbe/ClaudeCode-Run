# clientzone-help_SVC — Enterprise Architect View

## Platform Generation (Gen-1/Gen-2/Gen-3)

**Assessment: Gen-1**

Evidence:
- **Struts 1.2.8** MVC framework (end-of-life 2013) with XDoclet-based configuration. Struts 1.x is a hallmark of Gen-1 Ecount/Citi Prepaid applications.
- **Spring 2.0.8** (2008) — pre-annotations, XML-only Bean wiring. All Spring configuration is in DTD-based Spring 1.x/2.x XML format (`spring-beans.dtd`, not the modern XSD namespace).
- **Servlet 2.4** descriptor (`web.xml` declares `web-app_2_4.xsd`), consistent with J2EE 1.4 era (2003).
- **JSP with scriptlets** throughout (`global_error.jsp`, `help_content.jsp`) — no separation of concerns, no template engine (Thymeleaf, FreeMarker).
- **Tiles 1.1** (`tiles-config_1_1.dtd`) — superseded by Tiles 2/3 and then dropped entirely in modern stacks.
- **Adobe Flash (SWF)** as the primary media delivery format — end-of-life December 2020, last widely deployed in the 2008–2015 era.
- **XDoclet** as build-time code generation for Struts config (the `src/main/xdoclet/web/` fragments are XDoclet merge-point files used by xdoclet-struts tag).
- **Camtasia Studio 6** content (production dates circa 2010) committed directly into the WAR.
- **Version 1.0.4-SNAPSHOT** with no evidence of a Gen-2 or Gen-3 rewrite in progress.
- **SCM** pointing to a Subversion repository (`ecsvn.office.ecount.com`) — indicating the project predates the organisation's Git migration.
- `com.citi.prepaid.web` groupId and `Citibank, N.A.` branding in `footer.jsp` — the application has not been rebranded post-Wirecard/Onbe acquisition.

## Business Domain

**Domain**: Client Self-Service / Operator Training & Support

Sub-domain: Help & Documentation delivery for the **ClientZone portal** — Onbe's B2B prepaid program management interface used by corporate clients to:
- Issue prepaid cards (QuickPay, New Cardholder, Instant Issue, Virtual Instant Issue)
- Manage cardholders and card inventories
- Perform payment reversals and prechecks
- Upload bulk files
- Manage users and profile settings

This service sits within the **ClientZone bounded context**, acting as a satellite help/documentation service. It is a UI concern, not a payments processing concern.

## Role in Platform

`clientzone-help_SVC` plays a **supporting UI role** within the ClientZone platform:

- **Not on the payments processing path**: It has no access to the card issuance, payment, or authorisation systems. It purely serves static guidance content.
- **Satellite to ClientZone portal**: It is designed to be embedded within or linked from the main ClientZone portal application. The `help_links.xsl` and `help_content.jsp` both assume they are rendered inside a ClientZone page frame (they use the parent application's session context and request attributes such as `ClientZoneHelpConstants.RequestVariable.CONTENT_LOCATION`).
- **Single-affiliate deployment**: `affiliateContext.xml` hard-codes affiliate ID `100000` (`config.clientZone`). This service is not multi-tenant and cannot serve different help content sets for different client affiliates without code/configuration changes.
- **Contextual help provider**: Its role is to offload the help content delivery from the main ClientZone WAR into a separately deployable and independently scalable unit. However, given the Flash EOL, it is currently non-functional as a video help provider.

## Dependencies

**Upstream (this service depends on):**
| Dependency | Type | Evidence |
|---|---|---|
| `com.citi.prepaid.web:webapp-parent:10.0.0` | Build-time parent POM | pom.xml line 4-8 |
| `com.ecount.web.tags:eccm:1.1.0` | Runtime JAR (ECCM tag library + initializer) | pom.xml line 31-35; web.xml line 14 |
| `com.citi.prepaid.spring-dbctx:spring-dbctx-container:1.0.6` | Runtime JAR (Spring DB context container) | pom.xml line 37-41 |
| `com.citi.prepaid.springutils:springutils-generic:1.0.9` | Runtime JAR | pom.xml line 43-47 |
| `org.springframework:spring:2.0.8` | Runtime JAR (Spring framework) | pom.xml line 49-59 |
| `struts:struts-el:1.2.8` | Runtime JAR (Struts MVC) | pom.xml line 68-72 |
| CMS Service (HTTP) | Runtime remote service | cmsContext.xml lines 4-13 |
| CBASE_HOME_URL filesystem | Runtime config files | applicationContext.xml lines 9-10 |
| ClientZone portal session | Runtime session context | global_error.jsp lines 22-23; help_content.jsp line 1 |
| Nexus (d-na-stk01.nam.wirecard.sys) | Build-time artifact repository | settings.xml line 13 |
| GitHub Packages (onbe/onbe_maven_releases) | Build-time artifact repository | settings.xml line 111 |

**Downstream (services that depend on this):**
- The main ClientZone portal application, which embeds help content via iframe or AJAX calls to `/clientzone/login/help.do` (referenced in `help_links.xsl` line 27).
- No other known downstream consumers based on repository content.

## Integration Patterns

1. **Servlet include / AJAX request from parent portal**: The XSL template (`help_links.xsl`) generates JavaScript `getContent('lhsContent', '/clientzone/login/help.do', '?cType=swf&topic={$fun}')` calls (line 27), indicating AJAX (likely XMLHttpRequest) is used to load help content into a `lhsContent` div element within the ClientZone portal UI. This is a **client-side AJAX pull** pattern.

2. **Spring XML IoC**: Application is wired via three Spring XML context files loaded at startup: `applicationContext.xml`, `affiliateContext.xml`, `cmsContext.xml` (no `web.xml` `<context-param>` is visible; context loading is likely triggered by `EccmSimpleInitializer` listener or the Struts `DelegatingTilesRequestProcessor`).

3. **PropertyPlaceholderConfigurer**: Environment-specific configuration is injected via filesystem-resident `.properties` files at runtime — a Gen-1 pattern for externalising environment config without a config service.

4. **Struts 1.x + Tiles**: Request dispatching uses `DelegatingTilesRequestProcessor` (an integration class that bridges Spring IoC with Struts Tiles) — a pattern from the early 2000s.

5. **XSL Transform for navigation**: The `help_links.xsl` is applied client-side (the `.xsl` file contains `<?xml-stylesheet type="text/xsl" ...?>` which causes browser-side XSLT to render the navigation). This relies on browser-side XSLT support — increasingly unreliable in modern browsers and a Gen-1 pattern.

6. **CMS integration**: A `CMSService` bean connects to an external CMS for content, following an HTTP service call pattern. Details of request/response format (REST vs SOAP vs proprietary) are not visible from this repository alone.

## Strategic Status

**Status: Legacy / Deprecated (effectively non-functional)**

- The core delivery mechanism (Adobe Flash SWF) has been dead since December 2020. The application cannot deliver its primary content type to any modern browser.
- The framework stack (Struts 1.x, Spring 2.x, Servlet 2.4) carries critical CVEs and no vendor support.
- Content dates to 2010; the UI it documents has likely changed significantly.
- There is no Gen-2 or Gen-3 replacement evident in this repository.
- The application has had no source code changes (zero Java source files); maintenance has been limited to infrastructure concerns (CodeQL, Dependabot).
- The continued presence of this service in the Onbe GitHub organisation suggests it may still be deployed, but it provides no effective user value in its current state.

**Recommended strategic disposition**: Decommission or replace with a modern static documentation site (e.g., MkDocs, Confluence, or an embedded help system within the current ClientZone UI). All Flash-based video content should be re-recorded as MP4 and served through a CDN or modern video player.

## Migration Blockers

1. **Flash (SWF) content**: All help videos and players are in SWF format. New content must be re-produced in MP4/WebM format with a modern HTML5 video player before any re-deployment can deliver the same functionality.
2. **No Java source code**: There is no in-house application logic to migrate — the WAR is a configuration wrapper. However, the external class dependencies (`ClientZoneHelpConstants`, `EccmSimpleInitializer`, `CMSService`) are in unpublished internal JARs (`eccm:1.1.0`, `xplatform:2.5.45`) whose source is not in this repository. Migration requires source access to those libraries or replacement.
3. **External classpath dependencies for JSP compilation**: `help_content.jsp` imports `com.cbase.business.clientZone.ClientZoneHelpConstants` (line 1) and `global_error.jsp` imports `com.cbase.core.RequestContext` and `com.ecount.one.value.IApplication` (lines 1-2). These classes must be available on the classpath for JSP compilation. They come from `spring-dbctx-container` or `springutils-generic`; finding and replacing them is required for any framework migration.
4. **Parent POM coupling**: The build entirely depends on `webapp-parent:10.0.0`. Any migration must either extend the parent POM or break the parent dependency and establish an independent build.
5. **Affiliate model**: The single-affiliate hardcoding (`affiliateId=100000`) in `affiliateContext.xml` is a design constraint. A rewritten service would need to support multi-tenant affiliate routing if other ClientZone clients are to receive tailored help content.
6. **CMS coupling**: The CMS integration (`CMSService` bean) may be providing content beyond what is visible in the static `helpContent/` tree. The CMS service endpoint and API contract must be understood before decommissioning.
7. **Session context coupling**: The application reads `ClientZoneHelpConstants.RequestVariable.CONTENT_LOCATION` and `IApplication.SESSION_KEY_REQUEST_CONTEXT` from the parent application's request/session. A migrated service would need to establish its own context-passing mechanism or be absorbed into the parent portal.
