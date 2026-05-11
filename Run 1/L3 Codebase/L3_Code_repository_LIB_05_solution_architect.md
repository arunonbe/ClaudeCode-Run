# Solution Architect Analysis: repository_LIB

## Technical Architecture
- **Language**: Java 21
- **Build**: Maven multi-module (repository-common, repository-impl, repository-xmlrpc, repository-client)
- **ORM**: Hibernate 5 (SessionFactory via Spring injection), `@Transactional` on DAO classes
- **IoC**: Spring XML configuration (`repositoryContext.xml`)
- **Serialisation**: XML-RPC (`xmlrpc:3.1.4` Apache library)
- **Logging**: SLF4J + Lombok `@Slf4j` in impl classes; Commons Logging in older client code
- **Testing**: JUnit (version implied by parent POM); DAO integration tests present

### Module Responsibilities
```
repository-common/
  - Interfaces: RepositoryManager, ReportManager
  - Transfer Objects: ECountFileJournalTO, ECountFileDefinitionTO, ECountFileAttributeTO, ECountClientHostTO
  - Value Objects: FileExtensionVO
  - Utilities: FTPUtil, PropertiesLoader, ReportUtil, RepositoryProperties, ServiceTOMapping
  - Comparators: JournalFileDateComparator, JournalFileNameComparator (+ reverses), ComparatorFactory

repository-impl/
  - Implementations: RepositoryManagerImpl, ReportManagerImpl
  - DAOs: ReportDAO, ReportCategoryDAO, ProgramReportDAO (Hibernate 5)
  - Spring context: repositoryContext.xml

repository-xmlrpc/
  - XmlRpcReportServiceProxy: XML-RPC server-side proxy implementation

repository-client/
  - XmlRpcReportManagerClient: XML-RPC client calling the remote repository service
  - RPCWrapper: Low-level RPC abstraction
```

## API Surface
No REST or SOAP API surface. This is a library with programmatic Java interfaces:

**RepositoryManager interface** (repository-common):
- `getFile(context, fileId, memberId, programId)`
- `getFiles(context, memberId, programId, startDate, endDate, timePeriod, fileType, fileAttribute)`
- `getFilesDaysBack(context, memberId, programId, daysBack, fileType, fileAttribute)`
- `getAllFiles(context, memberId, programId, fileType, fileAttribute)` (+ paginated variants)
- `retrieveFile(context, memberId, fileDef, programId)`
- `storeFile(context, memberId, fileDef, override, programId[, fileType])`
- `uploadRequestFile(context, memberId, requestFile, fileFormat[, isMaker])`
- `SetFileAttribute(context, memberId, file, attributeID, attributeValue)`
- `processJobFile(...)` (multiple overloads)
- `uploadAndStoreFile(...)`

**ReportManager interface**:
- `getReportByName(name)`, `getReport(id)`, `getReportsByCategoryId(categoryId)`
- `getProgramReport(...)`, `getProgramReportsByCategory(...)`

## Security Posture

### Authentication & Authorisation
- No authentication within the library. Access control relies entirely on callers providing correct memberId/programId scoping.
- No cross-tenant isolation enforcement at this layer.

### Cryptography
- No cryptographic operations in this library.
- FTPUtil uses plain FTP (no FTPS/SFTP) — data in transit is not encrypted.

### Secrets Management
- No secrets handled directly. Connection strings and credentials are injected by the consuming application via Spring.

### Known CVEs / Vulnerable Dependencies
| Library | Version | Risk |
|---|---|---|
| Apache XML-RPC | 3.1.4 | CVE-2016-5003 (content-type header XSS), CVE-2016-5002 (XXE in parser); CRITICAL for server-side XML-RPC parsing |
| Hibernate 5 | (via parent POM) | Check for SQL injection risks in HQL if user input reaches queries; current usage uses parameterised queries — acceptable |
| xplatform / xplatformlibrary | Internal | Security posture unknown without source access |

## Technical Debt
1. **XML-RPC protocol** (`RPCWrapper.java`, `XmlRpcReportManagerClient.java`): Replaced by REST in modern systems; XXE vulnerability in XML-RPC library.
2. **FTPUtil** (`FTPUtil.java`): Plain FTP is a PCI DSS violation for any file containing cardholder data.
3. **Spring XML configuration** (`repositoryContext.xml`): Commented-out Hibernate 3 configuration left in-file (lines 58-103) — configuration drift risk.
4. **`ReturnStatus` checked exception** from cbase: Non-standard exception type locks consumers to cbase types.
5. **`RequestContext` from cbase**: Thread-bound context object ties the library to the cbase request model.
6. **Hibernate `getCurrentSession()`** pattern requires active Hibernate session context in calling thread — not compatible with reactive or async processing.
7. **`ServiceTOMapping` utility**: Likely contains field-mapping logic that would be replaced by MapStruct or similar in a Gen-3 migration.

## Gen-3 Migration Requirements
1. Replace XML-RPC client/server with REST client calling repository-service_SVC REST API.
2. Replace plain FTP in FTPUtil with SFTP or direct cloud storage SDK (Azure Blob / AWS S3).
3. Migrate Hibernate 5 DAOs to Spring Data JPA repositories (JpaRepository).
4. Remove cbase type dependencies from public API (`ECountFile`, `RequestContext`, `ReturnStatus`).
5. Migrate Spring XML config to Java `@Configuration` classes or Spring Boot auto-configuration.
6. Replace Commons Logging with SLF4J throughout.
7. Upgrade XML-RPC library or remove it entirely.

## Code-Level Risks (File:Line References)
- `FTPUtil.java` — entire class: uses plain FTP; violates PCI DSS Req 4.2 for files containing CHD.
- `repositoryContext.xml:58-103` — dead commented-out Hibernate 3 configuration left in production resource file; creates confusion and maintenance risk.
- `XmlRpcReportManagerClient.java` — XML-RPC client with xmlrpc:3.1.4; CVE-2016-5002 (XXE) and CVE-2016-5003 apply if responses from the XML-RPC server are not validated.
- `ReportDAO.java:21-23` — HQL query `"from Report where name=:reportName"` uses parameterised binding (safe); however, returns first result without checking for duplicates (`reports.get(0)`).
