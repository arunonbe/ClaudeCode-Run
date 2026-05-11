# Data Architect — webapp-common_LIB

## Data Stores
None. This is a compile-time library with no persistent storage, no database, no cache, and no message queue.

## Schema / Tables
Not applicable.

## Sensitive Data
- The `SSLLoginFilter` processes `HttpServletRequest` objects in memory, which may contain HTTP headers, query parameters, and form data from the calling application.
- Query parameters are read and re-appended to the redirect URL (`SSLLoginFilter.java:136–145`). If those parameters contain sensitive values (e.g., session tokens, account numbers), they would appear in the `Location` redirect header.
- The filter does not log request content, but does log the final redirect URL at DEBUG level (`SSLLoginFilter.java:109–113`). Log systems capturing DEBUG output could record redirect URLs containing query parameters.
- No cardholder data is handled directly by this library.

## Encryption
- The library's sole purpose is to enforce transport encryption (HTTPS redirect). It does not implement any cryptographic operations itself.
- At-rest encryption: not applicable (no persistence layer).

## Data Flow
```
Incoming HTTP Request
  |
  v
SSLLoginFilter.doFilter()
  |-- isSSLCheck() -> reads "check" init-param (web.xml)
  |-- checkSSLUrls() -> reads "no-ssl-urls" init-param, compares serverName
  |-- redirectSecureURL() -> reads: serverName, serverPort, requestURI, parameterNames/values
  |     WARNING: parameters re-assembled without URL encoding
  |-- response.sendRedirect(httpsUrl) -> HTTP 302 Location header
  |-- OR: chain.doFilter() -> pass-through
```

## Data Quality / Retention
Not applicable. No data is stored or retained.

## Compliance Gaps
1. **PCI DSS Req 4.2.1**: This filter is an HTTPS enforcement control. If it is not deployed (or `check` is set to `off`), cardholder data may flow over HTTP — a critical PCI DSS gap.
2. **Query string exposure in redirect**: Sensitive query parameters may appear in server access logs from the `Location` redirect header. Logs containing full redirect URLs should be treated as potentially sensitive under PCI DSS Req 10 (audit log protection).
3. **No TLS protocol/cipher enforcement**: The filter only checks whether the request `isSecure()`. It does not enforce minimum TLS version (TLS 1.2 per PCI DSS v4.0.1 Req 4.2.1) or cipher suite restrictions — those must be enforced at the servlet container level.
