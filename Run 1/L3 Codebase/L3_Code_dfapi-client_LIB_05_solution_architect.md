# Solution Architect Report — dfapi-client_LIB

## 1. Architecture Overview

dfapi-client_LIB is a **two-module Maven JAR library** providing a Java client for the Dodd-Frank API (international wire disclosure). It offers two transport implementations behind a common `ProtocolHandler` interface, configured via Spring XML.

```
dfapi-client_LIB
├── dfapiclient-common/
│   └── src/main/java/com/citi/prepaid/dfapi/
│       ├── services/DFAPIClient.java           — interface (execute method)
│       ├── services/DFAPIClientImpl.java       — delegates to ProtocolHandler
│       ├── handler/ProtocolHandler.java        — strategy interface
│       ├── request/QuoteRequest.java           — JAXB request DTO (2013)
│       ├── response/QuoteResponse.java         — JAXB response DTO (2013)
│       └── exception/DFException.java         — typed exceptions
│
└── dfapiclient-impl/
    └── src/main/java/com/citi/prepaid/dfapi/handler/
        ├── HTTPHandler.java                    — SOAP/HTTP via Apache Axis
        ├── JMSHandler.java                     — IBM MQ transport
        └── XMLHandler.java                     — XML serialization for JMS
    └── src/main/java/org/citidoddfrank/www/DFAPIWSDL/
        ├── DFAPIWSDLSOAPBindStub.java          — Axis-generated SOAP stub
        ├── DFAPIWSDLServLocator.java           — Axis service locator
        ├── DFAPIWSDLPortTypeProxy.java         — Axis proxy
        ├── TrustAllSSLSocketFactory.java       — CRITICAL: disables SSL validation
        └── [additional Axis-generated types]
    └── src/main/resources/com/citi/prepaid/dfapi/
        ├── dfapiInvoker.xml                    — Spring root context
        ├── httpConfig.xml                      — HTTP handler config
        └── jmsConfig.xml                       — JMS handler config
```

---

## 2. API Surface

**Type**: Java library (no HTTP endpoint)  
**Single method**: `QuoteResponse execute(QuoteRequest request) throws DFException`  
**Class**: `com.citi.prepaid.dfapi.services.DFAPIClient` (interface), implemented by `DFAPIClientImpl`

### Exception Types
`DFException.DFExceptionType`:
- `CONNECTION_ERROR` — network/transport failure
- `TIMEOUT_ERROR` — JMS receive timeout (JMSHandler line 62)

---

## 3. Security Architecture

| Control | Status | Detail |
|---|---|---|
| HTTPS to Citi endpoint | Active | `https://citigroupsoa.citigroup.com/` |
| SSL certificate validation | **Disabled** | `TrustAllSSLSocketFactory.java` — all certificates trusted regardless of validity |
| Client certificate auth | Partially configured | Certificate serial/CN in `httpclient.properties` for First National Bank of Omaha — unclear if used in production |
| MQ channel security | Unknown | `CPS.TOMCAT.SVRCONN.U` channel; no TLS/SSL channel config visible |
| Proxy authentication | Unknown | `webproxy.ssmb.com:8080` configured but no credentials visible |
| Log sanitization | None | Full request XML (containing client/bank IDs) logged in `JMSHandler` (line 45–46) |

**CRITICAL**: `TrustAllSSLSocketFactory` at `dfapiclient-impl/src/main/java/org/citidoddfrank/www/DFAPIWSDL/TrustAllSSLSocketFactory.java` completely disables TLS certificate validation. This class must be identified in any DFAPI HTTP call path and removed before production use.

---

## 4. Technical Debt

| Item | Location | Severity |
|---|---|---|
| `TrustAllSSLSocketFactory` — disables SSL | `org.citidoddfrank.www.DFAPIWSDL.TrustAllSSLSocketFactory` | Critical |
| Apache Axis 1.4 (2006, EOL) | All `DFAPIWSDLSOAPBindStub` and related classes | Critical |
| Log4j 1.x in test config | `dfapiclient-impl/src/test/resources/log4j.properties` | High |
| JAXB code generated 2013 | `QuoteRequest.java`, `QuoteResponse.java` | High |
| `SimpleDateFormat` not thread-safe | `QuoteRequest.java` lines 584, 605, 667, 688 — `new SimpleDateFormat()` in getters | High |
| `//TODO` on DFExceptionType | `HTTPHandler.java` line 111 — `throw new DFException(DFExceptionType.CONNECTION_ERROR); //TODO` | Medium |
| `isOurDeduct` property commented-out in `HTTPHandler` | `HTTPHandler.java` line 98: `//response.setNostroCountry(...)` | Low |
| Spring XML IoC (no Spring Boot) | `dfapiInvoker.xml`, `httpConfig.xml`, `jmsConfig.xml` | Medium |
| `daysToSettle` commented-out in `HTTPHandler` | `HTTPHandler.java` line 68: `//requestObj.setDaysToSettle(...)` | Medium — skipping a required Dodd-Frank field |

---

## 5. Gen-3 Migration Recommendations

1. **Replace Apache Axis with Apache CXF or Jakarta EE JAX-WS**: Regenerate WSDL stubs from `wsdl/DF.wsdl` using `wsdl2java` (CXF) targeting Java 11+
2. **Remove `TrustAllSSLSocketFactory`**: Configure proper TLS trust store with Citi's certificate chain
3. **Replace Log4j 1.x** with SLF4J + Log4j2 (already used in debit-api_API)
4. **Replace Spring XML** with Spring Boot auto-configuration; publish via GitHub Packages (workflow already present in `director-client_LIB` as a template)
5. **Thread-safe date handling**: Replace `SimpleDateFormat` with `java.time.DateTimeFormatter` (thread-safe)
6. **Restore commented-out fields**: Evaluate `daysToSettle`, `nostroCountry`, `beneDeductFeeType` — may be required by current Dodd-Frank rules
7. **JMS modernisation**: Replace IBM MQ 7.x/proprietary `MQJMS` with IBM MQ Jakarta Messaging 3.0 client
8. **Move configuration to Azure App Configuration**: Remove endpoint URLs and queue names from committed properties files

---

## 6. Code Quality Risks

| Risk | Impact |
|---|---|
| `TrustAllSSLSocketFactory` in production classpath | MITM attack on Citi DFAPI connection; disclosure data interception |
| `daysToSettle` not set in `HTTPHandler` (line 68 commented out) | Dodd-Frank disclosure may be non-compliant if settlement days are required |
| `SimpleDateFormat` thread-safety | Incorrect dates in requests under concurrent load; regulatory disclosure dates would be wrong |
| Silent `ParseException` swallowing in `HTTPHandler` (lines 100–105) | Partially populated response returned without exception; callers cannot detect failure |
| IBM MQ static IP | Operations failure if MQ host changes |
