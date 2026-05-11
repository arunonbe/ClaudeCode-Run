# pos-connector_LIB — Enterprise Architect View

## 1. Architectural Role and Classification

`pos-connector_LIB` occupies the **Card-Present Connectivity** layer within Onbe's prepaid payments platform. It is classified as a **legacy integration adapter** — a thin, protocol-translation layer bridging proprietary ISO 8583 POS network messaging with the Onbe platform's internal service architecture.

From an enterprise architecture standpoint, this component sits at the **boundary of Onbe's Cardholder Data Environment (CDE)**. ISO 8583 messages flowing through it may carry PAN and other CHD, placing this component firmly within PCI DSS scope.

## 2. Position in Enterprise Context

```
[POS Terminals / Acquirer Network]
           |
           | ISO 8583 TCP/IP
           |
    [pos-connector_LIB]         <-- THIS COMPONENT (CDE boundary)
           |
           | JNDI DataSource
           |
    [EcountCore Database]       <-- ecount platform core DB
           |
    [Onbe Prepaid Platform]
```

The connector acts as an inbound integration point for FDR (First Data Resources) POS host traffic. It is the only component in the observed codebase that uses jPOS, an ISO 8583 toolkit, making it the **sole owner** of the card-present transaction protocol surface.

## 3. Technology Stack Assessment

| Dimension | Current State | Target State Gap |
|---|---|---|
| Framework | Spring 1.2.7 (2006) | Spring Boot 3.x (managed by `prepaid-parent_PARENT`) |
| ISO 8583 library | jPOS 1.5.2 (2008) | jPOS 2.x or switch to modern ISO 8583 library |
| Servlet spec | Java EE 2.4 (2003) | Jakarta EE 10 / Spring Boot embedded |
| Build paradigm | Standalone WAR on Tomcat | Spring Boot fat JAR or containerized service |
| Deployment model | Manual WAR copy | CI/CD with GitHub Actions + container registry |

The technology debt in this component is extreme by enterprise standards — the Spring version used (1.2.7) predates Spring's modern DI model. This component appears to be a direct carry-over from a pre-Onbe legacy system (note the `com.ecount.web` package namespace and FDR-specific network addresses).

## 4. Integration Patterns

The component implements two integration patterns:
1. **Long-running connection adapter**: Maintains a persistent outbound TCP session to the payment host. This pattern is common in payment processing but unusual in modern cloud-native architectures.
2. **Fire-and-ACK**: `POSMessageListener` receives a message, immediately acknowledges it, and relies on the platform to process it asynchronously (though no async dispatch is observed in current code — the ACK is sent inline).

## 5. Architectural Concerns and Modernization Path

### 5.1 Single Point of Failure
There is a single `ISOMUX` instance with a single TCP channel. There is no connection pooling, load balancing, or secondary host fallback. A host unreachability event causes a full outage of card-present authorization until the keepalive thread reconnects.

**Recommendation**: Introduce a primary/secondary host failover pattern, following VISA/Mastercard switching guidelines.

### 5.2 CDE Scope and Isolation
Because ISO 8583 messages can carry PANs, this component sits inside the CDE. It should be deployed in network segments isolated from non-CDE systems. The JNDI data source connecting to `EcountCoreDataSource` should be reviewed to confirm only CDE-approved data flows occur.

### 5.3 Observability Gap
No distributed tracing, no metrics exposure (no Micrometer/Spring Actuator), and Log4j 1.x. This makes it impossible to correlate POS transaction events with downstream platform events in a modern observability stack (Elastic/Datadog/OpenTelemetry).

### 5.4 No Test Coverage
No test classes exist in `src/test/`. For a CDE component processing financial messages, the absence of any automated test coverage is a compliance and quality concern.

## 6. PCI DSS Compliance Architecture Assessment

| PCI DSS Requirement | Status | Finding |
|---|---|---|
| Req 2.2 — Secure configurations | Fail | Hardcoded Windows path; no baseline hardening documented |
| Req 3.3 — Do not store SAD | Risk | `m.dump(System.out)` may log SAD fields |
| Req 4.2 — Encrypt CHD in transit | Unknown | No TLS configured in code; requires network-level verification |
| Req 6.3.3 — Patch known vulnerabilities | Fail | Log4j 1.2.8, Spring 1.2.7 have critical CVEs |
| Req 10 — Log and monitor | Partial | Log4j present but no SIEM integration documented |
| Req 11.3 — Penetration testing | Unknown | No pentest artifacts in repo |

## 7. Strategic Recommendations

1. **Migrate to modern jPOS 2.x with Spring Boot** parent, aligning with `prepaid-parent_PARENT` (version 6.0.13, Java 21).
2. **Containerize** and deploy via the same CI/CD pipeline used for other services.
3. **Implement TLS termination** at the channel layer using jPOS's `TLSChannel` or a network proxy.
4. **Replace `dump()` logging** with structured, field-level masked logging.
5. **Add host failover** configuration to eliminate the single-host SPOF.
