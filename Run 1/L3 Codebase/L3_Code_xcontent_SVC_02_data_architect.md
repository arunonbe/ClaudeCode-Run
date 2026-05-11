# xcontent_SVC — Data Architect View

## Data Stores
| Store | Type | Bean ID | Purpose |
|-------|------|---------|---------|
| Filesystem (CMS content directory) | Local/mounted filesystem | `cmsPath` | Source of all brand content files (XML, HTML, images, PDFs) |
| Lucene RAMDirectory | In-memory index | `directory` | Full-text index of content files; rebuilt at startup |
| SQL Server (Tomcat-level) | RDBMS | `mssql-jdbc` + `HikariCP` copied to `tomcat-lib` | Present in dependencies but no JDBC beans configured in `CMSApplicationContext.xml` — likely used by inherited framework context |

## Schema / Tables
No Spring JDBC or JPA data access beans are defined in `CMSApplicationContext.xml`. The SQL Server JDBC driver and HikariCP are copied to Tomcat's shared library directory (`target/tomcat-lib`) during the Maven build via `maven-dependency-plugin` — suggesting they are used by other components within the same Tomcat instance, not by the xcontent application context itself.

The only data access model is the Lucene index:
- **Index name**: `cms` (configured as `lucene.cms.name`)
- **Index directory**: Filesystem path `${lucene.cms.dir}` (runtime value: `D:/c-base/runtime/xContent/content`)
- **In-memory cache**: `org.apache.lucene.store.RAMDirectory` — all indexed content held in JVM heap

## Sensitive Data
- **Content files**: Fee disclosure HTML pages (`fees_en_US.html`) and brand images — not personally identifiable information
- **No CHD (Cardholder Data)**: This service does not process PANs, CVVs, account numbers, or personal data
- **QA TLS certificate** (`config/certfile_qa.crt`): Embedded in Docker image; represents a configuration management concern but not a data sensitivity issue
- **`CBASE_HOME_URL`** environment variable: Filesystem path used to locate the properties file; not a secret but path exposure could aid in system reconnaissance

## Encryption
- **At-rest**: Content files on filesystem are not encrypted at the application level; relies on OS/storage-level controls
- **In-transit**: Tomcat `server.xml` configures an HTTP connector on port 80 only; no HTTPS connector is configured in the server.xml within this repo. TLS must be terminated upstream (load balancer or reverse proxy)
- **QA certificate handling**: `keytool -import ... -storepass changeit` in Dockerfile (line 20) — default Java keystore password `changeit` is used, which is the JVM default and a known credential
- **No field encryption** needed — service handles only public-facing brand assets

## Data Flow
```
Content Management Team
  → Places/updates files on CMS filesystem (${lucene.cms.dir})
  
Service Startup
  → Spring loads CMSApplicationContext.xml
  → CmsContext bean reads filesystem path
  → LuceneIndex.init() indexes files into RAMDirectory
  
Runtime Content Request
  → Client (One Platform / mobile) → XML-RPC over HTTP
  → Tomcat (port 80 in container, upstream TLS termination)
  → xcontent.war (/services/xcontentWebServices)
  → EcountIndex.search() → Lucene RAMDirectory query
  → Content item returned in XML-RPC response
  
Environment Config
  → Docker ENV CBASE_HOME_URL=file:///cbase
  → Mounted volume at /cbase containing applicationContext-xContent.properties
  → Properties override lucene.cms.dir, lucene.cms.name, lucene.cms.analyzer
```

## Data Quality / Retention
- Content is served exactly as files exist on the filesystem — no transformation or validation of content files at service layer
- No version control of content files at the service layer (versioning is done via the xContent-recipient git repository and Azure Blob sync)
- No retention policy defined — content persists until removed from the CMS filesystem
- In-memory Lucene index is volatile: content state is lost on service restart and rebuilt from filesystem

## Compliance Gaps
1. **No TLS at application layer**: Tomcat server.xml (file: `config/server.xml`, line 64) configures only an HTTP connector on port 80; no HTTPS connector; application relies entirely on upstream proxy for TLS — must be verified in infrastructure
2. **Default keystore password**: `changeit` used in Dockerfile (line 20) for Java cacerts — production deployments should use a managed PKI approach
3. **QA certificate in production Docker image**: `certfile_qa.crt` is included in the production Docker image build — QA trust anchor in production is a security hygiene concern
4. **Content updates require restart**: If fee schedule or terms content is updated, a service restart is required — risk of cardholder-facing portal displaying outdated legally required disclosures between update and restart
5. **No content integrity verification**: Files are indexed directly from the filesystem without checksum validation; a compromised CMS filesystem could serve malicious content to cardholder portals
