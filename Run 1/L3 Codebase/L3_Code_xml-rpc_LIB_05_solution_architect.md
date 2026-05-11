# Solution Architect Report — xml-rpc_LIB

## API Surface

The library defines a servlet (`XmlRPCServlet`) that is hosted inside consuming service WARs. The effective API surface per hosted service:

- **Endpoint**: Any URL mapped to `XmlRPCServlet` in the hosting WAR's web.xml.
- **Protocol**: HTTP POST with headers `RPC-Interface`, `RPC-Method`, `RPC-Agent`, `RPC-Affiliate`, `RPC-Global-Request-ID`, `RPC-TxID`, `RPC-Context`, `RPC-SASI-Context`.
- **Content-Type**: `application/x-mapxml` (proprietary).
- **Body**: Proprietary XML serialization of the input object.
- **GET support**: `doGet()` delegates to `doPost()` — the servlet accepts GET requests.

The client-side (`XMLRPCClient`) makes HTTP POST calls to service URIs resolved via `XMLRPCServiceLocator` (Director Service).

## Security Posture

**Critically weak at the authorization layer.** The servlet dispatches to any Spring bean based solely on the `RPC-Interface` and `RPC-Method` HTTP headers, with no access control, no authentication, and no allowlist of permitted interface/method combinations.

## Critical Vulnerabilities with File:Line Citations

| Severity | Finding | File:Line |
|----------|---------|-----------|
| **CRITICAL** | No authentication or authorization on RPC dispatch — any caller with network access can invoke any registered Spring bean method | `XmlRPCServletHelper.java:230–341` (`processRequest()` — no auth check) |
| **CRITICAL** | `RPC-Interface` and `RPC-Method` headers directly control which Spring bean is invoked — no allowlist | `XmlRPCServletHelper.java:270–278` (bean key construction from HTTP headers) |
| **HIGH** | `XmlRPCServlet.doGet()` delegates to `doPost()` — GET requests are treated as RPC invocations | `XmlRPCServlet.java:84–88` |
| **HIGH** | Commons HttpClient 3.x does not verify SSL hostname by default (CVE-2012-5783) — outbound RPC over HTTPS is vulnerable to MITM | `XMLRPCClient.java:36–43` (static `HttpClient` initialization) |
| **HIGH** | Connection pool of 1000 connections per host — resource exhaustion risk if targeted | `XMLRPCClient.java:39–40` |
| **HIGH** | Full request and response objects logged at DEBUG level including PII | `XmlRPCServletHelper.java:280–285`, `309–323` |
| **MEDIUM** | Reflection-based method invocation (`Method.invoke()`) with no method signature validation | `XmlRPCServletHelper.java:479–520` (`invokeImpl()`) |
| **MEDIUM** | `IOUtils.toString(istream)` without charset specification in `readFullInputStream()` — platform-default encoding used | `XmlRPCServletHelper.java:142` |
| **MEDIUM** | SNAPSHOT version in production — non-deterministic artifact resolution | `pom.xml:14` (`<version>3.1.3-SNAPSHOT</version>`) |
| **LOW** | `agentName` and `agentAffiliate` are passed from HTTP headers to Spring bean context without sanitization | `XmlRPCServletHelper.java:239–243` |

## Detailed Finding: Unauthorized Function Invocation

The core dispatch algorithm in `XmlRPCServletHelper.processRequest()` constructs Spring bean names directly from HTTP request headers:

```java
// XmlRPCServletHelper.java:270–278
final StringBuilder inputObjectLookupKey = new StringBuilder(req.getInterfaceName());
inputObjectLookupKey.append('.').append(req.getMethodName()).append(".Input");

final StringBuilder implObjectLookupKey = new StringBuilder(req.getInterfaceName());
implObjectLookupKey.append('.').append(req.getMethodName()).append(".Impl");
```

An attacker who can send HTTP POST requests to any `XmlRPCServlet`-mapped URL with forged `RPC-Interface` and `RPC-Method` headers can invoke any Spring bean in the application context that follows the naming convention `{X}.{Y}.Impl`. This includes:
- Data access objects that read/write cardholder data.
- Service methods that initiate financial transactions.
- Administrative operations (card blocking, account closure, SSN update).

The only mitigating control is network-level access restriction (firewall rules preventing external access to the RPC endpoint). If that firewall is bypassed, every service in the estate is fully compromised.

## Detailed Finding: Commons HttpClient SSL Bypass

`XMLRPCClient.java` line 43 creates a shared static `HttpClient`:
```java
httpClient = new HttpClient(connectionManager);
```

Apache Commons HttpClient 3.x (CVE-2012-5783) does not verify SSL certificate hostnames by default. All HTTPS-based outbound RPC calls are susceptible to man-in-the-middle attacks where the attacker presents any valid SSL certificate for any hostname. No `SSLSocketFactory` with hostname verification is configured.

## Technical Debt

- **Replace Commons HttpClient 3.x with Apache HttpClient 5.x** (or Spring's `RestTemplate` / `WebClient`): API-breaking change requiring updates to `XMLRPCClientUtils` and `XMLRPCClient`.
- **Add authentication to XmlRPCServlet**: Implement at minimum HMAC-signature verification or mTLS on the RPC channel. This requires protocol changes across all consumers.
- **Implement interface/method allowlist**: Maintain a registry of permitted `{Interface}.{Method}` combinations; reject any request not in the allowlist.
- **Remove doGet() delegation**: RPC endpoints should accept POST only; GET should return 405 Method Not Allowed.
- **Release SNAPSHOT version**: Publish `3.1.3` as a GA release to ensure artifact immutability.
- **Charset specification**: Fix `IOUtils.toString(istream)` to `IOUtils.toString(istream, StandardCharsets.UTF_8)`.
- **Disable DEBUG payload logging in production**: Add `@SensitiveData` annotation or a log-masking layer to prevent PII appearing in DEBUG-level logs.
- **Virtual thread compatibility**: Replace `ThreadLocalLogger` and `ThreadLocalStorage` patterns with structured context objects if Java 21 virtual threads are adopted.
- **Enforce TLS 1.2+**: Configure the HttpClient with a custom `SSLSocketFactory` that enforces TLS 1.2 minimum and validates hostname.
