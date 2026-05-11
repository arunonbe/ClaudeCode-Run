# xfire-utils_LIB — Solution Architect View

## Technical Architecture
- **Module structure**: 2-module Maven project
  - `xfire-utils-spring`: Spring `FactoryBean` for XFire SOAP client creation
  - `xfire-utils-springjms`: XFire JMS transport backed by Spring JMS infrastructure
- **Core technology**: XFire 1.2.4 (SOAP framework; predecessor to Apache CXF)
- **Spring version**: 2.0.2 (IoC container; AOP via `ProxyFactory`)
- **JMS**: Spring JMS + XFire JMS transport; runtime JMS provider is configurable
- **WSDL parsing**: WSDL4J (`javax.wsdl.*`) used for WSDL document resolution
- **Proxy mechanism**: `java.lang.reflect.Proxy` + Spring AOP `ProxyFactory` + `org.aopalliance.intercept.MethodInterceptor`

## API Surface
Library — no inbound API. Exposed Java API:

### `xfire-utils-spring`
**Class**: `com.ecount.xfire.spring.remoting.XFireClientFactoryBean`
- `setServiceClass(Class)` / `setServiceInterface(Class)` — target service Java interface
- `setWsdlDocumentUrl(String)` — WSDL URL for service discovery
- `setServiceName(String)` — optional service name override
- `setNamespaceUri(String)` — optional namespace override
- `setUrl(String)` — optional direct endpoint URL (bypasses WSDL endpoint resolution)
- `setEndpoint(QName)` — optional specific endpoint name
- `setUsername(String)` / `setPassword(String)` — HTTP Basic Auth
- `setLookupServiceOnStartup(boolean)` — eager vs lazy WSDL resolution
- `setInHandlers(List)` / `setOutHandlers(List)` / `setFaultHandlers(List)` — XFire handler pipeline
- `setXFire(XFire)` — inject XFire instance

### `xfire-utils-springjms`
- `SpringJmsChannel` — XFire channel over Spring `JmsTemplate`
- `SpringJmsTransport` — XFire transport implementing JMS delivery
- `SpringJmsListenerChannelAdapter` — bridges Spring JMS `MessageListener` to XFire channel
- `JmsUriParser` interface + `DefaultJmsUriParser` + `WebLogicJmsUriParser` — JMS endpoint URI parsing

## Security Posture

### Authentication
- HTTP Basic Auth via `username`/`password` properties — credentials are plaintext in Spring XML config (server-side files)
- No certificate-based authentication, no OAuth2, no token-based auth
- Authentication is optional; many SOAP endpoints may be unauthenticated

### Authorisation
- No authorisation within the library; delegated to the target service

### Crypto / TLS
- No TLS enforcement in the library — TLS is determined by the WSDL URL scheme (`http://` vs `https://`)
- If a consumer provides an `http://` WSDL URL, all SOAP traffic (including Basic Auth credentials) flows unencrypted
- No WS-Security (message signing, message encryption) implemented

### Secrets Management
- Username and password injected via Spring XML properties — exposed on server disk in application config files
- No vault or secrets manager integration

### Known CVE Risks
| Component | Version | Risk |
|-----------|---------|------|
| XFire 1.2.4 | 1.2.4 | EOL since 2007; CVE-2007-5585 (directory traversal in WSDL generation), possible XML injection vulnerabilities; no patches available |
| Spring | 2.0.2 | CVE-2011-2894 (ClassLoader manipulation); multiple post-2.x CVEs not applicable but framework is unpatched |
| ActiveMQ | 4.1.0-incubator | CVE-2014-3612, CVE-2015-5254 (deserialization RCE via ObjectMessage); test scope but risk if upgraded to runtime |
| Geronimo specs | rc4 versions | Pre-release artifacts; may contain security issues |
| commons-logging (transitive) | Various | CVE-2014-0114 risk if commons-beanutils present |

## Technical Debt
1. **XFire 1.2.4 (EOL 2007)**: No upgrade path within XFire; migration to Apache CXF requires complete API rewrite at all consumers
2. **Spring 2.0.2 (EOL ~2010)**: Cannot be incrementally upgraded to Spring Boot 3.x
3. **`1.0.0-SNAPSHOT` forever**: Non-deterministic artifact; impossible to enforce a stable dependency contract
4. **Raw types throughout**: `Class`, `List`, `Collection`, `Map` used without generics — Java 1.4/1.5 era code (`XFireClientFactoryBean` extensively uses raw types)
5. **HTTP Basic Auth in config files**: Anti-pattern; credentials must be in secrets vault
6. **No TLS enforcement**: Library permits cleartext SOAP calls
7. **Defunct Maven repositories in POM**: `people.apache.org/repo/m2-incubating-repository` is not resolvable from the internet; builds depend on local Nexus cache
8. **`ProxyInterceptor` double-checked locking** (`getClient()` in inner class): Correct pattern (synchronized method), but reflects the manual threading complexity of pre-Java-5 concurrent code
9. **`XFireClientFactoryBean.toString()` builds `StringBuffer`** instead of `StringBuilder` — Java 1.4 era pattern (minor but indicative of code age)

## Gen-3 Migration Requirements
This library should be retired, not migrated. Replacement approach:

1. Replace all SOAP/XFire clients with REST clients (Spring `RestTemplate` or `WebClient`) or gRPC clients
2. Replace JMS-over-SOAP with direct message queue integration (Azure Service Bus SDK, Spring Cloud Azure)
3. Replace HTTP Basic Auth with OAuth2 client credentials flow
4. Enforce TLS on all service endpoints; validate certificates
5. Once all consumer services are migrated, delete this library from all dependency chains
6. Remove `people.apache.org` Maven repository references from any build configurations that still reference them

## Code-Level Risks (file:line references)
| Risk | File | Line |
|------|------|------|
| Raw type `Class` (no generics) | `xfire-utils-spring/src/main/java/com/ecount/xfire/spring/remoting/XFireClientFactoryBean.java` | 67–68 |
| `password` stored/passed as plain String | `xfire-utils-spring/src/main/java/com/ecount/xfire/spring/remoting/XFireClientFactoryBean.java` | 345–365 |
| HTTP Basic Auth sent without TLS guarantee | `xfire-utils-spring/src/main/java/com/ecount/xfire/spring/remoting/XFireClientFactoryBean.java` | 462–471 |
| `StringBuffer` instead of `StringBuilder` | `xfire-utils-spring/src/main/java/com/ecount/xfire/spring/remoting/XFireClientFactoryBean.java` | 630 |
| Raw `List`, `Collection`, `Map` types | `xfire-utils-spring/src/main/java/com/ecount/xfire/spring/remoting/XFireClientFactoryBean.java` | Multiple |
| Defunct Apache incubating Maven repo | `pom.xml` | 106–111 |
| Spring 2.0.2 dependency | `xfire-utils-spring/pom.xml` | 22–25 |
| XFire 1.2.4 dependency | `xfire-utils-spring/pom.xml` | 16–19 |
