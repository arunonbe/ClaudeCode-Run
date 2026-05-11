# xcontent-content_LIB — Data Architect View

## Data Stores
| Store | Type | Bean ID | Purpose |
|-------|------|---------|---------|
| Filesystem (CMS content) | Local filesystem | `cmsPath` | Source content files; path: `D:/c-base/src/xContent/content` (hardcoded default) |
| Lucene RAMDirectory | In-memory index | `directory` | Runtime content index held entirely in JVM heap |

## Schema / Tables
This is a library; it does not connect to a relational database. All data is managed through Lucene indices on the filesystem.

**Lucene index parameters (from `CMSApplicationContext.xml`):**
| Parameter | Bean | Value |
|-----------|------|-------|
| Index name | `cmsName` | `cms` |
| Index path | `cmsPath` | `${lucene.cms.dir}` |
| Analyzer | `analyzer` | `WhitespaceAnalyzer` |
| Min searchers | `cmsContext` | 3 |
| Max searchers | `cmsContext` | 10 |
| Searcher timeout | `cmsContext` | 10 (seconds) |
| Writer timeout | `cmsContext` | 30 (seconds) |
| LuceneIndex: segment merge factor | constructor-arg[2] | 1 |
| LuceneIndex: max field length | constructor-arg[3] | 1 |
| LuceneIndex: max buffered docs | constructor-arg[4] | 30 |
| LuceneIndex: merge factor | constructor-arg[5] | 60 |

## Sensitive Data
- No PAN, CVV, account numbers, or personal data
- Content indexed is brand asset metadata (filenames, paths, content text)
- Configuration file path is a Windows local path — reveals server directory structure if exposed

## Encryption
- No encryption at application level
- Filesystem and memory content are unencrypted
- No TLS or secrets configuration in this library

## Data Flow
```
External properties file
  (D:/c-base/config/xContent/applicationContext-xContent.properties)
  → PropertyPlaceholderConfigurer resolves ${lucene.cms.dir}, ${lucene.cms.name}, ${lucene.cms.analyzer}

Host application startup
  → Loads CMSApplicationContext.xml beans
  → LuceneIndex instantiated with filesystem path
  → RAMDirectory populated from index at lucene.cms.dir
  → EcountIndex ready for search calls
```

## Comparison with xcontent_SVC
The `CMSApplicationContext.xml` in this library is functionally near-identical to the one in `xcontent_SVC`, with one key difference:

| Aspect | xcontent-content_LIB | xcontent_SVC |
|--------|---------------------|--------------|
| Property file path | Hardcoded `file:D:/c-base/config/xContent/...` | Dynamic `${CBASE_HOME_URL}/config/xContent/...` |
| Spring DTD | Spring 2.x DTD (`spring-beans.dtd`) | Spring 5.x schema (`spring-beans.xsd`) |
| PropertyPlaceholder class | `PropertyPlaceholderConfigurer` | `PropertySourcesPlaceholderConfigurer` |
| Java target in POM | 1.5 (Maven compiler) | 21 |

This library represents the original implementation that `xcontent_SVC` modernized.

## Compliance Gaps
1. **Hardcoded Windows file path** (`file:D:/c-base/config/...`) in `CMSApplicationContext.xml` line 8 — breaks environment portability; not suitable for containerized deployment
2. **Spring 2.x DTD** references (`http://www.springframework.org/dtd/spring-beans.dtd`) — HTTP, not HTTPS, DTD URL; outdated namespace
3. **Java 1.5 compile target** in POM — code compiled to 17-year-old bytecode level
4. **SNAPSHOT version in use** — non-deterministic build artifacts
