# xcontent-content_LIB — Solution Architect View

## Technical Architecture
- **Framework**: Spring 1.2.7 (IoC container only; no MVC, no security)
- **Content indexing**: Apache Lucene 2.0.0 with `RAMDirectory` in-memory storage
- **Java target**: 1.5 (Java 5 bytecode)
- **Packaging**: WAR (atypical for a library; suggests it may have historically been deployed standalone as well as used as a library)
- **Bean configuration**: Spring 2.x DTD-based XML (`spring-beans.dtd`)
- **Key classes** (compiled into this library, source in this repo):
  - `com.ecount.one.lucene.EcountIndex` — top-level index façade; exposes search API
  - `com.cdbaby.lucene.LuceneIndex` — low-level Lucene index manager (wraps IndexWriter/IndexSearcher)
  - `com.cdbaby.utils.CMSContext` — configuration + searcher pool manager
  - `com.cdbaby.utils.CreatePropertyIndex` — index document builder

## API Surface
This is a library; it has no inbound API surface. It exposes Java classes for import by consuming services.

**Exported beans (via CMSApplicationContext.xml):**
- `ecountIndex` (class: `com.ecount.one.lucene.EcountIndex`) — primary search entry point
- `cmsContext` (class: `com.cdbaby.utils.CMSContext`) — CMS configuration context
- `index` (class: `com.cdbaby.lucene.LuceneIndex`) — Lucene index instance
- `directory` (class: `org.apache.lucene.store.RAMDirectory`) — in-memory Lucene store
- `createPropertyIndex` (class: `com.cdbaby.utils.CreatePropertyIndex`) — index document factory

## Security Posture

### Authentication / Authorisation
- Library has no authentication or authorization; inherits from host application

### Crypto
- No encryption; purely file-based content indexing

### Secrets
- No secrets required or managed

### Known CVE Risks
| Component | Version | Risk |
|-----------|---------|------|
| Spring Framework | 1.2.7 | CVE-2011-2894 (ClassLoader manipulation), multiple deserialization CVEs; EOL since 2007 |
| Apache Lucene | 2.0.0 | No known RCE CVEs but completely unmaintained (18+ years old) |
| Servlet API | 2.4 (compile) | If overriding container API, may suppress newer security filters |
| JUnit | 3.8.1 | Test scope only; no production risk |

## Technical Debt
1. **Spring 1.2.7**: Pre-Spring Security, pre-AspectJ integration, pre-annotation configuration; all modern migration targets require complete rewrite
2. **Java 1.5 bytecode**: `Collection` without generics, `StringBuilder` unavailable, modern APIs inaccessible
3. **WAR packaging for a library**: Produces a WAR artifact but is used as a library; unusual and potentially confusing packaging
4. **Spring 2.x DTD namespace**: References `http://www.springframework.org/dtd/spring-beans.dtd` over HTTP (not HTTPS) — bean loading at startup makes an HTTP request to resolve DTD unless cached
5. **`com.cdbaby.*` package names**: Suggest a copy from an open-source example project (CDBaby was a music streaming service); no Onbe/ecount branding; provenance uncertain
6. **Hardcoded Windows path**: `file:D:/c-base/config/xContent/...` in `CMSApplicationContext.xml` line 8 — incompatible with Linux containers
7. **Lucene RAMDirectory**: Content must fit in JVM heap; no disk overflow; no persistence across restarts
8. **SNAPSHOT artifact**: Non-repeatable builds for consumers
9. **No test coverage visible** beyond JUnit 3.8.1 framework declaration

## Gen-3 Migration Requirements
This library should be retired, not migrated:

1. Replace the Lucene filesystem-scan + RAMDirectory pattern with Azure Blob Storage + CDN for static asset delivery
2. Replace content search with a structured CMS API (metadata-driven, not full-text scan)
3. Replace `com.cdbaby.*` and `com.ecount.one.lucene.*` classes with modern content management library or custom Spring Boot service
4. All class consumers must be identified and migrated before retirement
5. Remove Spring 1.2.7 dependency entirely — no upgrade path; must rewrite

## Code-Level Risks (file:line references)
| Risk | File | Line |
|------|------|------|
| Spring 1.2.7 dependency | `pom.xml` | 72–75 |
| Java 1.5 compile target | `pom.xml` | 33–36 |
| Hardcoded Windows config path | `src/main/resources/CMSApplicationContext.xml` | 8 |
| HTTP DTD URL (not HTTPS) | `src/main/resources/CMSApplicationContext.xml` | 3 |
| Lucene RAMDirectory (heap-only, no persistence) | `src/main/resources/CMSApplicationContext.xml` | 16 |
