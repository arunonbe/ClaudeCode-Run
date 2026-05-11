# Business Analyst Report — xml-rpc_LIB

## Business Purpose

`xml-rpc_LIB` (`com.citi.prepaid.service.core:xmlrpc:3.1.3-SNAPSHOT`) is the **most critical shared infrastructure dependency in the entire Onbe Gen-1/Gen-2 estate**. It implements a proprietary XML-based remote procedure call (XML-RPC) framework that serves as the **internal service bus** connecting all Gen-1 and most Gen-2 application components. Every service-to-service call, every client API invocation, every job service interaction, and every VBScript operational command flows through this library's servlet and client infrastructure.

The library is not a deployable service; it is a JAR dependency. However, its role as the universal internal transport protocol makes its security posture, reliability, and maintenance status of estate-wide importance.

## Capabilities

The library provides two main layers:

### Server-Side (Servlet)
- **`XmlRPCServlet`**: An `HttpServlet` that receives HTTP POST requests, parses custom `RPC-Interface` and `RPC-Method` headers, looks up the corresponding Spring beans, unmarshals the XML request body into a typed input object, invokes the implementation method via reflection, and marshals the result back to XML.
- **`XmlRPCServletHelper`**: Contains the complete servlet dispatch algorithm: request parsing, Spring context lookup, bean resolution (with agent-specific override support), reflection-based method invocation, response marshalling, and thread-local context management.
- **`LoggingUtils`**: Thread-local logger support for the servlet.

### Client-Side
- **`XMLRPCClient`**: HTTP client wrapper using Apache Commons HttpClient (`MultiThreadedHttpConnectionManager`) with pooled connections (max 1000 per host, 1000 total). Provides `invokeXMLRPCCall()` with support for synchronous, asynchronous, and affiliate-scoped invocations.
- **`XMLRPCServiceLocator`**: Abstract service endpoint resolution (defers to Director Service for dynamic service address lookup).
- **`XMLRPCClientUtils`**: The actual HTTP POST implementation — marshals input to XML, POST to service URI, and unmarshals response.

### Utilities
- **`XmlRPCToObjectMapper`** / **`XmlRPCFromObjectMapper`**: Bidirectional serialization between Java objects and the proprietary XML-RPC wire format (not standard W3C XML-RPC).
- **`EcountXMLDocument*`**: DOM-based XML document manipulation layer.
- **`XPathFactoryAccessor`**: Thread-safe XPath factory access.

## Client and Cardholder Impact

**Maximum impact.** Every cardholder-affecting transaction in the Gen-1 platform passes through this library:
- Card account creation, card loading, balance inquiry.
- ACH origination and return processing.
- Cardholder profile updates (including SSN, DOB).
- Job service batch file processing.
- IVR cardholder authentication.
- Client API requests from all client portals.

A defect, security vulnerability, or availability failure in `xml-rpc_LIB` affects the entire Gen-1/Gen-2 cardholder-facing platform simultaneously.

## Business Rules in Code

- Agent-specific bean override: If a Spring bean named `{Interface}.{Method}.Impl.{AgentName}` exists, it takes precedence over `{Interface}.{Method}.Impl`. This enables per-agent (per-bank) business logic customization without code branching.
- Global request ID propagation: The `RPC-Global-Request-ID` HTTP header is threaded through all service calls for end-to-end transaction tracing.
- Request context binding: Agent name, program ID, global request ID, and SASI context are bound to a thread-local `RequestContext` for the duration of each RPC invocation.
- Async execution flag: Callers can request asynchronous execution with a transaction ID (`asyncExecution=true`, `txId`).

## Regulatory Obligations

- **PCI DSS Req. 6.3**: All components that process cardholder data must be protected against known vulnerabilities. The XML-RPC library uses Apache Commons HttpClient 3.x (EOL), which has known CVEs. Upgrading this library requires coordinated changes across the entire estate.
- **PCI DSS Req. 6.4**: The servlet dispatches to any Spring bean by name from the HTTP header — there is no allowlist of permitted interface/method combinations, creating an unauthorized function invocation risk.
- **Reg E / NACHA**: Any transport failure in the RPC layer affecting ACH or payment processing constitutes a potential Reg E error requiring investigation and potential remediation.
- **GLBA**: The RPC context propagates agent and program identifiers that govern access to cardholder data. Corruption of this context could cause data isolation failures.

## Key Business Risks

1. **Estate-wide blast radius**: A critical CVE or defect in this library affects every Gen-1/Gen-2 service simultaneously. There is no fallback transport.
2. **Unauthorized method invocation**: Any caller who can reach the XML-RPC servlet and knows the bean naming convention can invoke any Spring bean method — there is no authentication or authorization at the RPC dispatch layer.
3. **No allowlist for interfaces**: The `RPC-Interface` and `RPC-Method` headers from HTTP requests directly control which Spring bean is invoked. An attacker with network access to the servlet can call any registered interface/method.
4. **SNAPSHOT version in production**: `3.1.3-SNAPSHOT` is a non-release version, meaning the artifact can change without a version bump.
