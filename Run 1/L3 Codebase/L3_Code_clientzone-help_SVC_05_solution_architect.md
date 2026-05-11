# clientzone-help_SVC — Solution Architect View

## Technical Architecture

`clientzone-help_SVC` is a **Java EE (J2EE 1.4) WAR** using a classic Gen-1 MVC stack. It has zero Java source code of its own — it is a pure configuration-and-content WAR.

**Stack summary:**
| Layer | Technology | Version |
|---|---|---|
| Web framework | Apache Struts | 1.2.8 (EOL 2013) |
| MVC processor | `DelegatingTilesRequestProcessor` | Spring-Struts bridge |
| Layout engine | Apache Tiles | 1.1 |
| IoC container | Spring Framework | 2.0.8 (2008) |
| Servlet spec | Servlet 2.4 / JSP 2.0 | J2EE 1.4 |
| View | JSP with scriptlets + JSTL 1.1 | |
| Tag libraries | Struts-EL, Tiles, ECCM (ecount custom), ecount-navigate, PrizeTags requesttags | |
| Navigation transform | XSLT (browser-side) | help_links.xsl |
| Media delivery | Adobe Flash SWF + swfobject.js | Flash EOL Dec 2020 |
| Logging | Log4j 1.2.14 (provided) | EOL 2015 |
| Build | Maven 3.9.1 (wrapper) | |
| Java target | Not explicitly specified (parent POM governs) | |

**Application structure:**
```
ClientZoneHelp.war
├── WEB-INF/
│   ├── web.xml                    -- Servlet 2.4 descriptor; EccmSimpleInitializer listener
│   ├── struts-config.xml          -- Struts 1.2 routing; 9 action mappings; GlobalExceptionHandler
│   ├── conf/
│   │   ├── applicationContext.xml -- Spring: PropertyPlaceholderConfigurer, internationalType bean
│   │   ├── affiliateContext.xml   -- Spring: requestContextLookup, config.clientZone (affiliateId=100000)
│   │   ├── cmsContext.xml         -- Spring: cmsService bean → external CMS HTTP endpoint
│   │   ├── tiles-defs.xml         -- Empty Tiles definition (real defs in parent)
│   │   ├── ecount-navigate.tld    -- listNavigationBar, sortTag custom tags
│   │   └── tld/requesttags.tld    -- PrizeTags: webAppContextPath, requestUri, requestUrl, parameterString
│   └── pages/
│       ├── help_content.jsp       -- Renders <embed> for SWF/PDF content
│       ├── help_links.jsp         -- Includes menu.jsp (sidebar navigation)
│       └── resource/
│           ├── help_links.xml     -- Static navigation data (4 top-level topics)
│           └── help_links.xsl     -- XSLT browser-side nav transform
├── META-INF/context.xml           -- Tomcat: /ClientZoneHelp, privileged=true
├── index.jsp                      -- Welcome page → redirects to getHelp.do
├── clientZone_header.jsp          -- JSP header: affiliate.name session logic, tag lib declarations
├── footer.jsp                     -- Footer: Citibank N.A. copyright 2009
├── global_error.jsp               -- Error page: leaks stack trace, server info, affiliate context
└── helpContent/
    └── region/{region}/{locale}/  -- Static content tree (SWF, MP4, PDF, HTML, PNG)
        └── contentmapping.properties
```

**No Java sources**: `src/main/java/.ignore` (the only file under Java src). All referenced Java classes are in external JARs:
- `com.cbase.business.clientZone.ClientZoneHelpConstants` — from an unidentified internal JAR
- `com.cbase.core.RequestContext` — from `spring-dbctx-container` or similar
- `com.ecount.one.value.IApplication` — from `springutils-generic` or `xplatform`
- `com.ecount.web.tags.eccm.model.simple.EccmSimpleInitializer` — from `eccm:1.1.0`
- `com.ecount.one.struts.exceptionHandler.GlobalExceptionHandler` — from `springutils-generic` or `xplatform`
- `com.ecount.one.struts.upload.SerializableCommonsMultipartRequestHandler` — from internal JAR
- `com.ecount.one.web.context.RequestContextLookup`, `RequestContextValue` — from `springutils-generic`
- `com.ecount.cms.CMSService` — from `xplatform:2.5.45` or a separate CMS library
- `com.ecount.one.tags.ListNavigationBar`, `ListSortHeader` — from `xplatform` or `springutils`

## API Surface

This application **exposes no REST, SOAP, or RPC API**. It is a server-rendered web UI component. Its external interface is:

**HTTP URL endpoints (Struts action mappings — `struts-config.xml`):**

| Path | Type | Forward Target |
|---|---|---|
| `/login` | GET | `.login.page` (Tiles def) |
| `/login/registerdisplay` | GET | `.login.registry.display.page` (form: `registerDisplayForm`) |
| `/add_funds/direct_deposit` | GET | `.add_funds.direct_deposit.page` |
| `/profile/category` | GET | `.profile.category.page` |
| `/profile/user` | GET | `.profile.user.page` |
| `/profile/security` | GET | `.profile.security.page` |
| `/profile/bank` | GET | `.profile.bank.page` |
| `/profile/bank_update` | GET | `.profile.bank_update.page` |
| `/profile/auto_withdrawal` | GET | `.profile.auto_withdrawal.page` |

Note: These action paths appear to be **boilerplate XDoclet merge fragments** copied from the parent platform, not genuinely implemented in this help WAR. The Tiles definitions they reference (`.login.page`, `.profile.*`) are empty in `tiles-defs.xml` (which contains only a single blank `<definition name="">`). The real tile definitions live in the parent application's classpath.

The only functional URL exposed by this WAR is:
- `GET /ClientZoneHelp/` → `index.jsp` → redirects to `getHelp.do`
- `GET /ClientZoneHelp/getHelp.do` — help content delivery (tile definition not visible in this repo)

**Cross-application call invoked by the parent portal:**
- `GET /clientzone/login/help.do?cType=swf&topic={topicCode}` (referenced in `help_links.xsl`, line 27) — the parent ClientZone WAR handles this URL; it likely forwards to a tile served from this help WAR.
- `GET /clientzone/login/help.do?cType=pdf&topic={topicCode}` — same, for PDF content.

**Global forwards (struts-config.xml, lines 31-36):**
- `error` → `.error.systemFailure`
- `device-ach-verify` → `/device/ach/verify.do`
- `device-ach-verify-failed` → `/device/ach/verify/failed.do`
- `device-ach-notfound` → `/device/ach/notfound.do`

These ACH device forwards are clearly copy-pasted infrastructure from the broader Struts platform and are not functional within a help WAR.

## Security Posture

**Rating: Critical — multiple high-severity issues**

### Authentication & Authorisation
- **No authentication configured in this WAR** (`web.xml` has no `<security-constraint>`, no `<login-config>`). The application relies on the parent ClientZone session, but there is no servlet filter, interceptor, or security constraint in this WAR to enforce it.
- If deployed at `/ClientZoneHelp` and the path is discoverable, all content is publicly accessible without credentials.

### Dependency CVEs (known at time of analysis)
| Dependency | Version | Notable CVEs / Status |
|---|---|---|
| Struts 1.x | 1.2.8 | EOL; CVE-2014-0094, CVE-2016-1181, CVE-2016-1182 (ClassLoader manipulation, input validation bypass) |
| Spring Framework | 2.0.8 | EOL; Spring4Shell (CVE-2022-22965) affects older Spring MVC with certain conditions; various Spring 2.x SpEL/DoS issues |
| Log4j | 1.2.14 | EOL; CVE-2022-23302 (JMSSink deserialization), CVE-2022-23305 (SQL injection via JDBCAppender), CVE-2022-23307 (deserialization) |
| Adobe Flash / SWF | EOL | Flash Player EOL; SWF files cannot be safely executed in modern browsers; historically associated with drive-by download exploit kits |
| swfobject.js | Unknown version | No integrity hash; bundled 24× in WAR |

### Information Leakage
- `global_error.jsp` (lines 33-54): Outputs `SERVER_NAME`, `SERVER_PORT`, `REMOTE_HOST`, `affiliate.name`, `default.affiliate.name`, `RequestContext` object, and full Java stack traces to the browser on any unhandled exception. This is a direct violation of OWASP A05 (Security Misconfiguration) and PCI DSS 6.2.
- `ProductionInfo.xml` (all topic folders): Developer workstation paths (`C:\Project Documents\Shweta\...`) and Windows usernames (`SRAVIN~1`) are embedded in the deployed WAR artifact.

### Credentials in Source Control
- `.mvn/wrapper/settings.xml` (lines 35-50): Four server blocks with plaintext passwords (`acmng`, `dwil15?`, `d3v0nly`). These credentials are committed to the Git repository and visible to anyone with repo access.

### XSLT / XSS Surface
- `help_links.xsl` (line 27) generates JavaScript inline: `onclick="getContent('lhsContent', '/clientzone/login/help.do', '?cType=swf&amp;topic={$fun}');"` — the `{$fun}` value is sourced from `mainLink/@helpTopic` in the static XML file. Since the XML is static (not user-supplied), this is not an immediate XSS vector, but the pattern is unsafe if the XML source is ever made dynamic.

### Session Attribute Handling
- `global_error.jsp` (lines 6-17): Reads a `landf` request parameter and stores it in the session (`session.setAttribute("affiliate.name", lAndf)`) without any sanitisation. This is a potential session poisoning vector: a crafted `landf` parameter can overwrite the `affiliate.name` session value.

### Privileged Tomcat Context
- `context.xml` line 2: `privileged="true"` grants this application access to Tomcat internals. A compromised WAR with privileged access can affect the entire Tomcat instance.

## Technical Debt

1. **Zero Java source code**: The application is entirely dependent on external private JARs for all runtime logic. Source code is unavailable in this repo; maintainability is severely limited.
2. **Struts 1.x / Spring 2.x stack**: 15+ year old frameworks with no upgrade path short of a full rewrite. Struts 1 does not support constructor injection, annotation configuration, or modern REST patterns.
3. **Flash-only media**: All 11 US topic folders and 11 EMEA topic folders contain SWF files. MP4 files exist but are used as source for the SWF wrapper — without the Flash player, MP4 is not surfaced to users by the current embed mechanism.
4. **XSLT browser-side navigation**: The `help_links.xsl` relies on browser-native XSLT support, which is declining. IE removed support in IE11 quirks modes; modern browsers vary in support.
5. **24× duplicate swfobject.js**: One copy per topic folder rather than a single shared static resource. Wastes WAR space and makes upgrades error-prone.
6. **Stale branding**: `footer.jsp` contains "© 2009 Citibank, N.A." — 15+ years out of date, legally incorrect post-Onbe rebranding.
7. **SVN SCM reference in pom.xml**: The `<scm>` block points to `http://ecsvn.office.ecount.com/svn/...` (lines 24-28), which is an internal server likely decommissioned. Maven Release Plugin will fail if invoked.
8. **SNAPSHOT version**: `1.0.4-SNAPSHOT` indicates this has never been formally released as a stable artifact.
9. **Empty Tiles definitions**: `tiles-defs.xml` is an empty placeholder. If the parent WAR's tile definitions are not loaded into the classpath, all Tiles-based forwards will fail with `NoSuchDefinitionException`.
10. **XDoclet merge fragments**: The `src/main/xdoclet/web/` directory contains Struts configuration fragments that duplicate what is already in `struts-config.xml`. This suggests the XDoclet build step was abandoned mid-migration, creating confusion about which file is authoritative.

## Gen-3 Migration Requirements

A Gen-3 migration would require the following to achieve parity and modernisation:

1. **Re-record all help content as MP4/WebM** using a modern screen recording tool. All SWF content must be replaced. 12 US topic videos + 12 EMEA topic videos minimum.
2. **Replace Flash embed with HTML5 video player**: Use `<video>` element or a library such as Video.js. Remove all 24 copies of `swfobject.js`.
3. **Replace static navigation XML/XSLT**: Migrate `help_links.xml` + `help_links.xsl` to a server-side rendered JSON-driven or React/Angular component, or static site generator.
4. **Replace Struts 1.x + Tiles**: Migrate to Spring MVC 6.x, Spring Boot 3.x, or a modern UI framework (React/Angular/Vue served from a CDN or Node.js server).
5. **Replace Spring 2.x XML config**: Migrate to annotation-based Spring configuration (`@Configuration`, `@Bean`) or Spring Boot auto-configuration.
6. **Remove JSP scriptlets**: Replace all `<% ... %>` scriptlet code in `global_error.jsp` and `help_content.jsp` with EL/Thymeleaf templates or controller-generated model attributes.
7. **Fix information leakage**: Remove stack trace output from error pages. Implement a proper error controller that logs internally and returns a safe generic error page to users.
8. **Introduce authentication enforcement**: Add Spring Security or equivalent filter chain to enforce that callers are authenticated before serving help content.
9. **Externalise content to a CMS or CDN**: Rather than bundling static binary content (MP4, PDF) in the WAR, serve from an authenticated CDN or the existing CMS integration (properly configured).
10. **Remove plaintext credentials**: Migrate Nexus/GitHub credentials to CI/CD secrets management (GitHub Secrets, Vault). Remove `.mvn/wrapper/settings.xml` credentials entirely.
11. **Multi-locale content parity**: Fill the Spanish (es_ES) and Portuguese BR (pt_BR) content gaps — currently all marked `<NOWEB>`.
12. **Multi-affiliate support**: If the Gen-3 ClientZone platform is multi-tenant, the help service must support tenant-specific content mapping rather than hardcoded `affiliateId=100000`.
13. **Observability**: Add structured logging (Log4j 2 or SLF4J + Logback), metrics (Micrometer), and health endpoints (`/actuator/health`).
14. **Containerisation**: Produce a `Dockerfile` and Kubernetes manifests; remove Tomcat-specific WAR deployment assumptions.
15. **Update branding**: Replace all `Citibank, N.A.`, `ecount`, and `clientzone.ecount.com` references with current Onbe branding.

## Code-Level Risks

| Risk | Location | Severity |
|---|---|---|
| Stack trace leakage to browser | `global_error.jsp` lines 43-54 | High |
| Session poisoning via unsanitised `landf` parameter | `global_error.jsp` lines 6-9 | High |
| Plaintext credentials in SCM | `.mvn/wrapper/settings.xml` lines 35-50 | Critical |
| Flash SWF served to end users | All `helpContent/**/*.swf` | Critical |
| Unauthenticated access to all WAR content | `web.xml` — no `<security-constraint>` | High |
| Privileged Tomcat context | `META-INF/context.xml` line 2 | Medium |
| Developer PII in committed artifacts | `ProductionInfo.xml` all topic folders | Medium |
| Server metadata exposed in error page | `global_error.jsp` lines 33-36 | Medium |
| Struts 1.x ClassLoader CVEs | `struts-config.xml` / runtime | Critical |
| Spring 2.x unpatched CVEs | `applicationContext.xml` / runtime | High |
| Log4j 1.x unpatched CVEs | `pom.xml` line 88 | High |
| Stale copyright/branding (legal risk) | `footer.jsp` line 12 | Low |
| SNAPSHOT artifact in potential production use | `pom.xml` line 13 | Medium |
| XDoclet merge fragments diverged from struts-config.xml | `src/main/xdoclet/web/` | Low |
| Empty Tiles definitions — runtime failure if parent not loaded | `tiles-defs.xml` | Medium |
