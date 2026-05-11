# DevOps & Operations Report — dfapi-client_LIB

## 1. Build System

| Attribute | Value |
|---|---|
| Build tool | Maven (Maven Wrapper `mvnw`) |
| Java version | Inferred Java 8+ (no explicit compiler version in module poms; parent may set) |
| Multi-module | Parent `pom.xml` → `dfapiclient-common`, `dfapiclient-impl` |
| Packaging | JAR (library — no boot packaging) |
| Parent POM | Not visible in root pom.xml (standalone) |
| Settings file | `.mvn/wrapper/settings.xml` |

### Module Structure

| Module | Artifact | Contents |
|---|---|---|
| `dfapiclient-common` | `dfapiclient-common` | `DFAPIClient` interface, `DFAPIClientImpl`, `QuoteRequest`, `QuoteResponse`, `ProtocolHandler`, `DFException` |
| `dfapiclient-impl` | `dfapiclient-impl` | `HTTPHandler`, `JMSHandler`, `XMLHandler`, Axis-generated WSDL stubs, Spring XML configs |

### Key Dependencies

| Library | Version | Purpose |
|---|---|---|
| Apache Axis | 1.x (implied by WSDL stubs) | SOAP/WSDL client — EOL |
| `com.ecount.core.library.MQLib` | Unknown | IBM MQ JMS wrapper |
| JAXB | JDK-bundled (2013 gen) | XML binding |
| Apache Commons Logging | Current | Logging facade |
| Spring Framework | Unknown version | XML-based IoC config (`dfapiInvoker.xml`, `httpConfig.xml`, `jmsConfig.xml`) |

---

## 2. CI/CD

### GitHub Actions Workflows
- `.github/workflows/codeql.yml` — CodeQL SAST only
- **No deployment or publish workflow** — this is a shared library; it appears to be published manually or via a parent pipeline

No GitLab CI present.

---

## 3. Configuration Management

### Spring XML Configuration Files

| File | Location | Purpose |
|---|---|---|
| `dfapiInvoker.xml` | `dfapiclient-impl/src/main/resources/com/citi/prepaid/dfapi/` | Root Spring context — wires `DFAPIClientImpl`, `ProtocolHandler`, selects HTTP or JMS handler |
| `httpConfig.xml` | Same directory | Configures `HTTPHandler` and `DFAPIWSDLSOAPBindStub` endpoint URL |
| `jmsConfig.xml` | Same directory | Configures `JMSHandler`, `MQJMS`, queue name, channel, TTL |

Configuration is via **Spring XML** (not Spring Boot). Callers import these XML files into their Spring application context.

### Test Properties

| File | Contents | Risk |
|---|---|---|
| `httpclient.properties` | DFAPI SOAP endpoint, internal test endpoint, proxy config, certificate serial/CN details | Internal hostnames and proxy committed to repo |
| `jms.properties` | IBM MQ hostname (`192.193.99.44`), port (`27197`), queue (`CPS.DF.RQ1`), channel, queue manager | Internal network infrastructure committed to repo |
| `log4j.properties` | Log4j 1.x logging config for tests | Log4j 1.x EOL security risk |

---

## 4. Observability

| Signal | Mechanism |
|---|---|
| Request/response logging | `log.info(">>> Return Code response ...")` and `log.info(">>> Return Message response ...")` in `HTTPHandler` (lines 120–121) |
| JMS correlation logging | `log.info("Request to be send to DFAPI with Correlation id ...")` in `JMSHandler` (line 45) |
| Error logging | `log.error(ex.getMessage(), ex)` in both handlers |
| Logging framework | Apache Commons Logging (facade); test config uses Log4j 1.x |

---

## 5. Infrastructure Dependencies

| System | Address | Protocol | Notes |
|---|---|---|---|
| Citi DFAPI (production) | `https://citigroupsoa.citigroup.com/DFAPIService/DFAPIWSDLServ` | HTTPS/SOAP | External Citi dependency |
| Citi DFAPI (internal test) | `http://dflnxswapu.nam.nsroot.net:7990/DFAPIService/DFAPIWSDLServ` | HTTP/SOAP | Internal non-prod endpoint |
| IBM MQ | `192.193.99.44:27197` | IBM MQ protocol | Queue `CPS.DF.RQ1`, Manager `GU00` |
| HTTP Proxy (test) | `webproxy.ssmb.com:8080` | HTTP proxy | Corporate proxy config |

---

## 6. Operational Risks

| Risk | Severity | Detail |
|---|---|---|
| Apache Axis 1.x EOL | Critical | No security patches; known vulnerabilities; must replace with modern WS-client (JAX-WS, CXF) |
| Log4j 1.x in test config | High | Log4j 1.x is EOL with CVEs; must upgrade to Log4j2 or SLF4J/Logback |
| `TrustAllSSLSocketFactory` | Critical | SSL validation disabled for production SOAP calls |
| IBM MQ IP address hardcoded | Medium | Static IP in `jms.properties` committed to repo; IP change breaks JMS path |
| No circuit breaker or timeout | Medium | HTTP and JMS handlers have no retry or timeout configuration visible beyond Axis defaults |
| Single-threaded `SimpleDateFormat` | Medium | Thread-safety issue in `QuoteRequest` date methods under concurrent use |
| No version published to GitHub Packages | Low | No publish workflow; distribution mechanism unclear |
