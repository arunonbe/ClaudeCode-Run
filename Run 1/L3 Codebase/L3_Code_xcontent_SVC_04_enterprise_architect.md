# xcontent_SVC — Enterprise Architect View

## Platform Generation
**Gen-1 (with Gen-2 operational wrapper)**

Core logic is Gen-1:
- Lucene 2.0.0 (released 2006) — extremely old search library
- `com.cdbaby.*` package names (CDBaby is an unrelated music company; this naming suggests the Lucene integration was adapted from an open-source example circa 2006)
- Spring 1.2.7 / 2.x era bean definitions in `CMSApplicationContext.xml` (Spring 2.x DTD namespace)
- XML-RPC service protocol
- Filesystem-based content store with in-memory RAMDirectory — no CDN, no object storage
- README still references Java 8 and SQL Server 2012

Operational wrapper is Gen-2/transitional:
- Java 21 compilation
- Log4j2 logging
- Dockerized with alpine-based JRE image
- GitHub Actions CI/CD
- Published to APIM (Azure API Management)
- `jakarta.servlet-api` dependency (Jakarta EE namespace — post Java EE 8)

The application has been containerized and CI-wrapped but its core content management logic has not been modernized.

## Business Domain
**Content Management and Delivery** — Brand asset delivery for cardholder-facing applications.

This service is the brand customization layer: it makes One Platform and mobile applications display affiliate-specific logos, fee schedules, HTML content, and imagery.

## Role in Platform
- **Content supply service**: Delivers affiliate-specific content to `oneplatform_WAPP`, mobile apps, and other cardholder-facing portals
- **Downstream of xContent-recipient**: The `xContent-recipient` repository provides the raw content files; xcontent_SVC indexes and serves them
- **Upstream of One Platform**: cardholder portals call xcontent_SVC for brand assets at runtime
- **APIM registered**: Exposed externally (or internally via APIM) at `/services/xcontentWebServices`

## Dependencies
**Inbound consumers:**
| Consumer | Interface |
|----------|-----------|
| One Platform (cardholder web) | XML-RPC |
| Mobile applications | XML-RPC |

**Outbound calls:**
| Dependency | Type |
|-----------|------|
| CMS Filesystem (volume mount) | Filesystem read (`lucene.cms.dir`) |
| SQL Server | JDBC (driver present in Tomcat lib; no app-level datasource bean visible) |

## Integration Patterns
- **XML-RPC**: Inbound content queries via `/services/xcontentWebServices`; WSDL published to APIM
- **Filesystem read**: Content loaded from mounted volume at startup; Lucene indexes in RAM
- **Spring XML application context**: Dependency injection via `CMSApplicationContext.xml`
- **Environment variable injection**: Runtime config via `CBASE_HOME_URL` environment variable and Tomcat `EnvironmentPropertySource`

## Strategic Status
**Replace / Migrate — High Priority**

- The content management mechanism (filesystem + Lucene RAMDirectory) is architecturally inadequate for a modern cloud-native platform:
  - No CDN support
  - No hot-reload of content
  - No content versioning at service layer
  - No high-availability without shared filesystem mount
- Lucene 2.0.0 is 18+ years old and unmaintained
- XML-RPC protocol limits modern client integration
- In Gen-3 architecture, this service should be replaced by:
  - Azure Blob Storage (or equivalent) for asset storage
  - A CDN (Azure CDN/Front Door) for asset delivery
  - A content management API service for structured content (locale, affiliate, document type)

## Migration Blockers
1. **Lucene 2.0.0**: No upgrade path without rewriting the indexing logic; version incompatible with modern Lucene (Lucene 2.x API is fundamentally different from Lucene 9.x)
2. **`com.cdbaby.*` classes**: Third-party (likely forked) classes for `CMSContext`, `LuceneIndex`, `CreatePropertyIndex` — source not in this repository; may not be available for migration
3. **`com.ecount.one.lucene.EcountIndex`**: Core indexing class not visible in this repository; likely in `xcontent-content_LIB`
4. **All callers use XML-RPC**: Migration to REST requires coordinated update of all consumer applications
5. **Filesystem content mount**: Assumes a shared filesystem mount in container deployment; cloud-native replacement requires Azure Blob Storage + CDN pipeline
6. **No content schema or API contract**: No documented schema for content payloads; consumers have implicit knowledge of content structure
