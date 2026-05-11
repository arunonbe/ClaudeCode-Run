# eccm_LIB — Data Architect Report

## Data Architecture Overview

`eccm_LIB` does **not** use a relational database. Its data layer is based entirely on:
1. **Apache Lucene 2.0.0** full-text search index (file-based or in-memory RAM directory)
2. **HTTP-based content retrieval** via Apache Commons HttpClient (for fetching content from a remote CMS service URL)
3. **Spring IoC** configuration injected through `CMSApplicationContext.xml`

The library has no JDBC, no JPA, and no SQL. It is a read-only data consumer from the CMS content store.

---

## Lucene Index Architecture

### Index Storage
`CMSApplicationContext.xml` (line 16) configures:
```xml
<bean id="directory" class="org.apache.lucene.store.RAMDirectory" />
```
The Lucene index is stored in **RAM** (in-memory). The `LuceneIndex.java` (8,538 bytes) manages population of this RAM directory from the filesystem path configured as:
```xml
<property name="luceneCmsPath"><value>D:/c-base/Runtime/xContent/content</value></property>
```
(`CMSApplicationContext.xml`, line 38)

This means:
- The Lucene index is re-built in RAM on application startup from a local filesystem directory
- The content files at `D:/c-base/Runtime/xContent/content` are the authoritative content source
- Index refresh is managed by `LuceneIndex.java` with configurable refresh intervals (10-second searcher timeout, 30-second writer timeout)

### Lucene Document Structure
`LuceneDocument.java` (1,122 bytes) defines the structure of indexed documents. Based on `DocumentParser.java` and `IndexSearch.java`, documents contain:
- A default ID field (configured as `"id"` in `CMSService.java` line 47)
- Multiple named fields corresponding to content properties (e.g., `affiliate_id`, `program_id`, `image_url`, `style_path`, `include_path`)
- The `XDoc.getFieldMap()` returns a `Map<String, String>` of all fields in the document

### Index Management Classes
| Class | Purpose |
|---|---|
| `LuceneIndex.java` | Manages index lifecycle — load, refresh, reader/writer coordination |
| `IndexManager.java` | Singleton index manager; tracks multiple named indexes |
| `IndexSearch.java` | Search execution; `search(name, searcher, analyzer, query, maxHits, defaultId)` |
| `DocumentParser.java` (eccm package) | Parses content documents into Lucene `Document` objects |
| `DocumentParser.java` (lucene package) | Alternative/extended parser |
| `DocumentRemover.java` | Removes documents from the Lucene index |
| `WithStopAnalyzer.java` | Custom Lucene analyzer with stop words for CMS content |

---

## HTTP Content Retrieval

`CMSService.java` (lines 10–11) imports `DefaultMethodRetryHandler` and `GetMethod` from Apache Commons HttpClient 3.0.1. The `getCmsServiceURL()` and `cmsContentContext` properties suggest the library can also retrieve content from a remote HTTP endpoint (the `ecount.node` system property at line 38). This means:
- CMS content can be fetched remotely over HTTP (not HTTPS in the 2004-era implementation)
- Content transmitted over plain HTTP would violate PCI DSS Requirement 4.2.1 if the CMS server is in a different network zone

---

## Spring Configuration Data

`CMSApplicationContext.xml` references externalized configuration from:
```
D:/c-base/config/xContent/applicationContext-xContent.properties
```
This properties file (not in the repository) provides:
- `${lucene.cms.dir}` — filesystem path to the CMS content directory
- `${lucene.cms.name}` — name of the Lucene index
- `${lucene.cms.analyzer}` — analyzer type for the index

The hardcoded Windows path `D:/c-base/Runtime/xContent/content` in `CMSApplicationContext.xml` (line 38) is a **deployment configuration smell** — it hardcodes a runtime path that differs between environments.

---

## Rules Engine Data Model

### `IRuleConfig` / `SimpleRuleConfig.java` (4,170 bytes)
The rules configuration stores rules in-memory as a `Map<String, IRule>`. Rules are loaded from Spring configuration (injected via `EccmSimpleInitializer.java`). The configuration structure:
```
SimpleRuleConfig
    └─► Map<ruleName, IRule>
           └─► ParameterIndexedImageRule (list of affiliate-indexed image URLs)
           └─► ParameterIndexedIncludeRule (list of affiliate-indexed JSP fragment paths)
           └─► ParameterIndexedStyleRule (list of affiliate-indexed CSS paths)
```

### `CreatePropertyIndex.java` (11,139 bytes — largest utility class)
This is the index population utility that reads content properties from the CMS content directory and builds the Lucene index. Its size suggests it contains significant logic for:
- Parsing content property files
- Mapping property keys to Lucene field names
- Handling multi-affiliate content overlays

---

## Context Data (`CMSContext.java`)

`CMSContext.java` (2,366 bytes) carries runtime configuration:
| Property | Type | Purpose |
|---|---|---|
| `cmsPath` | String | Filesystem path to CMS content |
| `cmsName` | String | Index name identifier |
| `analyzer` | String | Lucene analyzer type |
| `luceneCmsPath` | String | Alternate CMS filesystem path |
| `maxSearchers` | int | Maximum concurrent Lucene searchers |
| `minSearchers` | int | Minimum maintained searchers |
| `searcherTimeout` | int | Searcher cache timeout (10 seconds) |
| `writerTimeout` | int | Index writer timeout (30 seconds) |

---

## Sensitive Data Assessment

The ECCM CMS content system does **not** store PII, PANs, or financial data. It stores:
- UI content (images, styles, includes, links)
- Program/affiliate configuration
- Portal text and messages

However, the JSP tags (`PropertyTag.java` at 11,214 bytes) render content into portal pages. If the CMS content stores dynamically assembled HTML that includes member-specific data, XSS vulnerabilities in tag rendering could expose PII.

The `SecurePasswordTag.java` and `SecureTextTag.java` in the `xstruts.tld` tag library suggest that some form fields rendered by these tags handle credential input. These tags must properly set `autocomplete="off"` and avoid logging field values.

---

## Data Summary

| Data Type | Location | Sensitivity | Risk |
|---|---|---|---|
| CMS content (images, styles, text) | Lucene RAM index | Low | None |
| Program/affiliate config | Rules engine in-memory map | Low | Internal config exposure |
| CMS content filesystem | `D:/c-base/Runtime/xContent/content` | Low | Path disclosure |
| HTTP content from remote CMS node | Network (potentially plain HTTP) | Low-Medium | PCI DSS 4.2.1 if on HTTP |
| Password field rendering | `SecurePasswordTag` | High | Must not log values |
