# clientzone-help_SVC — Data Architect View

## Data Stores

This application has **no database of its own**. It is a pure content-delivery web application. Data is sourced from:

1. **Filesystem (static content)**: The primary data store is the WAR's own `helpContent/` tree deployed to the servlet container. Content is pre-compiled into the WAR as static binary and text files. No runtime writes occur to this store.

2. **External CMS service** (`cmsContext.xml`): A `com.ecount.cms.CMSService` bean (line 4) is wired to an external CMS backend via HTTP. Configuration properties:
   - `${cms.service.url}` — base URL of CMS service
   - `${cms.service.context}` — URL context path of CMS service
   - `${cms.content.context}` — content delivery context
   - `${cms.name}` — CMS instance name
   - `maxHits=30` — maximum results per query
   - `defaultId="id"` — default identifier field
   This CMS dependency is wired but it is not clear from the code whether it is actively used by this help WAR at runtime; no JSP or action references `cmsService` directly.

3. **External application configuration** (`applicationContext.xml`, lines 8-11):
   - `${CBASE_HOME_URL}/config/cz/clientzone.properties` — primary ClientZone runtime config
   - `${CBASE_HOME_URL}/config/xContent/applicationContext-xContent.properties` — xContent config
   - `classpath*:com/ecount/clientzone/clientzone.default.properties` — default fallback

4. **HTTP Session** (runtime): The only session data this application reads/writes is `affiliate.name` (set in `global_error.jsp`, line 9; read on line 16) and `IApplication.SESSION_KEY_REQUEST_CONTEXT`. Both are set by the parent ClientZone application before this help WAR is invoked.

## Schema & Tables

There are no database tables, SQL DDL, ORM mappings, or JPA/Hibernate entities in this repository. The data model is entirely file-based:

**Filesystem content schema (logical):**
```
helpContent/
  region/
    {region}/          -- "us" or "emea"
      {locale}/        -- "en_US", "es_ES", "pt_BR", "en_IE"
        contentmapping.properties   -- topic-to-label mapping
        {topicFolder}/              -- e.g., "createquickpay"
          *.swf                     -- Flash player (primary delivery)
          *.mp4                     -- Video source
          *.pdf                     -- PDF user guide
          *.html                    -- HTML wrapper page
          FirstFrame.png            -- Thumbnail image
          swfobject.js              -- Flash embed helper
          ProductionInfo.xml        -- Camtasia Studio production metadata
```

**contentmapping.properties key schema:**
- `{module}.heading` = display label for category
- `{module}.{N}.{topicFolder}` = sub-topic at position N, pointing to a filesystem subfolder

**help_links.xml navigation schema** (`src/main/webapp/WEB-INF/pages/resource/help_links.xml`):
```xml
<helpContents>
  <helpContent>
    <mainLink helpTopic="{topicCode}">{Label}</mainLink>
    <subLink>{SubLabel}</subLink>
  </helpContent>
</helpContents>
```
This XML structure is the data backing the left-hand navigation sidebar. It is static and hardcoded (4 main links: Overview, QuickPay, New Cardholder, Precheck).

## Sensitive Data Handling

The application itself does not handle, store, or transmit cardholder data, PII, or authentication credentials at the application level. However:

1. **Credentials in source control** (`.mvn/wrapper/settings.xml`):
   - Server `wirecard-mavenproxy-repository`: username `acmng`, password `acmng` (line 35-38)
   - Server `nexus-qa`: username `deployment`, password `dwil15?` (lines 39-42)
   - Server `ecount.release`: username `deployment`, password `d3v0nly` (lines 43-46)
   - Server `ecount.snapshot`: username `deployment`, password `d3v0nly` (lines 47-50)
   These are plaintext passwords committed to the Git repository.

2. **Developer workstation path leak** (`ProductionInfo.xml`):
   - `<VideoFilenameWithPath>C:\Project Documents\Shweta\CZ\Camtasia Test Recordings\...</VideoFilenameWithPath>` (line 4)
   - `<m_cf_strTempDir>C:\DOCUME~1\SRAVIN~1\LOCALS~1\Temp\</m_cf_strTempDir>` (line 191)
   - `<OutputBasePath>C:\Project Documents\Shweta\...` (line 183)
   Developer full names (Shweta, SRAVIN~1 = likely "sravinder" or similar) and internal file paths from a developer workstation are embedded in committed production content.

3. **Stack trace disclosure** (`global_error.jsp`, lines 43-54): The error page unconditionally renders full Java exception stack traces (`eCountException.printStackTrace`) into the HTTP response. This discloses internal package names, class structure, and library versions to any browser-facing user.

4. **Server metadata disclosure** (`global_error.jsp`, lines 33-36): `SERVER_NAME`, `SERVER_PORT`, `REMOTE_HOST` are unconditionally written to the error page HTML.

## Encryption & Protection

- **No TLS configuration** in this repository. TLS termination is assumed to be handled at the load balancer or Tomcat connector level in the deployment infrastructure.
- **No encryption at rest**: All content files (SWF, MP4, PDF) are stored as plaintext binary in the WAR with no encryption.
- **No token or session encryption** configured within this WAR; session management is delegated to the parent application container.
- **Flash (SWF) files**: Adobe Flash has documented security vulnerabilities and is unmaintained. Serving SWF files exposes any user that has a Flash plugin enabled to known exploit vectors.
- **swfobject.js**: A third-party JavaScript library for Flash embed detection is bundled in 24 copies across topic folders. No integrity hash (SRI) is applied. The version is not identifiable from the filename alone, but its presence alongside end-of-life SWF content is a supply chain risk.

## Data Flow

```
User Browser
    |
    | HTTP GET /ClientZoneHelp/getHelp.do?cType=swf&topic=createquickpay
    v
Servlet Container (Tomcat)
    |
    | Struts 1.2 ActionServlet → DelegatingTilesRequestProcessor
    | Spring 2.0.8 ApplicationContext loaded at startup
    v
help_content.jsp
    |
    | reads request attribute: ClientZoneHelpConstants.RequestVariable.CONTENT_LOCATION
    | (value set by upstream ClientZone action, not within this WAR)
    v
<embed src="{cPath}"> → Browser fetches SWF/PDF from WAR static content
    |
    v
helpContent/region/{region}/{locale}/{topicFolder}/*.swf  (or .pdf)
```

CMS data flow (wired but activation uncertain):
```
CMSService bean → HTTP → External CMS service ({cms.service.url})
    → returns content items (maxHits=30)
    → surfaced via directory/cmsContext beans
```

Configuration data flow:
```
Startup → PropertyPlaceholderConfigurer reads:
  1. ${CBASE_HOME_URL}/config/cz/clientzone.properties  (file system, external)
  2. ${CBASE_HOME_URL}/config/xContent/applicationContext-xContent.properties
  3. classpath:com/ecount/clientzone/clientzone.default.properties (in WAR)
→ Injects into beans: internationalType, helpApplicationContext, cmsService, etc.
```

## Data Quality & Retention

- **Content age**: The oldest confirmed content production date is March 2010 (NCH `ProductionInfo.xml`). At least 14 years of UI drift between help content and actual ClientZone UI is plausible.
- **No data versioning**: There is no content versioning mechanism. Content updates require a full WAR redeployment.
- **No content validation**: The `contentmapping.properties` references topic folder names that must exist on the filesystem; there is no startup validation that referenced folders actually exist in the deployed WAR.
- **Duplicate swfobject.js**: The same `swfobject.js` file is duplicated 24 times (12 US topics × 2 + 12 EMEA topics × 2 — one per topic folder per region). No shared static resource path is used.
- **Retention policy**: Not defined within this application. As a static content WAR, retention is effectively tied to WAR lifecycle.

## Compliance Gaps

1. **Plaintext credentials in SCM** (`.mvn/wrapper/settings.xml`): Violates Onbe/PCI DSS requirement 8 (protect individual credentials). Three distinct service account passwords are committed in cleartext.
2. **Developer PII in committed content** (`ProductionInfo.xml`): Partial usernames and file paths from developer workstations are stored in the repository and shipped in the WAR artifact. This may constitute GDPR Article 5 minimisation and storage limitation concern.
3. **No data classification label**: The repository contains no data classification metadata indicating sensitivity level of shipped content.
4. **Flash SWF at end of life**: Serving SWF to users presents an unpatched vulnerability surface; PCI DSS 6.3.3 (keep software protected from known vulnerabilities) is not met for any deployment that serves this content.
5. **Error page information leakage**: `global_error.jsp` violates PCI DSS 6.2 and OWASP best practices by leaking stack traces and infrastructure metadata to end users.
