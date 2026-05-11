# xcontent-content_LIB — Business Analyst View

## Business Purpose
`xcontent-content_LIB` is the original (Gen-1) content management library for Onbe's prepaid platform. It provides the shared Lucene-based content indexing and retrieval infrastructure used by the xContent service. This library predates the current `xcontent_SVC` and represents the older version of the same content management capability. The SCM URL reveals it originated in the Wirecard cloud platform (`gitlab.wirecard-cloud.com/issuing/wdnam/prepaid`), indicating a Wirecard-era Gen-1 codebase.

## Capabilities
- **Lucene Content Index**: Initializes and manages an Apache Lucene index for CMS content files
- **CMS Context Management**: Encapsulates content path, index name, analyzer type, and index pool configuration
- **Content Search**: Provides search capability over the indexed content files via the `EcountIndex` bean
- **Property-based Configuration**: Content location and behavior configured via external properties file

## Key Entities
| Entity | Description |
|--------|-------------|
| CMS Index (`cmsName`) | Named logical content index (value: `cms`) |
| CMS Path (`cmsPath`) | Filesystem path containing content source (default: `D:/c-base/src/xContent/content`) |
| Analyzer | Lucene text analyzer (value: `WhitespaceAnalyzer`) |
| LuceneIndex | Manages the physical Lucene index lifecycle |
| EcountIndex | Façade over `LuceneIndex` and `CMSContext` |
| CMSContext | Configuration holder for CMS connection pool settings |

## Business Rules
- Content must be present at `lucene.cms.dir` before service starts; no dynamic loading
- Analyzer is fixed at `WhitespaceAnalyzer` (no stemming, no language-specific analysis)
- Index pool: max 10 searchers, min 3 searchers; searcher timeout 10s; writer timeout 30s
- Configuration loaded from `D:/c-base/config/xContent/applicationContext-xContent.properties` (hardcoded Windows path in `CMSApplicationContext.xml` — no environment variable injection)
- This is a **library** (WAR packaging in pom.xml, version `2.0.0-SNAPSHOT`) — intended to be embedded in the xcontent service deployment

## Key Flows
1. **Index Initialization**: Host application starts → `CMSApplicationContext.xml` loads → beans initialized → `LuceneIndex` opens index at `lucene.cms.dir` → Lucene `RAMDirectory` populated → `EcountIndex` ready for queries
2. **Content Query**: `EcountIndex.search(...)` → Lucene query on `RAMDirectory` → result set returned

## Compliance Considerations
- Same as `xcontent_SVC`: content includes fee disclosures and terms; accuracy is a regulatory requirement
- No personal data flows through this library
- Hardcoded Windows path for config file (`file:D:/c-base/config/xContent/...`) — not suitable for containerized/cloud deployment without modification

## Business Risks
- **Version conflict with xcontent_SVC**: Both repos define essentially the same Spring beans (`CMSApplicationContext.xml` is near-identical between the two repositories); maintaining two copies increases risk of divergence
- **Hardcoded path**: The properties file path `D:/c-base/config/...` is not configurable without modifying the XML directly; incompatible with container/cloud deployment
- **SNAPSHOT version**: `2.0.0-SNAPSHOT` is unstable; library consumers may receive different behavior between builds
