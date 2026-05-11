# Enterprise Architect Report — dfapi-client_LIB

## 1. Platform Generation Classification

| Attribute | Value |
|---|---|
| Generation | Gen-1 / Gen-2 boundary — vintage 2006–2013 technology stack |
| Runtime | Java SE (library JAR); Spring XML IoC |
| Protocol (HTTP path) | SOAP via Apache Axis 1.4 (EOL 2012) |
| Protocol (JMS path) | IBM MQ via proprietary `MQJMS` wrapper |
| Code generation | Apache Axis WSDL2Java (2006), JAXB 2.1 (2013) |
| Modernization status | Minimal — no Spring Boot, no modern HTTP client |

---

## 2. Domain Context

**Domain**: Payments Compliance  
**Sub-domain**: Dodd-Frank Remittance Disclosure  
**Regulatory anchor**: Dodd-Frank Act Section 1073, implemented as Reg E §1005.31–§1005.36  
**External partner**: Citigroup / First National Bank of Omaha DFAPI

The library sits at the intersection of Onbe's international payment flows and US federal remittance disclosure requirements. Any international disbursement that qualifies as a "remittance transfer" under Reg E must obtain a disclosure quote via this (or equivalent) mechanism before execution.

---

## 3. Role in Platform

```
Onbe Disbursement Services
  │ Java method call
  ▼
DFAPIClientImpl.execute(QuoteRequest)
  │
  ├─ [HTTP] SOAP → Citigroup DFAPI (external)
  │           → Disclosure: fees, FX, delivery date
  │
  └─ [JMS]  XML → IBM MQ CPS.DF.RQ1
           → Disclosure: fees, FX, delivery date
```

Consumers: Any Onbe service that processes cross-border disbursements is expected to call this library to fulfill disclosure obligations before initiating the payment.

---

## 4. Dependencies

| Direction | System | Interface | Coupling |
|---|---|---|---|
| Outbound | Citi DFAPI (external) | SOAP over HTTPS (Apache Axis) | Tight — external vendor API |
| Outbound | IBM MQ | IBM MQ protocol | Tight — proprietary message queue |
| Inbound | Onbe disbursement services | Java library import | Loose (library) |
| Config | Spring XML | IoC container | Medium — Spring XML context required |
| Internal | `com.ecount.core.library.MQLib.MQJMS` | ECount proprietary MQ wrapper | Tight — internal platform library |

---

## 5. Architectural Patterns

| Pattern | Implementation | Quality |
|---|---|---|
| Strategy pattern | `ProtocolHandler` interface with `HTTPHandler` and `JMSHandler` implementations | Clean |
| Facade | `DFAPIClient` / `DFAPIClientImpl` hides transport selection | Good |
| Spring XML IoC | `dfapiInvoker.xml`, `httpConfig.xml`, `jmsConfig.xml` | Legacy — XML config, no annotations |
| JAXB object mapping | `QuoteRequest` / `QuoteResponse` with XML annotations | Good (but stale — 2013) |
| Apache Axis generated stubs | `DFAPIWSDLSOAPBindStub`, `DFAPIWSDLServLocator` | EOL pattern |

---

## 6. Current Status

| Aspect | Status |
|---|---|
| Last known change | Unknown — no workflow tags visible |
| Primary branch | `master` |
| Active transport | Both HTTP and JMS supported; runtime selection via Spring config |
| Test execution | Manual only (no CI test pipeline) |
| Security posture | Critical gaps (TrustAllSSLSocketFactory, Axis EOL, Log4j 1.x) |

---

## 7. Blockers for Modernization

| Blocker | Detail |
|---|---|
| Apache Axis 1.x EOL | Must replace with Apache CXF or JAX-WS RI; WSDL re-generation required |
| JAXB generated code from 2013 | Must regenerate from current DFAPI WSDL |
| `TrustAllSSLSocketFactory` | Must be removed; proper certificate chain required |
| Log4j 1.x | Must replace with SLF4J + Log4j2 |
| IBM MQ proprietary dependency (`MQJMS`) | Tightly coupled; migration to modern JMS 2.x or IBM MQ client required |
| Spring XML config | Should migrate to Spring Boot auto-configuration or annotation-based config |
| External Citi DFAPI dependency | Long-term risk; evaluate whether Onbe should migrate to an alternative remittance disclosure service |
