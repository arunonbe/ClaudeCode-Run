# xcontent_SVC — Solution Architect View

## Technical Architecture
- **Runtime**: Java 21 (Liberica OpenJRE Alpine), Tomcat 10.1.28, WAR deployment
- **Framework**: Spring Web MVC (spring-webmvc) for request dispatching; Spring XML context for bean wiring
- **Content indexing**: Apache Lucene 2.0.0 (`RAMDirectory` in-memory index)
- **Serialization**: Jackson Databind (`jackson-databind`) — present in dependencies; likely used for JSON responses alongside XML-RPC
- **Logging**: Log4j2 (log4j-api, log4j-core, log4j-1.2-api bridge, log4j-jakarta-web)
- **Key classes**:
  - `com.ecount.one.lucene.EcountIndex` — top-level index façade (source in xcontent-content_LIB)
  - `com.cdbaby.utils.CMSContext` — CMS configuration context
  - `com.cdbaby.lucene.LuceneIndex` — Lucene index implementation (source in xcontent-content_LIB)
  - `com.cdbaby.utils.CreatePropertyIndex` — index property builder

## API Surface

### Inbound
- **XML-RPC endpoint**: `/services/xcontentWebServices` (per APIM `BACKEND_SUFFIX` config in `deployment.yml`)
- **Static pages**: `index.jsp`, `welcome.html`, `not_found.html`, `unknown_error.html` — status/error pages
- **WSDL published to APIM**: `PUBLISH_TO_APIM: true` in deployment workflow

### Outbound
- Filesystem read from `${lucene.cms.dir}` (mounted at `/cbase/...` in container)
- No outbound HTTP calls visible in application context

## Security Posture

### Authentication
- No authentication configuration visible in `CMSApplicationContext.xml` or `web.xml` (web.xml not present — `failOnMissingWebXml=false`)
- The service relies on APIM or network-level access control; no application-level authentication enforced

### Authorisation
- No role-based access control defined at the application layer

### Crypto / TLS
- **No HTTPS connector** in `config/server.xml` (file: `config/server.xml`, line 64) — HTTP only on port 80
- TLS termination must be done upstream (load balancer, APIM, reverse proxy)
- Java truststore password `changeit` used in Docker build (file: `Dockerfile`, line 20) — default JVM password

### Secrets Management
- No secrets (credentials, API keys, tokens) are used by the application itself
- `CBASE_HOME_URL` is a filesystem path, not a secret

### Container Security
- Base image: `bellsoft/liberica-openjre-alpine:21` — minimal Alpine-based image; reduces attack surface
- Tomcat downloaded from `archive.apache.org` at build time (line 8 in Dockerfile) — build-time network dependency; should use pre-staged image layers
- `autoDeploy=false` in server.xml — reduces risk of accidental app deployment
- No user defined in Dockerfile — container runs as `root` (default); should run as non-root user

### Known CVE Risks
| Component | Version | Risk |
|-----------|---------|------|
| Apache Lucene | 2.0.0 | Ancient library (2006); no known remote exploitability but completely unmaintained |
| commons-discovery | 0.2 | EOL; no known critical CVEs but unmaintained |
| commons-logging | 1.1.1 | Old; CVE-2014-0114 (ClassLoader manipulation) if commons-beanutils is also present |
| Tomcat | 10.1.28 | Recent version — lower risk |
| Liberica JRE | 21 | Recent version — lower risk |

## Technical Debt
1. **Lucene 2.0.0**: 18+ year old library; `RAMDirectory` approach means all content must fit in JVM heap
2. **No content hot-reload**: Index is built at startup; content changes require pod restart
3. **`com.cdbaby.*` third-party classes**: Origin unclear; not in this repo; likely an ancient open-source fork — no community support
4. **Java 8 in README vs Java 21 in Dockerfile**: Documentation lag creates confusion for developers and operators
5. **No OpenAPI/WSDL spec visible in repo**: Only WSDL exists as artifact produced by the XML-RPC framework; no contract-first design
6. **Container runs as root**: No `USER` directive in Dockerfile — principle of least privilege violated
7. **Tomcat downloaded at build time**: Build reproducibility risk; should pin to a local registry image
8. **QA cert in image**: `certfile_qa.crt` in all environments including production image builds
9. **No liveness/readiness probes defined** in deployment configuration visible here

## Gen-3 Migration Requirements
1. Replace Lucene in-memory index + filesystem mount with Azure Blob Storage or object storage
2. Add Azure CDN / Front Door for edge delivery of static brand assets
3. Replace XML-RPC with REST API (OpenAPI 3.0 spec) for content queries
4. Implement authentication (OAuth2/API key) at application layer (not just APIM)
5. Implement content versioning and hot-reload without service restart
6. Run container as non-root user; add security context in Kubernetes manifest
7. Remove QA certificate from production image; use cert injection at runtime via Kubernetes secrets or Azure Key Vault
8. Replace `changeit` with managed PKI for Java truststore
9. Add structured logging with correlation IDs and OpenTelemetry
10. Add health/liveness/readiness endpoints (Spring Actuator or custom endpoint)

## Code-Level Risks (file:line references)
| Risk | File | Line |
|------|------|------|
| No HTTPS connector — HTTP only | `config/server.xml` | 64 |
| Default keystore password `changeit` | `Dockerfile` | 20 |
| Container runs as root (no USER directive) | `Dockerfile` | entire file |
| Tomcat downloaded at build time from archive.apache.org | `Dockerfile` | 8 |
| QA cert embedded in all builds | `Dockerfile` | 19–20 |
| Hardcoded path in CMSContext bean | `src/main/resources/CMSApplicationContext.xml` | 89 |
| `failOnMissingWebXml=false` — no web.xml security constraints | `pom.xml` | 153–155 |
