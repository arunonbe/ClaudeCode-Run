# eccm_LIB — Solution Architect Report

## Critical Flags

### FLAG-1: Apache Struts 1.2.8 — RCE Vulnerabilities — CRITICAL
**File**: `pom.xml` line 92
Apache Struts 1.x is end-of-life and affected by multiple critical CVEs:
- **CVE-2016-1181** (CVSS 8.1) — Remote code execution via ActionForm Enum manipulation
- **CVE-2016-1182** (CVSS 7.5) — Insufficient validation in Commons Validator
- **CVS-2016-4004** — ClassLoader manipulation in Struts 1.x

Any web application including `eccm_LIB` as a transitive dependency inherits these vulnerabilities. For a PCI DSS Level 1 service provider hosting cardholder portals, this is a **critical vulnerability requiring immediate attention**.

### FLAG-2: Apache Lucene 2.0.0 — EOL 18+ Years
**File**: `pom.xml` line 97
Lucene 2.0.0 (2006) has no security support. While not directly exploitable in most configurations, the in-memory index (`RAMDirectory`) processing untrusted CMS content could be subject to denial-of-service via crafted index entries.

### FLAG-3: CMS HTTP Retrieval — Potential Plain HTTP
**File**: `CMSService.java` lines 10–11 (CommonHttpClient imports), `CMSApplicationContext.xml` (CMS URL config)
The `CMSService` uses Commons HttpClient 3.0.1 to retrieve content from a remote CMS node URL. If the `ecount.node` system property or `cmsServiceURL` is set to an `http://` (non-TLS) URL, CMS content is fetched unencrypted. This would violate PCI DSS Requirement 4.2.1 if the CMS server is outside the local network.

### FLAG-4: `PropertyTag.java` — Potential XSS Risk
**File**: `PropertyTag.java` (11,214 bytes — largest class)
The `<eccm:property>` tag renders CMS content into JSP pages. If CMS content contains unescaped HTML or JavaScript, and the tag does not escape the output, stored XSS is possible. At 11 KB, this class contains significant rendering logic that should be audited for output encoding.

### FLAG-5: Hardcoded Windows Production Path in XML
**File**: `CMSApplicationContext.xml` line 38
```xml
<property name="luceneCmsPath"><value>D:/c-base/Runtime/xContent/content</value></property>
```
Production filesystem path hardcoded in Spring configuration XML committed to git. If this path differs in production, the fallback behavior is not clear. This also constitutes path disclosure.

---

## All Classes and Methods — Inventory

### Package: `com.ecount.cms`
| Class | Key Methods | Purpose |
|---|---|---|
| `CMSService` | `fire(queryString)`, `createAnalyzer(analyzerType)`, `setCmsServiceURL(url)` | Main CMS query service; executes Lucene searches |
| `CmsQueryBuilder` (8,155 bytes) | `buildQuery(...)` | Constructs Lucene query strings from request parameters |
| `DocumentParser` | `parse(InputStream)` | Parses CMS content documents into XDoc objects |
| `UrlRewrite` (7,329 bytes) | `rewrite(url, context)` | Applies URL rewriting rules for portal navigation |
| `XDoc` (2,102 bytes) | `getFieldMap()`, `get(fieldName)` | Wrapper for Lucene Document field map |

### Package: `com.ecount.eccm.lucene`
| Class | Key Methods | Purpose |
|---|---|---|
| `LuceneIndex` (8,538 bytes) | `getSearcher()`, `getWriter()`, `refresh()` | Manages Lucene index reader/writer lifecycle |
| `IndexManager` (3,924 bytes) | `getInstance()`, `getIndex(name)` | Singleton index registry |
| `IndexSearch` (3,145 bytes) | `search(name, searcher, analyzer, query, maxHits, id)` | Executes Lucene query and returns Hits |
| `DocumentParser` (4,784 bytes) | `parse(File)`, `parse(Directory)` | Populates Lucene index from filesystem documents |
| `DocumentRemover` (3,614 bytes) | `remove(term)` | Removes Lucene documents by term |
| `LuceneDocument` (1,122 bytes) | `getFields()` | Value object wrapping Lucene Document |
| `WithStopAnalyzer` (650 bytes) | `tokenStream(field, reader)` | Custom stop-word analyzer |

### Package: `com.ecount.eccm.utils`
| Class | Key Methods | Purpose |
|---|---|---|
| `CMSContext` (2,366 bytes) | Getters/setters for all config properties | Runtime configuration holder |
| `CreatePropertyIndex` (11,139 bytes) | `createIndex()`, `indexProperties(dir)` | Builds Lucene index from CMS property files |

### Package: `com.ecount.web.tags.eccm`
| Class | Tag | Key Methods | Purpose |
|---|---|---|---|
| `PropertyTag` (11,214 bytes) | `<eccm:property>` | `doStartTag()`, `doAfterBody()` | Renders affiliate-specific text/HTML content |
| `ImageTag` (1,907 bytes) | `<eccm:image>` | `doStartTag()` | Renders affiliate-specific card/logo image |
| `LinkTag` (2,048 bytes) | `<eccm:link>` | `doStartTag()` | Renders affiliate-specific navigation link |
| `IncludeTag` (1,035 bytes) | `<eccm:include>` | `doStartTag()` | Includes affiliate-specific JSP fragment |
| `ForEachTag` (2,253 bytes) | `<eccm:forEach>` | `doStartTag()`, `doAfterBody()` | Iterates CMS search results |
| `DocBaseTag` (1,424 bytes) | `<eccm:docBase>` | `doStartTag()` | Sets CMS document base URL |
| `UrlRewriteTag` (1,501 bytes) | `<eccm:urlRewrite>` | `doStartTag()` | Applies URL rewriting |
| `FmtMessageTag` (1,781 bytes) | `<eccm:fmtMessage>` | `doStartTag()` | Formats i18n messages |
| `SelectTag` (1,600 bytes) | `<eccm:select>` | `doStartTag()` | Renders affiliate-specific select |

### Package: `com.ecount.web.tags.eccm.model`
| Class | Purpose |
|---|---|
| `IContent` | Interface for content value objects |
| `IRule` | Interface for rule evaluation: `evaluate(PageContext, ruleName, property, value)` |
| `IRuleConfig` | Interface for rule configuration access |
| `IRuleManager` | Interface for rule manager lifecycle |
| `RuleManager` | Static rule manager delegate; `evaluate()`, `getRuleConfiguration()` |
| `RuleConfigException` | Exception for rule configuration errors |
| `RuleNotFoundException` | Exception when no rule found for name |

### Package: `com.ecount.web.tags.eccm.model.simple`
| Class | Purpose |
|---|---|
| `EccmSimpleInitializer` (2,578 bytes) | Spring-initialized rule configuration loader |
| `SimpleRuleConfig` (4,170 bytes) | In-memory rule map; `getRuleByName(name)`, `addRule(name, rule)` |
| `SimpleRuleManager` (1,074 bytes) | Simple implementation of IRuleManager |
| `ParameterIndexedImageRule` (2,236 bytes) | Selects image URL by affiliate/parameter index |
| `ParameterIndexedIncludeRule` (2,257 bytes) | Selects JSP include path by affiliate/parameter index |
| `ParameterIndexedStyleRule` (2,246 bytes) | Selects CSS path by affiliate/parameter index |

### Package: `com.ecount.web.tags.eccm.model.affiliate`
| Class | Purpose |
|---|---|
| `DefaultAffiliateSorter` (1,393 bytes) | Sorts content by affiliate priority |

### Package: `com.ecount.web.tags.struts`
| Class | Purpose |
|---|---|
| `SecurePasswordTag` (626 bytes) | Renders `<input type="password">` with security attributes |
| `SecureTextTag` (687 bytes) | Renders `<input type="text">` with security attributes |

---

## Security Vulnerability Summary

| Vulnerability | File | CVE | Severity |
|---|---|---|---|
| Apache Struts 1.2.8 RCE | `pom.xml` line 92 | CVE-2016-1181, CVE-2016-1182 | **Critical** |
| Commons HttpClient 3.0.1 — no TLS 1.2 | `pom.xml` line 36 | PCI DSS 4.2.1 | High |
| Apache Lucene 2.0.0 — EOL | `pom.xml` line 97 | No CVE/EOL risk | Medium |
| log4j 1.2.9 | `pom.xml` line 27 | CVE-2019-17571 | High |
| Spring 2.0.2 — multiple CVEs | `pom.xml` line 78 | Various | High |
| `PropertyTag` output encoding — potential XSS | `PropertyTag.java` | OWASP A03:2021 | High |
| Hardcoded production path in XML | `CMSApplicationContext.xml` line 38 | Info disclosure | Low |

---

## Remediation Priority Matrix

| Item | Priority | Effort |
|---|---|---|
| Replace Apache Struts 1.2.8 — eliminate from all consumers | P1 — Immediate | Very High (cross-repo) |
| Upgrade log4j 1.x to Log4j2 / Logback | P1 — 14 days | Low |
| Audit `PropertyTag.doStartTag()` for XSS (output encoding) | P1 — 7 days | Medium |
| Upgrade Commons HttpClient 3.x to Apache HttpComponents 5.x | P2 — 30 days | Medium |
| Upgrade Lucene 2.0.0 to Lucene 9.x | P2 — 90 days | Very High (API rewrite) |
| Replace `RAMDirectory` with `MMapDirectory` for production | P2 — 14 days | Low |
| Externalize hardcoded path from `CMSApplicationContext.xml` | P2 — 1 day | Trivial |
| Add test coverage for all JSP tag classes | P3 — 60 days | High |
| Plan migration away from eccm_LIB to modern content management | P3 — 18 months | Very High |
