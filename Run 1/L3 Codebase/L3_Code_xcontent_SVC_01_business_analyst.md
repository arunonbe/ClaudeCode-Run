# xcontent_SVC — Business Analyst View

## Business Purpose
xContent Service is a content management and delivery service for Onbe's cardholder-facing web application (One Platform) and mobile applications. It serves brand-specific XML files, images, logos, PDF documents, and other digital assets to cardholder portal pages, enabling per-affiliate content customization. The service uses Apache Lucene as an in-memory full-text index to efficiently locate and serve content items by affiliate/program.

The README describes it as: "xContent Service that references all brand-specific XML files, images, logos, contents, PDF, documents for cardholder facing application (One Platform), and Mobile applications."

## Capabilities
- **Content Indexing**: Builds and maintains an in-memory Lucene index (`RAMDirectory`) of content files from a configured filesystem path
- **Content Search and Retrieval**: Serves content queries using Lucene search; content files are keyed by `cms` index name
- **XML-RPC Service Endpoint**: Exposes content operations via XML-RPC at `/services/xcontentWebServices` (per deployment config `BACKEND_SUFFIX`)
- **Content Delivery**: Provides brand/affiliate-specific assets (images, XML data, HTML) to cardholder portals

## Key Entities
| Entity | Description |
|--------|-------------|
| CMS Index (`cmsName`) | Logical name of the content management index (value: `cms`) |
| CMS Path (`cmsPath`) | Filesystem path to content source files (configurable, default: `D:/c-base/runtime/xContent/content`) |
| Lucene Index | In-memory index of content items (RAMDirectory) |
| Content Item | A file/document in the CMS filesystem, indexed for retrieval |
| Analyzer (`WhitespaceAnalyzer`) | Tokenization strategy for content search |

## Business Rules
- Content is loaded from a filesystem path (`lucene.cms.dir`) and indexed in memory at startup
- Content is organized under a named CMS context (`lucene.cms.name=cms`)
- Index parameters: max 10 concurrent searchers, min 3 searchers, searcher timeout 10s, writer timeout 30s
- Content reloading/reindexing requires service restart (no hot-reload mechanism visible)
- The service is a read-only content delivery system; no content authoring capability is present in this service

## Key Flows
1. **Startup**: Service starts → Spring context loads → `CMSApplicationContext.xml` initialises beans → `EcountIndex` reads from `lucene.cms.dir` → Lucene `RAMDirectory` populated → service ready
2. **Content Request**: Caller (One Platform / mobile) → XML-RPC request to `/services/xcontentWebServices` → Lucene query → content item returned
3. **Content Update**: Content team modifies files on the filesystem → service restart required to reload Lucene index

## Compliance Considerations
- Content files served include HTML (fee disclosures, terms) and images — these are cardholder-facing materials and must comply with UDAAP (accurate, non-deceptive disclosures)
- Fee schedule HTML files (`fees_en_US.html`) are served; accuracy is a regulatory obligation
- No PAN, CVV, or account data flows through this service (content delivery only)
- The QA certificate (`certfile_qa.crt`) is bundled in the Docker image — environment-specific cert management is a security concern

## Business Risks
- **Stale content**: No hot-reload; any content update requires a service restart, creating a window where updated fee disclosures or terms are not reflected in the cardholder portal
- **Filesystem dependency**: Content availability depends on the mounted filesystem path; if the mount is unavailable, the in-memory index is empty and no content is served
- **Single index**: All affiliate content is in a single Lucene index; large affiliate portfolios may cause memory pressure
- **README describes Java 8 prerequisites** but Dockerfile uses Java 21 (Liberica JRE) — documentation is outdated
